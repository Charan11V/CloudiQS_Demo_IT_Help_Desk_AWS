#!/usr/bin/env python3
"""Rollback AgentCore Runtime to the previous CodeZip prefix."""
from __future__ import annotations

import sys
from pathlib import Path

from common import CODE_BUCKET, ROLE_NAME, boto_session, load_state, save_state
from deploy_agent import artifact, ensure_endpoint, put_runtime_ssm, wait_runtime


def main() -> int:
    state = load_state()
    runtime_id = state.get("agent_runtime_id")
    # Prefer versioned previous zip; fall back to previous_code_prefix.
    prev = state.get("previous_versioned_prefix") or state.get("previous_code_prefix")
    if not runtime_id or not prev:
        print("No previous_code_prefix recorded — deploy at least twice before rollback")
        return 1
    region = state.get("region") or "ap-south-2"
    bucket = state.get("code_bucket") or CODE_BUCKET
    role_arn = state.get("role_arn") or f"arn:aws:iam::{state.get('account_id')}:role/{ROLE_NAME}"
    control = boto_session().client("bedrock-agentcore-control", region_name=region)
    print(f"Rolling back {runtime_id} to s3://{bucket}/{prev}")
    kwargs = {
        "agentRuntimeId": runtime_id,
        "agentRuntimeArtifact": {
            "codeConfiguration": {
                "code": {"s3": {"bucket": bucket, "prefix": prev}},
                "runtime": "PYTHON_3_13",
                "entryPoint": ["main.py"],
            }
        },
        "roleArn": role_arn,
        "networkConfiguration": {"networkMode": "PUBLIC"},
        "protocolConfiguration": {"serverProtocol": "HTTP"},
        "environmentVariables": {
            "AWS_REGION": region,
            "AWS_DEFAULT_REGION": region,
            "OPENAI_BASE_URL": state.get("openai_base_url", "https://api.groq.com/openai/v1"),
            "OPENAI_MODEL_ID": state.get("openai_model_id", "openai/gpt-oss-20b"),
            "OPENAI_API_KEY_SSM": "/cloudiqs-demo/OPENAI_API_KEY",
            "TOOL_BRIDGE_SECRET_SSM": "/cloudiqs-demo/TOOL_BRIDGE_SECRET",
            "LOG_LEVEL": "INFO",
        },
        "description": "HELIO Strands + Groq GPT-OSS-20B (rollback)",
    }
    resp = control.update_agent_runtime(**kwargs)
    wait_runtime(control, runtime_id)
    ensure_endpoint(control, runtime_id)
    arn = resp.get("agentRuntimeArn") or state.get("agent_runtime_arn")
    # swap previous/current
    state["previous_code_prefix"] = state.get("code_prefix")
    state["code_prefix"] = prev
    state["agent_runtime_arn"] = arn
    save_state(state)
    put_runtime_ssm(arn)
    print(f"Rollback complete -> {prev}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
