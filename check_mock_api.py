"""Test mock API directly."""
import requests

BASE = "http://localhost:8000"

# Get token for northstar-asha
token = "northstar-asha"  # This is the Bearer token (persona_key)
headers = {"Authorization": f"Bearer {token}"}

print("Testing mock API directly with northstar-asha token:\n")

# Test the endpoints
endpoints = [
    "/v1/admin/integrations",
    "/v1/admin/policy",
    "/v1/audit",
    "/v1/analytics"
]

for endpoint in endpoints:
    resp = requests.get(f"{BASE}{endpoint}", headers=headers, timeout=5)
    print(f"{endpoint}")
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.text[:200]}")
    print()
