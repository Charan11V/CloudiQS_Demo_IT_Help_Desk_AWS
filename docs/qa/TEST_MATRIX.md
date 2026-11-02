# TEST MATRIX — Bakery

| Suite | Path | Gate | Requires |
|-------|------|------|----------|
| Security / tenant | `tests/bakery/security/` | P0 | API :8002 |
| P0 mutations | `tests/bakery/workflows/test_p0_mutations.py` | P0 | API + seed |
| Guided catalogue | `tests/bakery/workflows/test_guided_catalog.py` | P1 | API |
| Contracts | `tests/bakery/contracts/` | P0 | API |
| Seed / health | `tests/bakery/database/` | P1 | API |
| Legacy P0 script | `scripts/bakery_p0_retest.py` | P0 | API |
| Browser E2E | `tests/bakery/e2e/` (planned) | P1 | web :3001 + Playwright |
| Live AWS / Bedrock | `tests/bakery/live_aws/` | optional | AWS creds |

## Issue coverage (P0)

| Issue | Success mutate | Consent gate | Approval | Fail/ticket | Cross-tenant |
|-------|----------------|--------------|----------|-------------|--------------|
| ID-01 | yes | yes | n/a | — | peer execute denied |
| ID-02 | n/a | — | — | ticket path | — |
| ID-06 | partial | yes | required | — | — |
| NET-01 | yes | yes | yes | degraded warn | — |
| NET-02 | tool only | — | — | — | — |
| NET-04 | ticket | — | — | yes | — |
| DEV-01 | yes | yes | n/a | — | — |
| DEV-04 | tool fixed | — | — | — | — |
| APP-01 | tool | — | — | — | — |
| APP-04 | =ID-06 | — | — | — | — |
| PRINT-02 | tool | — | — | — | — |
| SEC-01 | yes | yes | n/a | escalated | — |
| REQ-01 | diagnosis fixed | — | — | — | — |
| GEN-UNKNOWN | ticket | — | — | yes | Beacon denied |

## Commands

```powershell
docker compose -f compose.bakery.yaml up -d --build
.\scripts\test-fast.ps1
.\scripts\test-full.ps1
```
