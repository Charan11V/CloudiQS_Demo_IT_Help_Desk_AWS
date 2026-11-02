"""Quick test script for HELIO endpoints (employee ACL + tenant_admin access)."""
import json
import sys

import requests

BASE = "http://localhost:8001"

# Employee may access these (expect 200).
EMPLOYEE_OK = [
    ("GET", "/workspace/summary"),
    ("GET", "/tickets"),
    ("GET", "/approvals"),
    ("GET", "/devices"),
    ("GET", "/analytics/agent-runs"),
    ("GET", "/knowledge"),
    ("GET", "/notifications"),
]

# Employee must be denied; tenant_admin must succeed with JSON.
RESTRICTED = [
    ("GET", "/admin/integrations"),
    ("GET", "/admin/policy"),
    ("GET", "/admin/audit"),
    ("GET", "/analytics/tickets"),
    ("GET", "/security/findings"),
]


def login(persona_key: str):
    resp = requests.post(
        f"{BASE}/auth/demo-login",
        json={"persona_key": persona_key},
        timeout=5,
    )
    if resp.status_code != 200:
        print(f"✗ Login failed ({persona_key}): {resp.status_code}")
        return None
    print(f"✓ Login successful ({persona_key})")
    return resp.cookies


def request(method: str, path: str, cookies, data=None):
    url = f"{BASE}{path}"
    if method == "GET":
        return requests.get(url, cookies=cookies, timeout=5)
    if method == "POST":
        return requests.post(url, json=data, cookies=cookies, timeout=5)
    raise ValueError(f"Unsupported method: {method}")


def expect_status(method, path, cookies, expected_status, label=""):
    prefix = f"{label} " if label else ""
    try:
        resp = request(method, path, cookies)
        ok = resp.status_code == expected_status
        mark = "✓" if ok else "✗"
        print(f"{mark} {prefix}{method} {path} - {resp.status_code} (expected {expected_status})")
        return ok
    except Exception as e:
        print(f"✗ {prefix}{method} {path} - {e}")
        return False


def expect_json_200(method, path, cookies, label=""):
    prefix = f"{label} " if label else ""
    try:
        resp = request(method, path, cookies)
        if resp.status_code != 200:
            print(f"✗ {prefix}{method} {path} - {resp.status_code} (expected 200)")
            return False
        body = resp.text.strip()
        if not body:
            print(f"✗ {prefix}{method} {path} - empty body")
            return False
        try:
            parsed = resp.json()
        except (json.JSONDecodeError, ValueError):
            print(f"✗ {prefix}{method} {path} - non-JSON body")
            return False
        if parsed is None or parsed == "" or parsed == [] or parsed == {}:
            # Allow empty containers only if they're valid JSON structures that
            # some list endpoints might return; still require parseable non-null.
            # Treat null alone as failure; empty list/dict are parseable.
            if parsed is None:
                print(f"✗ {prefix}{method} {path} - null JSON")
                return False
        print(f"✓ {prefix}{method} {path} - 200 JSON")
        return True
    except Exception as e:
        print(f"✗ {prefix}{method} {path} - {e}")
        return False


def test_conversation_flow(cookies) -> bool:
    print("\nTesting conversation flow (employee)...")
    try:
        resp = request("POST", "/conversations", cookies)
        if resp.status_code != 200:
            print(f"✗ Failed to create conversation: {resp.status_code}")
            return False
        conv_id = resp.json()["conversation_id"]
        print(f"✓ Created conversation {conv_id}")

        resp = request(
            "POST",
            f"/conversations/{conv_id}/runs",
            cookies,
            data={"message": "Fix my VPN connection"},
        )
        if resp.status_code != 200:
            print(f"✗ Failed to create run: {resp.status_code}")
            return False
        run_id = resp.json()["run_id"]
        print(f"✓ Created run {run_id}")
        return True
    except Exception as e:
        print(f"✗ Conversation flow - {e}")
        return False


def main() -> int:
    failures = 0

    print("Testing authentication (employee)...")
    employee_cookies = login("northstar-asha")
    if employee_cookies is None:
        return 1

    print("\nTesting employee-allowed endpoints (expect 200)...")
    for method, path in EMPLOYEE_OK:
        if not expect_status(method, path, employee_cookies, 200, label="employee"):
            failures += 1

    print("\nTesting employee-restricted endpoints (expect 403)...")
    for method, path in RESTRICTED:
        if not expect_status(method, path, employee_cookies, 403, label="employee"):
            failures += 1

    if not test_conversation_flow(employee_cookies):
        failures += 1

    print("\nTesting authentication (tenant_admin)...")
    admin_cookies = login("northstar-vikram")
    if admin_cookies is None:
        return 1

    print("\nTesting tenant_admin restricted endpoints (expect 200 JSON)...")
    for method, path in RESTRICTED:
        if not expect_json_200(method, path, admin_cookies, label="admin"):
            failures += 1

    print("\nDone!")
    if failures:
        print(f"{failures} check(s) failed")
        return 1
    print("All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
