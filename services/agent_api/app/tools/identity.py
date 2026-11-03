"""Identity tools."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.tools import ToolResult, ActorContext, EvidenceRecord
from app.enterprise.client import EnterpriseClient


class GetMyIdentityInput(BaseModel):
    """No parameters needed."""
    pass


async def get_my_identity(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetMyIdentityInput
) -> ToolResult:
    """Get current user identity."""
    try:
        data = await client.get_identity()
        
        evidence = [EvidenceRecord(
            source="identity_directory",
            record_id=data.get("user_id", "unknown"),
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_my_identity",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_my_identity",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetIdentityAccountInput(BaseModel):
    """Get identity account for a user."""
    target_user_id: str = Field(description="User ID to query")


async def get_identity_account(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetIdentityAccountInput
) -> ToolResult:
    """Get identity account status."""
    try:
        data = await client.get_identity_account(input.target_user_id)
        
        evidence = [EvidenceRecord(
            source="identity_directory",
            record_id=input.target_user_id,
            tenant_id=actor.tenant_id,
            last_synced_at=data.get("last_synced_at"),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_identity_account",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_identity_account",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )


class GetSigninHistoryInput(BaseModel):
    """Get signin history for a user."""
    target_user_id: str = Field(description="User ID to query")


async def get_signin_history(
    actor: ActorContext,
    client: EnterpriseClient,
    input: GetSigninHistoryInput
) -> ToolResult:
    """Get user sign-in history."""
    try:
        data = await client.get_signin_history(input.target_user_id)
        
        evidence = [EvidenceRecord(
            source="identity_signins",
            record_id=f"{input.target_user_id}_signins",
            tenant_id=actor.tenant_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            classification="employees",
            trust_level="verified_source_event"
        )]
        
        return ToolResult(
            ok=True,
            tool="get_signin_history",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="get_signin_history",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )
