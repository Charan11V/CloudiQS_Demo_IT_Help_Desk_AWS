#!/usr/bin/env python3
"""Diagnose tool-bridge: create session via docker exec, call public HTTPS bridge."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.request

import boto3

from common import DEMO_URL_DEFAULT, SSM_PREFIX


def main() -> int:
    ssm = boto3.client("ssm", region_name="us-east-1")
    secret = ssm.get_parameter(
        Name=f"{SSM_PREFIX}/TOOL_BRIDGE_SECRET", WithDecryption=True
    )["Parameter"]["Value"]
    print("secret_sha", hashlib.sha256(secret.encode()).hexdigest()[:12])

    iid = "i-0c506bd86c3d0ccd9"
    remote = (
        "docker exec compose-agent-api-1 printenv AGENTCORE_ENABLED; "
        "docker exec compose-agent-api-1 printenv TOOL_BRIDGE_PUBLIC_URL; "
        "docker exec compose-agent-api-1 python -c "
        "\"from app.agentcore.bridge import create_bridge_session; "
        "print('TOKEN=' + create_bridge_session("
        "bearer_token='northstar-asha', tenant_id='northstar', "
        "user_id='northstar-EMP-0001', role='employee', session_id='diag', "
        "run_id='diag-run', ttl_seconds=600))\""
    )
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [remote]},
    )
    cid = resp["Command"]["CommandId"]
    token = None
    for _ in range(40):
        time.sleep(2)
        inv = ssm.get_command_invocation(CommandId=cid, InstanceId=iid)
        if inv["Status"] not in {"Success", "Failed", "Cancelled", "TimedOut"}:
            continue
        print("CREATE_STATUS", inv["Status"])
        out = inv.get("StandardOutputContent") or ""
        err = inv.get("StandardErrorContent") or ""
        print(out[-1500:])
        if err:
            print("ERR", err[-800:])
        for line in out.splitlines():
            if line.startswith("TOKEN="):
                token = line.split("=", 1)[1].strip()
        break
    if not token:
        print("No token created")
        return 1

    body = json.dumps(
        {"arguments": {}, "run_id": "diag-run", "tool": "get_my_identity"},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    ts = str(int(time.time()))
    sig = hmac.new(
        secret.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()
    url = f"{DEMO_URL_DEFAULT.rstrip('/')}/api-backend/internal/agentcore/tools"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Helio-Bridge-Token": token,
            "X-Helio-Timestamp": ts,
            "X-Helio-Signature": sig,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("HTTP", resp.status, resp.read()[:900])
            return 0
    except Exception as e:
        if hasattr(e, "read"):
            print("HTTPERR", getattr(e, "code", None), e.read()[:900])
        else:
            print("ERR", e)
        return 1


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
