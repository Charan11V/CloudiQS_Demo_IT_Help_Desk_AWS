# FEATURE INVENTORY — Agentic Bakery Pro

Source of truth: `specs/agentic_bakery_helpdesk/CURSOR_MASTER_SPEC.md`, catalogue, seed, implemented code under `services/bakery_api` + `apps/bakery_web`.

Status legend: COMPLETE_AND_VERIFIED | IMPLEMENTED_UNTESTED | PARTIALLY_IMPLEMENTED | BROKEN | UI_ONLY | MOCK_ONLY | NOT_IMPLEMENTED | BLOCKED_EXTERNAL_DEPENDENCY

| ID | Expected | Sources | APIs | Tables | Roles | Coverage | Missing | Status | Defects | Actions |
|----|----------|---------|------|--------|-------|----------|---------|--------|---------|---------|
| AUTH-DEMO | Demo cookie login | `routers/auth.py`, `auth/session.py` | POST `/api/auth/demo-login` | users, sessions | any active user | contracts | password auth | COMPLETE_AND_VERIFIED | — | Revoke on logout done |
| AUTH-ME | Session identity + devices | `routers/auth.py` | GET `/api/auth/me` | users, devices, tenants | authenticated | contracts | — | COMPLETE_AND_VERIFIED | Was `/me` mismatch | Fixed nested `user` + devices |
| AUTH-LOGOUT | Clear + revoke session | `routers/auth.py` | POST `/api/auth/logout` | sessions | authenticated | contracts | — | COMPLETE_AND_VERIFIED | Cookie-only before | Revokes DB session |
| CAT-57 | Dynamic 57-issue menus | `routers/catalog.py`, catalog JSON | GET `/api/catalog` | — | authenticated | workflows | — | COMPLETE_AND_VERIFIED | Issue 404 tuple | HTTPException |
| GUIDE-NAV | Category→sub→issue | `guided_engine.py` | conversations turns | conversations, cases, messages | employee+ | workflows | True back-stack | PARTIALLY_IMPLEMENTED | Back≈start_over | Documented |
| GUIDE-CTRL | Back/Start/Else/Talk IT | guided_engine | turns control | tickets | authenticated | workflows | — | COMPLETE_AND_VERIFIED | — | — |
| GUIDE-FT | Free-text classify / ticket | guided_engine | turns free_text | tickets | employee | workflows | LLM classifier | PARTIALLY_IMPLEMENTED | Keyword map only | Ticket path honest |
| ID-01 | Unlock locked account | unlock_account, diagnosis | actions* | accounts, audit | owner | workflows/security | — | COMPLETE_AND_VERIFIED | Consent bypass | Execute gated |
| ID-02 | Self password reset | spec only | — | accounts | owner | none | tool | NOT_IMPLEMENTED | No tool | Ticket escalation |
| ID-06 | Entitlement grant | advanced_tools, diagnosis | actions + approvals | entitlements, audit | owner+approver | security partial | E2E approve grant | PARTIALLY_IMPLEMENTED | Missing justification | Payload fixed |
| NET-01 | VPN cert renew + IT approve | vpn_certificate | actions + approvals | vpn_profiles, audit | owner+IT | workflows | Connectivity claim | COMPLETE_AND_VERIFIED | TZ compare | Aware datetimes; degraded warned |
| NET-02 | VPN client update | quick_tools | actions | vpn_profiles | owner | guided entry | Full mutate assert | IMPLEMENTED_UNTESTED | — | Add mutate test |
| NET-04 | Outage-linked ticket | diagnosis + ticket | open_ticket | tickets | employee | guided | Dedicated tool | PARTIALLY_IMPLEMENTED | Was GEN-UNKNOWN | NET-04 issue_code |
| DEV-01 | Safe disk cleanup | disk_cleanup | actions | devices, temp_files, audit | owner | workflows | — | COMPLETE_AND_VERIFIED | — | — |
| DEV-04 | Pending restart | quick_tools | actions | devices, audit | owner | none mutate | Guided E2E | PARTIALLY_IMPLEMENTED | reboot_count missing | Incremented |
| APP-01 | Restart app/cache | quick_tools | actions | app_installations | owner | none | E2E | IMPLEMENTED_UNTESTED | — | Add workflow test |
| APP-04 | Entitlement (app) | same as ID-06 | actions + approvals | entitlements | owner+approver | none | — | PARTIALLY_IMPLEMENTED | Same as ID-06 | Shared tool |
| PRINT-02 | Retry/cancel own job | quick_tools | actions | print_jobs | owner | none | E2E | PARTIALLY_IMPLEMENTED | operation vs action | Mapped |
| SEC-01 | Phishing escalation | advanced_tools | actions | security_events, tickets | reporter | workflows | Analyst close | COMPLETE_AND_VERIFIED | — | Never fake-resolved |
| REQ-01 | Install approved app | advanced_tools, diagnosis | actions | app_installations | owner | none | E2E | PARTIALLY_IMPLEMENTED | Bad app_id | Resolve from seed allowlist |
| TKT-MINE | List own tickets | tickets.py | GET `/api/tickets/mine` | tickets | requester | workflows | Status transitions API | PARTIALLY_IMPLEMENTED | No transition API | Documented |
| TKT-GET | Ticket detail + RBAC | tickets.py | GET `/api/tickets/{id}` | tickets | requester/IT | security | — | COMPLETE_AND_VERIFIED | — | Tenant filtered |
| APPR-QUEUE | IT pending list | approvals.py | GET `/api/approvals/pending` | approval_requests | IT | contracts | — | COMPLETE_AND_VERIFIED | UI field mismatch | Enriched |
| APPR-DECIDE | Approve/reject | approvals.py | POST `.../decision` | approvals, intents | IT | workflows | Expire/cancel API | PARTIALLY_IMPLEMENTED | — | — |
| ACT-LIFECYCLE | Intent→consent→exec | actions.py | `/api/actions/*` | action_* | actor/IT | security+workflows | Payload freeze hash enforce | PARTIALLY_IMPLEMENTED | Execute without consent | Fixed |
| AUDIT | Audit on mutations | tools/* | — | audit_events | system | via tool results | Query API | PARTIALLY_IMPLEMENTED | No audit list API | — |
| UI-EMP | Helpdesk chat | `apps/bakery_web/helpdesk` | proxied /api | — | employee | none Playwright | Refresh resume | PARTIALLY_IMPLEMENTED | getMe/consent broken | Client fixed |
| UI-IT | Approval queue | `apps/bakery_web/it` | approvals | — | IT | none Playwright | — | PARTIALLY_IMPLEMENTED | decision payload | Client fixed |
| DEMO-BANNER | Demo Mode label | DemoModeBanner | — | — | all | visual | — | COMPLETE_AND_VERIFIED | — | — |
| SEED | demo_seed load | seed.py | POST `/api/dev/seed/reset` | all | IT only | database | — | COMPLETE_AND_VERIFIED | Any user reset | Role-gated |
| BEDROCK | Live agent runtime | — | — | — | — | none | AWS | BLOCKED_EXTERNAL_DEPENDENCY | Not wired | Local tools only |
| RAG-KB | Knowledge retrieval | — | — | — | — | none | AWS KB | NOT_IMPLEMENTED | — | — |
| NON-P0×45 | Catalogue leaves | catalog + ticket | turns | tickets | employee | catalog count | Per-issue adapters | PARTIALLY_IMPLEMENTED | Ticket fallback | Honest |

## Notes

- All mutating tools are **simulated** and must remain labelled Demo Mode.
- HELIO stack remains separate; Bakery uses `compose.bakery.yaml`.
