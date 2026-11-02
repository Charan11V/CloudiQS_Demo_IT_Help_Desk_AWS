"""Session management with HttpOnly cookies."""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Cookie, HTTPException, Response
from itsdangerous import URLSafeTimedSerializer

from app.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE, SESSION_SIGNING_KEY
from app.db import get_db
from app.models import Session

# Demo tokens: persona_key == Bearer token value used by mock API
_FALLBACK_TOKENS = {
    "northstar-asha": "northstar-EMP-0001",
    "northstar-kiran": "northstar-EMP-0005",
    "northstar-leena": "northstar-EMP-0006",
    "northstar-rahul": "northstar-EMP-0002",
    "northstar-priya": "northstar-EMP-0003",
    "northstar-vikram": "northstar-EMP-0004",
    "northstar-arjun-security": "northstar-EMP-0011",
    "northstar-omar-terminated": "northstar-EMP-0009",
    "beacon-neha": "beacon-EMP-0001",
    "beacon-alice": "beacon-EMP-0004",
    "beacon-sofia": "beacon-EMP-0006",
    "beacon-david": "beacon-EMP-0002",
    "beacon-meera": "beacon-EMP-0003",
    "beacon-james": "beacon-EMP-0005",
    "beacon-noah-security": "beacon-EMP-0007",
}


def _load_demo_tokens() -> dict[str, str]:
    candidates: list[Path] = [
        Path("/pack/data/fixtures/demo_tokens_INSECURE_PUBLIC.json"),
    ]
    here = Path(__file__).resolve()
    for idx in range(min(6, len(here.parents))):
        candidates.append(
            here.parents[idx]
            / "cloudiqs_enterprise_demo_pack"
            / "data"
            / "fixtures"
            / "demo_tokens_INSECURE_PUBLIC.json"
        )
    for path in candidates:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return dict(_FALLBACK_TOKENS)


DEMO_TOKENS = _load_demo_tokens()
serializer = URLSafeTimedSerializer(SESSION_SIGNING_KEY)


def create_session(persona_key: str) -> tuple[str, dict]:
    """Create a new session for a persona. Returns (session_id, public session_data)."""
    if "terminated" in persona_key.lower():
        raise HTTPException(401, "Identity disabled or inactive; HR lifecycle may require reconciliation")

    user_id = DEMO_TOKENS.get(persona_key)
    if not user_id:
        raise HTTPException(401, f"Invalid persona key: {persona_key}")

    # Mock API Authorization: Bearer <persona_key>
    bearer_token = persona_key
    tenant_id = user_id.split("-", 1)[0]
    session_id = secrets.token_urlsafe(32)

    with get_db() as db:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE)
        db.add(
            Session(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                persona_key=persona_key,
                bearer_token=bearer_token,
                expires_at=expires_at,
            )
        )

    return session_id, {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "persona_key": persona_key,
    }


def get_session_cookie(
    session_id: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME),
) -> dict:
    """Resolve authenticated session from HttpOnly cookie."""
    if not session_id:
        raise HTTPException(401, "Not authenticated")

    with get_db() as db:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session:
            raise HTTPException(401, "Invalid session")
        if datetime.now(timezone.utc) > session.expires_at.replace(tzinfo=timezone.utc):
            db.delete(session)
            raise HTTPException(401, "Session expired")
        session.last_seen = datetime.now(timezone.utc)
        return {
            "session_id": session.session_id,
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "persona_key": session.persona_key,
            "bearer_token": session.bearer_token,
        }


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
        secure=False,  # local Docker demo
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def delete_session(session_id: str) -> None:
    with get_db() as db:
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if session:
            db.delete(session)
