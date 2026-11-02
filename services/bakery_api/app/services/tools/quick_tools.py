"""
P0 Tool: NET-02 - Update VPN Client
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from ...models import VpnProfile, Service, AuditEvent
from ...services.guided_engine import generate_id


def update_mock_vpn_client(
    db: Session,
    tenant_id: str,
    user_id: str,
    vpn_id: str,
    expected_version: int,
    idempotency_key: str,
    target_version: str = "5.3"
) -> dict:
    """
    Update VPN client to compliant version
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User ID
        vpn_id: VPN profile ID
        expected_version: Expected version
        idempotency_key: Unique key
        target_version: Version to update to
        
    Returns:
        dict with success status
    """
    
    # Check for existing execution
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {"success": True, "message": "Already updated (idempotent)", "cached": True}
    
    # Get and lock VPN profile
    stmt = select(VpnProfile).where(
        VpnProfile.vpn_id == vpn_id,
        VpnProfile.tenant_id == tenant_id,
        VpnProfile.user_id == user_id,
        VpnProfile.version == expected_version
    ).with_for_update()
    
    vpn_profile = db.execute(stmt).scalar_one_or_none()
    
    if not vpn_profile:
        return {"success": False, "error": "VPN profile not found or access denied"}
    
    # Check service health
    service_stmt = select(Service).where(
        Service.tenant_id == tenant_id,
        Service.service_name.like('%vpn%')
    )
    vpn_service = db.execute(service_stmt).scalar_one_or_none()
    service_healthy = vpn_service and vpn_service.status == "healthy"
    
    before_state = {
        "client_version": vpn_profile.client_version,
        "version": vpn_profile.version
    }
    
    # Update client version
    vpn_profile.client_version = target_version
    vpn_profile.version += 1
    
    after_state = {
        "client_version": vpn_profile.client_version,
        "version": vpn_profile.version
    }
    
    # Audit
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=vpn_id,
        action="update_mock_vpn_client",
        before_json=before_state,
        after_json=after_state,
        reason=f"Updated VPN client to version {target_version}",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    db.commit()
    
    # Verify
    verified_vpn = db.execute(select(VpnProfile).where(VpnProfile.vpn_id == vpn_id)).scalar_one()
    
    if not service_healthy:
        return {
            "success": True,
            "message": "VPN client updated in demo system, but service is degraded",
            "vpn_id": vpn_id,
            "before": before_state,
            "after": after_state,
            "service_status": "degraded",
            "warning": "Connection may still fail due to VPN service outage"
        }
    
    return {
        "success": True,
        "message": "VPN client updated successfully in demo system",
        "vpn_id": vpn_id,
        "before": before_state,
        "after": after_state,
        "verified": {"client_version": verified_vpn.client_version}
    }


"""
P0 Tool: DEV-04 - Perform Mock Restart
"""
def perform_mock_restart(
    db: Session,
    tenant_id: str,
    user_id: str,
    device_id: str,
    expected_version: int,
    idempotency_key: str
) -> dict:
    """Perform mock device restart"""
    from ...models import Device
    
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {"success": True, "message": "Already restarted (idempotent)", "cached": True}
    
    stmt = select(Device).where(
        Device.device_id == device_id,
        Device.tenant_id == tenant_id,
        Device.assigned_to == user_id,
        Device.version == expected_version
    ).with_for_update()
    
    device = db.execute(stmt).scalar_one_or_none()
    
    if not device:
        return {"success": False, "error": "Device not found or access denied"}
    
    before_state = {
        "restart_pending": device.restart_pending,
        "reboot_count": device.reboot_count or 0,
        "version": device.version
    }
    
    device.restart_pending = False
    device.reboot_count = (device.reboot_count or 0) + 1
    device.version += 1
    
    after_state = {
        "restart_pending": device.restart_pending,
        "reboot_count": device.reboot_count,
        "version": device.version
    }
    
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=device_id,
        action="perform_mock_restart",
        before_json=before_state,
        after_json=after_state,
        reason="Mock device restart performed",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    db.commit()
    
    verified_device = db.execute(select(Device).where(Device.device_id == device_id)).scalar_one()
    
    return {
        "success": True,
        "message": "Device restart simulated successfully",
        "device_id": device_id,
        "before": before_state,
        "after": after_state,
        "verified": {
            "restart_pending": verified_device.restart_pending,
            "reboot_count": verified_device.reboot_count,
        }
    }


"""
P0 Tool: APP-01 - Restart App and Cache
"""
def restart_mock_app_and_cache(
    db: Session,
    tenant_id: str,
    user_id: str,
    installation_id: str,
    expected_version: int,
    idempotency_key: str
) -> dict:
    """Restart application and clear cache"""
    from ...models import AppInstallation
    
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {"success": True, "message": "Already restarted (idempotent)", "cached": True}
    
    stmt = select(AppInstallation).where(
        AppInstallation.installation_id == installation_id,
        AppInstallation.tenant_id == tenant_id,
        AppInstallation.user_id == user_id,
        AppInstallation.version == expected_version
    ).with_for_update()
    
    app_install = db.execute(stmt).scalar_one_or_none()
    
    if not app_install:
        return {"success": False, "error": "App installation not found or access denied"}
    
    before_state = {
        "health": app_install.health,
        "version": app_install.version
    }
    
    app_install.health = "healthy"
    app_install.version += 1
    
    after_state = {
        "health": app_install.health,
        "version": app_install.version
    }
    
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=installation_id,
        action="restart_mock_app_and_cache",
        before_json=before_state,
        after_json=after_state,
        reason="Application restarted and cache cleared",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    db.commit()
    
    verified_app = db.execute(
        select(AppInstallation).where(AppInstallation.installation_id == installation_id)
    ).scalar_one()
    
    return {
        "success": True,
        "message": "Application restarted successfully in demo system",
        "installation_id": installation_id,
        "before": before_state,
        "after": after_state,
        "verified": {"health": verified_app.health}
    }


"""
P0 Tool: PRINT-02 - Retry or Cancel Print Job
"""
def retry_or_cancel_own_print_job(
    db: Session,
    tenant_id: str,
    user_id: str,
    job_id: str,
    expected_version: int,
    idempotency_key: str,
    action: str = "retry"  # "retry" or "cancel"
) -> dict:
    """Retry or cancel user's own print job"""
    from ...models import PrintJob
    
    existing_audit = db.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.operation_id == idempotency_key
        )
    ).scalar_one_or_none()
    
    if existing_audit:
        return {"success": True, "message": "Already processed (idempotent)", "cached": True}
    
    stmt = select(PrintJob).where(
        PrintJob.job_id == job_id,
        PrintJob.tenant_id == tenant_id,
        PrintJob.user_id == user_id,  # Can only modify own jobs
        PrintJob.version == expected_version
    ).with_for_update()
    
    print_job = db.execute(stmt).scalar_one_or_none()
    
    if not print_job:
        return {"success": False, "error": "Print job not found or access denied"}
    
    before_state = {
        "status": print_job.status,
        "version": print_job.version
    }
    
    if action == "cancel":
        print_job.status = "cancelled"
    else:  # retry
        print_job.status = "printing"
    
    print_job.version += 1
    
    after_state = {
        "status": print_job.status,
        "version": print_job.version
    }
    
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=job_id,
        action="retry_or_cancel_own_print_job",
        before_json=before_state,
        after_json=after_state,
        reason=f"Print job {action}ed",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    db.commit()
    
    verified_job = db.execute(select(PrintJob).where(PrintJob.job_id == job_id)).scalar_one()
    
    return {
        "success": True,
        "message": f"Print job {action}ed successfully in demo system",
        "job_id": job_id,
        "action": action,
        "before": before_state,
        "after": after_state,
        "verified": {"status": verified_job.status}
    }
