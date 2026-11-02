"""Admin router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/integrations")
async def get_integrations(session: dict = Depends(get_session_cookie)):
    """Get integrations."""
    client = get_enterprise_client(session)
    try:
        integrations = await client.get_integrations()
        return integrations
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.post("/integrations/{integration_key}/test")
async def test_integration(integration_key: str, session: dict = Depends(get_session_cookie)):
    """Test integration connection."""
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") != "tenant_admin":
        raise HTTPException(403, "Admin only")
    
    # Mock test result
    return {
        "integration_key": integration_key,
        "status": "ok",
        "latency_ms": 45,
        "tested_at": "2024-10-31T12:00:00Z",
        "message": "Connection successful"
    }


@router.post("/integrations/{integration_key}/disable")
async def disable_integration(integration_key: str, session: dict = Depends(get_session_cookie)):
    """Disable an integration."""
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") != "tenant_admin":
        raise HTTPException(403, "Admin only")
    
    return {
        "integration_key": integration_key,
        "status": "disabled",
        "message": "Integration disabled (demo mode)"
    }


@router.get("/users")
async def get_users(session: dict = Depends(get_session_cookie)):
    """Get tenant users."""
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") != "tenant_admin":
        raise HTTPException(403, "Admin only")
    
    # Return simulated user list from identity source
    try:
        users = await client.get("/v1/sources/identity_directory", params={"limit": 100})
        return users
    except Exception:
        return []


@router.get("/policy")
async def get_policy(session: dict = Depends(get_session_cookie)):
    """Get tenant policy."""
    client = get_enterprise_client(session)
    try:
        policy = await client.get_policy()
        return policy
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


class PolicyUpdateBody(BaseModel):
    auto_approve_thresholds: dict | None = None
    security_settings: dict | None = None


@router.patch("/policy")
async def update_policy(body: PolicyUpdateBody, session: dict = Depends(get_session_cookie)):
    """Update tenant policy."""
    client = get_enterprise_client(session)
    me = await client.get_identity()
    if me.get("role") != "tenant_admin":
        raise HTTPException(403, "Admin only")
    
    return {
        "message": "Policy update accepted (demo mode)",
        "updated_fields": list(body.model_dump(exclude_none=True).keys())
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = 50,
    session: dict = Depends(get_session_cookie)
):
    """Get audit log."""
    client = get_enterprise_client(session)
    try:
        audit = await client.get_audit_log(limit=limit)
        return audit
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
