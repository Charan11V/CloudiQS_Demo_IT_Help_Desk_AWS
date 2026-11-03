#!/usr/bin/env python3
"""Integration probes for AgentCore + GPT-OSS + tool bridge (best-effort, non-destructive where possible)."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

from common import DEMO_URL_DEFAULT, REGION, boto_session, load_state, read_dotenv_value


def invoke_runtime(arn: str, payload: dict) -> dict:
    client = boto_session().client("bedrock-agentcore", region_name=REGION)
    sid = ("e2e-" + uuid.uuid4().hex + "-" + uuid.uuid4().hex)[:64]
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=sid,
        payload=json.dumps(payload).encode("utf-8"),
        qualifier="DEFAULT",
    )
    chunks = []
    for chunk in resp.get("response", []):
        if isinstance(chunk, (bytes, bytearray)):
            chunks.append(bytes(chunk))
        elif isinstance(chunk, dict) and "chunk" in chunk:
            part = chunk["chunk"]
            if isinstance(part, dict) and "bytes" in part:
                chunks.append(part["bytes"])
    raw = b"".join(chunks).decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.rfind("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        return {"raw": raw}


def main() -> int:
    results = []
    state = load_state()
    arn = state.get("agent_runtime_arn")
    if not arn:
        print("No runtime ARN in state — run deploy-agent first")
        return 1

    # 1) Runtime boots and returns structured JSON (bridge may fail if unreachable)
    r1 = invoke_runtime(
        arn,
        {
            "prompt": "Say hello in one short sentence. Do not call tools.",
            "actor": {
                "tenant_id": "acme",
                "user_id": "u_asha",
                "role": "employee",
                "session_id": "e2e-session",
            },
            "bridge": {
                "url": f"{DEMO_URL_DEFAULT.rstrip('/')}/api-backend/internal/agentcore/tools",
                "token": "invalid-on-purpose",
            },
            "run_id": "e2e-chat-" + uuid.uuid4().hex[:8],
        },
    )
    ok_chat = bool(r1.get("ok") or r1.get("plain_language_summary") or r1.get("headline") or r1.get("error"))
    live = bool(r1.get("verified_live") or (r1.get("provider") or {}).get("model_id"))
    results.append(
        {
            "test": "1_gptoss_or_runtime_response",
            "pass": ok_chat,
            "verified_live": live,
            "snippet": str(r1)[:500],
        }
    )

    # 2) Missing actor rejected
    r2 = invoke_runtime(arn, {"prompt": "hi"})
    results.append(
        {
            "test": "2_rejects_missing_actor",
            "pass": r2.get("ok") is False,
            "snippet": str(r2)[:300],
        }
    )

    # 3) SSM secrets present
    ssm = boto_session().client("ssm")
    try:
        key = ssm.get_parameter(Name="/cloudiqs-demo/OPENAI_API_KEY", WithDecryption=True)
        results.append({"test": "3_ssm_openai_key", "pass": bool(key["Parameter"]["Value"])})
    except Exception as exc:
        results.append({"test": "3_ssm_openai_key", "pass": False, "error": str(exc)})

    # 4) Bridge ping via public URL
    import urllib.request

    bridge_ping = f"{DEMO_URL_DEFAULT.rstrip('/')}/api-backend/internal/agentcore/ping"
    try:
        with urllib.request.urlopen(bridge_ping, timeout=15) as resp:
            body = resp.read().decode()
            results.append(
                {
                    "test": "4_bridge_ping_public",
                    "pass": resp.status == 200 and "ok" in body,
                    "body": body[:200],
                }
            )
    except Exception as exc:
        results.append({"test": "4_bridge_ping_public", "pass": False, "error": str(exc)})

    # 5) Local .env still has GPT-OSS config (local mode independence)
    results.append(
        {
            "test": "5_local_env_gptoss_config",
            "pass": bool(read_dotenv_value("OPENAI_MODEL_ID"))
            and "gpt-oss" in read_dotenv_value("OPENAI_MODEL_ID"),
        }
    )

    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}
    path = Path(__file__).resolve().parents[2] / "deploy" / "agentcore" / "e2e_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    failed = [r for r in results if not r.get("pass")]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
