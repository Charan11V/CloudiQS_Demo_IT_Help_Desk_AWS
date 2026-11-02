import http.cookiejar, json, urllib.error, urllib.request

class S:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def req(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        r = urllib.request.Request(
            "http://127.0.0.1:8002" + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with self.opener.open(r, timeout=60) as resp:
                return resp.status, json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")


s = S()
s.req("POST", "/api/auth/demo-login", {"user_id": "NS-002"})
print("reset", s.req("POST", "/api/dev/seed/reset", {}))
emp = S()
emp.req("POST", "/api/auth/demo-login", {"user_id": "NS-001"})
code, intent = emp.req(
    "POST",
    "/api/actions/intents",
    {
        "action_code": "renew_mock_vpn_certificate",
        "target": "VPN-NS-001",
        "expected_version": 1,
        "payload": {},
    },
)
print("intent", code, intent)
code, c = emp.req(
    "POST", f"/api/actions/{intent['action_id']}/consent", {"consented": True}
)
print("consent", code, c)
it = S()
it.req("POST", "/api/auth/demo-login", {"user_id": "NS-002"})
code, ap = it.req(
    "POST",
    f"/api/approvals/{c['approval_id']}/decision",
    {"decision": "approved", "reason": "x"},
)
print("approve", code, ap)
code, ex = emp.req("POST", f"/api/actions/{intent['action_id']}/execute", {})
print("exec", code, json.dumps(ex, indent=2))
