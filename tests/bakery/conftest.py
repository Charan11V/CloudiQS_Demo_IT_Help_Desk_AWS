"""Fixtures for Bakery API integration tests against the Docker demo stack."""
from __future__ import annotations

import urllib.request

import pytest

from tests.bakery.helpers import ApiSession, BASE


@pytest.fixture(scope="session")
def api_base():
    return BASE


@pytest.fixture(scope="session")
def ensure_api(api_base):
    try:
        with urllib.request.urlopen(f"{api_base}/health", timeout=5) as r:
            assert r.status == 200
    except Exception as exc:
        pytest.skip(f"Bakery API not reachable at {api_base}: {exc}")


@pytest.fixture
def reset_seed(ensure_api):
    s = ApiSession()
    s.login("NS-002")
    code, data = s.request("POST", "/api/dev/seed/reset", {})
    assert code == 200 and data.get("success"), data
    return data


@pytest.fixture
def asha(ensure_api, reset_seed):
    s = ApiSession()
    s.login("NS-001")
    return s


@pytest.fixture
def rahul(ensure_api, reset_seed):
    s = ApiSession()
    s.login("NS-002")
    return s


@pytest.fixture
def beacon_user(ensure_api, reset_seed):
    s = ApiSession()
    code, data = s.request("POST", "/api/auth/demo-login", {"user_id": "BC-001"})
    if code != 200:
        pytest.skip("Beacon tenant user BC-001 not in seed")
    return s
