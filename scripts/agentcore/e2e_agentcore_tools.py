#!/usr/bin/env python3
"""Direct AgentCore invoke with a live tool-bridge session created on EC2 agent-api."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import boto3

from common import load_state

OUT = Path(__file__).resolve().parents[2] / "deploy" / "agentcore" / "e2e_tools_results.json"


def main() -> int:
    state = load_state()
    arn = state["agent_runtime_arn"]
    region = state.get("region") or "ap-south-2"
    ssm = boto3.client("ssm", region_name="us-east-1")
    iid = "i-0c506bd86c3d0ccd9"

    # Create an ephemeral bridge session inside the running agent-api process namespace
    # by hitting a tiny python snippet via docker exec.
    create_cmd = r'''
docker exec compose-agent-api-1 python - <<'PY'
import json
from app.agentcore.bridge import create_bridge_session
token = create_bridge_session(
  bearer_token="northstar-asha",
  tenant_id="northstar",
  user_id="northstar-EMP-0001",
  role="employee",
  session_id="e2e-session-"+__import__("uuid").uuid4().hex[:8],
  run_id="e2e-run-"+__import__("uuid").uuid4().hex[:8],
  ttl_seconds=600,
)
print(token)
PY
'''
    # docker exec -i needed for heredoc; use python -c instead for reliability
    create_cmd = '''docker exec compose-agent-api-1 python -c "from app.agentcore.bridge import create_bridge_session; import uuid; rid='e2e-run-'+uuid.uuid4().hex[:8]; print(create_bridge_session(bearer_token='northstar-asha', tenant_id='northstar', user_id='northstar-EMP-0001', role='employee', session_id='e2e-'+uuid.uuid4().hex[:8], run_id=rid, ttl_seconds=600)+' '+rid)"'''

    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [create_cmd]},
    )
    cid = resp["Command"]["CommandId"]
    token = None
    run_id = None
    for _ in range(30):
        time.sleep(2)
        inv = ssm.get_command_invocation(CommandId=cid, InstanceId=iid)
        if inv["Status"] in {"Success", "Failed", "Cancelled", "TimedOut"}:
            out = (inv.get("StandardOutputContent") or "").strip().splitlines()
            err = inv.get("StandardErrorContent") or ""
            if inv["Status"] != "Success" or not out:
                print("bridge session create failed", inv["Status"], out, err[-500:])
                return 1
            parts = out[-1].split()
            token, run_id = parts[0], parts[1]
            break
    assert token and run_id

    bridge_url = "http://ec2-3-80-12-216.compute-1.amazonaws.com/api-backend/internal/agentcore/tools"
    payload = {
        "prompt": "Use tools to get my identity and list my VPN sessions, then reply with a short summary.",
        "actor": {
            "tenant_id": "northstar",
            "user_id": "northstar-EMP-0001",
            "role": "employee",
            "session_id": "e2e-session",
        },
        "bridge": {"url": bridge_url, "token": token},
        "run_id": run_id,
    }
    client = boto3.client("bedrock-agentcore", region_name=region)
    sid = ("e2e-" + uuid.uuid4().hex + "-" + uuid.uuid4().hex)[:64]
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=sid,
        payload=json.dumps(payload).encode("utf-8"),
        qualifier="DEFAULT",
    )
    chunks = []
    for chunk in response.get("response", []):
        if isinstance(chunk, (bytes, bytearray)):
            chunks.append(bytes(chunk))
        elif isinstance(chunk, dict) and "chunk" in chunk:
            part = chunk["chunk"]
            if isinstance(part, dict) and "bytes" in part:
                chunks.append(part["bytes"])
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    data = json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}
    tool_events = data.get("tool_events") or []
    result = {
        "ok": bool(data.get("ok")),
        "verified_live": bool(data.get("verified_live")),
        "provider": data.get("provider"),
        "tool_calls": data.get("tool_calls"),
        "tool_events": tool_events,
        "headline": data.get("headline"),
        "summary": (data.get("plain_language_summary") or "")[:400],
        "pass_chat": bool(data.get("ok") and data.get("verified_live")),
        "pass_tools": any(bool(t.get("ok")) for t in tool_events) if tool_events else False,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass_chat"] and result["pass_tools"] else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
