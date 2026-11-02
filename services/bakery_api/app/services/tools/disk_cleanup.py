"""
P0 Tool: DEV-01 - Safe Disk Cleanup
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from ...models import Device, TemporaryFile, AuditEvent
from ...services.guided_engine import generate_id


def run_mock_safe_cleanup(
    db: Session,
    tenant_id: str,
    user_id: str,
    device_id: str,
    expected_version: int,
    idempotency_key: str,
    object_ids: list[int] = None
) -> dict:
    """
    Perform safe cleanup of temporary files on user's device
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        user_id: User ID (must be device owner)
        device_id: Device ID to clean
        expected_version: Expected device version for optimistic locking
        idempotency_key: Unique key for this operation
        object_ids: Optional list of specific temp file IDs to clean
        
    Returns:
        dict with success status and cleanup details
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
            "message": "Cleanup already performed (idempotent)",
            "cached": True
        }
    
    # Get and lock device
    stmt = select(Device).where(
        Device.device_id == device_id,
        Device.tenant_id == tenant_id,
        Device.assigned_to == user_id,  # Ensure ownership
        Device.version == expected_version
    ).with_for_update()
    
    device = db.execute(stmt).scalar_one_or_none()
    
    if not device:
        return {
            "success": False,
            "error": "Device not found, version mismatch, or access denied"
        }
    
    # Get allowlisted temporary files
    temp_files_query = select(TemporaryFile).where(
        TemporaryFile.tenant_id == tenant_id,
        TemporaryFile.device_id == device_id,
        TemporaryFile.removed == False
    )
    
    if object_ids:
        # Support object_id strings from seed or numeric primary keys
        str_ids = [str(x) for x in object_ids]
        int_ids = []
        for x in object_ids:
            try:
                int_ids.append(int(x))
            except (TypeError, ValueError):
                pass
        from sqlalchemy import or_

        clauses = [TemporaryFile.object_id.in_(str_ids)]
        if int_ids:
            clauses.append(TemporaryFile.id.in_(int_ids))
        temp_files_query = temp_files_query.where(or_(*clauses))
    
    temp_files_query = temp_files_query.with_for_update()
    temp_files = db.execute(temp_files_query).scalars().all()
    
    if not temp_files:
        return {
            "success": False,
            "error": "No temporary files available for cleanup"
        }
    
    # Calculate total bytes to reclaim
    reclaimed_bytes = sum(f.size_bytes for f in temp_files)
    reclaimed_gb = reclaimed_bytes / (1024 ** 3)
    
    # Store before state
    before_state = {
        "disk_free_gb": device.disk_free_gb,
        "disk_free_pct": device.disk_free_pct,
        "version": device.version
    }
    
    # Mark files as removed
    file_paths = []
    for temp_file in temp_files:
        temp_file.removed = True
        file_paths.append(temp_file.file_path)
    
    # Update device disk space
    device.disk_free_gb += reclaimed_gb
    device.disk_free_pct = (device.disk_free_gb / device.disk_total_gb) * 100
    device.version += 1
    
    # Validate constraints
    if device.disk_free_gb > device.disk_total_gb:
        db.rollback()
        return {
            "success": False,
            "error": "Constraint violation: free space cannot exceed total capacity"
        }
    
    db.flush()
    
    # Store after state
    after_state = {
        "disk_free_gb": device.disk_free_gb,
        "disk_free_pct": device.disk_free_pct,
        "version": device.version,
        "reclaimed_gb": reclaimed_gb,
        "files_removed": len(temp_files)
    }
    
    # Create audit event
    audit_event = AuditEvent(
        event_id=generate_id("AUDIT"),
        tenant_id=tenant_id,
        actor=user_id,
        resource=device_id,
        action="run_mock_safe_cleanup",
        before_json=before_state,
        after_json=after_state,
        reason=f"Safe cleanup of {len(temp_files)} temporary files, reclaimed {reclaimed_gb:.2f} GB",
        operation_id=idempotency_key
    )
    db.add(audit_event)
    
    db.commit()
    
    # Verification read
    verification_stmt = select(Device).where(Device.device_id == device_id)
    verified_device = db.execute(verification_stmt).scalar_one()
    
    expected_free_gb = round(before_state["disk_free_gb"] + reclaimed_gb, 2)
    actual_free_gb = round(verified_device.disk_free_gb, 2)
    
    if abs(actual_free_gb - expected_free_gb) > 0.01:
        raise Exception(f"Verification failed: expected {expected_free_gb} GB free, got {actual_free_gb} GB")
    
    return {
        "success": True,
        "message": f"Cleaned {reclaimed_gb:.2f} GB of temporary files in demo system",
        "device_id": device_id,
        "files_removed": len(temp_files),
        "reclaimed_bytes": reclaimed_bytes,
        "reclaimed_gb": round(reclaimed_gb, 2),
        "before": before_state,
        "after": after_state,
        "verified": {
            "disk_free_gb": verified_device.disk_free_gb,
            "disk_free_pct": round(verified_device.disk_free_pct, 2)
        }
    }
