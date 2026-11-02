"""API contract checks for frontend/backend alignment."""


def test_me_returns_nested_user_and_devices(asha):
    code, data = asha.request("GET", "/api/auth/me")
    assert code == 200, data
    assert data["user"]["user_id"] == "NS-001"
    assert data["user"]["full_name"] or data["display_name"]
    assert data["tenant_name"]
    assert "devices" in data
    assert data.get("demo_mode") is True


def test_catalog_issue_404(asha):
    code, data = asha.request("GET", "/api/catalog/issues/NOT-A-REAL-CODE")
    assert code == 404, data


def test_logout_revokes_session(ensure_api, reset_seed):
    from tests.bakery.helpers import ApiSession

    s = ApiSession()
    s.login("NS-001")
    code, _ = s.request("GET", "/api/auth/me")
    assert code == 200
    code, _ = s.request("POST", "/api/auth/logout", {})
    assert code == 200
    code, data = s.request("GET", "/api/auth/me")
    assert code == 401, data


def test_approval_decision_schema(asha, rahul):
    code, intent = asha.request(
        "POST",
        "/api/actions/intents",
        {
            "action_code": "renew_mock_vpn_certificate",
            "target": "VPN-NS-001",
            "expected_version": 1,
            "payload": {},
        },
    )
    assert code == 200
    code, c = asha.request(
        "POST", f"/api/actions/{intent['action_id']}/consent", {"consented": True}
    )
    assert c.get("approval_id")
    code, pending = rahul.request("GET", "/api/approvals/pending")
    assert code == 200
    row = next(a for a in pending["approvals"] if a["approval_id"] == c["approval_id"])
    assert row.get("requester_name")
    assert row.get("target_resource")
    assert row.get("expires_at")
    assert row.get("description")
