from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth.session import get_current_user
from ..models import Ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


IT_ROLES = {"it_engineer", "it_manager", "tenant_admin"}


def _ticket_row(ticket: Ticket, *, include_description: bool = False) -> dict:
    row = {
        "ticket_id": ticket.ticket_id,
        "requester": ticket.requester,
        "issue_code": ticket.issue_code,
        "summary": ticket.summary,
        "status": ticket.status,
        "priority": ticket.priority,
        "assigned_team": ticket.assigned_team,
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
