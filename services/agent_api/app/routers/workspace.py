"""Workspace router."""
from fastapi import APIRouter, Depends
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/summary")
async def workspace_summary(session: dict = Depends(get_session_cookie)):
    """Get workspace summary for current user."""
    client = get_enterprise_client(session)
    
    # Get identity
    identity = await client.get_identity()
    
    # Get devices assigned to the signed-in user (not full tenant inventory for staff)
    devices = await client.list_devices(session["user_id"])
    
    # Get recent tickets
    tickets = await client.list_tickets(limit=5)
    
    # Get pending approvals
    approvals = await client.list_approvals(status="pending")
    
    return {
        "identity": identity,
        "devices": devices,
        "recent_tickets": tickets,
        "pending_approvals": approvals,
        "tenant_id": session["tenant_id"],
        "user_id": session["user_id"]
    }
