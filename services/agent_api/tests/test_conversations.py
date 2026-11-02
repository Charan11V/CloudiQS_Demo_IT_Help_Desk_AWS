"""Test conversations and agent runs."""
import pytest
import time


def test_create_conversation(authenticated_client):
    """Test creating a conversation."""
    response = authenticated_client.post("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data


def test_list_conversations(authenticated_client):
    """Test listing conversations."""
    # Create a conversation first
    response = authenticated_client.post("/conversations")
    assert response.status_code == 200
    
    # List conversations
    response = authenticated_client.get("/conversations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_agent_run_vpn_scenario(authenticated_client):
    """Test agent run with VPN scenario."""
    # Create conversation
    response = authenticated_client.post("/conversations")
    conversation_id = response.json()["conversation_id"]
    
    # Create run with VPN message
    response = authenticated_client.post(
        f"/conversations/{conversation_id}/runs",
        json={"message": "My VPN won't connect and my laptop is slow"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    run_id = data["run_id"]
    
    # Wait for run to complete
    for _ in range(10):
        time.sleep(1)
        response = authenticated_client.get(f"/runs/{run_id}")
        if response.json()["status"] == "completed":
            break
    
    # Check run result
    response = authenticated_client.get(f"/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["output"] is not None
    assert "VPN" in data["output"]["headline"] or "vpn" in data["output"]["summary"].lower()


def test_create_agent_run_account_unlock(authenticated_client):
    """Test agent run with account unlock scenario."""
    # Create conversation
    response = authenticated_client.post("/conversations")
    conversation_id = response.json()["conversation_id"]
    
    # Create run with account locked message
    response = authenticated_client.post(
        f"/conversations/{conversation_id}/runs",
        json={"message": "My account is locked"}
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    
    # Wait for completion
    for _ in range(10):
        time.sleep(1)
        response = authenticated_client.get(f"/runs/{run_id}")
        if response.json()["status"] == "completed":
            break
    
    # Check result
    response = authenticated_client.get(f"/runs/{run_id}")
    data = response.json()
    assert data["status"] == "completed"
    assert "account" in data["output"]["summary"].lower()


def test_get_tool_events(authenticated_client):
    """Test getting tool events from a run."""
    # Create conversation and run
    response = authenticated_client.post("/conversations")
    conversation_id = response.json()["conversation_id"]
    
    response = authenticated_client.post(
        f"/conversations/{conversation_id}/runs",
        json={"message": "Check my VPN"}
    )
    run_id = response.json()["run_id"]
    
    # Wait for completion
    for _ in range(10):
        time.sleep(1)
        response = authenticated_client.get(f"/runs/{run_id}")
        if response.json()["status"] in ["completed", "failed"]:
            break
    
    # Get tool events
    response = authenticated_client.get(f"/runs/{run_id}/tool-events")
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    # Simulator should have called multiple tools
    assert len(events) > 0
