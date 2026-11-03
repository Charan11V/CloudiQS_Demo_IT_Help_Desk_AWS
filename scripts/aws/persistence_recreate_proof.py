#!/usr/bin/env python3
"""Prove bakery Postgres survives container recreate (seed-if-empty, no --reset).

Inserts a marker ticket into bakery-postgres, force-recreates bakery-api only,
then asserts the marker still exists in Postgres (and ideally via API).

  python scripts/aws/persistence_recreate_proof.py

Writes docs/PERSISTENCE_PROOF.json
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "PERSISTENCE_PROOF.json"
BASE = os.environ.get("DEMO_URL", "http://ec2-3-80-12-216.compute-1.amazonaws.com").rstrip("/")
REGION = os.environ.get("AWS_REGION", "us-east-1")
STACK = "CloudiQSDemoStack"


def resolve_secret() -> str:
    secret = os.environ.get("DEMO_ACCESS_SECRET", "")
    if secret:
        return secret
    ssm = boto3.client("ssm", region_name=REGION)
    return ssm.get_parameter(Name="/cloudiqs-demo/DEMO_ACCESS_SECRET", WithDecryption=True)[
        "Parameter"
    ]["Value"]


class Client:
    def __init__(self, secret: str):
        self.cj: dict[str, str] = {}
        self.secret = secret

    def request(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"Accept": "application/json"}
        if self.cj:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cj.items())
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode()
                for k, v in resp.headers.items():
                    if k.lower() == "set-cookie":
                        part = v.split(";", 1)[0]
                        if "=" in part:
                            ck, cv = part.split("=", 1)
                            self.cj[ck.strip()] = cv.strip()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"detail": raw}
            return e.code, payload


def wait_cmd(ssm, instance_id: str, command_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(5)
        out = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if out["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            return out
    raise TimeoutError(command_id)


def main() -> int:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    marker = f"PERSIST-PROOF-{stamp}"
    result: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "demo_url": BASE,
        "marker_ticket_id": marker,
        "steps": [],
    }

    secret = resolve_secret()
    cfn = boto3.client("cloudformation", region_name=REGION)
    outs = {
        o["OutputKey"]: o["OutputValue"]
        for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
    }
    instance_id = outs["InstanceId"]
    ssm = boto3.client("ssm", region_name=REGION)

    # Shell: insert marker → force-recreate bakery-api → wait healthy → count marker
    # Priority uses bakery enum (medium). Requester NS-001 matches demo bakery user.
    # Mirror fast_deploy env so compose.aws.yaml image vars resolve
    shell = f"""set -euo pipefail
cd /opt/cloudiqs-demo/compose
set +e; source /opt/cloudiqs-demo/env.sh 2>/dev/null; set -e
REGISTRY=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.${{AWS_REGION:-us-east-1}}.amazonaws.com
export ECR_WEB_IMAGE=${{ECR_WEB_IMAGE:-cloudiqs-demo-web:local}}
docker image inspect "$ECR_WEB_IMAGE" >/dev/null 2>&1 || export ECR_WEB_IMAGE=$REGISTRY/cloudiqs-demo-web:latest
export ECR_AGENT_IMAGE=${{ECR_AGENT_IMAGE:-cloudiqs-demo-agent-api:local}}
docker image inspect "$ECR_AGENT_IMAGE" >/dev/null 2>&1 || export ECR_AGENT_IMAGE=$REGISTRY/cloudiqs-demo-agent-api:latest
export ECR_MOCK_IMAGE=${{ECR_MOCK_IMAGE:-cloudiqs-demo-mock-api:local}}
docker image inspect "$ECR_MOCK_IMAGE" >/dev/null 2>&1 || export ECR_MOCK_IMAGE=$REGISTRY/cloudiqs-demo-mock-api:latest
export ECR_BAKERY_IMAGE=${{ECR_BAKERY_IMAGE:-bakery-api:local}}
MARKER='{marker}'
docker compose -f compose.aws.yaml exec -T bakery-postgres \\
  psql -U bakery -d bakery -v ON_ERROR_STOP=1 <<SQL
INSERT INTO tickets (ticket_id, tenant_id, requester, issue_code, summary, description, status, priority, assigned_team, version, created_at, updated_at)
SELECT '$MARKER',
       COALESCE((SELECT tenant_id FROM users WHERE user_id='NS-001' LIMIT 1), (SELECT tenant_id FROM tenants LIMIT 1)),
       'NS-001',
       'NET-01',
       '$MARKER',
       'persistence proof row',
       'open',
       'medium',
       'Network / VPN Desk',
       1,
       NOW(),
       NOW()
WHERE NOT EXISTS (SELECT 1 FROM tickets WHERE ticket_id='$MARKER');
SQL
echo INSERT_OK
BEFORE=$(docker compose -f compose.aws.yaml exec -T bakery-postgres psql -U bakery -d bakery -tAc "SELECT count(*) FROM tickets WHERE ticket_id='$MARKER';")
echo BEFORE_COUNT=$BEFORE
docker compose -f compose.aws.yaml up -d --no-deps --force-recreate bakery-api
for i in $(seq 1 48); do
  if docker compose -f compose.aws.yaml exec -T bakery-api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" >/dev/null 2>&1; then
    echo HEALTHY
    break
  fi
  sleep 5
done
AFTER=$(docker compose -f compose.aws.yaml exec -T bakery-postgres psql -U bakery -d bakery -tAc "SELECT count(*) FROM tickets WHERE ticket_id='$MARKER';")
echo AFTER_COUNT=$AFTER
grep -n "app.seed" compose.aws.yaml || true
! grep -q "app.seed --reset" compose.aws.yaml && echo NO_RESET_OK
"""

    send = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [shell]},
        TimeoutSeconds=600,
    )
    command_id = send["Command"]["CommandId"]
    inv = wait_cmd(ssm, instance_id, command_id, timeout=600)
    stdout = inv.get("StandardOutputContent") or ""
    stderr = inv.get("StandardErrorContent") or ""
    result["ssm"] = {
        "command_id": command_id,
        "status": inv["Status"],
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-1000:],
    }

    after_count = 0
    for line in stdout.splitlines():
        if line.startswith("AFTER_COUNT="):
            try:
                after_count = int(line.split("=", 1)[1].strip())
            except ValueError:
                pass

    # API visibility check
    c = Client(secret)
    c.request("POST", "/api/demo-access", {"secret": secret})
    c.request("POST", "/bakery-api/auth/demo-login", {"user_id": "NS-001"})
    st, mine = c.request("GET", "/bakery-api/tickets/mine")
    tickets = mine.get("tickets") or []
    found_api = any(t.get("ticket_id") == marker for t in tickets)
    result["api_list_status"] = st
    result["found_via_api"] = found_api
    result["found_via_sql"] = after_count >= 1
    result["no_reset_compose"] = "NO_RESET_OK" in stdout
    result["recreate_healthy"] = "HEALTHY" in stdout
    result["passed"] = (
        inv["Status"] == "Success"
        and after_count >= 1
        and "NO_RESET_OK" in stdout
        and "HEALTHY" in stdout
    )
    result["note"] = (
        "bakery-api force-recreated; postgres volume retained; compose uses seed-if-empty (no --reset)"
        if result["passed"]
        else "persistence proof failed — inspect ssm stdout/stderr"
    )

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "out": str(OUT), "after_count": after_count, "found_api": found_api}, indent=2))
    print(stdout[-800:])
    if stderr.strip():
        print("STDERR:", stderr[-600:], file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
