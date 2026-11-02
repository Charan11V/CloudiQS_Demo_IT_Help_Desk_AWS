"""Devices router."""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
async def list_devices(session: dict = Depends(get_session_cookie)):
    """List devices assigned to the current user (My devices)."""
    client = get_enterprise_client(session)
    # Always scope to the signed-in user so IT/staff personas see their own
    # hardware here, not the full tenant inventory.
    devices = await client.list_devices(session["user_id"])
    return devices


@router.get("/{device_id}")
async def get_device(device_id: str, session: dict = Depends(get_session_cookie)):
    """Get device details including diagnostics."""
    client = get_enterprise_client(session)
    try:
        diagnostics = await client.get_device_diagnostics(device_id)
        return diagnostics
    except Exception as exc:
        raise HTTPException(404, f"Device not found: {exc}")
