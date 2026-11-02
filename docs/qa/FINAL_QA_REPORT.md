# FINAL QA REPORT — Agentic Bakery Pro

**Date:** 2026-11-01  
**Stack:** Next.js (`:3001`) + FastAPI (`:8002`) + Postgres (`:5433`) via `compose.bakery.yaml`  
**Mode:** Demo Mode (simulated enterprise mutations)

## Executive summary

Audit found multiple **P0** auth/consent and frontend contract defects. Those were fixed and locked with regression tests. Automated suite now **23/23 pytest passed** against the live Docker API with real seed resets and real DB mutations (not mocked success).

Release readiness for **local demo / guided P0 helpdesk**: **CONDITIONAL GO**  
Not ready for: live AWS Bedrock agent runtime, full 57-issue automated resolution, ticket lifecycle management UI.

## Tests executed

| Suite | Result |
|-------|--------|
| `python -m pytest tests/bakery -q` | **23 passed** |
| `python scripts/bakery_p0_retest.py` | **13 passed** |
| Security (consent, peer execute, tenant ticket, RBAC) | passed |
| P0 mutations (ID-01, DEV-01, NET-01, SEC-01, idempotency) | passed |
| Guided catalogue / unknown ticket | passed |
| API contracts (`/auth/me`, logout revoke, approvals schema) | passed |
| Seed/health | passed |

## Defects fixed this cycle (see DEFECT_LOG.md)

Consent bypass on execute; peer execute; frontend `/me`, consent body, approval decision body; catalog 404; VPN datetime; SEC kwargs; REQ-01 app_id; ID-06 justification; DEV-04 reboot_count; PRINT operation alias; logout revoke; seed-reset RBAC; post-fix options; approvals UI fields; IT side-panel link.

## Remaining risks / blockers

| Item | Severity | Notes |
|------|----------|-------|
| ID-02 self-reset tool | P1 | Ticket-only |
| Playwright E2E not authored | P2 | API covered; browser journeys not automated |
| Bedrock / Strands / AgentCore | Blocked | Tool architecture only |
| Ticket status transition API | P2 | Create/list only |
| True Back navigation stack | P2 | Resets to welcome |
| Non-P0 specialised adapters | P2 | Honest ticket fallback |
| pytest-cov line % | — | Not measured this run |

## Feature path coverage

- Catalogue leaves represented: **57** (navigation + ticket fallback)
- P0 mutate verified in pytest: **ID-01, DEV-01, NET-01, SEC-01** (+ gates)
- Security boundaries: employee approvals denied, seed reset IT-only, cross-tenant ticket 404, no execute without consent, peer employee cannot execute

## Commands

```powershell
docker compose -f compose.bakery.yaml up -d --build
.\scripts\test-fast.ps1
.\scripts\test-full.ps1
.\scripts\reset-test-db.ps1
```

URLs: http://127.0.0.1:3001 (UI) · http://127.0.0.1:8002/health (API)

## Deliverables

1. `docs/qa/FEATURE_INVENTORY.md`
2. `docs/qa/TEST_MATRIX.md`
3. `docs/qa/DEFECT_LOG.md`
4. `docs/qa/COVERAGE_REPORT.md`
5. `docs/qa/FINAL_QA_REPORT.md`
6. `tests/bakery/**` integration/security/workflow suite
7. Production fixes under `services/bakery_api` + `apps/bakery_web`
8. Scripts: `test-fast.ps1`, `test-full.ps1`, `reset-test-db.ps1`
