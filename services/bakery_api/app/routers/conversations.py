from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..db import get_db
from ..auth.session import get_current_user
from ..services.guided_engine import GuidedEngine

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class TurnRequest(BaseModel):
    option_id: Optional[str] = None
    option_ids: Optional[list[str]] = None
    free_text: Optional[str] = None
    control: Optional[str] = None


def _persist(engine: GuidedEngine, conversation_id: str, result: dict) -> dict:
    engine.save_ui_snapshot(conversation_id, result)
    return result


@router.post("")
async def create_conversation(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    engine = GuidedEngine(db, current_user["tenant_id"], current_user["user_id"])
    conversation_id = engine.create_conversation()

    result = engine.process_turn(conversation_id)
    if result.get("assistant_message"):
        engine.add_message(conversation_id, "assistant", result["assistant_message"])
    return _persist(engine, conversation_id, result)


@router.get("/active")
async def get_active_conversation(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resume the user's most recent chat (refresh-safe)."""
    engine = GuidedEngine(db, current_user["tenant_id"], current_user["user_id"])
    conversation = engine.get_active_conversation()
    if not conversation:
        raise HTTPException(status_code=404, detail="No active conversation")
    payload = engine.resume_conversation(conversation.conversation_id)
    if not payload:
        raise HTTPException(status_code=404, detail="No active conversation")
    return payload


@router.post("/{conversation_id}/turns")
async def process_turn(
    conversation_id: str,
    request: TurnRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a conversation turn"""
    engine = GuidedEngine(db, current_user["tenant_id"], current_user["user_id"])

    conversation = engine.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.free_text:
        engine.add_message(conversation_id, "user", request.free_text)
    elif request.option_ids:
        engine.add_message(
            conversation_id, "user", f"Confirmed selection: {', '.join(request.option_ids)}"
        )
    elif request.option_id:
        engine.add_message(conversation_id, "user", f"Confirmed selection: {request.option_id}")
    elif request.control:
        engine.add_message(conversation_id, "user", f"Control: {request.control}")

    result = engine.process_turn(
        conversation_id,
        option_id=request.option_id,
        option_ids=request.option_ids,
        free_text=request.free_text,
        control=request.control
    )

    if result.get("assistant_message"):
        engine.add_message(conversation_id, "assistant", result["assistant_message"])

    return _persist(engine, conversation_id, result)


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation details / resume snapshot"""
    engine = GuidedEngine(db, current_user["tenant_id"], current_user["user_id"])

    payload = engine.resume_conversation(conversation_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return payload
