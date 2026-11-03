"""Authenticated tool-bridge endpoint used by AgentCore Runtime tools."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.agentcore.bridge import get_bridge_session, verify_signature
from app.enterprise.client import EnterpriseClient
from app.tools import ActorContext
from app.tools.registry import TOOLS

router = APIRouter(tags=["agentcore-bridge"])


class BridgeToolRequest(BaseModel):
    tool: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None


@router.post("/internal/agentcore/tools")
async def execute_bridged_tool(request: Request):
    """
    Execute a HELIO registry tool on behalf of AgentCore Runtime.

    Auth: X-Helio-Bridge-Token (ephemeral per-run) + HMAC signature.
    Enterprise bearer tokens never leave this process toward AgentCore.
    """
    body = await request.body()
    token = request.headers.get("X-Helio-Bridge-Token") or ""
    ts = request.headers.get("X-Helio-Timestamp") or ""
    sig = request.headers.get("X-Helio-Signature") or ""

    if not token or not verify_signature(ts, body, sig):
        raise HTTPException(status_code=401, detail="invalid bridge authentication")

    sess = get_bridge_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="bridge session expired or unknown")

    try:
        payload = json.loads(body.decode("utf-8"))
        req = BridgeToolRequest(**payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid payload: {exc}") from exc

    if req.tool not in TOOLS:
        raise HTTPException(status_code=404, detail=f"unknown tool: {req.tool}")

    if req.run_id and req.run_id != sess.run_id:
        raise HTTPException(status_code=403, detail="run_id mismatch")

    meta = TOOLS[req.tool]
    input_cls = meta["input_class"]
    fn = meta["fn"]
    actor = ActorContext(
        tenant_id=sess.tenant_id,
        user_id=sess.user_id,
        role=sess.role,
        session_id=sess.session_id,
    )
    client = EnterpriseClient(bearer_token=sess.bearer_token, tenant_id=sess.tenant_id)

    try:
        validated = input_cls(**(req.arguments or {})) if req.arguments else input_cls()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid tool arguments: {exc}") from exc

    result = await fn(actor, client, validated)
    return {
        "ok": result.ok,
        "tool": result.tool,
        "request_id": result.request_id,
        "data": result.data,
        "warnings": result.warnings,
        "evidence": [e.model_dump() for e in (result.evidence or [])],
        "error": result.error,
        "is_simulated_source": True,
        "via": "agentcore_tool_bridge",
    }


@router.get("/internal/agentcore/ping")
async def bridge_ping():
    return {"ok": True, "service": "agentcore-tool-bridge"}
