"""Adversarial tenant and RBAC tests — must reject cross-tenant and privilege abuse."""
from tests.bakery.helpers import ApiSession


def test_employee_cannot_list_approvals(asha):
    code, data = asha.request("GET", "/api/approvals/pending")
    assert code == 403, data


def test_employee_cannot_reset_seed(asha):
    code, data = asha.request("POST", "/api/dev/seed/reset", {})
    assert code == 403, data


def test_beacon_cannot_read_northstar_ticket(asha, beacon_user):
    code, conv = asha.request("POST", "/api/conversations", {})
    assert code == 200
    cid = conv["conversation_id"]
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": "Uncatalogued coffee machine AD sync failure"},
    )
    assert code == 200
    # Others triage asks before raising; confirm to create the ticket under test.
    if not (state.get("ticket") or {}).get("ticket_id"):
        assert state.get("state") == "AWAITING_UNKNOWN_TICKET_CONFIRM"
        code, state = asha.request(
            "POST",
            f"/api/conversations/{cid}/turns",
            {"option_id": "confirm_raise_ticket"},
        )
        assert code == 200
    ticket_id = (state.get("ticket") or {}).get("ticket_id")
    assert ticket_id

    code, data = beacon_user.request("GET", f"/api/tickets/{ticket_id}")
    assert code in (403, 404), data


def test_cannot_execute_without_consent(asha):
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
    code, data = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 403, data
    assert "consent" in str(data).lower()


def test_peer_employee_cannot_execute_others_intent(asha, reset_seed):
    peer = ApiSession()
    # NS-005 is a northstar employee (not IT / tenant_admin)
    code, _ = peer.request("POST", "/api/auth/demo-login", {"user_id": "NS-005"})
    assert code == 200

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
    asha.request("POST", f"/api/actions/{intent['action_id']}/consent", {"consented": True})
    code, data = peer.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 403, data


def test_vpn_renew_requires_approval_before_execute(asha):
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
    assert c.get("requires_approval") is True
    code, data = asha.request("POST", f"/api/actions/{intent['action_id']}/execute", {})
    assert code == 403, data
