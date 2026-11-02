"""Test tenant isolation."""
import pytest


def test_northstar_cannot_access_beacon_data(client):
    """Test that Northstar user cannot access Beacon data."""
    # Login as Northstar Asha
    response = client.post("/auth/demo-login", json={"persona_key": "northstar-asha"})
    assert response.status_code == 200
    
    # Try to access tickets (will be filtered by tenant in enterprise API)
    response = client.get("/tickets")
    assert response.status_code == 200
    tickets = response.json()["tickets"]
    
    # Ensure no Beacon tickets
    for ticket in tickets:
        assert ticket.get("tenant_id") != "beacon"


def test_beacon_cannot_access_northstar_data(client):
    """Test that Beacon user cannot access Northstar data."""
    # Login as Beacon Neha
    response = client.post("/auth/demo-login", json={"persona_key": "beacon-neha"})
    assert response.status_code == 200
    
    # Try to access tickets
    response = client.get("/tickets")
    assert response.status_code == 200
    tickets = response.json()["tickets"]
    
    # Ensure no Northstar tickets
    for ticket in tickets:
        assert ticket.get("tenant_id") != "northstar"


def test_session_tenant_matches_user(client):
    """Test that session tenant always matches authenticated user."""
    # Login as Northstar user
    response = client.post("/auth/demo-login", json={"persona_key": "northstar-asha"})
    assert response.status_code == 200
    
    # Get session
    response = client.get("/auth/session")
    session = response.json()
    
    assert session["tenant_id"] == "northstar"
    assert session["user_id"].startswith("northstar-")
