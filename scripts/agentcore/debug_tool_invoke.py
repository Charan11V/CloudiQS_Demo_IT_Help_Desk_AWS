#!/usr/bin/env python3
import json
import time
import uuid

import boto3

from common import load_state


def main() -> int:
    state = load_state()
    arn = state["agent_runtime_arn"]
    region = state.get("region") or "ap-south-2"
    ssm = boto3.client("ssm", region_name="us-east-1")
    iid = "i-0c506bd86c3d0ccd9"
    create_cmd = (
        "docker exec compose-agent-api-1 python -c "
        "\"from app.agentcore.bridge import create_bridge_session; import uuid; "
        "rid='e2e-run-'+uuid.uuid4().hex[:8]; "
        "print(create_bridge_session(bearer_token='northstar-asha', tenant_id='northstar', "
        "user_id='northstar-EMP-0001', role='employee', session_id='e2e-'+uuid.uuid4().hex[:8], "
        "run_id=rid, ttl_seconds=600)+' '+rid)\""
    )
    resp = ssm.send_command(
        InstanceIds=[iid],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [create_cmd]},
    )
    cid = resp["Command"]["CommandId"]
    token = run_id = None
    for _ in range(30):
        time.sleep(2)
        inv = ssm.get_command_invocation(CommandId=cid, InstanceId=iid)
        if inv["Status"] not in {"Success", "Failed", "Cancelled", "TimedOut"}:
            continue
        print("CREATE_STATUS", inv["Status"])
        print("OUT", inv.get("StandardOutputContent"))
        print("ERR", (inv.get("StandardErrorContent") or "")[-800:])
        if inv["Status"] != "Success":
            return 1
        parts = (inv.get("StandardOutputContent") or "").strip().splitlines()[-1].split()
        token, run_id = parts[0], parts[1]
        break
    print("token_len", len(token), "run", run_id)

    bridge = "http://ec2-3-80-12-216.compute-1.amazonaws.com/api-backend/internal/agentcore/tools"
    payload = {
        "prompt": "Call get_my_identity tool then say DONE",
        "actor": {
            "tenant_id": "northstar",
            "user_id": "northstar-EMP-0001",
            "role": "employee",
            "session_id": "e2e",
        },
        "bridge": {"url": bridge, "token": token},
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
    print("RAW", raw[:2500])
    return 0


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
