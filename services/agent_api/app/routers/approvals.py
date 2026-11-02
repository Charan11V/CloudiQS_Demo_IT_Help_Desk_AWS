"""Approvals router - separate from actions for clarity."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(
    status: Optional[str] = None,
    session: dict = Depends(get_session_cookie),
):
    """List approvals for the current user (filtered by role in mock)."""
    client = get_enterprise_client(session)
    approvals = await client.list_approvals(status=status)
    return {"approvals": approvals, "count": len(approvals)}
