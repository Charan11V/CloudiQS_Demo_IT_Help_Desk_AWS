"""Authentication router."""
from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel, Field
from app.auth.session import (
    create_session, get_session_cookie, set_session_cookie,
    clear_session_cookie, delete_session
)
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/auth", tags=["auth"])


class DemoLoginRequest(BaseModel):
    persona_key: str = Field(description="Persona key from demo tokens")


class SessionResponse(BaseModel):
    tenant_id: str
    user_id: str
    persona_key: str
    role: str | None = None
    name: str | None = None
    email: str | None = None


@router.post("/demo-login")
async def demo_login(body: DemoLoginRequest, response: Response):
    try:
        session_id, session_data = create_session(body.persona_key)
        set_session_cookie(response, session_id)
        # Enrich with identity for immediate UI
        try:
            client = get_enterprise_client({**session_data, "bearer_token": body.persona_key})
            me = await client.get_identity()
        except Exception:
            me = {}
        return {
            "success": True,
            "tenant_id": session_data["tenant_id"],
            "user_id": session_data["user_id"],
            "persona_key": session_data["persona_key"],
            "role": me.get("role"),
            "name": me.get("name"),
            "email": me.get("email"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login failed: {str(e)}")


@router.post("/logout")
async def logout(response: Response, session: dict = Depends(get_session_cookie)):
    delete_session(session["session_id"])
    clear_session_cookie(response)
    return {"success": True}


@router.get("/session", response_model=SessionResponse)
async def get_session(session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    me = await client.get_identity()
    return SessionResponse(
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        persona_key=session["persona_key"],
        role=me.get("role"),
        name=me.get("name"),
        email=me.get("email"),
    )
