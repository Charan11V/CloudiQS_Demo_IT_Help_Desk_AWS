"""Seed integrity checks exposed through authenticated APIs / stats."""


def test_dev_stats_populated(rahul):
    code, data = rahul.request("GET", "/api/dev/stats")
    assert code == 200, data
    assert data["tenant_id"] == "northstar"
    assert data["users"] >= 10
    assert data["accounts"] >= 10
    assert data["devices"] >= 10


def test_health_endpoints(ensure_api):
    from tests.bakery.helpers import ApiSession
    import urllib.request
    import json

    with urllib.request.urlopen("http://127.0.0.1:8002/health", timeout=5) as r:
        body = json.loads(r.read().decode())
        assert body.get("status") == "ok"

    s = ApiSession()
    s.login("NS-002")
    code, data = s.request("GET", "/api/dev/health")
    assert code == 200
    assert data.get("status") == "healthy"
