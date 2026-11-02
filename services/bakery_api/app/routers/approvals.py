from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from ..db import get_db
from ..auth.session import get_current_user, require_role
from ..models import ApprovalRequest, ActionIntent

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


def _utcnow():
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    if dt is None:
        return _utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: Optional[str] = None


@router.get("")
@router.get("/pending")
async def list_pending_approvals(
    current_user: dict = Depends(require_role(["it_engineer", "it_manager"])),
    db: Session = Depends(get_db)
):
    """List pending approval requests for IT staff"""
    
    approvals = db.query(ApprovalRequest).join(
        ActionIntent, ApprovalRequest.action_id == ActionIntent.action_id
    ).filter(
        ActionIntent.tenant_id == current_user["tenant_id"],
        ApprovalRequest.status == "pending",
        ApprovalRequest.expiry > _utcnow()
    ).all()
    
    result = []
    for approval in approvals:
        intent = db.query(ActionIntent).filter(
            ActionIntent.action_id == approval.action_id
        ).first()
        
        requester = intent.actor if intent else None
        action_code = intent.action_code if intent else None
        target = intent.target if intent else None
        result.append({
            "approval_id": approval.approval_id,
            "action_id": approval.action_id,
            "action_code": action_code,
            "requester": requester,
            "requester_id": requester,
            "requester_name": requester or "unknown",
            "target": target,
            "target_resource": target,
            "description": f"Approve {action_code} on {target}" if action_code else "Approval request",
            "impact": "Simulated demo mutation after approval (Demo Mode)",
            "required_role": approval.required_role,
            "status": approval.status,
            "created_at": approval.created_at.isoformat(),
            "expiry": approval.expiry.isoformat(),
            "expires_at": approval.expiry.isoformat(),
        })
    
    return {"approvals": result, "count": len(result)}


@router.post("/{approval_id}/decision")
async def make_approval_decision(
    approval_id: str,
    request: ApprovalDecisionRequest,
    current_user: dict = Depends(require_role(["it_engineer", "it_manager"])),
    db: Session = Depends(get_db)
):
    """Make an approval decision"""
    
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")
    
    approval = db.query(ApprovalRequest).join(
        ActionIntent, ApprovalRequest.action_id == ActionIntent.action_id
    ).filter(
        ApprovalRequest.approval_id == approval_id,
        ActionIntent.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")
    
    if _as_aware(approval.expiry) < _utcnow():
        approval.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Approval has expired")
    
    # Check role authorization
    if current_user["role"] not in [approval.required_role, "it_manager", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient role for this approval")
    
    # Update approval
    approval.status = request.decision
    approval.reviewer_id = current_user["user_id"]
    approval.decision_at = _utcnow()
    
    # Update intent state
    intent = db.query(ActionIntent).filter(
        ActionIntent.action_id == approval.action_id
    ).first()
    
    if intent:
        if request.decision == "approved":
            intent.state = "approved"
        else:
            intent.state = "rejected"
    
    db.commit()
    
    return {
        "approval_id": approval_id,
        "decision": request.decision,
        "decided_by": current_user["user_id"],
        "decided_at": approval.decision_at.isoformat()
    }


@router.get("/{approval_id}")
async def get_approval_details(
    approval_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get approval request details"""
    
    approval = db.query(ApprovalRequest).join(
        ActionIntent, ApprovalRequest.action_id == ActionIntent.action_id
    ).filter(
        ApprovalRequest.approval_id == approval_id,
        ActionIntent.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    intent = db.query(ActionIntent).filter(
        ActionIntent.action_id == approval.action_id
    ).first()
    
    return {
        "approval_id": approval.approval_id,
        "action_id": approval.action_id,
        "action_code": intent.action_code if intent else None,
        "target": intent.target if intent else None,
        "payload": intent.payload if intent else None,
        "requester": intent.actor if intent else None,
        "required_role": approval.required_role,
        "status": approval.status,
        "reviewer_id": approval.reviewer_id,
        "decision_at": approval.decision_at.isoformat() if approval.decision_at else None,
        "created_at": approval.created_at.isoformat(),
        "expiry": approval.expiry.isoformat()
    }
