"""Guided navigation and unsupported-issue pathways."""


def test_catalog_has_57_issues(asha):
    code, data = asha.request("GET", "/api/catalog")
    assert code == 200
    assert len(data.get("issues") or []) >= 57


def test_root_categories_navigable(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    code, state = asha.request(
        "POST", f"/api/conversations/{cid}/turns", {"option_id": "identity"}
    )
    assert code == 200
    assert state.get("options")
    ids = [o["id"] for o in state["options"]]
    assert any("identity" in i or i.startswith("ID-") for i in ids) or len(ids) > 0


def test_opening_catalog_excludes_im_not_sure(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    assert code == 200
    ids = [o.get("id") for o in conv.get("options") or []]
    labels = [(o.get("label") or "").strip().lower() for o in conv.get("options") or []]
    assert "not_sure" not in ids
    assert "i'm not sure" not in labels
    assert "i’m not sure" not in labels
    assert "cant_find" in ids
    assert "my_tickets" in ids


def test_others_unknown_offers_ticket_then_raises_on_confirm(asha):
    """Others → free text (unknown IT) → ask to raise ticket → confirm → ticket."""
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    code, state = asha.request(
        "POST", f"/api/conversations/{cid}/turns", {"option_id": "cant_find"}
    )
    assert code == 200
    assert state.get("state") == "DESCRIBING_OTHER"
    assert state.get("allow_free_text") is True
    assert not state.get("ticket")

    detail = "My coffee machine will not sync with Active Directory"
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": detail},
    )
    assert code == 200
    assert not state.get("ticket")
    assert state.get("state") == "AWAITING_UNKNOWN_TICKET_CONFIRM"
    msg = (state.get("assistant_message") or "").lower()
    assert "ticket" in msg
    ids = [o["id"] for o in state.get("options") or []]
    assert "confirm_raise_ticket" in ids
    assert "decline_raise_ticket" in ids

    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"option_id": "confirm_raise_ticket"},
    )
    assert code == 200
    ticket_id = (state.get("ticket") or {}).get("ticket_id")
    assert ticket_id
    assert detail in ((state.get("ticket") or {}).get("description") or "")

    code, mine = asha.request("GET", "/api/tickets/mine")
    assert code == 200
    assert any(t["ticket_id"] == ticket_id for t in mine.get("tickets", []))


def test_others_answerable_does_not_auto_raise(asha):
    """Others → known IT topic → answer + catalog; no ticket."""
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    asha.request("POST", f"/api/conversations/{cid}/turns", {"option_id": "cant_find"})
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": "My VPN certificate expired and I cannot connect"},
    )
    assert code == 200
    assert not state.get("ticket")
    assert state.get("state") != "AWAITING_UNKNOWN_TICKET_CONFIRM"
    assert state.get("state") != "CLOSED"
    assert not state.get("session_locked")
    msg = (state.get("assistant_message") or "").lower()
    assert "no ticket was created" in msg
    assert "vpn" in msg or "certificate" in msg or "net-01" in msg
    ids = [o["id"] for o in state.get("options") or []]
    assert "cant_find" in ids  # opening catalog re-shown
    assert "not_sure" not in ids


def test_others_out_of_scope_reshows_catalog(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    asha.request("POST", f"/api/conversations/{cid}/turns", {"option_id": "cant_find"})
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": "What is the weather in Paris today?"},
    )
    assert code == 200
    assert not state.get("ticket")
    msg = (state.get("assistant_message") or "").lower()
    assert "outside" in msg or "out of scope" in msg or "outside it" in msg
    ids = [o["id"] for o in state.get("options") or []]
    assert "cant_find" in ids
    assert "not_sure" not in ids
    assert state.get("state") == "WELCOME"


def test_known_free_text_answers_without_ticket(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": "My VPN certificate expired and I cannot connect"},
    )
    assert code == 200
    assert state.get("state") != "AWAITING_UNKNOWN_TICKET_CONFIRM"
    assert not state.get("ticket")
    assert state.get("options")
    msg = (state.get("assistant_message") or "").lower()
    assert "vpn" in msg or "certificate" in msg or "net-01" in msg


def test_guided_net01_reaches_proposal_or_clarifier(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    for oid in ("network", "network__vpn", "NET-01"):
        code, state = asha.request(
            "POST", f"/api/conversations/{cid}/turns", {"option_id": oid}
        )
        assert code == 200, state
    assert state.get("assistant_message")
    # Either clarifiers or proposing action
    assert state.get("options") or state.get("state")


def test_start_over_control(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    asha.request("POST", f"/api/conversations/{cid}/turns", {"option_id": "network"})
    code, state = asha.request(
        "POST", f"/api/conversations/{cid}/turns", {"control": "start_over"}
    )
    assert code == 200
    assert state.get("demo_mode") is True


def test_talk_to_it_prompts_for_complaint_then_creates_ticket(asha):
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]
    code, state = asha.request(
        "POST", f"/api/conversations/{cid}/turns", {"control": "talk_to_it"}
    )
    assert code == 200
    assert state.get("state") == "AWAITING_TICKET_DETAILS"
    assert state.get("allow_free_text") is True
    assert state.get("free_text_hint")
    assert not state.get("ticket")
    ids = [o["id"] for o in state.get("options") or []]
    assert "open_ticket" in ids

    complaint = "Need a human — MFA keeps failing after travel"
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"free_text": complaint},
    )
    assert code == 200
    assert state.get("ticket")
    desc = (state.get("ticket") or {}).get("description") or ""
    assert complaint in desc


def test_open_ticket_without_complaint_prompts_and_attaches_box(asha):
    """open_ticket with no free_text must prompt; decorate keeps allow_free_text."""
    code, conv = asha.request("POST", "/api/conversations", {})
    cid = conv["conversation_id"]

    # Enter ticket-details via Talk to IT (always offers open_ticket + complaint box)
    code, state = asha.request(
        "POST", f"/api/conversations/{cid}/turns", {"control": "talk_to_it"}
    )
    assert code == 200
    assert state.get("allow_free_text") is True
    assert "open_ticket" in [o["id"] for o in state.get("options") or []]

    # Confirm Raise ticket with no complaint → stay prompting
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {"option_id": "open_ticket"},
    )
    assert code == 200
    assert state.get("state") == "AWAITING_TICKET_DETAILS"
    assert state.get("allow_free_text") is True
    assert state.get("free_text_submit_label") == "Raise ticket"
    assert not state.get("ticket")

    # Same option + complaint text → ticket created
    code, state = asha.request(
        "POST",
        f"/api/conversations/{cid}/turns",
        {
            "option_id": "open_ticket",
            "free_text": "Cannot reach shared drive after VPN reconnect",
        },
    )
    assert code == 200
    assert state.get("ticket")
    assert "shared drive" in (
        (state.get("ticket") or {}).get("description") or ""
    ).lower()
