#!/usr/bin/env python3
"""Push compose + seed assets and start services on the demo EC2 via SSM."""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
REGION = os.environ.get("AWS_REGION", "us-east-1")
PROFILE = os.environ.get("AWS_PROFILE", "cloudiqs-demo-deployer")
PREFIX = "/cloudiqs-demo"


def session() -> boto3.Session:
    # Prefer explicit env credentials (e.g. aws configure export-credentials after aws login).
    # Root login sessions cannot AssumeRole into CloudiQSDemoDeployRole.
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return boto3.Session(region_name=REGION)
    try:
        return boto3.Session(profile_name=PROFILE, region_name=REGION)
    except Exception:
        return boto3.Session(region_name=REGION)


def stack_outputs(cfn) -> dict:
    stacks = cfn.describe_stacks(StackName="CloudiQSDemoStack")["Stacks"]
    return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}


def get_param(ssm, name: str, default: str = "") -> str:
    try:
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    except ClientError:
        return default


def wait_cmd(ssm, cmd_id: str, instance_id: str) -> int:
    for _ in range(120):
        time.sleep(5)
        inv = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=instance_id)
        st = inv["Status"]
        if st in ("Success", "Cancelled", "TimedOut", "Failed"):
            print(inv.get("StandardOutputContent", ""))
            err = inv.get("StandardErrorContent", "")
            if err:
                print(err, file=sys.stderr)
            return 0 if st == "Success" else 1
    print("SSM command wait timeout", file=sys.stderr)
    return 1


