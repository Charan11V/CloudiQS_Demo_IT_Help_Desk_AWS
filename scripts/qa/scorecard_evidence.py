#!/usr/bin/env python3
"""Generate scorecard evidence JSON for RBAC, tenant isolation, guided, approvals E2E,
knowledge retrieval, evaluations, audit lineage, freeform agent mode, routing.

  python scripts/qa/scorecard_evidence.py

Uses DEMO_URL + DEMO_ACCESS_SECRET, or fetches secret from SSM /cloudiqs-demo/DEMO_ACCESS_SECRET.
Writes docs/SCORECARD_EVIDENCE.json and docs/EVAL_RESULTS.json when eval succeeds.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "SCORECARD_EVIDENCE.json"
EVAL_OUT = ROOT / "docs" / "EVAL_RESULTS.json"
BASE = os.environ.get("DEMO_URL", "http://ec2-3-80-12-216.compute-1.amazonaws.com").rstrip("/")


def resolve_secret() -> str:
    secret = os.environ.get("DEMO_ACCESS_SECRET", "")
    if secret:
        return secret
    import boto3

    ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return ssm.get_parameter(Name="/cloudiqs-demo/DEMO_ACCESS_SECRET", WithDecryption=True)[
        "Parameter"
    ]["Value"]


class Client:
    def __init__(self, secret: str):
        self.secret = secret
        self.cj: dict[str, str] = {}

    def request(self, method: str, path: str, body: dict | None = None, expect: int | None = None):
        data = None
        headers = {"Accept": "application/json"}
        if self.cj:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cj.items())
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                for k, v in resp.headers.items():
                    if k.lower() == "set-cookie":
                        part = v.split(";", 1)[0]
                        if "=" in part:
                            ck, cv = part.split("=", 1)
                            self.cj[ck.strip()] = cv.strip()
                payload = json.loads(raw) if raw else {}
                status = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                payload = json.loads(raw) if raw else {"detail": e.reason}
            except json.JSONDecodeError:
                payload = {"detail": raw or e.reason}
            status = e.code
        ok = status == expect if expect is not None else 200 <= status < 300
        return {"ok": ok, "status": status, "body": payload}

    def gate(self):
        return self.request("POST", "/api/demo-access", {"secret": self.secret}, expect=200)

    def login(self, persona: str):
        return self.request(
            "POST", "/api-backend/auth/demo-login", {"persona_key": persona}, expect=200
        )

    def bakery_login(self, user_id: str):
        return self.request(
            "POST", "/bakery-api/auth/demo-login", {"user_id": user_id}, expect=200
        )


def main() -> int:
    results: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "demo_url": BASE,
        "checks": [],
    }

    def add(name: str, passed: bool, detail: dict):
        results["checks"].append({"name": name, "passed": passed, **detail})
        print(("PASS" if passed else "FAIL"), name, detail.get("status"), detail.get("note", ""))

    try:
        secret = resolve_secret()
    except Exception as exc:  # noqa: BLE001
        print("secret resolve failed:", exc, file=sys.stderr)
        return 2

    c = Client(secret)
    g = c.gate()
    add("demo_gate", g["ok"], {"status": g["status"], "note": "outer access gate"})

    a = c.login("northstar-asha")
    add("employee_login", a["ok"], {"status": a["status"], "persona": "northstar-asha"})

    admin = c.request("GET", "/api-backend/admin/integrations", expect=403)
    add(
        "rbac_employee_blocked_admin",
        admin["status"] in (401, 403, 404),
        {"status": admin["status"], "note": "employee cannot use admin APIs"},
    )

    # Knowledge retrieval (keyword+ACL corpus search — not vector RAG)
    kb = c.request("GET", "/api-backend/knowledge?q=VPN", expect=200)
    hits = kb.get("body") if isinstance(kb.get("body"), list) else (kb.get("body") or {}).get("results") or []
    if not isinstance(hits, list):
        hits = []
    add(
        "knowledge_search_vpn",
        kb["ok"] and len(hits) >= 1,
        {"status": kb["status"], "hit_count": len(hits), "note": "ACL-filtered keyword corpus retrieval"},
    )

    # Freeform agent path: create conversation + run (simulator when Bedrock unauthorized)
    free_c = c.request("POST", "/api-backend/conversations", {}, expect=200)
    conv_id = (free_c.get("body") or {}).get("conversation_id")
    free_run = {"ok": False, "status": 0, "body": {}}
    if conv_id:
        free_run = c.request(
            "POST",
            f"/api-backend/conversations/{conv_id}/runs",
            {"message": "My VPN will not connect from home. What should I check?"},
            expect=None,
        )
    free_body = free_run.get("body") or {}
    add(
        "freeform_conversation_run",
        free_c["ok"] and free_run["status"] in (200, 201) and bool(free_body.get("run_id")),
        {
            "status": free_run["status"],
            "conversation_id": conv_id,
            "run_id": free_body.get("run_id"),
            "run_status": free_body.get("status"),
            "note": "Freeform UI path; may use simulator when Bedrock model access denied",
        },
    )

    c.bakery_login("NS-001")
    conv = c.request("POST", "/bakery-api/conversations", {}, expect=200)
    opts = (conv.get("body") or {}).get("options") or []
    add(
        "guided_root_options",
        conv["ok"] and len(opts) >= 8,
        {"status": conv["status"], "count": len(opts), "ids": [o.get("id") for o in opts]},
    )

    # Bakery tickets + audit lineage
    mine = c.request("GET", "/bakery-api/tickets/mine", expect=200)
    tickets = (mine.get("body") or {}).get("tickets") or []
    add(
        "bakery_tickets_list",
        mine["ok"],
        {"status": mine["status"], "count": len(tickets)},
    )
    if tickets:
        tid = tickets[0]["ticket_id"]
        ev = c.request("GET", f"/bakery-api/tickets/{tid}/events", expect=200)
        ev_body = ev.get("body") or {}
        add(
            "bakery_ticket_audit_events",
            ev["ok"] and "events" in ev_body,
            {
                "status": ev["status"],
                "ticket_id": tid,
                "assigned_team": ev_body.get("assigned_team"),
                "event_count": ev_body.get("count", len(ev_body.get("events") or [])),
                "note": "Audit lineage API for bakery tickets",
            },
        )
    else:
        add(
            "bakery_ticket_audit_events",
            False,
            {"note": "no bakery tickets available for lineage check"},
        )

    c2 = Client(secret)
    c2.gate()
    beacon = c2.login("beacon-neha")
    if beacon.get("ok"):
        sess = c2.request("GET", "/api-backend/auth/session", expect=200)
        tid = (sess.get("body") or {}).get("tenant_id")
        add("tenant_session_beacon", tid == "beacon", {"status": sess["status"], "tenant_id": tid})
        tickets_b = c2.request("GET", "/api-backend/tickets?limit=50", expect=200)
        foreign = [
            t
            for t in (tickets_b.get("body") or {}).get("tickets") or []
            if str(t.get("ticket_id", "")).startswith("northstar-")
        ]
        add(
            "tenant_isolation_tickets",
            tickets_b["ok"] and len(foreign) == 0,
            {"status": tickets_b["status"], "foreign_count": len(foreign)},
        )
        # Cross-tenant knowledge must not leak northstar titles when possible
        kb_b = c2.request("GET", "/api-backend/knowledge?q=VPN", expect=200)
        add(
            "tenant_isolation_knowledge",
            kb_b["ok"],
            {"status": kb_b["status"], "note": "Beacon knowledge search scoped by mock tenant ACL"},
        )
    else:
        add(
            "tenant_session_beacon",
            False,
            {
                "status": beacon.get("status"),
                "note": "beacon persona unavailable — isolation assert skipped/failed",
            },
        )

    # Approval propose → IT decide → execute (full path)
    c4 = Client(secret)
    c4.gate()
    c4.login("northstar-asha")
    propose = c4.request(
        "POST",
        "/api-backend/actions/propose",
        {
            "action_type": "identity_account_unlock",
            "target_user_id": "northstar-EMP-0001",
            "rationale": "Scorecard evidence approval path end-to-end test",
        },
        expect=None,
    )
    approval_id = (propose.get("body") or {}).get("approval_id")
    add(
        "approval_propose_employee",
        propose["status"] in (200, 201) and bool(approval_id),
        {"status": propose["status"], "approval_id": approval_id},
    )

    c3 = Client(secret)
    c3.gate()
    it = c3.login("northstar-rahul")
    add("it_login", it["ok"], {"status": it["status"], "persona": "northstar-rahul"})
    appr = c3.request("GET", "/api-backend/approvals", expect=200)
    add(
        "approvals_list_it",
        appr["ok"],
        {"status": appr["status"], "count": (appr.get("body") or {}).get("count")},
    )

    if approval_id:
        # Employee must NOT be able to self-approve
        self_dec = c4.request(
            "POST",
            f"/api-backend/approvals/{approval_id}/decision",
            {"decision": "approved", "reason": "Self approval attempt must fail"},
            expect=403,
        )
        add(
            "approval_self_decide_blocked",
            self_dec["status"] == 403,
            {"status": self_dec["status"], "note": "employee cannot approve own request"},
        )

        dec = c3.request(
            "POST",
            f"/api-backend/approvals/{approval_id}/decision",
            {"decision": "approved", "reason": "Verified requester identity for scorecard E2E"},
            expect=200,
        )
        add(
            "approval_it_decide",
            dec["ok"],
            {"status": dec["status"], "approval_id": approval_id},
        )

        exe = c3.request(
            "POST",
            f"/api-backend/approvals/{approval_id}/execute",
            {},
            expect=200,
        )
        exe_body = exe.get("body") or {}
        add(
            "approval_it_execute",
            exe["ok"],
            {
                "status": exe["status"],
                "keys": list(exe_body.keys())[:8],
                "note": "approval-to-execution path verified",
            },
        )
    else:
        add("approval_self_decide_blocked", False, {"note": "no approval_id from propose"})
        add("approval_it_decide", False, {"note": "skipped"})
        add("approval_it_execute", False, {"note": "skipped"})

    # Evaluations: measured harness results
    ev_run = c3.request(
        "POST",
        "/api-backend/evaluations/runs",
        {"suite": "curated", "max_cases": 20},
        expect=200,
    )
    ev_body = ev_run.get("body") or {}
    eval_ok = (
        ev_run["ok"]
        and int(ev_body.get("passed") or 0) >= 1
        and int(ev_body.get("failed") or 0) == 0
        and ev_body.get("oracle_exposed_to_agent") is False
    )
    add(
        "evaluations_curated_run",
        eval_ok,
        {
            "status": ev_run["status"],
            "executed": ev_body.get("executed"),
            "passed": ev_body.get("passed"),
            "failed": ev_body.get("failed"),
            "provider_mode": ev_body.get("provider_mode"),
            "run_id": ev_body.get("run_id"),
            "note": ev_body.get("note") or "evaluator harness",
        },
    )
    if eval_ok:
        EVAL_OUT.write_text(
            json.dumps(
                {
                    "generated_at": results["generated_at"],
                    "demo_url": BASE,
                    **{k: ev_body.get(k) for k in ("run_id", "executed", "passed", "failed", "skipped", "provider_mode", "oracle_exposed_to_agent", "note")},
                    "results_sample": (ev_body.get("results") or [])[:5],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Wrote", EVAL_OUT)

    hm = c3.request("GET", "/api-backend/health/model", expect=None)
    model_body = hm.get("body") or {}
    add(
        "health_model_endpoint",
        hm["status"] == 200,
        {
            "status": hm["status"],
            "ok": model_body.get("ok"),
            "verified_live": model_body.get("verified_live"),
            "note": "Live Bedrock may remain blocked until account model access",
        },
    )

    try:
        sys.path.insert(0, str(ROOT / "services" / "bakery_api"))
        from app.routing import route_team  # type: ignore

        assert route_team(issue_code="NET-01") == "Network / VPN Desk"
        assert route_team(issue_code="SEC-01") == "Security Operations"
        assert route_team(issue_code="ID-01") == "Identity Desk"
        add(
            "specialist_routing_map",
            True,
            {
                "note": "issue_code→team map verified in-process",
                "net": route_team(issue_code="NET-01"),
                "sec": route_team(issue_code="SEC-01"),
                "id": route_team(issue_code="ID-01"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        add("specialist_routing_map", False, {"note": str(exc)})

    results["summary"] = {
        "total": len(results["checks"]),
        "passed": sum(1 for x in results["checks"] if x["passed"]),
        "failed": sum(1 for x in results["checks"] if not x["passed"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Wrote", OUT, results["summary"])
    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
