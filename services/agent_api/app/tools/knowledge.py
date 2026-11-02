"""Knowledge base tools."""
import uuid
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.tools import ToolResult, ActorContext, EvidenceRecord
from app.enterprise.client import EnterpriseClient


class SearchCurrentKnowledgeInput(BaseModel):
    """Search knowledge base."""
    query: str = Field(description="Search query")
    category: Optional[str] = Field(None, description="Optional category filter")


async def search_current_knowledge(
    actor: ActorContext,
    client: EnterpriseClient,
    input: SearchCurrentKnowledgeInput
) -> ToolResult:
    """Search current (non-superseded) knowledge base."""
    try:
        data = await client.search_knowledge(input.query, include_superseded=False)
        
        evidence = []
        for doc in data:
            evidence.append(EvidenceRecord(
                source="knowledge_documents",
                record_id=doc.get("document_id", "unknown"),
                tenant_id=actor.tenant_id,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                classification=doc.get("classification", "employees"),
                version=doc.get("version"),
                trust_level="verified_source_event" if not doc.get("untrusted") else "unverified_vendor"
            ))
        
        return ToolResult(
            ok=True,
            tool="search_current_knowledge",
            request_id=str(uuid.uuid4()),
            data=data,
            evidence=evidence
        )
    except Exception as e:
        return ToolResult(
            ok=False,
            tool="search_current_knowledge",
            request_id=str(uuid.uuid4()),
            error={
                "code": "tool_error",
                "safe_message": str(e),
                "retryable": False
            },
            evidence=[]
        )
