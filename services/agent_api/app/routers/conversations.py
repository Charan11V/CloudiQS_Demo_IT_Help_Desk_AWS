"""Conversations and agent runs router."""
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client
from app.db import get_db
from app.models import ChatConversation, ChatMessage, AgentRun, ToolEvent, EvidenceRef, RunEvent
from app.tools import ActorContext
from app.agent.factory import run_agent, get_provider_info

router = APIRouter(tags=["conversations"])


class CreateRunRequest(BaseModel):
    """Create agent run request."""
    message: str = Field(min_length=1, max_length=10000)
    client_request_id: Optional[str] = None


@router.post("/conversations")
async def create_conversation(session: dict = Depends(get_session_cookie)):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    
    with get_db() as db:
        conversation = ChatConversation(
            conversation_id=conversation_id,
            tenant_id=session["tenant_id"],
            user_id=session["user_id"]
        )
        db.add(conversation)
    
    return {"conversation_id": conversation_id}


@router.get("/conversations")
async def list_conversations(session: dict = Depends(get_session_cookie)):
    """List conversations for current user."""
    with get_db() as db:
        conversations = db.query(ChatConversation).filter(
            ChatConversation.tenant_id == session["tenant_id"],
            ChatConversation.user_id == session["user_id"]
        ).order_by(ChatConversation.updated_at.desc()).limit(50).all()
        
        return [{
            "conversation_id": c.conversation_id,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        } for c in conversations]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, session: dict = Depends(get_session_cookie)):
    """Get conversation details."""
    with get_db() as db:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.conversation_id == conversation_id,
            ChatConversation.tenant_id == session["tenant_id"],
            ChatConversation.user_id == session["user_id"]
        ).first()
        
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.created_at).all()
        
        return {
            "conversation_id": conversation.conversation_id,
            "created_at": conversation.created_at.isoformat(),
            "messages": [{
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            } for m in messages]
        }


@router.post("/conversations/{conversation_id}/runs")
async def create_run(
    conversation_id: str,
    body: CreateRunRequest,
    session: dict = Depends(get_session_cookie)
):
    """Create and execute agent run."""
    # Verify conversation ownership
    with get_db() as db:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.conversation_id == conversation_id,
            ChatConversation.tenant_id == session["tenant_id"],
            ChatConversation.user_id == session["user_id"]
        ).first()
        
        if not conversation:
            raise HTTPException(404, "Conversation not found")
        
        # Create user message
        user_message = ChatMessage(
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=body.message
        )
        db.add(user_message)
        
        # Create agent run
        run_id = str(uuid.uuid4())
        provider_info = get_provider_info()
        
        agent_run = AgentRun(
            run_id=run_id,
            conversation_id=conversation_id,
            tenant_id=session["tenant_id"],
            user_id=session["user_id"],
            mode=provider_info["mode"],
            status="running",
            prompt_version="helpdesk_supervisor_v1",
            model_id=provider_info.get("model_id"),
            input_message=body.message
        )
        db.add(agent_run)
        db.commit()
        
        # Create run event
        run_event = RunEvent(
            run_id=run_id,
            event_type="run.created",
            data_json=json.dumps({"run_id": run_id, "mode": provider_info["mode"]})
        )
        db.add(run_event)
    
    # Execute agent asynchronously
    asyncio.create_task(execute_agent_run(run_id, body.message, session))
    
    return {"run_id": run_id, "status": "running"}


