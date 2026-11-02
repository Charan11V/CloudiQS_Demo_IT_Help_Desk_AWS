# HELIO Test Results

**Date:** 2026-10-31 · **Mode:** `MODEL_PROVIDER=simulator` · **Runtime:** Docker Compose

## Baseline pack
- `pytest` in `cloudiqs_enterprise_demo_pack`: **14 passed** (after ticket/comment/integration/escalation extensions)
- `python scripts/validate_pack.py`: ok — 47 feeds, 2404 records, 160 eval cases

## Docker health
| Service | Port | Status |
|---|---|---|
| enterprise-mock-api | 127.0.0.1:8000 | healthy |
| agent-api | 127.0.0.1:8001 | healthy (`/health/ready` ok, mock connected) |
| web | 127.0.0.1:3000 | up (HTTP 200) |

## Hard-gate evidence (API)
| Gate | Result |
|---|---|
| Docker-local boot | PASS |
| Persona login (Asha) | PASS |
| Terminated Omar denied | PASS (401) |
| Wrong-tenant disclosure | PASS (Beacon → northstar ticket → **404**) |
| Forbidden mutation / Vikram unlock eligibility | PASS (`vikram eligible 0`) |
| Approval SoD (Rahul unlock) | PASS — propose → approve → execute `succeeded_mock`; IdP `account_state=active` |
| Real source evidence in agent run | PASS — tools: identity, devices, diagnostics, vpn, knowledge, outages |
| No phantom success | PASS — cert renewal remains proposal/blocked by MDM policy messaging |
| Idempotent ticket create | PASS — same Idempotency-Key → `idempotent_replay:true`, same ticket_id |
| Employee chat + engineer approvals | PASS (API); UI login + overview verified in browser |
| Persisted workflow | PASS — app SQLite runs/tool events + mock approvals/actions |

## Observed Asha simulator outcome
Headline: *Multiple issues identified: VPN certificate expired and device resource pressure*  
Findings include expired cert, 94% CPU / 4% disk, MDM noncompliance blocker.

## Bedrock
Not verified in this environment (no AWS credentials). Factory implements Strands+Bedrock path; fails honestly if enabled without access.

## UI browser verification
- Login persona chooser (Northstar/Beacon, Omar disabled) — PASS
- Overview greets **Good morning, Asha Rao**; employee nav limited to Workspace — PASS
- AI Support shows simulator diagnosis (expired cert, 94% CPU / 4% disk, MDM noncompliance) — PASS
- Mock API in Docker: **14 passed** (`PYTHONPATH=/app pytest -q /app/tests`)

## Remaining gaps (honest)
- Eval runner is deterministic policy harness over curated scenarios, not full 160 LLM adjudicated runs
- Event delivery uses persisted run-event polling (not full SSE reconnect UX polish)
- Playwright e2e suite under `apps/web` not fully executed in CI against Compose in this pass
- Seed approval execute may 409 on historical hash mismatches — **new** runtime approvals execute cleanly
- Bedrock live smoke **not verified** (no AWS credentials in environment)
- AgentCore Runtime / Cognito / real IdP mutations are intentionally out of scope
