"""Ticket tools."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.tools import ToolResult, ActorContext, EvidenceRecord
from app.enterprise.client import EnterpriseClient


class ListTicketsInput(BaseModel):
    """List tickets."""
    status: Optional[str] = Field(None, description="Filter by status")
    target_user_id: Optional[str] = Field(None, description="Filter by user")


async def list_tickets(
    actor: ActorContext,
    client: EnterpriseClient,
    input: ListTicketsInput
) -> ToolResult:
    """List tickets."""
    try:
        data = await client.list_tickets(status=input.status)
        
        evidence = [EvidenceRecord(
            source="itsm_tickets",
            record_id="ticket_list",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="list_tickets",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="list_tickets",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetTicketInput(BaseModel):
    """Get ticket details."""
    ticket_id: str = Field(description="Ticket ID")


async def get_ticket(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetTicketInput
) -> ToolResult:
    """Get ticket details."""
    try:
        data = await client.get_ticket(input.ticket_id)
        
        evidence = [EvidenceRecord(
            source="itsm_tickets",
            record_id=input.ticket_id,
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_ticket",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_ticket",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class CreateSupportTicketInput(BaseModel):
    """Create support ticket."""
    summary: str = Field(min_length=5, max_length=250)
    description: str = Field(min_length=5, max_length=4000)
    category: str = Field(pattern="^(identity|vpn|device|email|software|network|business_app|security|onboarding|offboarding|procurement|cloud_access)$")
    priority: str = Field(default="P3", pattern="^(P1|P2|P3|P4)$")
    idempotency_key: str = Field(description="Idempotency key for safe retry")


async def create_support_ticket(
    actor: ActorContext,
    client: EnterpriseClient,
    input: CreateSupportTicketInput
) -> ToolResult:
    """Create a support ticket with idempotency."""
    try:
        data = await client.create_ticket(
            summary=input.summary,
            description=input.description,
            category=input.category,
            priority=input.priority,
            idempotency_key=input.idempotency_key
        )
        
        evidence = [EvidenceRecord(
            source="itsm_tickets",
            record_id=data.get("ticket_id", "unknown"),
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="create_support_ticket",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="create_support_ticket",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": "504" in str(e) or "timeout" in str(e).lower()
            },
            evidence=[]
        )


class ProposeAccountUnlockInput(BaseModel):
    """Propose account unlock."""
    target_user_id: str = Field(description="User to unlock")
    rationale: str = Field(min_length=5, max_length=1000)


async def propose_account_unlock(
    actor: ActorContext,
    client: EnterpriseClient,
    input: ProposeAccountUnlockInput
) -> ToolResult:
    """Propose account unlock - requires approval."""
    try:
        data = await client.create_approval(
            action_type="identity_account_unlock",
            target_user_id=input.target_user_id,
            device_id=None,
            rationale=input.rationale
        )
        
        evidence = [EvidenceRecord(
            source="approvals",
            record_id=data.get("approval_id", "unknown"),
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="propose_account_unlock",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence,
            warnings=["This is a proposal only. A human reviewer must approve before execution."]
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="propose_account_unlock",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class ProposeVpnCertificateRenewalInput(BaseModel):
    """Propose VPN certificate renewal."""
    device_id: str = Field(description="Device ID")
    target_user_id: str = Field(description="Device owner")
    rationale: str = Field(min_length=5, max_length=1000)


async def propose_vpn_certificate_renewal(
    actor: ActorContext,
    client: EnterpriseClient,
    input: ProposeVpnCertificateRenewalInput
) -> ToolResult:
    """Propose VPN certificate renewal - requires approval and compliance check."""
    try:
        data = await client.create_approval(
            action_type="vpn_certificate_renewal",
            target_user_id=input.target_user_id,
            device_id=input.device_id,
            rationale=input.rationale
        )
        
        evidence = [EvidenceRecord(
            source="approvals",
            record_id=data.get("approval_id", "unknown"),
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="propose_vpn_certificate_renewal",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence,
            warnings=[
                "This is a proposal only. A human reviewer must approve.",
                "Device MDM compliance will be verified before execution."
            ]
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="propose_vpn_certificate_renewal",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )
