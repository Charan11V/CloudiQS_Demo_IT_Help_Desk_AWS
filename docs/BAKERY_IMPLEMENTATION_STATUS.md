# Agentic Bakery Pro — Implementation Status

**Demo Mode** stack (preserves HELIO compose): `compose.bakery.yaml`

| Service | URL |
|---------|-----|
| Employee / IT web | http://127.0.0.1:3001 |
| FastAPI | http://127.0.0.1:8002 |
| PostgreSQL | 127.0.0.1:5433 |

## Implemented (working)

- Guided catalogue navigation from `guided_flow_catalog.json` (**57 issues**)
- Free-text unknown → persisted ticket (`GEN-UNKNOWN`), never claimed as resolved
- Controls: Back / Start Over / Something Else / Talk to IT (via engine options)
- Cookie session auth (`bakery_session`), demo login, tenant-scoped APIs
- Action lifecycle: intent → consent → optional IT approval → execute → audit + verification
- Tool kwargs filtered by signature; timezone-aware expiry checks
- Employee UI `/helpdesk`, IT UI `/it`, Demo Mode banner
- Seed from `demo_seed.json` (`POST /api/dev/seed/reset`)

### Executable mock tools (mutations are real DB writes, labelled demo)

| Issue | Tool | Notes |
|-------|------|-------|
| ID-01 | `unlock_own_account` | Verified E2E |
| DEV-01 | `run_mock_safe_cleanup` | Verified E2E |
| NET-01 | `renew_mock_vpn_certificate` | IT approval; renews cert; may warn if VPN service degraded |
| NET-02 | `update_mock_vpn_client` | Wired in tool map |
| DEV-04 | `perform_mock_restart` | Wired |
| APP-01 | `restart_mock_app_and_cache` | Wired |
| PRINT-02 | `retry_or_cancel_own_print_job` | Wired |
| SEC-01 | `create_security_incident` | Creates SEC event + escalation ticket |
| ID-06 / APP-04 | `request_entitlement_grant` | Approval-gated |
| REQ-01 | `install_mock_approved_software` | Wired |

## P0 tests (`scripts/bakery_p0_retest.py`)

Latest: **13/13 passed** → `docs/BAKERY_P0_TEST_RESULTS.json`

Includes: seed reset, NET-01 propose/approve/execute, DEV-01, ID-01, SEC-01, GEN-UNKNOWN ticket, guided NET-01/NET-02 menu entry, approvals list, tickets/mine, catalog 57.

## Incomplete / deferred (honest)

- **ID-02** `issue_self_reset_challenge` — not implemented as a mutating tool; falls through to ticket/escalation
- **NET-04** `create_outage_linked_ticket` — not a dedicated tool; use ticket pathway
- Full diagnosis→consent→mutation for every P0 leaf via UI not exhaustively automated beyond the suite above
- Bedrock / Strands / AgentCore adapters are architectural hooks only (tool map + FastAPI), not live AWS agent runtime
- Catalogue leaves without a tool: navigate + open real ticket / escalate (no fake “resolved”)
- Web middleware cookie name fixed to `bakery_session`; eslint hook-deps warnings only
- HELIO stack left running as orphans alongside bakery compose

## Run

```bash
docker compose -f compose.bakery.yaml up -d --build
python scripts/bakery_p0_retest.py
```