def main() -> int:
    s = session()
    cfn = s.client("cloudformation")
    ssm = s.client("ssm")
    s3 = s.client("s3")
    sts = s.client("sts")

    outs = stack_outputs(cfn)
    iid = outs.get("InstanceId")
    bucket = outs.get("BackupBucketName")
    if not iid or not bucket:
        print("Missing stack outputs InstanceId/BackupBucketName", file=sys.stderr)
        return 1

    account = sts.get_caller_identity()["Account"]
    registry = f"{account}.dkr.ecr.{REGION}.amazonaws.com"
    tag = os.environ.get("IMAGE_TAG", "latest")

    # Upload compose + seed sqlite to S3 for the instance to pull
    compose = (ROOT / "compose.aws.yaml").read_bytes()
    s3.put_object(Bucket=bucket, Key="deploy/compose.aws.yaml", Body=compose)
    seed = ROOT / "cloudiqs_enterprise_demo_pack" / "data" / "canonical" / "enterprise.sqlite"
    if seed.exists():
        s3.upload_file(str(seed), bucket, "deploy/canonical/enterprise.sqlite")
    # Also upload pack knowledge lightly? runtime needs pack mount — upload tarball of pack data
    pack_runtime = ROOT / "cloudiqs_enterprise_demo_pack" / "data" / "runtime.sqlite"
    if pack_runtime.exists():
        s3.upload_file(str(pack_runtime), bucket, "deploy/runtime.sqlite")

    session_key = get_param(ssm, f"{PREFIX}/APP_SESSION_SIGNING_KEY", "REPLACE_AT_DEPLOY")
    demo_secret = get_param(ssm, f"{PREFIX}/DEMO_ACCESS_SECRET", "REPLACE_AT_DEPLOY")
    model = get_param(ssm, f"{PREFIX}/BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
    provider = get_param(ssm, f"{PREFIX}/MODEL_PROVIDER", "openai_compatible")
    openai_model = get_param(ssm, f"{PREFIX}/OPENAI_MODEL_ID", "openai/gpt-oss-20b")
    openai_base = get_param(ssm, f"{PREFIX}/OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    demo_now = get_param(ssm, f"{PREFIX}/DEMO_NOW", "2026-10-31T10:00:00Z")
    log_level = get_param(ssm, f"{PREFIX}/LOG_LEVEL", "INFO")

    if session_key == "REPLACE_AT_DEPLOY" or demo_secret == "REPLACE_AT_DEPLOY":
        print(
            "WARNING: SSM secrets still REPLACE_AT_DEPLOY. "
            "Generate SecureString values before public demos (see docs/AWS_DEPLOYMENT.md).",
            file=sys.stderr,
        )

    origin = ""
    # Prefer token from instance env (set at launch); leave blank if unknown
    commands = [
        # No -x: avoid leaking secrets into SSM command output
        "set -euo pipefail",
        "source /opt/cloudiqs-demo/env.sh || true",
        f"export AWS_REGION={REGION}",
        f"export BACKUP_BUCKET={bucket}",
        f"aws s3 cp s3://{bucket}/deploy/compose.aws.yaml /opt/cloudiqs-demo/compose/compose.aws.yaml",
        "mkdir -p /opt/cloudiqs-demo/data/canonical /opt/cloudiqs-demo/data/pack",
        f"aws s3 cp s3://{bucket}/deploy/canonical/enterprise.sqlite /opt/cloudiqs-demo/data/canonical/enterprise.sqlite || true",
        f"test -f /opt/cloudiqs-demo/data/runtime.sqlite || aws s3 cp s3://{bucket}/deploy/runtime.sqlite /opt/cloudiqs-demo/data/runtime.sqlite || cp /opt/cloudiqs-demo/data/canonical/enterprise.sqlite /opt/cloudiqs-demo/data/runtime.sqlite",
        "touch /opt/cloudiqs-demo/data/app.sqlite",
        # Minimal pack mount for agent-api (knowledge files optional)
        "mkdir -p /opt/cloudiqs-demo/data/pack/data",
        "ln -sfn /opt/cloudiqs-demo/data/canonical /opt/cloudiqs-demo/data/pack/data/canonical || true",
        f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {registry}",
        f"export ECR_WEB_IMAGE={registry}/cloudiqs-demo-web:{tag}",
        f"export ECR_AGENT_IMAGE={registry}/cloudiqs-demo-agent-api:{tag}",
        f"export ECR_MOCK_IMAGE={registry}/cloudiqs-demo-mock-api:{tag}",
        f"export MODEL_PROVIDER={provider}",
        f"export BEDROCK_MODEL_ID={model}",
        f"export OPENAI_MODEL_ID={openai_model}",
        f"export OPENAI_BASE_URL={openai_base}",
        f"export DEMO_NOW={demo_now}",
        f"export LOG_LEVEL={log_level}",
        f"export APP_SESSION_SIGNING_KEY='{session_key}'",
        f"export DEMO_ACCESS_SECRET='{demo_secret}'",
        "export DEMO_GATE_ENABLED=1",
        "export NEXT_PUBLIC_RUNTIME_BADGE=AWS",
        f"export NEXT_PUBLIC_OPENAI_MODEL_ID={openai_model}",
        f"export NEXT_PUBLIC_AWS_REGION={REGION}",
        f"export NEXT_PUBLIC_MODEL_PROVIDER={provider}",
        # Empty until CloudFront is enabled (unverified accounts cannot create CF distributions)
        "export ORIGIN_VERIFY_TOKEN=",
        "sed -i 's/^export ORIGIN_VERIFY_TOKEN=.*/export ORIGIN_VERIFY_TOKEN=/' /opt/cloudiqs-demo/env.sh || true",
        "cd /opt/cloudiqs-demo/compose",
        "docker compose -f compose.aws.yaml pull",
        "docker compose -f compose.aws.yaml up -d",
        "docker compose -f compose.aws.yaml ps",
        "sleep 8",
        "curl -sf http://127.0.0.1/api/health || true",
    ]

    print(f"Deploying to instance {iid} …")
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
        TimeoutSeconds=1800,
    )
    cmd_id = resp["Command"]["CommandId"]
    print("SSM CommandId:", cmd_id)
    rc = wait_cmd(ssm, cmd_id, iid)
    if rc == 0:
        print("CloudFront URL:", outs.get("CloudFrontUrl"))
        print("Remember demo access secret from SSM /cloudiqs-demo/DEMO_ACCESS_SECRET")
    return rc


if __name__ == "__main__":
    sys.exit(main())
