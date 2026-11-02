from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from ..db import get_db
from ..auth.session import get_current_user
from ..models import ActionIntent, ApprovalRequest, ActionExecution
from ..services.guided_engine import generate_id
import hashlib
import inspect
import json


def _utcnow():
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    if dt is None:
        return _utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

router = APIRouter(prefix="/api/actions", tags=["actions"])


class CreateActionIntentRequest(BaseModel):
    action_code: str
    target: str
    payload: dict
    expected_version: Optional[int] = None


class ConsentRequest(BaseModel):
    consented: bool


@router.post("/intents")
async def create_action_intent(
    request: CreateActionIntentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create an action intent"""
    
    action_id = generate_id("ACTION")
    idempotency_key = f"{current_user['user_id']}:{request.action_code}:{request.target}:{datetime.utcnow().isoformat()}"
    
    # Calculate payload hash
    payload_str = json.dumps(request.payload, sort_keys=True)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
    
    # Create intent
    intent = ActionIntent(
        action_id=action_id,
        tenant_id=current_user["tenant_id"],
        actor=current_user["user_id"],
        target=request.target,
        action_code=request.action_code,
        payload=request.payload,
        payload_sha256=payload_hash,
        expected_version=request.expected_version,
        idempotency_key=idempotency_key,
        expires_at=_utcnow() + timedelta(hours=24),
        state="pending"
    )
    
    db.add(intent)
    db.commit()
    
    return {
        "action_id": action_id,
        "state": "pending",
        "expires_at": intent.expires_at.isoformat()
    }


@router.post("/{action_id}/consent")
async def user_consent(
    action_id: str,
    request: ConsentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User provides consent for an action"""
    
    intent = db.query(ActionIntent).filter(
        ActionIntent.action_id == action_id,
        ActionIntent.tenant_id == current_user["tenant_id"],
        ActionIntent.actor == current_user["user_id"]
    ).first()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Action intent not found")
    
    if not request.consented:
        intent.state = "cancelled"
        db.commit()
        return {"action_id": action_id, "state": "cancelled"}
    
    # Check if approval is required
    requires_approval = _requires_approval(intent.action_code)
    
    if requires_approval:
        # Create approval request
        approval_id = generate_id("APPR")
        approval = ApprovalRequest(
            approval_id=approval_id,
            action_id=action_id,
            required_role="it_engineer",
            status="pending",
            expiry=_utcnow() + timedelta(hours=48)
        )
        db.add(approval)
        intent.state = "awaiting_approval"
        db.commit()
        
        return {
            "action_id": action_id,
            "state": "awaiting_approval",
            "approval_id": approval_id,
            "requires_approval": True
        }
    else:
        # Can execute immediately
        intent.state = "consented"
        db.commit()
        
        return {
            "action_id": action_id,
            "state": "consented",
            "ready_to_execute": True
        }


@router.post("/{action_id}/execute")
async def execute_action(
    action_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a consented (and approved when required) action"""
    
    intent = db.query(ActionIntent).filter(
        ActionIntent.action_id == action_id,
        ActionIntent.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Action intent not found")

    # Only the original actor (or IT staff for assisted execute) may run the intent
    it_roles = {"it_engineer", "it_manager", "tenant_admin"}
    if intent.actor != current_user["user_id"] and current_user["role"] not in it_roles:
        raise HTTPException(status_code=403, detail="Only the requester or IT can execute this action")
    
    # Check if expired
    if _as_aware(intent.expires_at) < _utcnow():
        intent.state = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Action intent has expired")

    # Idempotent replay of a successful execution (before terminal-state rejection)
    existing_execution = db.query(ActionExecution).filter(
        ActionExecution.action_id == action_id,
        ActionExecution.state == "success"
    ).first()
    
    if existing_execution:
        return {
            "action_id": action_id,
            "execution_id": existing_execution.execution_id,
            "state": "success",
            "result": existing_execution.result_data,
            "cached": True
        }

    if intent.state in ("executed", "cancelled", "rejected", "expired"):
        raise HTTPException(status_code=400, detail=f"Action cannot be executed from state '{intent.state}'")
    
    # Check approval if required
    requires_approval = _requires_approval(intent.action_code)
    
    if requires_approval:
        approval = db.query(ApprovalRequest).filter(
            ApprovalRequest.action_id == action_id,
            ApprovalRequest.status == "approved"
        ).first()
        
        if not approval:
            raise HTTPException(status_code=403, detail="Action not approved")
        if intent.state not in ("approved", "awaiting_approval"):
            raise HTTPException(status_code=403, detail="Action not in approved state")
    else:
        # Non-approval tools require explicit user consent first
        if intent.state not in ("consented", "approved"):
            raise HTTPException(
                status_code=403,
                detail="User consent required before execution",
            )
    
    # Execute the action
    execution_id = generate_id("EXEC")
    execution = ActionExecution(
        execution_id=execution_id,
        action_id=action_id,
        attempts=1,
        started_at=_utcnow(),
        state="running"
    )
    db.add(execution)
    db.commit()
    
    try:
        # Call the appropriate tool
        result = _execute_tool(
            db=db,
            action_code=intent.action_code,
            tenant_id=intent.tenant_id,
            actor=intent.actor,
            target=intent.target,
            payload=intent.payload,
            expected_version=intent.expected_version,
            idempotency_key=intent.idempotency_key
        )
        
        execution.state = "success" if result.get("success") else "failed"
        execution.completed_at = _utcnow()
        execution.result_data = result
        intent.state = "executed"
        
        db.commit()
        
        return {
            "action_id": action_id,
            "execution_id": execution_id,
            "state": execution.state,
            "result": result
        }
        
    except Exception as e:
        execution.state = "failed"
        execution.completed_at = _utcnow()
        execution.result_data = {"error": str(e)}
        db.commit()
        
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/{action_id}")
async def get_action_status(
    action_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get action status"""
    
    intent = db.query(ActionIntent).filter(
        ActionIntent.action_id == action_id,
        ActionIntent.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Action not found")
    
    # Get execution if exists
    execution = db.query(ActionExecution).filter(
        ActionExecution.action_id == action_id
    ).first()
    
    # Get approval if exists
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.action_id == action_id
    ).first()
    
    return {
        "action_id": action_id,
        "action_code": intent.action_code,
        "state": intent.state,
        "created_at": intent.created_at.isoformat(),
        "expires_at": intent.expires_at.isoformat(),
        "approval": {
            "approval_id": approval.approval_id,
            "status": approval.status,
            "required_role": approval.required_role
        } if approval else None,
        "execution": {
            "execution_id": execution.execution_id,
            "state": execution.state,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
        } if execution else None
    }


def _requires_approval(action_code: str) -> bool:
    """Check if action requires approval"""
    approval_required_actions = [
        "renew_mock_vpn_certificate",
        "request_entitlement_grant",
        "request_licence_assignment",
        "install_restricted_software",
        "request_shared_drive_access"
    ]
    return action_code in approval_required_actions


def _execute_tool(db: Session, action_code: str, tenant_id: str, actor: str, 
                  target: str, payload: dict, expected_version: Optional[int], 
                  idempotency_key: str) -> dict:
    """Execute the appropriate tool based on action code"""
    
    from ..services.tools.unlock_account import unlock_own_account
    from ..services.tools.disk_cleanup import run_mock_safe_cleanup
    from ..services.tools.vpn_certificate import renew_mock_vpn_certificate
    from ..services.tools.quick_tools import (
        update_mock_vpn_client,
        perform_mock_restart,
        restart_mock_app_and_cache,
        retry_or_cancel_own_print_job
    )
    from ..services.tools.advanced_tools import (
        create_security_incident,
        request_entitlement_grant,
        install_mock_approved_software
    )
    
    tool_map = {
        "unlock_own_account": unlock_own_account,
        "run_mock_safe_cleanup": run_mock_safe_cleanup,
        "renew_mock_vpn_certificate": renew_mock_vpn_certificate,
        "update_mock_vpn_client": update_mock_vpn_client,
        "perform_mock_restart": perform_mock_restart,
        "restart_mock_app_and_cache": restart_mock_app_and_cache,
        "retry_or_cancel_own_print_job": retry_or_cancel_own_print_job,
        "create_security_incident": create_security_incident,
        "request_entitlement_grant": request_entitlement_grant,
        "install_mock_approved_software": install_mock_approved_software
    }
    
    tool = tool_map.get(action_code)
    if not tool:
        return {"success": False, "error": f"Tool '{action_code}' not implemented"}

    # Map generic target to tool-specific resource ids
    kwargs = {
        "db": db,
        "tenant_id": tenant_id,
        "user_id": actor,
        "expected_version": expected_version,
        "idempotency_key": idempotency_key,
        "approved": True,  # execute endpoint is post-approval / consented
        **(payload or {}),
    }
    target_keys = {
        "unlock_own_account": "account_id",
        "run_mock_safe_cleanup": "device_id",
        "renew_mock_vpn_certificate": "vpn_id",
        "update_mock_vpn_client": "vpn_id",
        "perform_mock_restart": "device_id",
        "restart_mock_app_and_cache": "installation_id",
        "retry_or_cancel_own_print_job": "job_id",
        "install_mock_approved_software": "device_id",
        "request_entitlement_grant": "target",
        "create_security_incident": "target",
    }
    key = target_keys.get(action_code)
    if key and key not in kwargs:
        kwargs[key] = target

    # SEC incident defaults
    if action_code == "create_security_incident":
        kwargs.setdefault("incident_type", "phishing")
        kwargs.setdefault("description", f"Security report from guided helpdesk for {actor}")

    # PRINT-02: diagnosis may send operation= instead of action=
    if action_code == "retry_or_cancel_own_print_job" and "action" not in kwargs:
        kwargs["action"] = kwargs.pop("operation", "retry")

    # ID-06 / APP-04 defaults
    if action_code == "request_entitlement_grant":
        kwargs.setdefault("justification", "Guided helpdesk entitlement request")
        if "resource" not in kwargs and isinstance(target, str) and ":" in target:
            parts = target.split(":")
            if len(parts) >= 3:
                kwargs.setdefault("resource", parts[1])
                kwargs.setdefault("scope", parts[2])

    # REQ-01: ensure device_id + app_id
    if action_code == "install_mock_approved_software":
        kwargs.setdefault("device_id", target)
        kwargs.setdefault("app_id", kwargs.get("app_id") or f"{tenant_id}:secure_browser")

    try:
        sig = inspect.signature(tool)
        filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return tool(**filtered)
    except Exception as e:
        return {"success": False, "error": str(e)}
