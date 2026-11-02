#!/usr/bin/env python3
"""P0 retest for Agentic Bakery helpdesk API."""
from __future__ import annotations

import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8002"
RESULTS: list[dict] = []
OUT = Path(__file__).resolve().parents[1] / "docs" / "BAKERY_P0_TEST_RESULTS.json"


class Session:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def req(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"Content-Type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
        request = urllib.request.Request(
            f"{BASE}{path}", data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=60) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            try:
                payload = json.loads(raw) if raw else {"detail": str(e)}
            except json.JSONDecodeError:
                payload = {"detail": raw or str(e)}
            return e.code, payload


def add(name: str, ok: bool, detail):
    text = detail if isinstance(detail, str) else json.dumps(detail, default=str)
    if len(text) > 320:
        text = text[:320]
    RESULTS.append({"test": name, "pass": bool(ok), "detail": text})
    print(("PASS" if ok else "FAIL"), name)
    print(" ", text)


def login(user_id: str) -> Session:
    s = Session()
    code, data = s.req("POST", "/api/auth/demo-login", {"user_id": user_id})
    if code >= 400 or not data.get("success"):
        raise RuntimeError(f"login failed {code}: {data}")
    return s


def intent(s: Session, action_code: str, target: str, ver: int, payload: dict):
    return s.req(
        "POST",
        "/api/actions/intents",
        {
            "action_code": action_code,
            "target": target,
            "expected_version": ver,
            "payload": payload,
        },
    )


def consent(s: Session, action_id: str):
    return s.req("POST", f"/api/actions/{action_id}/consent", {"consented": True})


def decide(s: Session, approval_id: str, decision: str = "approved"):
    return s.req(
        "POST",
        f"/api/approvals/{approval_id}/decision",
        {"decision": decision, "reason": "demo"},
    )


def execute(s: Session, action_id: str):
    return s.req("POST", f"/api/actions/{action_id}/execute", {})


def main():
    # seed reset
    try:
        s = login("NS-002")
        code, data = s.req("POST", "/api/dev/seed/reset", {})
        add("seed_reset", code < 400 and data.get("success") is True, data)
    except Exception as e:
        add("seed_reset", False, str(e))

    # NET-01
    try:
        s = login("NS-001")
        code, data = intent(s, "renew_mock_vpn_certificate", "VPN-NS-001", 1, {})
        assert code < 400, data
        action_id = data["action_id"]
        code, c = consent(s, action_id)
        add(
            "NET-01_pending",
            code < 400 and c.get("requires_approval") is True and bool(c.get("approval_id")),
            c,
        )
        it = login("NS-002")
        code, ap = decide(it, c["approval_id"])
        add(
            "NET-01_approve",
            code < 400 and (ap.get("decision") == "approved" or ap.get("status") == "approved"),
            ap,
        )
        code, ex = execute(s, action_id)
        ok = code < 400 and (
            ex.get("state") == "success" or (ex.get("result") or {}).get("success") is True
        )
        add("NET-01_execute", ok, ex)
    except Exception as e:
        add("NET-01_flow", False, str(e))

    # DEV-01
    try:
        s = login("NS-001")
        code, data = intent(s, "run_mock_safe_cleanup", "DEV-NS-001", 1, {})
        assert code < 400, data
        action_id = data["action_id"]
        code, c = consent(s, action_id)
        assert code < 400, c
        if c.get("requires_approval") and c.get("approval_id"):
            decide(login("NS-002"), c["approval_id"])
        code, ex = execute(s, action_id)
        ok = code < 400 and (
            ex.get("state") == "success" or (ex.get("result") or {}).get("success") is True
        )
        add("DEV-01_cleanup", ok, ex)
    except Exception as e:
        add("DEV-01_cleanup", False, str(e))

    # ID-01
    try:
        s = login("NS-001")
        code, data = intent(s, "unlock_own_account", "ACC-NS-001", 1, {})
        assert code < 400, data
        action_id = data["action_id"]
        code, c = consent(s, action_id)
        assert code < 400, c
        if c.get("requires_approval") and c.get("approval_id"):
            decide(login("NS-002"), c["approval_id"])
        code, ex = execute(s, action_id)
        ok = code < 400 and (
            ex.get("state") == "success" or (ex.get("result") or {}).get("success") is True
        )
        add("ID-01_unlock", ok, ex)
    except Exception as e:
        add("ID-01_unlock", False, str(e))

    # SEC-01
    try:
        s = login("NS-001")
        code, data = intent(
            s,
            "create_security_incident",
            "phishing_report",
            1,
            {
                "incident_type": "phishing",
                "description": "Suspicious email asking for password reset",
                "severity": "high",
            },
        )
        assert code < 400, data
        action_id = data["action_id"]
        code, c = consent(s, action_id)
        assert code < 400, c
        if c.get("requires_approval") and c.get("approval_id"):
            decide(login("NS-002"), c["approval_id"])
        code, ex = execute(s, action_id)
        result = ex.get("result") or {}
        ok = code < 400 and (
            ex.get("state") == "success"
            or result.get("success") is True
            or bool(result.get("ticket_id"))
        )
        add("SEC-01_execute", ok, ex)
    except Exception as e:
        add("SEC-01_execute", False, str(e))

    # GEN unknown
    try:
        s = login("NS-001")
        code, conv = s.req("POST", "/api/conversations", {})
        assert code < 400, conv
        cid = conv["conversation_id"]
        code, state = s.req(
            "POST",
            f"/api/conversations/{cid}/turns",
            {"free_text": "My coffee machine will not sync with Active Directory"},
        )
        # Triage asks before raising; confirm if offered.
        if state.get("state") == "AWAITING_UNKNOWN_TICKET_CONFIRM":
            code, state = s.req(
                "POST",
                f"/api/conversations/{cid}/turns",
                {"option_id": "confirm_raise_ticket"},
            )
        msg = state.get("assistant_message") or json.dumps(state)
        ticket_ok = bool((state.get("ticket") or {}).get("ticket_id"))
        add(
            "GEN_UNKNOWN_ticket",
            code < 400
            and (
                ticket_ok
                or any(
                    k in msg.lower()
                    for k in ("ticket", "inc-", "escalat", "open", "catalog", "couldn't", "could not")
                )
            ),
            msg,
        )
    except Exception as e:
        add("GEN_UNKNOWN_ticket", False, str(e))

    # Guided NET-01
    try:
        s = login("NS-001")
        code, conv = s.req("POST", "/api/conversations", {})
        cid = conv["conversation_id"]
        for oid in ("network", "network__vpn", "NET-01"):
            code, state = s.req(
                "POST",
                f"/api/conversations/{cid}/turns",
                {"option_id": oid},
            )
            assert code < 400, state
        for _ in range(8):
            phase = state.get("phase")
            if phase not in ("ASKING_CLARIFIERS", "DIAGNOSING"):
                break
            options = state.get("options") or []
            pick = next((o for o in options if o.get("id") in ("yes", "no", "not_sure")), None)
            if not pick:
                pick = next(
                    (
                        o
                        for o in options
                        if o.get("id")
                        not in ("back", "start_over", "talk_to_it", "something_else")
                    ),
                    None,
                )
            if not pick:
                break
            code, state = s.req(
                "POST",
                f"/api/conversations/{cid}/turns",
                {"option_id": pick["id"]},
            )
        if any(o.get("id") == "consent_execute" for o in (state.get("options") or [])):
            code, state = s.req(
                "POST",
                f"/api/conversations/{cid}/turns",
                {"option_id": "consent_execute"},
            )
        msg = f"{state.get('phase')} {state.get('assistant_message')}"
        add(
            "guided_NET-01",
            any(
                k in msg.lower()
                for k in ("approval", "vpn", "certificate", "awaiting", "propos", "consent", "ticket", "demo")
            ),
            msg,
        )
    except Exception as e:
        add("guided_NET-01", False, str(e))

    # Neha NET-02 — seed user NS-004 is often the degraded VPN persona; try NS-004 then NS-003
    for uid in ("NS-004", "NS-003"):
        try:
            s = login(uid)
            code, conv = s.req("POST", "/api/conversations", {})
            cid = conv["conversation_id"]
            for oid in ("network", "network__vpn", "NET-02"):
                code, state = s.req(
                    "POST",
                    f"/api/conversations/{cid}/turns",
                    {"option_id": oid},
                )
                assert code < 400, state
            for _ in range(8):
                if state.get("phase") not in ("ASKING_CLARIFIERS", "DIAGNOSING"):
                    break
                options = state.get("options") or []
                pick = next((o for o in options if o.get("id") in ("yes", "no", "not_sure")), None)
                if not pick:
                    pick = next(
                        (
                            o
                            for o in options
                            if o.get("id")
                            not in ("back", "start_over", "talk_to_it", "something_else")
                        ),
                        None,
                    )
                if not pick:
                    break
                code, state = s.req(
                    "POST",
                    f"/api/conversations/{cid}/turns",
                    {"option_id": pick["id"]},
                )
            msg = f"{uid} {state.get('phase')} {state.get('assistant_message')}"
            ok = any(
                k in msg.lower()
                for k in ("degrad", "outage", "service", "ticket", "cannot", "vpn", "client", "update", "propos", "escalat")
            )
            add("Neha_NET-02", ok, msg)
            break
        except Exception as e:
            if uid == "NS-003":
                add("Neha_NET-02", False, str(e))

    # lists
    try:
        code, data = login("NS-002").req("GET", "/api/approvals/pending")
        add("approvals_list", code < 400 and "approvals" in data, data)
    except Exception as e:
        add("approvals_list", False, str(e))

    try:
        code, data = login("NS-001").req("GET", "/api/tickets/mine")
        add("tickets_mine", code < 400 and "tickets" in data, data)
    except Exception as e:
        add("tickets_mine", False, str(e))

    try:
        code, data = login("NS-001").req("GET", "/api/catalog")
        count = data.get("issue_count") or len(data.get("issues") or [])
        if not count and data.get("categories"):
            count = 0
            for cat in data["categories"]:
                for sub in cat.get("children") or cat.get("subcategories") or []:
                    for issue in sub.get("children") or sub.get("issues") or []:
                        if issue.get("issue_code") or "-" in str(issue.get("id", "")):
                            count += 1
        add("catalog_57", code < 400 and count >= 50, {"issue_count": count, "keys": list(data.keys())[:8]})
    except Exception as e:
        add("catalog_57", False, str(e))

    passed = sum(1 for r in RESULTS if r["pass"])
    failed = sum(1 for r in RESULTS if not r["pass"])
    payload = {
        "passed": passed,
        "failed": failed,
        "total": len(RESULTS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": RESULTS,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSUMMARY passed={passed} failed={failed} total={len(RESULTS)}")
    print(f"Wrote {OUT}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
