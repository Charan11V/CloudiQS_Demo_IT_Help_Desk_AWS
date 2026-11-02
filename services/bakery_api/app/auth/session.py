from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Cookie, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
import secrets
import hashlib
from ..db import get_db
from ..models import Session as SessionModel, User
from ..config import get_settings

settings = get_settings()


def _utcnow():
    return datetime.now(timezone.utc)


def create_session_id() -> str:
    """Generate a secure random session ID"""
    return secrets.token_urlsafe(32)


def create_session(db: Session, tenant_id: str, user_id: str) -> str:
    """Create a new session for a user"""
    session_id = create_session_id()
    expires_at = _utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE)
    
    new_session = SessionModel(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        status="active",
        expires_at=expires_at,
        version=1
    )
    
    db.add(new_session)
    db.commit()
    
    return session_id


def get_session(db: Session, session_id: str) -> Optional[SessionModel]:
    """Get a session by ID"""
    stmt = select(SessionModel).where(
        SessionModel.session_id == session_id,
        SessionModel.status == "active",
        SessionModel.expires_at > _utcnow()
    )
    return db.execute(stmt).scalar_one_or_none()


def get_current_user(
    bakery_session: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Get the current authenticated user from session cookie"""
    if not bakery_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = get_session(db, bakery_session)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    # Get user details
    stmt = select(User).where(
        User.tenant_id == session.tenant_id,
        User.user_id == session.user_id,
        User.is_active == True
    )
    user = db.execute(stmt).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return {
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "department": user.department
    }


def require_role(allowed_roles: list[str]):
    """Dependency to require specific roles"""
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker


def check_tenant_access(current_user: dict, resource_tenant_id: str) -> bool:
    """Check if user can access a resource from another tenant"""
    if current_user["tenant_id"] != resource_tenant_id:
        return False
    return True


def ensure_tenant_match(current_user: dict, resource_tenant_id: str):
    """Raise 403 if tenant doesn't match"""
    if not check_tenant_access(current_user, resource_tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")
