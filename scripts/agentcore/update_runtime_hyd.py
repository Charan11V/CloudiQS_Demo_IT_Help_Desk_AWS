#!/usr/bin/env python3
"""Package CodeZip and update the existing Hyderabad AgentCore Runtime (fast path)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from common import AGENT_NAME, REGION, RUNTIME_DIR, boto_session, load_state, save_state
from package_codezip import ZIP_PATH, main as package_main
from deploy_agent import wait_runtime, ensure_endpoint


def main() -> int:
    rc = package_main()
    if rc != 0:
        return rc
    state = load_state()
    account = state["account_id"]
    bucket = state["code_bucket"]
    runtime_id = state["agent_runtime_id"]
    role_arn = state["role_arn"]
    region = state.get("region") or REGION
    s3 = boto_session().client("s3", region_name=region)
    version = (RUNTIME_DIR / "VERSION").read_text(encoding="utf-8").strip()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    key = f"{AGENT_NAME}/v{version}-{stamp}/deployment_package.zip"
    latest = f"{AGENT_NAME}/deployment_package.zip"
    print(f"Uploading s3://{bucket}/{key}")
    s3.upload_file(str(ZIP_PATH), bucket, key, ExtraArgs={"ExpectedBucketOwner": account})
    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": key},
        Key=latest,
        ExpectedBucketOwner=account,
    )
    control = boto_session().client("bedrock-agentcore-control", region_name=region)
    prev = state.get("code_prefix")
    prev_versioned = state.get("last_versioned_prefix") or prev
    control.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": bucket, "prefix": latest}},
                "runtime": "PYTHON_3_13",
                "entryPoint": ["main.py"],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        environmentVariables={
            "AWS_REGION": region,
            "AWS_DEFAULT_REGION": region,
            "OPENAI_BASE_URL": state.get("openai_base_url", "https://api.groq.com/openai/v1"),
            "OPENAI_MODEL_ID": state.get("openai_model_id", "openai/gpt-oss-20b"),
            "OPENAI_API_KEY_SSM": "/cloudiqs-demo/OPENAI_API_KEY",
            "TOOL_BRIDGE_SECRET_SSM": "/cloudiqs-demo/TOOL_BRIDGE_SECRET",
            "LOG_LEVEL": "INFO",
        },
        description="HELIO Strands + Groq GPT-OSS-20B in ap-south-2",
    )
    wait_runtime(control, runtime_id)
    ensure_endpoint(control, runtime_id)
    got = control.get_agent_runtime(agentRuntimeId=runtime_id)
    arn = got.get("agentRuntimeArn") or state["agent_runtime_arn"]
    versions = state.get("versions") or []
    versions.append(
        {
            "runtime_id": runtime_id,
            "arn": arn,
            "prefix": key,
            "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": version,
        }
    )
    state.update(
        {
            "previous_code_prefix": prev,
            "code_prefix": latest,
            "previous_versioned_prefix": prev_versioned,
            "last_versioned_prefix": key,
            "agent_runtime_arn": arn,
            "versions": versions[-10:],
        }
    )
    save_state(state)
    print(__import__("json").dumps({"arn": arn, "version": version, "prefix": key}, indent=2))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
