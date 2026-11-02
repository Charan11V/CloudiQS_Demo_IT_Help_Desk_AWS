"""Network and VPN tools."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.tools import ToolResult, ActorContext, EvidenceRecord
from app.enterprise.client import EnterpriseClient


class GetVpnSessionsInput(BaseModel):
    """Get VPN sessions."""
    target_user_id: Optional[str] = Field(None, description="User ID to query, defaults to self")


async def get_vpn_sessions(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetVpnSessionsInput
) -> ToolResult:
    """Get VPN sessions for a user."""
    try:
        target = input.target_user_id or actor.user_id
        data = await client.get_vpn_sessions(target)
        
        evidence = [EvidenceRecord(
            source="vpn_sessions",
            record_id=f"{target}_vpn",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_vpn_sessions",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_vpn_sessions",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetServiceOutagesInput(BaseModel):
    """No parameters needed."""
    pass


async def get_service_outages(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetServiceOutagesInput
) -> ToolResult:
    """Get current service outages."""
    try:
        data = await client.get_service_outages()
        
        evidence = [EvidenceRecord(
            source="service_health_outages",
            record_id="current_outages",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="internal",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_service_outages",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_service_outages",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetServiceCatalogInput(BaseModel):
    """No parameters needed."""
    pass


async def get_service_catalog(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetServiceCatalogInput
) -> ToolResult:
    """Get service catalog."""
    try:
        data = await client.get_service_catalog()
        
        evidence = [EvidenceRecord(
            source="service_catalog",
            record_id="catalog",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_service_catalog",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_service_catalog",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )
