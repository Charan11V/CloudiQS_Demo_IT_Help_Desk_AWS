from tests.bakery.helpers import ApiSession

s = ApiSession()
s.login("NS-001")
c, conv = s.request("POST", "/api/conversations", {})
assert c == 200, conv
assert conv.get("selection_mode") == "single"
assert conv.get("require_confirm") is True
print("welcome ok", conv["selection_mode"], conv.get("confirm_label"))

cid = conv["conversation_id"]
c, t = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"option_ids": ["identity"], "option_id": "identity"},
)
assert c == 200 and t.get("require_confirm"), t
print("nav ok", t.get("state"), t.get("selection_mode"))

c, t2 = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"free_text": "weird coffee AD issue xyz"},
)
assert c == 200, t2
ids = [o["id"] for o in (t2.get("options") or [])]
assert "confirm_raise_ticket" in ids and "decline_raise_ticket" in ids, t2
print("ticket offer ok")

c, t2b = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"option_ids": ["confirm_raise_ticket"]},
)
assert c == 200 and t2b.get("ticket"), t2b
ids = [o["id"] for o in (t2b.get("options") or [])]
assert "anything_else_yes" in ids and "anything_else_no" in ids, t2b
print("ticket anything else ok")

c, t3 = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"option_ids": ["anything_else_no"]},
)
assert c == 200 and t3.get("state") == "CLOSED", t3
print("closed ok", (t3.get("assistant_message") or "")[:100])

c, conv2 = s.request("POST", "/api/conversations", {})
cid2 = conv2["conversation_id"]
s.request("POST", f"/api/conversations/{cid2}/turns", {"option_ids": ["network"]})
s.request("POST", f"/api/conversations/{cid2}/turns", {"option_ids": ["network__vpn"]})
c, t4 = s.request("POST", f"/api/conversations/{cid2}/turns", {"option_ids": ["NET-01"]})
assert c == 200, t4
assert t4.get("selection_mode") in ("single", "multiple"), t4
print("NET-01 clarifier ok", t4.get("state"), t4.get("selection_mode"), t4.get("require_confirm"))
print("SMOKE PASS")
