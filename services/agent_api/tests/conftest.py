"""Pytest configuration and fixtures."""
import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["APP_SESSION_SIGNING_KEY"] = "test-key-only"
os.environ["MODEL_PROVIDER"] = "simulator"

# Create temporary database for testing
test_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
os.environ["APP_DB_PATH"] = test_db.name


@pytest.fixture(scope="session")
def app():
    """Create test application."""
    from app.main import app
    from app.db import init_db
    init_db()
    return app


@pytest.fixture(scope="function")
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def authenticated_client(client):
    """Create authenticated test client."""
    # Login as Asha
    response = client.post("/auth/demo-login", json={"persona_key": "northstar-asha"})
    assert response.status_code == 200
    return client


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Cleanup after tests."""
    yield
    # Remove test database
    try:
        os.unlink(test_db.name)
    except:
        pass
