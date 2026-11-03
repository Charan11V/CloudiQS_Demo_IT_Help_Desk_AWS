"""IAM-authenticated client for Amazon Bedrock AgentCore Runtime."""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import boto3

from app.config import (
    AGENTCORE_ENABLED,
    AGENTCORE_QUALIFIER,
    AGENTCORE_REGION,
    AGENTCORE_RUNTIME_ARN,
    OPENAI_BASE_URL,
    OPENAI_MODEL_ID,
    TOOL_BRIDGE_PUBLIC_URL,
)


class AgentCoreError(RuntimeError):
    pass


def agentcore_configured() -> bool:
    return bool(AGENTCORE_ENABLED and AGENTCORE_RUNTIME_ARN and TOOL_BRIDGE_PUBLIC_URL)


def invoke_helio_agentcore(
    *,
    prompt: str,
    actor: dict[str, Any],
    bridge_token: str,
    run_id: str,
    conversation_history: Optional[list[dict]] = None,
    runtime_session_id: Optional[str] = None,
) -> dict[str, Any]:
    if not agentcore_configured():
        raise AgentCoreError("AgentCore is not configured (ARN / bridge URL / enabled flag)")

    payload = {
        "prompt": prompt,
        "run_id": run_id,
        "actor": actor,
        "conversation_history": conversation_history or [],
        "bridge": {
            "url": TOOL_BRIDGE_PUBLIC_URL.rstrip("/"),
            "token": bridge_token,
        },
        "model": {
            "provider": "openai_compatible",
            "model_id": OPENAI_MODEL_ID,
            "base_url": OPENAI_BASE_URL,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    session_id = runtime_session_id or str(uuid.uuid4())
    # AgentCore requires runtimeSessionId length >= 33
    if len(session_id) < 33:
        session_id = (session_id + "-" + uuid.uuid4().hex)[:64]

    client = boto3.client("bedrock-agentcore", region_name=AGENTCORE_REGION)
    kwargs: dict[str, Any] = {
        "agentRuntimeArn": AGENTCORE_RUNTIME_ARN,
        "runtimeSessionId": session_id,
        "payload": body,
        "qualifier": AGENTCORE_QUALIFIER or "DEFAULT",
    }
    response = client.invoke_agent_runtime(**kwargs)

    chunks: list[bytes] = []
    stream = response.get("response")
    if hasattr(stream, "__iter__") and not isinstance(stream, (bytes, bytearray)):
        for chunk in stream:
            if isinstance(chunk, (bytes, bytearray)):
                chunks.append(bytes(chunk))
            elif isinstance(chunk, dict) and "chunk" in chunk:
                part = chunk["chunk"]
                if isinstance(part, dict) and "bytes" in part:
                    chunks.append(part["bytes"])
                elif isinstance(part, (bytes, bytearray)):
                    chunks.append(bytes(part))
            elif isinstance(chunk, str):
                chunks.append(chunk.encode("utf-8"))
    elif isinstance(stream, (bytes, bytearray)):
        chunks.append(bytes(stream))

    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        raise AgentCoreError("Empty AgentCore response")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some runtimes wrap SSE / multiple JSON objects — take last JSON object
        start = raw.rfind("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise AgentCoreError(f"Non-JSON AgentCore response: {raw[:400]}")
