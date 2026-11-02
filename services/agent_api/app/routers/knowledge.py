"""Knowledge browser routes."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.session import get_session_cookie
from app.db import get_db
from app.enterprise.client import get_enterprise_client
from app.models import KnowledgeRevision

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("")
async def search_knowledge(
    q: str = Query(min_length=2, default="VPN"),
    include_superseded: bool = False,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    return await client.get(
        "/v1/knowledge/search",
        params={"q": q, "include_superseded": str(include_superseded).lower()},
    )


class KnowledgeUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=20000)
    classification: str = Field(default="employees", pattern="^(employees|internal|admin|security)$")


@router.post("")
async def upload_knowledge(body: KnowledgeUpload, session: dict = Depends(get_session_cookie)):
    """Persist a demo KB revision in app DB (not mock seed). Admin only."""
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") != "tenant_admin":
        raise HTTPException(403, "Admin only")

    doc_id = f"{session['tenant_id']}-KB-LOCAL-{uuid4().hex[:8]}"
    with get_db() as db:
        db.add(
            KnowledgeRevision(
                revision_id=str(uuid4()),
                tenant_id=session["tenant_id"],
                document_id=doc_id,
                title=body.title,
                body=body.body,
                classification=body.classification,
                version="1.0-local",
                status="current",
                created_by=session["user_id"],
                created_at=datetime.now(timezone.utc),
            )
        )
    return {"document_id": doc_id, "status": "current", "version": "1.0-local", "is_simulated": True}
