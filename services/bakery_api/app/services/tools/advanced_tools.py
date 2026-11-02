"""
Additional P0 Tools: SEC-01, APP-04/ID-06, REQ-01
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from typing import Optional
from ...models import SecurityEvent, Entitlement, Application, AppInstallation, Device, Ticket, AuditEvent
from ...services.guided_engine import generate_id


def create_security_incident(
    db: Session,
    tenant_id: str,
    user_id: str,
    incident_type: str,
    description: str,
    severity: str = "high",
    idempotency_key: str = None
) -> dict:
    """
    P0 Tool: SEC-01 - Create security incident (always escalated, never auto-resolved)
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User reporting
        incident_type: Type of security incident (phishing, malware, etc.)
        description: Description of the incident
        severity: Severity level
        idempotency_key: Unique key
        
    Returns:
        dict with incident and ticket details
    """
    
    if not idempotency_key:
        idempotency_key = f"sec_incident:{user_id}:{datetime.utcnow().isoformat()}"
    
    # Check for existing incident
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        # Return existing incident
        return {
            "success": True,
            "message": "Incident already reported (idempotent)",
            "cached": True
        }
    
    # Create security event
    event_id = generate_id("SEC")
    security_event = SecurityEvent(
        event_id=event_id,
        tenant_id=tenant_id,
        user_id=user_id,
        severity=severity,
        event_type=incident_type,
        description=description,
        review_status="pending"
    )
    db.add(security_event)
    
    # Create escalation ticket
    ticket_id = generate_id("INC")
    ticket = Ticket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        requester=user_id,
        issue_code="SEC-01",
        summary=f"Security incident: {incident_type}",
        description=description,
        status="open",
        priority="high" if severity in ["high", "critical"] else "medium",
        assigned_team="Security Team",
        version=1
    )
    db.add(ticket)
    
    # Audit
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=event_id,
        action="create_security_incident",
        before_json={},
        after_json={
            "event_id": event_id,
            "ticket_id": ticket_id,
            "severity": severity,
            "incident_type": incident_type
        },
        reason="Security incident reported by user",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Security incident reported and escalated to security team",
        "event_id": event_id,
        "ticket_id": ticket_id,
        "status": "escalated",
        "warning": "Do not open suspicious links or attachments. Security team will investigate.",
        "outcome": "escalated"
    }


def request_entitlement_grant(
    db: Session,
    tenant_id: str,
    user_id: str,
    resource: str,
    scope: str,
    justification: str,
    idempotency_key: str,
    approved: bool = False
) -> dict:
    """
    P0 Tool: APP-04/ID-06 - Request entitlement grant (requires approval)
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User requesting access
        resource: Resource name (e.g., "jira", "confluence")
        scope: Access scope (e.g., "admin", "read")
        justification: Business justification
        idempotency_key: Unique key
        approved: Whether approved by app owner
        
    Returns:
        dict with entitlement details
    """
    
    if not approved:
        return {
            "success": False,
            "error": "App owner approval required for entitlement grant",
            "requires_approval": True,
            "status": "pending_approval"
        }
    
    # Check for existing execution
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {
            "success": True,
            "message": "Entitlement already granted (idempotent)",
            "cached": True
        }
    
    # Check if entitlement already exists
    existing_entitlement = db.execute(
        select(Entitlement).where(
            Entitlement.tenant_id == tenant_id,
            Entitlement.user_id == user_id,
            Entitlement.resource == resource,
            Entitlement.scope == scope
        )
    ).scalar_one_or_none()
    
    if existing_entitlement:
        return {
            "success": False,
            "error": "Entitlement already exists",
            "entitlement_id": existing_entitlement.entitlement_id
        }
    
    # Create entitlement
    entitlement_id = generate_id("ENT")
    entitlement = Entitlement(
        entitlement_id=entitlement_id,
        tenant_id=tenant_id,
        user_id=user_id,
        resource=resource,
        scope=scope,
        status="active",
        version=1
    )
    db.add(entitlement)
    
    # Audit
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=entitlement_id,
        action="request_entitlement_grant",
        before_json={},
        after_json={
            "entitlement_id": entitlement_id,
            "resource": resource,
            "scope": scope,
            "status": "active"
        },
        reason=f"Entitlement granted after approval: {justification}",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    # Verify
    verified_ent = db.execute(
        select(Entitlement).where(Entitlement.entitlement_id == entitlement_id)
    ).scalar_one()
    
    return {
        "success": True,
        "message": f"Access to {resource} ({scope}) granted in demo system",
        "entitlement_id": entitlement_id,
        "resource": resource,
        "scope": scope,
        "verified": {
            "status": verified_ent.status
        }
    }


def install_mock_approved_software(
    db: Session,
    tenant_id: str,
    user_id: str,
    app_id: str,
    device_id: str,
    expected_version: int,
    idempotency_key: str
) -> dict:
    """
    P0 Tool: REQ-01 - Install approved software
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User requesting installation
        app_id: Application ID to install
        device_id: Target device
        expected_version: Expected device version
        idempotency_key: Unique key
        
    Returns:
        dict with installation details
    """
    
    # Check for existing execution
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {
            "success": True,
            "message": "Software already installed (idempotent)",
            "cached": True
        }
    
    # Verify app is approved
    app = db.execute(
        select(Application).where(
            Application.app_id == app_id,
            Application.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    
    if not app:
        return {
            "success": False,
            "error": "Application not found or not approved for this tenant"
        }
    
    if not app.allowed_to_self_install:
        return {
            "success": False,
            "error": "This application requires approval for installation",
            "requires_approval": True
        }
    
    # Verify device ownership
    device = db.execute(
        select(Device).where(
            Device.device_id == device_id,
            Device.tenant_id == tenant_id,
            Device.assigned_to == user_id,
            Device.version == expected_version
        ).with_for_update()
    ).scalar_one_or_none()
    
    if not device:
        return {
            "success": False,
            "error": "Device not found, version mismatch, or access denied"
        }
    
    # Check if already installed
    existing_install = db.execute(
        select(AppInstallation).where(
            AppInstallation.tenant_id == tenant_id,
            AppInstallation.device_id == device_id,
            AppInstallation.app_id == app_id
        )
    ).scalar_one_or_none()
    
    if existing_install:
        return {
            "success": False,
            "error": "Application already installed on this device",
            "installation_id": existing_install.installation_id
        }
    
    # Create installation
    installation_id = generate_id("INST")
    installation = AppInstallation(
        installation_id=installation_id,
        tenant_id=tenant_id,
        device_id=device_id,
        user_id=user_id,
        app_id=app_id,
        installed_version=app.approved_version,
        health="healthy",
        version=1
    )
    db.add(installation)
    
    # Update device version
    device.version += 1
    
    # Audit
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=installation_id,
        action="install_mock_approved_software",
        before_json={},
        after_json={
            "installation_id": installation_id,
            "app_id": app_id,
            "app_name": app.app_name,
            "device_id": device_id,
            "installed_version": app.approved_version
        },
        reason=f"Installed approved software: {app.app_name}",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    # Verify
    verified_install = db.execute(
        select(AppInstallation).where(AppInstallation.installation_id == installation_id)
    ).scalar_one()
    
    return {
        "success": True,
        "message": f"{app.app_name} installed successfully in demo system",
        "installation_id": installation_id,
        "app_name": app.app_name,
        "installed_version": app.approved_version,
        "verified": {
            "health": verified_install.health
        }
    }
