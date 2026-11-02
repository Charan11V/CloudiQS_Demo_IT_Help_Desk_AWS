# 36 Browser and Backend Acceptance Scenarios

The `ui_e2e.jsonl` suite defines 36 product acceptance targets. Each needs executable Playwright + API code written against the actual HELIO app. **Screenshots or agent answers alone cannot pass them.**

For stable selectors, prefer `data-testid` names: `role-switcher`, `agent-provider-badge`, `chat-input`, `chat-send`, `message-source`, `source-drawer`, `ticket-submit`, `approval-propose`, `approval-approve`, `approval-execute`, `audit-table`, `evaluation-run`, `theme-toggle`, `sidebar-toggle`. Use accessible roles and labels when stable.

Test one genuine authenticated role per browser context. Do not trust a UI-only persona selector as proof of access control. Send direct API requests with alternate tenant IDs and protected IDs to verify backend rejection.

For each case provide evidence: Playwright result, actual HTTP request/response status, relevant state readback, screenshot on failure, generated trace ID and elapsed time. If feature not implemented, mark `SKIPPED_UNSUPPORTED` and file a gap—do not grant a pass.

## Acceptance catalogue

- **UI-001 — login:** login. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-002 — logout:** logout. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-003 — employee-home:** employee home. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-004 — chat-stream:** chat stream. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-005 — chat-citation:** chat citation. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-006 — chat-tool-trace:** chat tool trace. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-007 — ticket-create:** ticket create. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-008 — ticket-duplicate:** ticket duplicate. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-009 — ticket-priority:** ticket priority. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-010 — ticket-privacy:** ticket privacy. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-011 — admin-policies:** admin policies. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-012 — admin-integration:** admin integration. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-013 — KB-upload:** KB upload. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-014 — KB-current:** KB current. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-015 — approval-create:** approval create. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-016 — approval-review:** approval review. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-017 — approval-execute:** approval execute. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-018 — approval-expired:** approval expired. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-019 — approval-hash:** approval hash. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-020 — manager-analytics:** manager analytics. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-021 — cross-tenant-direct-url:** cross tenant direct url. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-022 — browser-mobile:** browser mobile. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-023 — browser-desktop:** browser desktop. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-024 — keyboard:** keyboard. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-025 — contrast:** contrast. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-026 — loading:** loading. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-027 — empty:** empty. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-028 — error:** error. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-029 — evaluation-page:** evaluation page. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-030 — eval-oracle-leak:** eval oracle leak. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-031 — network-isolation:** network isolation. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-032 — reset:** reset. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-033 — agentcore-label:** agentcore label. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-034 — audit-redact:** audit redact. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-035 — traces-time:** traces time. Confirm real persisted/authorised behaviour with browser + API evidence.

- **UI-036 — permissions-server:** permissions server. Confirm real persisted/authorised behaviour with browser + API evidence.
