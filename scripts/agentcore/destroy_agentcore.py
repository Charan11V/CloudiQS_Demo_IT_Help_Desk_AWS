#!/usr/bin/env python3
"""Remove AgentCore resources created by HELIO deploy — does NOT destroy EC2/app data."""
from __future__ import annotations

import sys
from pathlib import Path

from common import AGENT_NAME, CODE_BUCKET, ROLE_NAME, SSM_PREFIX, boto_session, load_state, save_state


def main() -> int:
    confirm = ""
    for arg in sys.argv[1:]:
        if arg.startswith("--confirm="):
            confirm = arg.split("=", 1)[1]
    if confirm != "DESTROY_AGENTCORE":
        print("Refused: pass --confirm=DESTROY_AGENTCORE")
        return 1

    state = load_state()
    control = boto_session().client("bedrock-agentcore-control")
    s3 = boto_session().client("s3")
    ssm = boto_session().client("ssm")
    iam = boto_session().client("iam")

    runtime_id = state.get("agent_runtime_id")
    if not runtime_id:
        try:
            for item in control.list_agent_runtimes().get("agentRuntimes") or []:
                if item.get("agentRuntimeName") == AGENT_NAME:
                    runtime_id = item.get("agentRuntimeId")
                    break
        except Exception as exc:
            print(f"list note: {exc}")

    if runtime_id:
        try:
            control.delete_agent_runtime(agentRuntimeId=runtime_id)
            print(f"Deleted runtime {runtime_id}")
        except Exception as exc:
            print(f"delete runtime: {exc}")

    # Clear SSM AgentCore pointers (keep OPENAI key / app secrets)
    for name in (
        f"{SSM_PREFIX}/AGENTCORE_RUNTIME_ARN",
        f"{SSM_PREFIX}/AGENTCORE_ENABLED",
        f"{SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL",
        f"{SSM_PREFIX}/AGENTCORE_QUALIFIER",
        f"{SSM_PREFIX}/AGENTCORE_REGION",
    ):
        try:
            ssm.delete_parameter(Name=name)
            print(f"Deleted SSM {name}")
        except Exception:
            pass

    # Delete code objects under agent prefix (keep bucket)
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=CODE_BUCKET, Prefix=f"{AGENT_NAME}/"):
            objs = [{"Key": o["Key"]} for o in page.get("Contents") or []]
            if objs:
                s3.delete_objects(Bucket=CODE_BUCKET, Delete={"Objects": objs})
                print(f"Deleted {len(objs)} S3 objects")
    except Exception as exc:
        print(f"S3 cleanup note: {exc}")

    try:
        iam.delete_role_policy(RoleName=ROLE_NAME, PolicyName="HelioAgentCoreRuntimeInline")
        iam.delete_role(RoleName=ROLE_NAME)
        print(f"Deleted role {ROLE_NAME}")
    except Exception as exc:
        print(f"role cleanup note: {exc}")

    try:
        iam.delete_role_policy(RoleName="CloudiQSDemoRuntimeRole", PolicyName="HelioAgentCoreInvoke")
    except Exception:
        pass

    state["destroyed"] = True
    state.pop("agent_runtime_id", None)
    state.pop("agent_runtime_arn", None)
    save_state(state)
    print("AgentCore teardown complete. EC2 / SQLite / ECR app stack untouched.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
