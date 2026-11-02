"""Health check router."""
from fastapi import APIRouter
import httpx
from app.config import ENTERPRISE_API_URL, MODEL_PROVIDER, APP_DB_PATH
from app.agent.factory import get_provider_info

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ready")
async def health_ready():
    """Health check with dependency status."""
    status = {
        "ok": True,
        "provider": get_provider_info(),
        "database": {
            "path": str(APP_DB_PATH),
            "exists": APP_DB_PATH.exists()
        },
        "enterprise_api": {
            "url": ENTERPRISE_API_URL,
            "connected": False
        }
    }
    
    # Check enterprise API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ENTERPRISE_API_URL}/health")
            if response.status_code == 200:
                status["enterprise_api"]["connected"] = True
                status["enterprise_api"]["response"] = response.json()
    except Exception as e:
        status["enterprise_api"]["error"] = str(e)
        status["ok"] = False
    
    return status
