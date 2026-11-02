"""Development and admin tools router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.config import CONFIRM_RESET_DEMO, APP_DB_PATH
from app.db import Base, engine

router = APIRouter(prefix="/dev", tags=["dev"])


class ResetDemoRequest(BaseModel):
    """Reset demo request."""
    confirmation_token: str = Field(description="Must match CONFIRM_RESET_DEMO env var")


@router.post("/reset-demo")
async def reset_demo(body: ResetDemoRequest):
    """Reset demo data - requires confirmation token."""
    if not CONFIRM_RESET_DEMO:
        raise HTTPException(403, "Demo reset not enabled. Set CONFIRM_RESET_DEMO environment variable.")
    
    if body.confirmation_token != CONFIRM_RESET_DEMO:
        raise HTTPException(403, "Invalid confirmation token")
    
    # Drop all tables and recreate
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        return {
            "success": True,
            "message": "Application database reset successfully",
            "database": str(APP_DB_PATH)
        }
    except Exception as e:
        raise HTTPException(500, f"Reset failed: {str(e)}")


@router.get("/status")
async def dev_status():
    """Get development status and configuration."""
    from app.config import MODEL_PROVIDER, BEDROCK_MODEL_ID, BEDROCK_REGION
    from app.agent.factory import get_provider_info
    
    return {
        "provider": get_provider_info(),
        "database": {
            "path": str(APP_DB_PATH),
            "exists": APP_DB_PATH.exists()
        },
        "config": {
            "model_provider": MODEL_PROVIDER,
            "bedrock_model_id": BEDROCK_MODEL_ID if MODEL_PROVIDER == "bedrock" else None,
            "bedrock_region": BEDROCK_REGION if MODEL_PROVIDER == "bedrock" else None
        }
    }
