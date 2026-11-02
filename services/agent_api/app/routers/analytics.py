"""Analytics router."""
from fastapi import APIRouter, Depends, HTTPException
import httpx
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/tickets")
async def get_ticket_analytics(session: dict = Depends(get_session_cookie)):
    """Get ticket analytics."""
    client = get_enterprise_client(session)
    try:
        analytics = await client.get_analytics()
        return analytics
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@router.get("/agent-runs")
async def get_agent_run_analytics(session: dict = Depends(get_session_cookie)):
    """Get agent run analytics from application database."""
    from app.db import get_db
    from app.models import AgentRun
    from sqlalchemy import func
    
    with get_db() as db:
        # Total runs by status
        status_counts = db.query(
            AgentRun.status,
            func.count(AgentRun.run_id)
        ).filter(
            AgentRun.tenant_id == session["tenant_id"]
        ).group_by(AgentRun.status).all()
        
        # Total runs by mode
        mode_counts = db.query(
            AgentRun.mode,
            func.count(AgentRun.run_id)
        ).filter(
            AgentRun.tenant_id == session["tenant_id"]
        ).group_by(AgentRun.mode).all()
        
        return {
            "total_runs": sum(count for _, count in status_counts),
            "status_counts": {status: count for status, count in status_counts},
            "mode_counts": {mode: count for mode, count in mode_counts}
        }