async def execute_agent_run(run_id: str, message: str, session: dict):
    """Execute agent run in background."""
    client = get_enterprise_client(session)
    try:
        me = await client.get_identity()
        role = me.get("role", "employee")
    except Exception:
        role = "employee"
    actor = ActorContext(
        tenant_id=session["tenant_id"],
        user_id=session["user_id"],
        role=role,
        session_id=session["session_id"]
    )
    
    # Get conversation history for context
    conversation_history = []
    with get_db() as db:
        run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
        if run and run.conversation_id:
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == run.conversation_id
            ).order_by(ChatMessage.created_at.desc()).limit(10).all()
            # Reverse to get chronological order, exclude the current message
            conversation_history = [
                {"role": m.role, "content": m.content}
                for m in reversed(messages[1:]) if m.content != message
            ]
    
    try:
        # Run agent with history (AgentCore when configured; else local Strands/simulator)
        outcome, tool_results = await run_agent(
            message,
            actor,
            client,
            run_id,
            conversation_history,
            bearer_token=session.get("bearer_token"),
        )
        
        # Store results
        with get_db() as db:
            # Update run
            agent_run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            if agent_run:
                agent_run.status = "completed"
                agent_run.completed_at = datetime.now(timezone.utc)
                agent_run.output_json = json.dumps({
                    "headline": outcome.headline,
                    "summary": outcome.plain_language_summary,
                    "findings": outcome.findings,
                    "suggested_steps": outcome.suggested_steps,
                    "action_state": outcome.action_state
                })
                
                # Store tool events
                for tool_result in tool_results:
                    tool_event = ToolEvent(
                        event_id=str(uuid.uuid4()),
                        run_id=run_id,
                        tool_name=tool_result.tool,
                        status="completed" if tool_result.ok else "failed",
                        input_json=json.dumps({}),
                        output_json=json.dumps(tool_result.data) if tool_result.ok else None,
                        error_message=json.dumps(tool_result.error) if tool_result.error else None,
                        completed_at=datetime.now(timezone.utc)
                    )
                    db.add(tool_event)
                    
                    # Store evidence
                    for evidence in tool_result.evidence:
                        evidence_ref = EvidenceRef(
                            evidence_id=str(uuid.uuid4()),
                            run_id=run_id,
                            source=evidence.source,
                            record_id=evidence.record_id,
                            tenant_id=evidence.tenant_id,
                            observed_at=datetime.fromisoformat(evidence.observed_at.replace("Z", "+00:00")) if evidence.observed_at else None,
                            last_synced_at=datetime.fromisoformat(evidence.last_synced_at.replace("Z", "+00:00")) if evidence.last_synced_at else None,
                            classification=evidence.classification,
                            trust_level=evidence.trust_level,
                            version=evidence.version
                        )
                        db.add(evidence_ref)
                
                # Create assistant message
                assistant_message = ChatMessage(
                    message_id=str(uuid.uuid4()),
                    conversation_id=agent_run.conversation_id,
                    role="assistant",
                    content=outcome.plain_language_summary
                )
                db.add(assistant_message)
                
                # Final event — include headline/summary so pollers see Bedrock failures honestly
                final_event = RunEvent(
                    run_id=run_id,
                    event_type="run.completed",
                    data_json=json.dumps(
                        {
                            "status": "completed",
                            "headline": outcome.headline,
                            "summary": (outcome.plain_language_summary or "")[:500],
                        }
                    ),
                )
                db.add(final_event)
    
    except Exception as e:
        # Store error
        with get_db() as db:
            agent_run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
            if agent_run:
                agent_run.status = "failed"
                agent_run.completed_at = datetime.now(timezone.utc)
                agent_run.error_message = str(e)
                
                error_event = RunEvent(
                    run_id=run_id,
                    event_type="run.failed",
                    data_json=json.dumps({"error": str(e)})
                )
                db.add(error_event)


@router.get("/runs")
async def list_recent_runs(limit: int = 20, session: dict = Depends(get_session_cookie)):
    """List recent agent runs for the current tenant (activity console)."""
    limit = max(1, min(limit, 100))
    with get_db() as db:
        rows = (
            db.query(AgentRun)
            .filter(AgentRun.tenant_id == session["tenant_id"])
            .order_by(AgentRun.started_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "run_id": r.run_id,
                "conversation_id": r.conversation_id,
                "status": r.status,
                "mode": r.mode,
                "input_message": (r.input_message or "")[:200],
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error": r.error_message,
            }
            for r in rows
        ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, session: dict = Depends(get_session_cookie)):
    """Get run details."""
    with get_db() as db:
        run = db.query(AgentRun).filter(
            AgentRun.run_id == run_id,
            AgentRun.tenant_id == session["tenant_id"]
        ).first()
        
        if not run:
            raise HTTPException(404, "Run not found")

        output = json.loads(run.output_json) if run.output_json else None
        return {
            "run_id": run.run_id,
            "status": run.status,
            "mode": run.mode,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "output": output,
            # Top-level aliases for ops/smoke probes (UI reads output.*)
            "headline": (output or {}).get("headline") if isinstance(output, dict) else None,
            "summary": (output or {}).get("summary") if isinstance(output, dict) else None,
            "error": run.error_message,
        }


@router.get("/runs/{run_id}/events")
async def get_run_events(run_id: str, session: dict = Depends(get_session_cookie)):
    """Get run events (for SSE-like polling)."""
    with get_db() as db:
        run = db.query(AgentRun).filter(
            AgentRun.run_id == run_id,
            AgentRun.tenant_id == session["tenant_id"]
        ).first()
        
        if not run:
            raise HTTPException(404, "Run not found")
        
        events = db.query(RunEvent).filter(
            RunEvent.run_id == run_id
        ).order_by(RunEvent.event_id).all()
        
        return {
            "run_id": run_id,
            "events": [{
                "event_id": e.event_id,
                "event_type": e.event_type,
                "data": json.loads(e.data_json),
                "created_at": e.created_at.isoformat()
            } for e in events]
        }


@router.get("/runs/{run_id}/tool-events")
async def get_tool_events(run_id: str, session: dict = Depends(get_session_cookie)):
    """Get tool events for a run."""
    with get_db() as db:
        run = db.query(AgentRun).filter(
            AgentRun.run_id == run_id,
            AgentRun.tenant_id == session["tenant_id"]
        ).first()
        
        if not run:
            raise HTTPException(404, "Run not found")
        
        tool_events = db.query(ToolEvent).filter(
            ToolEvent.run_id == run_id
        ).order_by(ToolEvent.started_at).all()
        
        return [{
            "event_id": e.event_id,
            "tool_name": e.tool_name,
            "status": e.status,
            "started_at": e.started_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "duration_ms": e.duration_ms,
            "error": e.error_message
        } for e in tool_events]
