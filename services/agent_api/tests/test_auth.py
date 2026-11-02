"""Test authentication."""
import pytest


def test_login_success(client):
    """Test successful login."""
    response = client.post("/auth/demo-login", json={"persona_key": "northstar-asha"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["tenant_id"] == "northstar"
    assert data["user_id"] == "northstar-EMP-0001"


def test_login_terminated_user(client):
    """Test login as terminated user is denied."""
    response = client.post("/auth/demo-login", json={"persona_key": "northstar-omar-terminated"})
    assert response.status_code == 401


def test_get_session(authenticated_client):
    """Test get current session."""
    response = authenticated_client.get("/auth/session")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "northstar"
    assert data["user_id"] == "northstar-EMP-0001"


def test_logout(authenticated_client):
    """Test logout."""
    response = authenticated_client.post("/auth/logout")
    assert response.status_code == 200
    
    # Session should be invalid now
    response = authenticated_client.get("/auth/session")
    assert response.status_code == 401


def test_unauthenticated_access(client):
    """Test unauthenticated access is denied."""
    response = client.get("/workspace/summary")
    assert response.status_code == 401
