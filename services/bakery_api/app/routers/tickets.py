from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth.session import get_current_user
from ..models import Ticket, TicketEvent
from ..services.guided_engine import generate_id

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


IT_ROLES = {"it_engineer", "it_manager", "tenant_admin"}
CLOSEABLE = {"open", "in_progress", "pending", "resolved"}
TERMINAL = {"closed"}


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., description="open | in_progress | resolved | closed")


def _ticket_row(ticket: Ticket, *, include_description: bool = False) -> dict:
    row = {
        "ticket_id": ticket.ticket_id,
        "requester": ticket.requester,
        "issue_code": ticket.issue_code,
        "summary": ticket.summary,
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_team": ticket.assigned_team,
        "assigned_to": ticket.assigned_to,
        "category": ticket.issue_code,
        "source": "bakery",
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }
    if include_description:
        row["description"] = ticket.description
        row["version"] = ticket.version
    return row


@router.get("/mine")
async def get_my_tickets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List tickets for the current user.

    Employees see their own tickets. IT roles see all tickets in the tenant
    so bakery-raised INC-* items appear in HELIO / bakery My Tickets.
    """
    query = db.query(Ticket).filter(Ticket.tenant_id == current_user["tenant_id"])
    if current_user["role"] not in IT_ROLES:
        query = query.filter(Ticket.requester == current_user["user_id"])

    tickets = query.order_by(Ticket.created_at.desc()).all()
    result = [_ticket_row(ticket) for ticket in tickets]
    return {"tickets": result, "count": len(result)}


@router.get("/{ticket_id}")
async def get_ticket_details(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get ticket details"""
    
    ticket = db.query(Ticket).filter(
        Ticket.ticket_id == ticket_id,
        Ticket.tenant_id == current_user["tenant_id"]
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access: requester or IT staff can view
    if ticket.requester != current_user["user_id"] and current_user["role"] not in IT_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _ticket_row(ticket, include_description=True)


@router.get("/{ticket_id}/events")
async def list_ticket_events(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Audit lineage for a bakery ticket (status changes and related events)."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id, Ticket.tenant_id == current_user["tenant_id"])
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.requester != current_user["user_id"] and current_user["role"] not in IT_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    events = (
        db.query(TicketEvent)
        .filter(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.occurred_at.asc())
        .all()
    )
    return {
        "ticket_id": ticket_id,
        "assigned_team": ticket.assigned_team,
        "assigned_to": ticket.assigned_to,
        "status": ticket.status,
        "events": [
            {
                "event_id": e.event_id,
                "actor": e.actor,
                "prior_status": e.prior_status,
                "next_status": e.next_status,
                "reason": e.reason,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in events
        ],
        "count": len(events),
    }


@router.patch("/{ticket_id}")
async def update_ticket_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """IT-only status update (resolve / close) for bakery-raised tickets."""
    if current_user["role"] not in IT_ROLES:
        raise HTTPException(status_code=403, detail="Only IT roles can update ticket status")

    wanted = (body.status or "").strip().lower()
    if wanted not in {"open", "in_progress", "resolved", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_id == ticket_id, Ticket.tenant_id == current_user["tenant_id"])
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    prior = (ticket.status or "open").lower()
    if prior == wanted:
        return _ticket_row(ticket, include_description=True)

    if wanted in TERMINAL and prior not in CLOSEABLE | {"closed"}:
        raise HTTPException(status_code=400, detail=f"Cannot move {prior} → {wanted}")

    ticket.status = wanted
    ticket.updated_at = datetime.now(timezone.utc)
    ticket.version = (ticket.version or 1) + 1
    db.add(
        TicketEvent(
            event_id=generate_id("TEVT"),
            ticket_id=ticket.ticket_id,
            actor=current_user["user_id"],
            prior_status=prior,
            next_status=wanted,
            reason=f"IT set status to {wanted}",
        )
    )
    db.commit()
    db.refresh(ticket)
    return _ticket_row(ticket, include_description=True)
