"""Ephemeral tool-bridge sessions for AgentCore Runtime tool execution.

Sessions are stored in SQLite so AgentCore callbacks (and docker-exec diagnostics)
share the same store as the uvicorn process that created the run.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import TOOL_BRIDGE_SECRET, TOOL_BRIDGE_TOKEN_TTL_SECONDS
from app.db import get_db
from app.models import AgentCoreBridgeSession


@dataclass
class BridgeSession:
    token: str
    bearer_token: str
    tenant_id: str
    user_id: str
    role: str
    session_id: str
    run_id: str
    expires_at: float


def _aware_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _purge(db) -> None:
    now = datetime.now(timezone.utc)
    (
        db.query(AgentCoreBridgeSession)
        .filter(AgentCoreBridgeSession.expires_at < now)
        .delete(synchronize_session=False)
    )


def create_bridge_session(
    *,
    bearer_token: str,
    tenant_id: str,
    user_id: str,
    role: str,
    session_id: str,
    run_id: str,
    ttl_seconds: Optional[int] = None,
) -> str:
    token = secrets.token_urlsafe(32)
    ttl = ttl_seconds if ttl_seconds is not None else TOOL_BRIDGE_TOKEN_TTL_SECONDS
    expires = datetime.now(timezone.utc).timestamp() + max(60, ttl)
    expires_dt = datetime.fromtimestamp(expires, tz=timezone.utc)
    with get_db() as db:
        _purge(db)
        db.add(
            AgentCoreBridgeSession(
                token=token,
                bearer_token=bearer_token,
                tenant_id=tenant_id,
                user_id=user_id,
                role=role,
                session_id=session_id,
                run_id=run_id,
                expires_at=expires_dt,
            )
        )
    return token


def get_bridge_session(token: str) -> Optional[BridgeSession]:
    with get_db() as db:
        _purge(db)
        row = db.query(AgentCoreBridgeSession).filter(AgentCoreBridgeSession.token == token).first()
        if not row:
            return None
        expires = _aware_utc(row.expires_at)
        if expires < datetime.now(timezone.utc):
            db.delete(row)
            return None
        return BridgeSession(
            token=row.token,
            bearer_token=row.bearer_token,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            role=row.role,
            session_id=row.session_id,
            run_id=row.run_id,
            expires_at=expires.timestamp(),
        )


def revoke_bridge_session(token: str) -> None:
    with get_db() as db:
        (
            db.query(AgentCoreBridgeSession)
            .filter(AgentCoreBridgeSession.token == token)
            .delete(synchronize_session=False)
        )


def verify_signature(timestamp: str, body: bytes, signature: str) -> bool:
    """HMAC-SHA256 over `{timestamp}.` + body using TOOL_BRIDGE_SECRET."""
    if not TOOL_BRIDGE_SECRET:
        return False
    try:
        ts = int(timestamp)
    except Exception:
        return False
    if abs(int(time.time()) - ts) > 300:
        return False
    expected = hmac.new(
        TOOL_BRIDGE_SECRET.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
