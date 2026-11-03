#!/usr/bin/env python3
"""
Unified HELIO ops for AgentCore-separated deploys.

Commands:
  dev                 Local Docker with GPT-OSS-20B (AgentCore disabled)
  deploy-agent        Deploy/update only AgentCore CodeZip
  deploy-web          Fast-update frontend on existing EC2
  deploy-all          Agent + web (+ agent-api bridge wiring via fast_deploy)
  status              Show versions / health
  logs                Tail AgentCore CloudWatch logs
  rollback            Previous AgentCore CodeZip
  destroy-agentcore   Remove AgentCore resources only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from common import (
    AGENT_NAME,
    REGION,
    ROOT,
    SSM_PREFIX,
    boto_session,
    ensure_path,
    load_state,
    run,
)


def cmd_dev(_: argparse.Namespace) -> int:
    ensure_path()
    run(["docker", "compose", "up", "--build", "-d"], cwd=ROOT)
    print("Local stack up. AgentCore disabled locally (MODEL_PROVIDER from .env).")
    print("UI: http://127.0.0.1:3000  agent: http://127.0.0.1:8001/health/ready")
    return 0


def cmd_deploy_agent(_: argparse.Namespace) -> int:
    from deploy_agent import main as deploy_main

    return deploy_main()


def cmd_deploy_web(_: argparse.Namespace) -> int:
    return run(
        [sys.executable, str(ROOT / "scripts" / "aws" / "fast_deploy.py"), "--service", "web"],
        check=False,
    ).returncode


def cmd_deploy_all(_: argparse.Namespace) -> int:
    rc = cmd_deploy_agent(_)
    if rc != 0:
        return rc
    # Patch agent-api env on EC2 with AgentCore SSM values, then rebuild agent+web quickly.
    patch = run(
        [sys.executable, str(Path(__file__).resolve().parent / "patch_ec2_agentcore_env.py")],
        check=False,
    )
    if patch.returncode != 0:
        print("WARNING: EC2 env patch failed — apply SSM values manually if needed")
    return run(
        [sys.executable, str(ROOT / "scripts" / "aws" / "fast_deploy.py"), "--service", "all"],
        check=False,
    ).returncode


def cmd_status(_: argparse.Namespace) -> int:
    state = load_state()
    control = boto_session().client("bedrock-agentcore-control")
    out = {
        "region": REGION,
        "state_file": str(Path(__file__).resolve().parents[2] / "deploy" / "agentcore" / "state.json"),
        "local_state": {
            "agent_runtime_id": state.get("agent_runtime_id"),
            "agent_runtime_arn": state.get("agent_runtime_arn"),
            "code_prefix": state.get("code_prefix"),
            "previous_code_prefix": state.get("previous_code_prefix"),
            "versions": state.get("versions", [])[-3:],
        },
    }
    rid = state.get("agent_runtime_id")
    if rid:
        try:
            out["runtime"] = control.get_agent_runtime(agentRuntimeId=rid)
        except Exception as exc:
            out["runtime_error"] = str(exc)
    try:
        ssm = boto_session().client("ssm")
        names = [
            f"{SSM_PREFIX}/AGENTCORE_ENABLED",
            f"{SSM_PREFIX}/AGENTCORE_RUNTIME_ARN",
            f"{SSM_PREFIX}/TOOL_BRIDGE_PUBLIC_URL",
            f"{SSM_PREFIX}/MODEL_PROVIDER",
            f"{SSM_PREFIX}/OPENAI_MODEL_ID",
        ]
        params = ssm.get_parameters(Names=names, WithDecryption=False).get("Parameters") or []
        out["ssm"] = {p["Name"]: p["Value"] for p in params}
    except Exception as exc:
        out["ssm_error"] = str(exc)
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_logs(_: argparse.Namespace) -> int:
    state = load_state()
    logs = boto_session().client("logs")
    patterns = [
        f"/aws/bedrock-agentcore/runtimes/{AGENT_NAME}",
        f"/aws/bedrock-agentcore/runtimes/{state.get('agent_runtime_id', AGENT_NAME)}",
    ]
    # Discover matching groups
    groups = []
    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate(logGroupNamePrefix="/aws/bedrock-agentcore/runtimes/"):
        for g in page.get("logGroups") or []:
            name = g["logGroupName"]
            if AGENT_NAME in name or (state.get("agent_runtime_id") or "") in name:
                groups.append(name)
    if not groups:
        # try exact patterns
        groups = patterns
    for g in groups[:3]:
        print(f"===== {g} =====")
        try:
            streams = logs.describe_log_streams(
                logGroupName=g, orderBy="LastEventTime", descending=True, limit=3
            ).get("logStreams") or []
            for st in streams:
                sn = st["logStreamName"]
                print(f"--- stream {sn} ---")
                events = logs.get_log_events(logGroupName=g, logStreamName=sn, limit=40)
                for e in events.get("events") or []:
                    msg = e.get("message", "")
                    # Redact obvious key patterns
                    if "api_key" in msg.lower() or "sk-" in msg:
                        msg = "[redacted]"
                    print(msg)
        except Exception as exc:
            print(f"log read error: {exc}")
    return 0


def cmd_rollback(_: argparse.Namespace) -> int:
    from rollback import main as rollback_main

    return rollback_main()


def cmd_destroy(args: argparse.Namespace) -> int:
    from destroy_agentcore import main as destroy_main

    sys.argv = ["destroy_agentcore.py", f"--confirm={args.confirm}"]
    return destroy_main()


def main() -> int:
    ensure_path()
    parser = argparse.ArgumentParser(description="HELIO AgentCore ops")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dev")
    sub.add_parser("deploy-agent")
    sub.add_parser("deploy-web")
    sub.add_parser("deploy-all")
    sub.add_parser("status")
    sub.add_parser("logs")
    sub.add_parser("rollback")
    p_destroy = sub.add_parser("destroy-agentcore")
    p_destroy.add_argument("--confirm", default="")
    args = parser.parse_args()
    dispatch = {
        "dev": cmd_dev,
        "deploy-agent": cmd_deploy_agent,
        "deploy-web": cmd_deploy_web,
        "deploy-all": cmd_deploy_all,
        "status": cmd_status,
        "logs": cmd_logs,
        "rollback": cmd_rollback,
        "destroy-agentcore": cmd_destroy,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
