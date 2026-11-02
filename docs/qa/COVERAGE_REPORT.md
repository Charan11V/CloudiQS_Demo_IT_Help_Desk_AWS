# COVERAGE REPORT — Bakery

## Measured (executed 2026-11-01)

| Suite | Discovered | Executed | Passed | Failed | Skipped |
|-------|------------|----------|--------|--------|---------|
| `pytest tests/bakery` | 23 | 23 | **23** | 0 | 0 |
| `scripts/bakery_p0_retest.py` | 13 | 13 | see JSON | — | — |

Line/branch coverage via `pytest-cov` was **not** collected in this run (no `--cov` flag). Do not invent percentages.

## Module exercise evidence (integration, not line %)

| Module | Exercised by |
|--------|--------------|
| `routers/auth.py` | contracts logout/me |
| `routers/actions.py` | security consent gates + mutation workflows |
| `routers/approvals.py` | NET-01 + approval schema |
| `routers/tickets.py` | unknown ticket + cross-tenant |
| `routers/catalog.py` | 57 issues + 404 |
| `routers/dev.py` | seed reset role gate + stats |
| `tools/unlock_account.py` | ID-01 |
| `tools/disk_cleanup.py` | DEV-01 |
| `tools/vpn_certificate.py` | NET-01 |
| `tools/advanced_tools.create_security_incident` | SEC-01 |
| `guided_engine.py` | catalog navigation + free-text |

## Not measured

- Playwright E2E browser coverage
- pytest-cov line/branch %
- Live Bedrock / AgentCore
- Every non-P0 catalogue leaf mutation path
