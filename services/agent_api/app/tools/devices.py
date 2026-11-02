"""Device tools."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.tools import ToolResult, ActorContext, EvidenceRecord
from app.enterprise.client import EnterpriseClient


class ListAssignedDevicesInput(BaseModel):
    """List assigned devices."""
    target_user_id: Optional[str] = Field(None, description="User ID to query, defaults to self")


async def list_assigned_devices(
    actor: ActorContext,
    client: EnterpriseClient,
    input: ListAssignedDevicesInput
) -> ToolResult:
    """List devices assigned to a user."""
    try:
        target = input.target_user_id or actor.user_id
        data = await client.list_devices(target)
        
        evidence = [EvidenceRecord(
            source="devices",
            record_id=f"{target}_devices",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="list_assigned_devices",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="list_assigned_devices",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetDeviceDiagnosticsInput(BaseModel):
    """Get device diagnostics."""
    device_id: str = Field(description="Device ID")


async def get_device_diagnostics(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetDeviceDiagnosticsInput
) -> ToolResult:
    """Get comprehensive device diagnostics."""
    try:
        data = await client.get_device_diagnostics(input.device_id)
        
        # Multiple sources in diagnostics
        evidence = []
        for source in ["mdm_managed_devices", "endpoint_telemetry", "device_patch_compliance"]:
            if data.get(source):
                evidence.append(EvidenceRecord(
                    source=source,
                    record_id=input.device_id,
                    tenant_id=actor.tenant_id,
                    last_synced_at=data[source].get("last_synced_at") if isinstance(data[source], dict) else None,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    classification="employees",
                    trust_level="verified_source_event"
                ))
        
        return ToolResult(
            ok=True,
            tool="get_device_diagnostics",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_device_diagnostics",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )
