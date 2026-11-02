from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db, drop_tables, create_tables
from ..seed import seed_database
from ..auth.session import get_current_user, require_role
from ..config import get_settings

router = APIRouter(prefix="/api/dev", tags=["dev"])
settings = get_settings()


@router.post("/seed/reset")
async def reset_seed_data(
    current_user: dict = Depends(require_role(["it_engineer", "it_manager", "tenant_admin"])),
    db: Session = Depends(get_db)
):
    """Reset database and reseed - demo/IT only"""
    
    if not settings.ALLOW_DEMO_LOGIN:
        raise HTTPException(status_code=403, detail="Only available in demo mode")
    
    try:
        # Close current session
        db.close()
        
        # Reset and reseed
        seed_database(reset=True)
        
        return {"success": True, "message": "Database reset and reseeded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    
    try:
        # Test database connection
        from ..models import Tenant
        tenant_count = db.query(Tenant).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "tenant_count": tenant_count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get system statistics"""
    
    from ..models import User, Account, Device, Ticket, Conversation
    
    stats = {
        "tenant_id": current_user["tenant_id"],
        "users": db.query(User).filter(User.tenant_id == current_user["tenant_id"]).count(),
        "accounts": db.query(Account).filter(Account.tenant_id == current_user["tenant_id"]).count(),
        "devices": db.query(Device).filter(Device.tenant_id == current_user["tenant_id"]).count(),
        "tickets": db.query(Ticket).filter(Ticket.tenant_id == current_user["tenant_id"]).count(),
        "conversations": db.query(Conversation).filter(Conversation.tenant_id == current_user["tenant_id"]).count()
    }
    
    return stats
