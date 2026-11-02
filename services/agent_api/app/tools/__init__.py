"""Agent tools with evidence envelopes."""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    """Evidence record from a tool call."""
    source: str
    record_id: str
    tenant_id: str
    observed_at: Optional[str] = None
    last_synced_at: Optional[str] = None
    retrieved_at: str
    classification: str
    version: Optional[str] = None
    trust_level: str


class ToolResult(BaseModel):
    """Standardized tool result envelope."""
    ok: bool
    tool: str
    request_id: str
    data: Optional[Any] = None
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    is_simulated_source: bool = True
    error: Optional[Dict[str, Any]] = None


class ActorContext(BaseModel):
    """Actor context injected by server."""
    tenant_id: str
    user_id: str
    role: str
    session_id: str
