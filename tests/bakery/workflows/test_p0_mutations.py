"""P0 mutation workflows with pre/post DB-visible verification via API results."""


def _consent_and_maybe_approve(actor, it, action_id):
    code, c = actor.request(
        "POST", f"/api/actions/{action_id}/consent", {"consented": True}
    )
    assert code == 200, c
    if c.get("requires_approval") and c.get("approval_id"):
        code, ap = it.request(
            "POST",
            f"/api/approvals/{c['approval_id']}/decision",
            {"decision": "approved", "reason": "qa"},
        )
        assert code == 200, ap
    return c


def test_id01_unlock_mutates_account(asha, rahul):
    code, intent = asha.request(
        "POST",
        "/api/actions/intents",
        {
            "action_code": "unlock_own_account",
            "target": "ACC-NS-001",
            "expected_version": 1,
            "payload": {},
        },
    )
    assert code == 200
    _consent_and_maybe_approve(asha, rahul, intent["action_id"])
    code, ex = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 200, ex
    assert ex.get("state") == "success"
    result = ex["result"]
    assert result["success"] is True
    assert result["before"]["status"] == "locked"
    assert result["after"]["status"] == "active"
    assert result["verified"]["status"] == "active"


def test_dev01_cleanup_reclaims_disk(asha, rahul):
    code, intent = asha.request(
        "POST",
        "/api/actions/intents",
        {
            "action_code": "run_mock_safe_cleanup",
            "target": "DEV-NS-001",
            "expected_version": 1,
            "payload": {},
        },
    )
    assert code == 200
    _consent_and_maybe_approve(asha, rahul, intent["action_id"])
    code, ex = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 200, ex
    assert ex["state"] == "success"
    result = ex["result"]
    assert result["success"] is True
    assert result["reclaimed_bytes"] > 0
    assert result["after"]["disk_free_gb"] > result["before"]["disk_free_gb"]


def test_net01_renew_after_approval(asha, rahul):
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
    _consent_and_maybe_approve(asha, rahul, intent["action_id"])
    code, ex = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 200, ex
    assert ex["state"] == "success"
    result = ex["result"]
    assert result["success"] is True
    assert result["after"]["version"] == result["before"]["version"] + 1
    assert result["verified"]["expires_in_days"] > 30
    # Honest degraded path allowed
    if result.get("service_status") == "degraded":
        assert "degraded" in result.get("message", "").lower() or result.get("warning")


def test_sec01_creates_incident_ticket(asha, rahul):
    code, intent = asha.request(
        "POST",
        "/api/actions/intents",
        {
            "action_code": "create_security_incident",
            "target": "phishing_report",
            "expected_version": 1,
            "payload": {
                "incident_type": "phishing",
                "description": "QA phishing report",
                "severity": "high",
            },
        },
    )
    assert code == 200
    _consent_and_maybe_approve(asha, rahul, intent["action_id"])
    code, ex = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 200, ex
    assert ex["state"] == "success"
    result = ex["result"]
    assert result["success"] is True
    assert result.get("ticket_id")
    assert result.get("status") == "escalated"
    assert result.get("outcome") == "escalated"


def test_idempotent_unlock(asha, rahul):
    code, intent = asha.request(
        "POST",
        "/api/actions/intents",
        {
            "action_code": "unlock_own_account",
            "target": "ACC-NS-001",
            "expected_version": 1,
            "payload": {},
        },
    )
    assert code == 200
    _consent_and_maybe_approve(asha, rahul, intent["action_id"])
    code1, ex1 = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    code2, ex2 = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code1 == 200 and code2 == 200
    assert ex1["state"] == "success"
    assert ex2.get("cached") is True or ex2["state"] == "success"
