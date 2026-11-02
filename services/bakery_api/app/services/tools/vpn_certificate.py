"""
P0 Tool: NET-01 - Renew VPN Certificate (requires IT approval)
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from ...models import VpnProfile, Service, AuditEvent
from ...services.guided_engine import generate_id


def _utcnow():
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def renew_mock_vpn_certificate(
    db: Session,
    tenant_id: str,
    user_id: str,
    vpn_id: str,
    expected_version: int,
    idempotency_key: str,
    approved: bool = False
) -> dict:
    """
    Renew VPN certificate (requires IT approval)
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User ID (must be VPN profile owner)
        vpn_id: VPN profile ID
        expected_version: Expected VPN profile version
        idempotency_key: Unique key for this operation
        approved: Whether IT has approved this action
        
    Returns:
        dict with success status and renewal details
    """
    
    if not approved:
        return {
            "success": False,
            "error": "IT approval required for VPN certificate renewal",
            "requires_approval": True
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
            "message": "Certificate already renewed (idempotent)",
            "cached": True
        }
    
    # Get and lock VPN profile
    stmt = select(VpnProfile).where(
        VpnProfile.vpn_id == vpn_id,
        VpnProfile.tenant_id == tenant_id,
        VpnProfile.user_id == user_id,  # Ensure ownership
        VpnProfile.version == expected_version
    ).with_for_update()
    
    vpn_profile = db.execute(stmt).scalar_one_or_none()
    
    if not vpn_profile:
        return {
            "success": False,
            "error": "VPN profile not found, version mismatch, or access denied"
        }
    
    # Check VPN service health
    service_stmt = select(Service).where(
        Service.tenant_id == tenant_id,
        Service.service_name.like('%vpn%')
    )
    vpn_service = db.execute(service_stmt).scalar_one_or_none()
    
    service_healthy = vpn_service and vpn_service.status == "healthy"
    
    # Store before state
    before_expiry = _as_aware(vpn_profile.cert_expires_at)
    before_state = {
        "cert_expires_at": before_expiry.isoformat() if before_expiry else None,
        "status": vpn_profile.status,
        "version": vpn_profile.version
    }
    
    # Renew certificate (90 days from now)
    new_expiry = _utcnow() + timedelta(days=90)
    vpn_profile.cert_expires_at = new_expiry
    vpn_profile.version += 1
    
    db.flush()
    
    # Store after state
    after_state = {
        "cert_expires_at": _as_aware(vpn_profile.cert_expires_at).isoformat(),
        "status": vpn_profile.status,
        "version": vpn_profile.version
    }
    
    # Create audit event
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=vpn_id,
        action="renew_mock_vpn_certificate",
        before_json=before_state,
        after_json=after_state,
        reason="VPN certificate renewed after IT approval",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    # Verification read
    verification_stmt = select(VpnProfile).where(VpnProfile.vpn_id == vpn_id)
    verified_vpn = db.execute(verification_stmt).scalar_one()
    verified_expiry = _as_aware(verified_vpn.cert_expires_at)
    now = _utcnow()

    if verified_expiry is None or verified_expiry <= now:
        raise Exception("Verification failed: certificate still expired after renewal")

    expires_in_days = (verified_expiry - now).days
    
    # Check if VPN service is degraded
    if not service_healthy:
        return {
            "success": True,
            "message": "Certificate renewed in demo system, but VPN service is currently degraded",
            "vpn_id": vpn_id,
            "before": before_state,
            "after": after_state,
            "verified": {
                "cert_expires_at": verified_expiry.isoformat(),
                "expires_in_days": expires_in_days
            },
            "service_status": "degraded",
            "warning": "Connection may still fail due to VPN service outage"
        }
    
    return {
        "success": True,
        "message": "VPN certificate renewed successfully in demo system",
        "vpn_id": vpn_id,
        "before": before_state,
        "after": after_state,
        "verified": {
            "cert_expires_at": verified_expiry.isoformat(),
            "expires_in_days": expires_in_days
        }
    }
