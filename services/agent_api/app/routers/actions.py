"""Actions and approvals router."""
from __future__ import annotations

from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
import hashlib
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.auth.session import get_session_cookie
from app.db import get_db
from app.enterprise.client import get_enterprise_client
from app.models import ActionIntent, Notification

router = APIRouter(tags=["actions"])


class ProposeActionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(pattern="^(identity_account_unlock|vpn_certificate_renewal)$")
    target_user_id: str
    device_id: Optional[str] = None
    rationale: str = Field(min_length=5, max_length=1000)


@router.post("/actions/propose")
async def propose_action(body: ProposeActionBody, session: dict = Depends(get_session_cookie)):
    """Create immutable action intent + mock approval request (proposal only)."""
    client = get_enterprise_client(session)
    payload = {
        "action_type": body.action_type,
        "target_user_id": body.target_user_id,
        "device_id": body.device_id,
        "rationale": body.rationale,
    }
    try:
        result = await client.create_approval(
            action_type=body.action_type,
            target_user_id=body.target_user_id,
            rationale=body.rationale,
            device_id=body.device_id,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, exc.response.text)

    intent_id = str(uuid4())
    payload_s = json.dumps(payload, sort_keys=True)
    with get_db() as db:
        db.add(
            ActionIntent(
                intent_id=intent_id,
                tenant_id=session["tenant_id"],
                action_type=body.action_type,
                target_user_id=body.target_user_id,
                device_id=body.device_id,
                rationale=body.rationale,
                payload_json=payload_s,
                payload_hash=hashlib.sha256(payload_s.encode()).hexdigest(),
                status="awaiting_approval",
                approval_id=result.get("approval_id"),
                created_at=datetime.now(timezone.utc),
            )
        )
        # Notify eligible reviewers is handled when they poll approvals; notify requester
        db.add(
            Notification(
                notification_id=str(uuid4()),
                tenant_id=session["tenant_id"],
                user_id=session["user_id"],
                type="action_requested",
                title="Approval requested",
                body=f"{body.action_type} pending review",
                link=f"/approvals?id={result.get('approval_id')}",
                is_read=False,
            )
        )
    return {**result, "intent_id": intent_id, "action_state": "awaiting_approval"}


@router.get("/approvals")
@router.get("/actions/approvals")
async def list_approvals(
    status: Optional[str] = None,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    approvals = await client.list_approvals(status=status)
    return {"approvals": approvals, "count": len(approvals)}


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(min_length=5, max_length=500)


@router.post("/approvals/{approval_id}/decision")
@router.post("/actions/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    try:
        return await client.decide_approval(approval_id, body.decision, body.reason)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, exc.response.text)


@router.post("/approvals/{approval_id}/execute")
@router.post("/actions/approvals/{approval_id}/execute")
async def execute_approval(approval_id: str, session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    try:
        result = await client.execute_approval(approval_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, exc.response.text)

    with get_db() as db:
        db.add(
            Notification(
                notification_id=str(uuid4()),
                tenant_id=session["tenant_id"],
                user_id=session["user_id"],
                type="action_executed",
                title="Action executed (simulated)",
                body=f"Approval {approval_id} execution recorded",
                link=f"/approvals?id={approval_id}",
                is_read=False,
            )
        )
    return result
