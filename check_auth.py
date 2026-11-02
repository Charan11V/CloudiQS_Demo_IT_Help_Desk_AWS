"""Check authentication / ACL on restricted endpoints."""
import requests

BASE = "http://localhost:8001"

RESTRICTED = [
    "/admin/integrations",
    "/admin/policy",
    "/admin/audit",
    "/analytics/tickets",
    "/security/findings",
]


def check(persona_key: str, expected_status: int):
    resp = requests.post(
        f"{BASE}/auth/demo-login",
        json={"persona_key": persona_key},
        timeout=5,
    )
    cookies = resp.cookies
    print(f"Testing as {persona_key} (expect {expected_status}):\n")
    for endpoint in RESTRICTED:
        r = requests.get(f"{BASE}{endpoint}", cookies=cookies, timeout=5)
        mark = "✓" if r.status_code == expected_status else "✗"
        print(f"{mark} {endpoint}")
        print(f"  Status: {r.status_code}")
        if r.status_code < 500:
            print(f"  Response: {r.text[:200]}")
        print()


check("northstar-asha", 403)
print()
check("northstar-vikram", 200)
