"""Tickets router."""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth.session import get_session_cookie
from app.enterprise.client import get_enterprise_client

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
async def list_tickets(
    status: Optional[str] = None,
    limit: int = 100,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    tickets = await client.list_tickets(status=status, limit=limit)
    return {"tickets": tickets, "count": len(tickets)}


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    try:
        return await client.get_ticket(ticket_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            raise HTTPException(404, "Ticket not found")
        raise HTTPException(exc.response.status_code, "Upstream ticket error")


class CreateTicketBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=5, max_length=250)
    description: str = Field(min_length=5, max_length=4000)
    category: str = Field(
        pattern="^(identity|vpn|device|email|software|network|business_app|security|onboarding|offboarding|procurement|cloud_access)$"
    )
    priority: str = Field(default="P3", pattern="^(P1|P2|P3|P4)$")
    idempotency_key: Optional[str] = Field(default=None, max_length=100)
    demo_fault: Optional[str] = None


@router.post("")
async def create_ticket(
    body: CreateTicketBody,
    response: Response,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    key = body.idempotency_key or f"ui-{uuid4().hex}"
    headers = {"Idempotency-Key": key}
    if body.demo_fault:
        headers["X-Demo-Fault"] = body.demo_fault
    payload = {
        "summary": body.summary,
        "description": body.description,
        "category": body.category,
        "priority": body.priority,
    }
    try:
        result = await client.post("/v1/tickets", json=payload, extra_headers=headers)
        response.status_code = 201
        return result
    except httpx.HTTPStatusError as exc:
        # Preserve 504 unknown-after-commit semantics
        if exc.response.status_code == 504:
            raise HTTPException(
                504,
                {
                    "error": "simulated_timeout_after_successful_commit",
                    "status": "unknown_to_client",
                    "hint": "retry with identical Idempotency-Key",
                    "idempotency_key": key,
                },
            )
        if exc.response.status_code == 409:
            raise HTTPException(409, "Idempotency conflict")
        detail = exc.response.text
        raise HTTPException(exc.response.status_code, detail)


class PatchTicketBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None


@router.patch("/{ticket_id}")
async def patch_ticket(
    ticket_id: str,
    body: PatchTicketBody,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    try:
        return await client.patch(f"/v1/tickets/{ticket_id}", json=body.model_dump(exclude_none=True))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            raise HTTPException(exc.response.status_code, "Not authorised or not found")
        raise HTTPException(exc.response.status_code, exc.response.text)


class CommentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=4000)
    visibility: str = Field(default="public", pattern="^(public|internal)$")


@router.post("/{ticket_id}/comments")
async def add_comment(
    ticket_id: str,
    body: CommentBody,
    session: dict = Depends(get_session_cookie),
):
    client = get_enterprise_client(session)
    try:
        return await client.post(
            f"/v1/tickets/{ticket_id}/comments",
            json=body.model_dump(),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(exc.response.status_code, exc.response.text)


@router.get("/{ticket_id}/comments")
async def list_comments(ticket_id: str, session: dict = Depends(get_session_cookie)):
    client = get_enterprise_client(session)
    try:
        return await client.get(f"/v1/tickets/{ticket_id}/comments")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            raise HTTPException(404, "Ticket not found")
        raise HTTPException(exc.response.status_code, exc.response.text)
