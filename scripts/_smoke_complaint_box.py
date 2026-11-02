"""Quick smoke: talk_to_it → prompt → open_ticket without/with complaint."""
from __future__ import annotations

import json
import http.cookiejar
import urllib.request

BASE = "http://127.0.0.1:8002"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def req(method: str, path: str, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with opener.open(request, timeout=60) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


code, login = req("POST", "/api/auth/demo-login", {"user_id": "NS-001"})
assert code == 200 and login.get("success"), login
code, conv = req("POST", "/api/conversations", {})
cid = conv["conversation_id"]
code, state = req("POST", f"/api/conversations/{cid}/turns", {"control": "talk_to_it"})
print("talk_to_it state=", state.get("state"))
print("allow_free_text=", state.get("allow_free_text"))
print("hint=", state.get("free_text_hint"))
print("submit=", state.get("free_text_submit_label"))
print("options=", [o.get("id") for o in state.get("options") or []])
assert state.get("allow_free_text") is True
assert state.get("state") == "AWAITING_TICKET_DETAILS"
assert not state.get("ticket")

code, state2 = req(
    "POST", f"/api/conversations/{cid}/turns", {"option_id": "open_ticket"}
)
print(
    "open_ticket no text state=",
    state2.get("state"),
    "ticket=",
    bool(state2.get("ticket")),
    "allow=",
    state2.get("allow_free_text"),
)
assert state2.get("state") == "AWAITING_TICKET_DETAILS"
assert state2.get("allow_free_text") is True

code, state3 = req(
    "POST",
    f"/api/conversations/{cid}/turns",
    {"option_id": "open_ticket", "free_text": "Smoke complaint about VPN"},
)
print("with complaint ticket=", (state3.get("ticket") or {}).get("ticket_id"))
assert state3.get("ticket")
print("SMOKE_API_OK")
