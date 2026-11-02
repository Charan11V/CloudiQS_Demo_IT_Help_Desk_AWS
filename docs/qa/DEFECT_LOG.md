# DEFECT LOG — Bakery QA

| ID | Sev | Title | Status | Evidence |
|----|-----|-------|--------|----------|
| DEF-001 | P0 | Execute without consent | **FIXED** | `actions.py` requires consented/approved; regression `test_cannot_execute_without_consent` |
| DEF-002 | P0 | Peer can execute another user's intent | **FIXED** | Actor/IT check; `test_peer_employee_cannot_execute_others_intent` |
| DEF-003 | P0 | Frontend `/api/me` wrong path | **FIXED** | `api-client.ts` → `/auth/me` |
| DEF-004 | P0 | IT approval decision body `{approved}` vs `{decision}` | **FIXED** | api-client maps decision |
| DEF-005 | P0 | Consent body empty `{}` → 422 | **FIXED** | sends `{consented:true}` |
| DEF-006 | P1 | Catalog issue 404 returned as body tuple | **FIXED** | HTTPException |
| DEF-007 | P1 | NET-01 naive/aware datetime crash | **FIXED** | vpn_certificate + session aware UTC |
| DEF-008 | P1 | SEC-01 unexpected `expected_version` kwarg | **FIXED** | inspect.signature filter |
| DEF-009 | P1 | REQ-01 hard-coded `approved_demo_app` | **FIXED** | diagnosis picks allowlisted uninstalled app |
| DEF-010 | P1 | ID-06 missing justification | **FIXED** | diagnosis payload + tool defaults |
| DEF-011 | P1 | DEV-04 did not increment `reboot_count` | **FIXED** | quick_tools |
| DEF-012 | P1 | PRINT-02 `operation` vs `action` | **FIXED** | diagnosis + executor alias |
| DEF-013 | P1 | Logout did not revoke session | **FIXED** | status=revoked |
| DEF-014 | P1 | Any user could seed-reset | **FIXED** | IT role required |
| DEF-015 | P1 | `yes_resolved`/`still_failing` unhandled | **FIXED** | guided_engine handlers |
| DEF-016 | P2 | Approvals UI fields missing | **FIXED** | enriched pending payload |
| DEF-017 | P2 | No IT link in employee side panel | **FIXED** | SidePanel link for IT roles |
| DEF-018 | P1 | ID-02 self-reset tool | **OPEN** | Not implemented — ticket only |
| DEF-019 | P2 | True “Back” stack navigation | **OPEN** | Back resets to welcome |
| DEF-020 | P2 | Ticket status transition API | **OPEN** | Create/list only |
| DEF-021 | P3 | Playwright E2E suite | **OPEN** | Not yet authored |
| DEF-022 | P3 | Live Bedrock evaluation | **BLOCKED** | No AWS agent wiring |

Reproduction for open items is via catalogue navigation / missing tool codes documented in FEATURE_INVENTORY.
