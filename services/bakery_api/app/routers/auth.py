from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from ..db import get_db
from ..models import User, Device, Tenant, Session as SessionModel
from ..auth.session import create_session, get_current_user
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


class DemoLoginRequest(BaseModel):
    user_id: str


@router.post("/demo-login")
async def demo_login(request: DemoLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Demo login endpoint - only enabled when ALLOW_DEMO_LOGIN=1"""
    if not settings.ALLOW_DEMO_LOGIN:
        raise HTTPException(status_code=403, detail="Demo login is disabled")
    
    stmt = select(User).where(
        User.user_id == request.user_id,
        User.is_active == True  # noqa: E712
    )
    user = db.execute(stmt).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
    
    session_id = create_session(db, user.tenant_id, user.user_id)
    
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax"
    )
    
    return {
        "success": True,
        "user": {
            "tenant_id": user.tenant_id,
            "user_id": user.user_id,
            "display_name": user.display_name,
            "full_name": user.display_name,
            "role": user.role
        }
    }


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current authenticated user, devices, and tenant context"""
    tenant = db.execute(
        select(Tenant).where(Tenant.tenant_id == current_user["tenant_id"])
    ).scalar_one_or_none()
    devices = db.execute(
        select(Device).where(
            Device.tenant_id == current_user["tenant_id"],
            Device.assigned_to == current_user["user_id"],
        )
    ).scalars().all()

    user_block = {
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "email": current_user["email"],
        "display_name": current_user["display_name"],
        "full_name": current_user["display_name"],
        "role": current_user["role"],
        "department": current_user.get("department"),
    }
    return {
        **current_user,
        "full_name": current_user["display_name"],
        "tenant_name": tenant.display_name if tenant else current_user["tenant_id"],
        "demo_mode": True,
        "user": user_block,
        "devices": [
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "platform": d.platform,
                "asset_id": d.asset_tag or d.device_id,
                "health_status": d.health,
                "disk_free_gb": d.disk_free_gb,
                "disk_total_gb": d.disk_total_gb,
            }
            for d in devices
        ],
    }


@router.post("/logout")
async def logout(
    response: Response,
    db: Session = Depends(get_db),
    bakery_session: Optional[str] = Cookie(None),
):
    """Logout: revoke DB session and clear cookie"""
    if bakery_session:
        row = db.execute(
            select(SessionModel).where(SessionModel.session_id == bakery_session)
        ).scalar_one_or_none()
        if row:
            row.status = "revoked"
            db.commit()
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return {"success": True}
