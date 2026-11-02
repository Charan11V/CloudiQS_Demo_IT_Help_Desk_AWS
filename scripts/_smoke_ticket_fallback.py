from tests.bakery.helpers import ApiSession

s = ApiSession()
s.login("NS-001")
c, conv = s.request("POST", "/api/conversations", {})
assert c == 200, conv
cid = conv["conversation_id"]
for oid in ["requests", "requests__access_request", "REQ-03"]:
    c, t = s.request("POST", f"/api/conversations/{cid}/turns", {"option_ids": [oid]})
    assert c == 200, t

c, t = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"free_text": "Just testing the agent"},
)
assert c == 200, t
print("STATE", t.get("state"))
print("MSG", (t.get("assistant_message") or "")[:280])
print("OPTS", [(o["id"], o["label"]) for o in (t.get("options") or [])])
assert t.get("state") == "AWAITING_TICKET_DETAILS", t
ids = [o["id"] for o in (t.get("options") or [])]
assert ids == ["open_ticket"], ids
labels = [o.get("label") for o in (t.get("options") or [])]
assert labels == ["Raise a ticket"], labels
msg = (t.get("assistant_message") or "").lower()
assert "raise a" in msg or "ticket" in msg, msg
assert "necessary tools" not in msg and "don't have" not in msg, msg

c, t2 = s.request(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"option_ids": ["open_ticket"]},
)
assert c == 200, t2
ticket = t2.get("ticket") or {}
desc = ticket.get("description") or ""
print("TICKET", ticket.get("ticket_id"), ticket.get("summary"))
print("DESC", desc)
assert "Just testing the agent" in desc, desc
assert ticket.get("ticket_id")
print("PASS")
