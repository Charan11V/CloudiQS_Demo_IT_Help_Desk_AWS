# HELIO Implementation Matrix

Status as of: 2026-10-31

## Backend Modules

| Module | Route(s) | Status | Notes |
|--------|----------|--------|-------|
| **A. Authentication & Session** | `/auth/*` | ✅ Working | Demo login, session management, HttpOnly cookies |
| **B. Workspace Summary** | `/workspace/summary` | ✅ Working | Returns identity, devices, tickets, approvals |
| **C. Conversations & Runs** | `/conversations/*`, `/runs/*` | ✅ Working | Create conversation, run agent, poll status; `GET /runs` lists recent activity |
| **D. Tickets** | `/tickets/*` | ✅ Working | List, get, create, patch, comments; employees create P2–P4 (P1 SoD-gated to IT) |
| **E. Approvals/Actions** | `/approvals/*`, `/actions/*` | ✅ Working | List, propose, decide (approve/reject), execute |
| **F. Analytics** | `/analytics/*` | ✅ Working | Ticket analytics, agent run statistics (role-gated) |
| **G. Admin** | `/admin/*` | ✅ Working | Integrations test, users, policy GET/PATCH (demo ack), audit |
| **H. Knowledge** | `/knowledge` | ✅ Working | Search via `?q=`; upload admin-only |
| **I. Security** | `/security/*` | ✅ Working | Findings, escalations; upstream 403/4xx mapped (no 500 leak) |
| **J. Devices** | `/devices/*` | ✅ Working | List user devices, diagnostics |
| **K. Evaluations** | `/evaluations/*` | ✅ Working | List/start runs, get results/tests |
| **L. Notifications** | `/notifications/*` | ✅ Working | List, mark as read |

## Agent Engine

| Component | Status | Notes |
|-----------|--------|-------|
| Simulator | ✅ Working | VPN+device diagnosis, account unlock, conversation history support |
| Follow-up handling | ✅ Working | Detects follow-ups from history, provides concrete next steps |
| Tool registry | ✅ Working | 15+ real tools calling enterprise mock API |
| Evidence tracking | ✅ Working | Source, trust level, timestamps |
| Bedrock integration | 🟡 Partial | Framework present, fails gracefully if not configured |
| Ollama integration | 🟡 Partial | Framework present, falls back to simulator |

## Frontend Pages

| Page | Path | Status | Notes |
|------|------|--------|-------|
| Login | `/login` | ✅ Working | Persona selection |
| Dashboard | `/` | ✅ Working | Environment summary, quick CTAs |
| Support/Chat | `/support` | ✅ Working | open_ticket, request_approval, safe_instruction, view_evidence, escalate wired |
| Tickets | `/tickets`, `/tickets/[id]` | ✅ Working | Comment; status/reopen for IT roles (mock transitions) |
| Approvals | `/approvals` | ✅ Working | Decide + execute |
| Analytics | `/analytics` | ✅ Working | Ticket + agent-run stats; 403 UI for employees |
| Devices | `/devices` | ✅ Working | List + refresh |
| Knowledge | `/knowledge` | ✅ Working | Search button → `GET /knowledge?q=` |
| Security | `/security` | ✅ Working | Findings + escalations list (role-restricted) |
| Admin | `/admin` | ✅ Working | Integration test + policy save (demo PATCH) |
| Evaluations | `/evaluations` | ✅ Working | List + run curated suite |
| Agent Activity | `/agent` | ✅ Working | Recent runs from `GET /runs` |
| Shell | header | ✅ Working | Notifications dropdown + mark-read; Search → knowledge |

## Chat recommended actions

| Action | Status | Behavior |
|--------|--------|----------|
| `open_ticket` | ✅ | `POST /tickets` (default P3) |
| `request_approval` | ✅ | `POST /actions/propose` |
| `safe_instruction` | ✅ | Toast only (intentional) |
| `view_evidence` | ✅ | Toast from `AgentOutput.findings`; optional navigate `/security` |
| `escalate` | ✅ | Employee: P2 ticket (P1 SoD). IT/security: P1 ticket + `POST /security/escalations` |

## Intentional limitations (not dead UI)

- **P1 ticket create** — employees get 403 from mock SoD; escalate uses **P2** for employees
- **Security escalations POST** — employees **403** (not 500); IT engineer / security analyst only
- **Ticket status patch** — IT roles only; employees can comment on own tickets
- **Admin policy PATCH** — demo acknowledgment (no durable mock policy store)
- **Live LLM** — Bedrock/Ollama optional; simulator default
- **Notification delivery** — in-app list/mark-read only (no email/Slack)

## Verified API evidence (2026-10-31)

```
POST /tickets asha P3 → 201 northstar-INC-NEW-a69493615d
POST /tickets asha P2 → 201 northstar-INC-NEW-95459006c5
POST /tickets asha P1 → 403 (SoD: P1 requires IT role)
POST /security/escalations asha → 403
POST /tickets rahul P1 → 201 northstar-INC-NEW-c9b7c7200e
POST /security/escalations rahul + ticket_id → 200 northstar-ESC-05a307fc3ae3
  (ticket_id forwarded)
PATCH /admin/policy → 200
POST /evaluations/runs → 200
GET /knowledge?q=VPN → 200
GET /notifications → 200
GET /runs → 200
```

Role-aware `test_endpoints.py`: employee ACL + tenant_admin 200 JSON — passing.

## Docker Services

| Service | Port | Health | Notes |
|---------|------|--------|-------|
| `web` | 3000 | ✅ | Next.js 15 |
| `agent-api` | 8001 | ✅ | FastAPI + Simulator |
| `enterprise-mock-api` | 8000 | ✅ | Mutable SQLite mock |

Rebuild after this sweep: `docker compose up --build -d web agent-api`
