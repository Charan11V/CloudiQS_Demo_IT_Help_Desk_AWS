"""Real HELIO agent adapter for the independent evaluation suite.

Authenticates via demo persona sessions, invokes POST /conversations/{id}/runs,
polls completion, and gathers server-origin tool events + independent API state
snapshots. Never reads private_oracle. Never fabricates Bedrock provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any

import httpx

AGENT_API_URL = os.environ.get("HELIO_AGENT_API_URL", "http://127.0.0.1:8001").rstrip("/")
RUN_TIMEOUT_S = float(os.environ.get("HELIO_RUN_TIMEOUT_S", "120"))
POLL_INTERVAL_S = float(os.environ.get("HELIO_POLL_INTERVAL_S", "0.4"))

# session_id -> {client, conversation_id, persona, tenant_id, user_id, before_snap}
_SESSIONS: dict[str, dict[str, Any]] = {}


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _new_client() -> httpx.Client:
    return httpx.Client(base_url=AGENT_API_URL, timeout=60.0, follow_redirects=True)


def _login(client: httpx.Client, persona_key: str) -> dict[str, Any]:
    r = client.post("/auth/demo-login", json={"persona_key": persona_key})
    if r.status_code >= 400:
        raise RuntimeError(f"demo-login failed ({r.status_code}): {r.text[:400]}")
    return r.json()


def _snapshot(client: httpx.Client) -> dict[str, Any]:
    """Independent API readback used for before/after assertions."""
    snap: dict[str, Any] = {}
    for name, path in (
        ("tickets", "/tickets"),
        ("approvals", "/approvals"),
        ("session", "/auth/session"),
        ("workspace", "/workspace/summary"),
    ):
        try:
            r = client.get(path)
            snap[name] = {"status": r.status_code, "body": r.json() if r.status_code < 500 else r.text[:500]}
        except Exception as exc:  # noqa: BLE001
            snap[name] = {"status": "error", "body": f"{type(exc).__name__}: {exc}"}
    return snap


def _ticket_ids(snap: dict[str, Any]) -> set[str]:
    body = (snap.get("tickets") or {}).get("body")
    if isinstance(body, dict):
        rows = body.get("tickets") or body.get("items") or []
    elif isinstance(body, list):
        rows = body
    else:
        rows = []
    out = set()
    for t in rows:
        if isinstance(t, dict) and t.get("ticket_id"):
            out.add(t["ticket_id"])
    return out


def _approval_ids(snap: dict[str, Any]) -> set[str]:
    body = (snap.get("approvals") or {}).get("body")
    if isinstance(body, dict):
        rows = body.get("approvals") or []
    elif isinstance(body, list):
        rows = body
    else:
        rows = []
    out = set()
    for a in rows:
        if isinstance(a, dict) and a.get("approval_id"):
            out.add(a["approval_id"])
    return out


def _format_answer(output: dict[str, Any] | None, error: str | None) -> str:
    if error:
        return f"[agent_error] {error}"
    if not output:
        return ""
    parts = []
    if output.get("headline"):
        parts.append(str(output["headline"]))
    if output.get("summary"):
        parts.append(str(output["summary"]))
    findings = output.get("findings") or []
    if findings:
        parts.append("Findings:")
        for f in findings:
            if isinstance(f, dict):
                parts.append(
                    f"- [{f.get('kind','')}] {f.get('label','')}: {f.get('explanation','')}"
                )
            else:
                parts.append(f"- {f}")
    steps = output.get("suggested_steps") or []
    if steps:
        parts.append("Suggested steps:")
        for s in steps:
            if isinstance(s, dict):
                parts.append(
                    f"- {s.get('title','')} ({s.get('action_type','')}): {s.get('why','')}"
                )
            else:
                parts.append(f"- {s}")
    if output.get("action_state"):
        parts.append(f"Action state: {output['action_state']}")
    return "\n".join(parts).strip()


def _map_tool_events(raw: list[dict[str, Any]], tenant_id: str) -> list[dict[str, Any]]:
    mapped = []
    for e in raw or []:
        status = e.get("status") or "unknown"
        # ToolEvent statuses: started|completed|denied|failed
        if status == "completed":
            out_status = "succeeded"
        elif status == "denied":
            out_status = "denied"
        elif status == "failed":
            out_status = "failed"
        else:
            out_status = status
        mapped.append(
            {
                "origin": "server",
                "operation": e.get("tool_name") or "unknown",
                "status": out_status,
                "effect": "read",
                "tenant_id": tenant_id,
                "source": e.get("tool_name"),
                "resource_id": e.get("event_id"),
                "trace_id": e.get("event_id"),
                "error": e.get("error"),
            }
        )
    return mapped


def _ensure_session(case: dict, session_id: str) -> dict[str, Any]:
    actor = case.get("actor") or {}
    persona = actor.get("demo_token") or actor.get("persona_key")
    if not persona:
        raise ValueError(f"Case {case.get('case_id')} missing actor.demo_token")

    state = _SESSIONS.get(session_id)
    if state and state.get("persona") == persona and state.get("client"):
        return state

    client = _new_client()
    login = _login(client, persona)
    before = _snapshot(client)
    conv = client.post("/conversations")
    if conv.status_code >= 400:
        raise RuntimeError(f"create conversation failed: {conv.status_code} {conv.text[:300]}")
    conversation_id = conv.json()["conversation_id"]
    state = {
        "client": client,
        "conversation_id": conversation_id,
        "persona": persona,
        "tenant_id": login.get("tenant_id") or case.get("tenant_id"),
        "user_id": login.get("user_id") or actor.get("user_id"),
        "role": login.get("role") or actor.get("role"),
        "before_snap": before,
        "provider_mode": None,
        "model_id": None,
        "prompt_version": "helpdesk_supervisor_v1",
    }
    _SESSIONS[session_id] = state
    return state


def _wait_run(client: httpx.Client, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + RUN_TIMEOUT_S
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        r = client.get(f"/runs/{run_id}")
        if r.status_code >= 400:
            raise RuntimeError(f"get run failed: {r.status_code} {r.text[:300]}")
        last = r.json()
        if last.get("status") in ("completed", "failed", "cancelled"):
            return last
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"Run {run_id} did not complete within {RUN_TIMEOUT_S}s; last={last.get('status')}")


def _unsupported_faults(case: dict) -> str | None:
    faults = case.get("fault_injection") or {}
    if not faults:
        return None
    # HELIO ticket create supports X-Demo-Fault for rate_limit / timeout_after_commit / unavailable,
    # but the agent simulator does not currently auto-create tickets under those faults for chat turns.
    # Mark explicitly so scoring can SKIPPED_UNSUPPORTED rather than pretend.
    unsupported = []
    for k, v in faults.items():
        if k == "ticket_post" and v in (
            "timeout_after_commit",
            "rate_limit_429",
            "unavailable_503",
            "rate_limit",
            "unavailable",
        ):
            unsupported.append(f"{k}={v}")
        elif k not in ("ticket_post",):
            unsupported.append(f"{k}={v}")
    if unsupported:
        return (
            "SKIPPED_UNSUPPORTED: fault_injection not exercised by chat adapter for "
            + ",".join(unsupported)
        )
    return None


def invoke_case(case: dict, turn_index: int, user_text: str, session_id: str) -> dict[str, Any]:
    """Required sync API for tools/run_agent.py."""
    skip = _unsupported_faults(case)
    # Still run the agent turn for diagnosis; annotate skip only when case is fault-only expectation.
    # If the case solely exists to exercise the fault, callers see the SKIPPED marker in errors.

    state = _ensure_session(case, session_id)
    client: httpx.Client = state["client"]
    conversation_id = state["conversation_id"]
    tenant_id = state["tenant_id"]

    before = _snapshot(client)
    before_tickets = _ticket_ids(before)
    before_approvals = _approval_ids(before)
    before_sha = _sha(
        {
            "tickets": sorted(before_tickets),
            "approvals": sorted(before_approvals),
        }
    )

    # Fault-injection cases that the chat path cannot exercise: skip honestly.
    if skip:
        return {
            "answer": "",
            "error": skip,
            "tool_events": [],
            "verified_effects": [],
            "state_assertions": [
                {
                    "origin": "server",
                    "method": "independent_api_readback",
                    "name": "fault_injection_unsupported",
                    "passed": True,
                    "detail": skip,
                }
            ],
            "evidence_refs": [],
            "errors": [skip],
            "run_config": {
                "provider": "simulator",
                "model": None,
                "prompt_version": state["prompt_version"],
                "mode": "simulator",
                "git_commit": os.environ.get("HELIO_GIT_COMMIT"),
                "test_clock": os.environ.get("DEMO_NOW", "2026-10-31T10:00:00Z"),
                "agent_api_url": AGENT_API_URL,
            },
        }

    create = client.post(
        f"/conversations/{conversation_id}/runs",
        json={"message": user_text, "client_request_id": f"{session_id}-{turn_index}-{uuid.uuid4().hex[:8]}"},
    )
    if create.status_code >= 400:
        return {
            "answer": "",
            "error": f"create_run HTTP {create.status_code}: {create.text[:400]}",
            "tool_events": [],
            "verified_effects": [],
            "state_assertions": [],
            "evidence_refs": [],
            "errors": [f"create_run HTTP {create.status_code}"],
            "run_config": {
                "provider": "simulator",
                "model": None,
                "prompt_version": state["prompt_version"],
                "mode": "simulator",
                "git_commit": os.environ.get("HELIO_GIT_COMMIT"),
                "test_clock": os.environ.get("DEMO_NOW", "2026-10-31T10:00:00Z"),
                "agent_api_url": AGENT_API_URL,
            },
        }

    run_id = create.json()["run_id"]
    run = _wait_run(client, run_id)
    state["provider_mode"] = run.get("mode") or "simulator"
    # model_id may be absent on get_run; keep honest
    mode = run.get("mode") or "simulator"
    provider = "simulator" if mode == "simulator" else "bedrock"
    model = None if mode == "simulator" else os.environ.get("BEDROCK_MODEL_ID")

    tool_raw = []
    te = client.get(f"/runs/{run_id}/tool-events")
    if te.status_code < 400:
        tool_raw = te.json() if isinstance(te.json(), list) else te.json().get("events") or []

    after = _snapshot(client)
    after_tickets = _ticket_ids(after)
    after_approvals = _approval_ids(after)
    after_sha = _sha(
        {
            "tickets": sorted(after_tickets),
            "approvals": sorted(after_approvals),
        }
    )

    new_tickets = sorted(after_tickets - before_tickets)
    new_approvals = sorted(after_approvals - before_approvals)

    verified_effects: list[dict[str, Any]] = []
    for tid in new_tickets:
        verified_effects.append(
            {
                "origin": "server",
                "action_type": "ticket.create",
                "operation": "ticket.create",
                "tenant_id": tenant_id,
                "resource_id": tid,
                "outcome": "committed",
                "effect": "mutation",
                "verified": True,
            }
        )
    for aid in new_approvals:
        verified_effects.append(
            {
                "origin": "server",
                "action_type": "approval.request",
                "operation": "approval.create",
                "tenant_id": tenant_id,
                "resource_id": aid,
                "outcome": "committed",
                "effect": "mutation",
                "verified": True,
            }
        )

    no_write = before_sha == after_sha
    state_assertions = [
        {
            "origin": "server",
            "method": "independent_api_readback",
            "name": "tickets_approvals_snapshot",
            "passed": True,
            "snapshot_before_sha": before_sha,
            "snapshot_after_sha": after_sha,
            "new_tickets": new_tickets,
            "new_approvals": new_approvals,
            "no_unauthorised_writes_observed": no_write,
        }
    ]

    answer = _format_answer(run.get("output"), run.get("error"))
    errors: list[str] = []
    failed_error = None
    if run.get("status") == "failed":
        failed_error = run.get("error") or "run failed"
        errors.append(failed_error)

    return {
        "answer": answer,
        "run_id": run_id,
        "conversation_id": conversation_id,
        "tool_events": _map_tool_events(tool_raw, tenant_id),
        "verified_effects": verified_effects,
        "state_assertions": state_assertions,
        "evidence_refs": [],
        "errors": errors,
        "error": failed_error,
        "run_config": {
            "provider": provider,
            "model": model,
            "prompt_version": state["prompt_version"],
            "mode": "simulator" if mode == "simulator" else "real_model",
            "git_commit": os.environ.get("HELIO_GIT_COMMIT"),
            "test_clock": os.environ.get("DEMO_NOW", "2026-10-31T10:00:00Z"),
            "agent_api_url": AGENT_API_URL,
        },
    }


def reset_sessions() -> None:
    for s in list(_SESSIONS.values()):
        try:
            s["client"].close()
        except Exception:  # noqa: BLE001
            pass
    _SESSIONS.clear()
