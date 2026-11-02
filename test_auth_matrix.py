"""Test endpoints with authorized personas."""
import requests

BASE = "http://localhost:8001"

# Test with different personas
personas = {
    "northstar-asha": "employee",
    "northstar-vikram": "tenant_admin",
    "northstar-priya": "it_manager",
    "northstar-arjun-security": "security_analyst"
}

endpoints_to_test = {
    "/admin/integrations": ["tenant_admin"],
    "/admin/policy": ["tenant_admin", "it_manager"],
    "/admin/audit": ["tenant_admin", "security_analyst"],
    "/analytics/tickets": ["tenant_admin", "it_manager"]
}

print("Testing authorization matrix:\n")
for persona_key, role in personas.items():
    print(f"\n{persona_key} ({role}):")
    print("=" * 60)
    
    # Login
    resp = requests.post(f"{BASE}/auth/demo-login", json={"persona_key": persona_key}, timeout=5)
    if resp.status_code != 200:
        print(f"  ✗ Login failed")
        continue
    cookies = resp.cookies
    
    # Test each endpoint
    for endpoint, allowed_roles in endpoints_to_test.items():
        resp = requests.get(f"{BASE}{endpoint}", cookies=cookies, timeout=5)
        expected = 200 if role in allowed_roles else 403
        status_icon = "✓" if resp.status_code == expected else "✗"
        print(f"  {status_icon} {endpoint:<25} → {resp.status_code} (expected {expected})")
