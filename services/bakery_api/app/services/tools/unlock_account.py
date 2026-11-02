"""
P0 Tool: ID-01 - Unlock Own Account
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from ...models import Account, AuditEvent
from ...services.guided_engine import generate_id


def unlock_own_account(
    db: Session,
    tenant_id: str,
    user_id: str,
    account_id: str,
    expected_version: int,
    idempotency_key: str
) -> dict:
    """
    Unlock user's own account after identity verification
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User ID (must match account owner)
        account_id: Account ID to unlock
        expected_version: Expected account version for optimistic locking
        idempotency_key: Unique key for this operation
        
    Returns:
        dict with success status and account details
    """
    
    # Check for existing execution with this idempotency key
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        # Return cached result
        return {
            "success": True,
            "message": "Account already unlocked (idempotent)",
            "account_id": account_id,
            "cached": True
        }
    
    # Get and lock account
    stmt = select(Account).where(
        Account.account_id == account_id,
        Account.tenant_id == tenant_id,
        Account.user_id == user_id,  # Ensure ownership
        Account.version == expected_version
    ).with_for_update()
    
    account = db.execute(stmt).scalar_one_or_none()
    
    if not account:
        return {
            "success": False,
            "error": "Account not found, version mismatch, or access denied"
        }
    
    # Check if account is actually locked
    if account.status != "locked":
        return {
            "success": False,
            "error": f"Account is not locked (current status: {account.status})"
        }
    
    # Check if risk flag prevents automatic unlock
    if account.risk_flag:
        return {
            "success": False,
            "error": "Account flagged for security review - automatic unlock not permitted",
            "escalation_required": True
        }
    
    # Store before state
    before_state = {
        "status": account.status,
        "lock_reason": account.lock_reason,
        "failed_logins": account.failed_logins,
        "version": account.version
    }
    
    # Perform unlock
    account.status = "active"
    account.lock_reason = None
    account.failed_logins = 0
    account.version += 1
    
    db.flush()
    
    # Store after state
    after_state = {
        "status": account.status,
        "lock_reason": account.lock_reason,
        "failed_logins": account.failed_logins,
        "version": account.version
    }
    
    # Create audit event
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=account_id,
        action="unlock_own_account",
        before_json=before_state,
        after_json=after_state,
        reason="User self-service unlock after identity verification",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    # Verification read
    verification_stmt = select(Account).where(Account.account_id == account_id)
    verified_account = db.execute(verification_stmt).scalar_one()
    
    if verified_account.status != "active":
        raise Exception("Verification failed: account status not active after unlock")
    
    return {
        "success": True,
        "message": "Account unlocked successfully in demo system",
        "account_id": account_id,
        "before": before_state,
        "after": after_state,
        "verified": {
            "status": verified_account.status,
            "failed_logins": verified_account.failed_logins
        }
    }
