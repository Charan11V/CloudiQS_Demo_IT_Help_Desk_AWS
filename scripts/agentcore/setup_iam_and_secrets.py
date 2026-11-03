#!/usr/bin/env python3
"""Idempotent IAM role + SSM secrets for HELIO AgentCore (does not touch app DBs)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from common import (
    ACCOUNT_ID,
    AGENT_NAME,
    CODE_BUCKET,
    REGION,
    ROLE_NAME,
    SSM_PREFIX,
    boto_session,
    load_state,
    random_secret,
    read_dotenv_value,
    save_state,
)

TRUST = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AssumeRolePolicy",
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": ACCOUNT_ID},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:*"
                },
            },
        }
    ],
}

RUNTIME_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Logs",
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:PutResourcePolicy",
            ],
            "Resource": [
                f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:/aws/bedrock-agentcore/runtimes/*",
                f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:*",
            ],
        },
        {
            "Sid": "MetricsTraces",
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets",
                "cloudwatch:PutMetricData",
            ],
            "Resource": "*",
        },
        {
            "Sid": "S3CodeArtifact",
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:GetObjectVersion"],
            "Resource": [f"arn:aws:s3:::{CODE_BUCKET}/{AGENT_NAME}/*"],
        },
        {
            "Sid": "S3ListCodeBucket",
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{CODE_BUCKET}"],
            "Condition": {"StringLike": {"s3:prefix": [f"{AGENT_NAME}/*"]}},
        },
        {
            "Sid": "ReadHelioSecrets",
            "Effect": "Allow",
            "Action": ["ssm:GetParameter", "ssm:GetParameters"],
            "Resource": [
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/OPENAI_API_KEY",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/TOOL_BRIDGE_SECRET",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/OPENAI_BASE_URL",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/OPENAI_MODEL_ID",
            ],
        },
        {
            "Sid": "KmsDecryptSsmIfNeeded",
            "Effect": "Allow",
            "Action": ["kms:Decrypt"],
            "Resource": ["*"],
            "Condition": {
                "StringEquals": {"kms:ViaService": [f"ssm.{REGION}.amazonaws.com"]}
            },
        },
        {
            "Sid": "WorkloadToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
            ],
            "Resource": [
                f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:workload-identity-directory/default",
                f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:workload-identity-directory/default/workload-identity/{AGENT_NAME}-*",
            ],
        },
        # Intentionally NO bedrock:InvokeModel — account has no FM authorization; GPT-OSS stays on Groq.
    ],
}

EC2_INVOKE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "InvokeHelioAgentCore",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime",
                "bedrock-agentcore:InvokeAgentRuntimeWithBidirectionalStream",
            ],
            "Resource": [
                f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:runtime/{AGENT_NAME}-*",
                f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT_ID}:runtime/{AGENT_NAME}-*/runtime-endpoint/*",
            ],
        },
        {
            "Sid": "ReadAgentCoreConfig",
            "Effect": "Allow",
            "Action": ["ssm:GetParameter", "ssm:GetParameters"],
            "Resource": [
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/AGENTCORE_*",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/TOOL_BRIDGE_*",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/OPENAI_*",
                f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter{SSM_PREFIX}/MODEL_PROVIDER",
            ],
        },
    ],
}


def put_ssm(name: str, value: str, secure: bool = True, overwrite: bool = True) -> None:
    ssm = boto_session().client("ssm")
    kwargs = {
        "Name": name,
        "Value": value,
        "Type": "SecureString" if secure else "String",
        "Overwrite": overwrite,
    }
    ssm.put_parameter(**kwargs)
    print(f"SSM put {name} ({'SecureString' if secure else 'String'})")


def ensure_role() -> str:
    iam = boto_session().client("iam")
    role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
    try:
        iam.get_role(RoleName=ROLE_NAME)
        print(f"Role exists: {ROLE_NAME}")
        iam.update_assume_role_policy(
            RoleName=ROLE_NAME, PolicyDocument=json.dumps(TRUST)
        )
    except iam.exceptions.NoSuchEntityException:
        iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST),
            Description="HELIO AgentCore Runtime execution role (no Bedrock FM)",
            Tags=[
                {"Key": "Project", "Value": "CloudiQSDemo"},
                {"Key": "Component", "Value": "AgentCore"},
            ],
        )
        print(f"Created role {ROLE_NAME}")
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName="HelioAgentCoreRuntimeInline",
        PolicyDocument=json.dumps(RUNTIME_POLICY),
    )
    return role_arn


def ensure_ec2_invoke_policy() -> None:
    iam = boto_session().client("iam")
    role = "CloudiQSDemoRuntimeRole"
    try:
        iam.put_role_policy(
            RoleName=role,
            PolicyName="HelioAgentCoreInvoke",
            PolicyDocument=json.dumps(EC2_INVOKE_POLICY),
        )
        print(f"Attached HelioAgentCoreInvoke to {role}")
    except Exception as exc:
        print(f"WARNING: could not attach invoke policy to {role}: {exc}")


def ensure_bucket() -> None:
    s3 = boto_session().client("s3")
    try:
        s3.head_bucket(Bucket=CODE_BUCKET)
        print(f"Bucket exists: {CODE_BUCKET}")
    except Exception:
        kwargs = {"Bucket": CODE_BUCKET}
        if REGION != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": REGION}
        s3.create_bucket(**kwargs)
        s3.put_public_access_block(
            Bucket=CODE_BUCKET,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        print(f"Created bucket {CODE_BUCKET}")


def ensure_secrets() -> dict:
    ssm = boto_session().client("ssm")
    out = {}

    openai_key = read_dotenv_value("OPENAI_API_KEY") or read_dotenv_value("GROQ_API_KEY")
    if not openai_key:
        try:
            openai_key = ssm.get_parameter(
                Name=f"{SSM_PREFIX}/OPENAI_API_KEY", WithDecryption=True
            )["Parameter"]["Value"]
        except Exception:
            openai_key = ""
    if not openai_key:
        raise SystemExit(
            "OPENAI_API_KEY missing in .env and SSM — required for GPT-OSS-20B on Groq"
        )
    put_ssm(f"{SSM_PREFIX}/OPENAI_API_KEY", openai_key, secure=True)

    base_url = read_dotenv_value("OPENAI_BASE_URL") or "https://api.groq.com/openai/v1"
    model_id = read_dotenv_value("OPENAI_MODEL_ID") or "openai/gpt-oss-20b"
    put_ssm(f"{SSM_PREFIX}/OPENAI_BASE_URL", base_url, secure=False)
    put_ssm(f"{SSM_PREFIX}/OPENAI_MODEL_ID", model_id, secure=False)
    # Prefer openai_compatible for live GPT-OSS (Bedrock FM not authorized).
    put_ssm(f"{SSM_PREFIX}/MODEL_PROVIDER", "openai_compatible", secure=False)

    try:
        bridge_secret = ssm.get_parameter(
            Name=f"{SSM_PREFIX}/TOOL_BRIDGE_SECRET", WithDecryption=True
        )["Parameter"]["Value"]
    except Exception:
        bridge_secret = random_secret(48)
        put_ssm(f"{SSM_PREFIX}/TOOL_BRIDGE_SECRET", bridge_secret, secure=True)
    else:
        print("Reusing existing TOOL_BRIDGE_SECRET")

    out["openai_base_url"] = base_url
    out["openai_model_id"] = model_id
    out["tool_bridge_secret_set"] = True
    return out


def ensure_log_retention() -> None:
    logs = boto_session().client("logs")
    # Retention applied after runtime creates the group; also pre-create a parent-friendly group.
    group = f"/aws/bedrock-agentcore/runtimes/{AGENT_NAME}"
    try:
        logs.create_log_group(logGroupName=group)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    except Exception as exc:
        print(f"log group note: {exc}")
    try:
        logs.put_retention_policy(logGroupName=group, retentionInDays=7)
        print(f"Log retention 7d on {group}")
    except Exception as exc:
        print(f"retention note: {exc}")


def ensure_budget_note() -> None:
    print(
        "Budget alerts (CloudiQSDemo-Monthly) already exist — they notify, they do NOT hard-cap spend."
    )


def main() -> int:
    ensure_bucket()
    role_arn = ensure_role()
    secrets = ensure_secrets()
    ensure_ec2_invoke_policy()
    ensure_log_retention()
    ensure_budget_note()
    state = load_state()
    state.update(
        {
            "region": REGION,
            "account_id": ACCOUNT_ID,
            "role_arn": role_arn,
            "code_bucket": CODE_BUCKET,
            "agent_name": AGENT_NAME,
            **secrets,
        }
    )
    save_state(state)
    print(json.dumps({"role_arn": role_arn, "bucket": CODE_BUCKET}, indent=2))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
