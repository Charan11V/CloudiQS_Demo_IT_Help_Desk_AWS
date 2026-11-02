"""In-app notifications."""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.session import get_session_cookie
from app.db import get_db
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(session: dict = Depends(get_session_cookie)):
    with get_db() as db:
        rows = (
            db.query(Notification)
            .filter(
                Notification.tenant_id == session["tenant_id"],
                Notification.user_id == session["user_id"],
            )
            .order_by(Notification.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "notification_id": n.notification_id,
                "kind": n.type,
                "title": n.title,
                "body": n.body,
                "link": n.link,
                "read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, session: dict = Depends(get_session_cookie)):
    with get_db() as db:
        n = (
            db.query(Notification)
            .filter(
                Notification.notification_id == notification_id,
                Notification.tenant_id == session["tenant_id"],
                Notification.user_id == session["user_id"],
            )
            .first()
        )
        if not n:
            raise HTTPException(404, "Notification not found")
        n.is_read = True
        return {"ok": True}
