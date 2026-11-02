"""Test agent tools."""
import pytest
from app.tools import ActorContext
from app.tools.identity import get_my_identity, GetMyIdentityInput
from app.enterprise.client import EnterpriseClient


@pytest.mark.asyncio
async def test_get_my_identity_tool():
    """Test get_my_identity tool."""
    # Create mock context
    actor = ActorContext(
        tenant_id="northstar",
        user_id="northstar-EMP-0001",
        role="employee",
        session_id="test"
    )
    
    # Create client with demo token
    client = EnterpriseClient(
        bearer_token="northstar-asha",
        tenant_id="northstar"
    )
    
    # Call tool
    result = await get_my_identity(actor, client, GetMyIdentityInput())
    
    assert result.ok is True
    assert result.tool == "get_my_identity"
    assert result.data is not None
    assert result.data["user_id"] == "northstar-EMP-0001"
    assert len(result.evidence) > 0
    assert result.evidence[0].source == "identity_directory"
