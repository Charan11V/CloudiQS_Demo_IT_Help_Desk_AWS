# Agentic Bakery Pro - IT Helpdesk Backend

Complete FastAPI backend for guided IT helpdesk with P0 tool implementations.

## Project Structure

```
bakery_api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration settings
│   ├── db.py                # Database session management
│   ├── models.py            # SQLAlchemy models (all tables)
│   ├── seed.py              # Database seeding from demo_seed.json
│   ├── auth/
│   │   ├── __init__.py
│   │   └── session.py       # Session management & auth
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Demo login & /api/me
│   │   ├── catalog.py       # GET /api/catalog
│   │   ├── conversations.py # Conversation turns
│   │   ├── actions.py       # Action intents & execution
│   │   ├── approvals.py     # IT approval workflow
│   │   ├── tickets.py       # Ticket management
│   │   └── dev.py           # Dev/health endpoints
│   └── services/
│       ├── __init__.py
│       ├── guided_engine.py # Deterministic state machine
│       └── tools/
│           ├── __init__.py
│           ├── unlock_account.py     # ID-01
│           ├── disk_cleanup.py       # DEV-01
│           ├── vpn_certificate.py    # NET-01
│           └── quick_tools.py        # NET-02, DEV-04, APP-01, PRINT-02
├── requirements.txt
├── Dockerfile
└── README.md
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Create docker-compose.yml in parent directory
cd ..
docker-compose up -d postgres
cd bakery_api
docker-compose up --build
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+psycopg://bakery:bakery@localhost:5432/bakery"
export ALLOW_DEMO_LOGIN=1

# Seed database
python -m app.seed --reset

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication
- `POST /api/auth/demo-login` - Demo login with user_id
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

### Catalog
- `GET /api/catalog` - Get guided flow catalog (all 57 issues)
- `GET /api/catalog/issues/{issue_code}` - Get specific issue

### Conversations
- `POST /api/conversations` - Create new conversation
- `POST /api/conversations/{id}/turns` - Process a turn
- `GET /api/conversations/{id}` - Get conversation state

### Actions
- `POST /api/actions/intents` - Create action intent
- `POST /api/actions/{id}/consent` - User consent
- `POST /api/actions/{id}/execute` - Execute action
- `GET /api/actions/{id}` - Get action status

### Approvals (IT Engineers)
- `GET /api/approvals` - List pending approvals
- `POST /api/approvals/{id}/decision` - Approve/reject
- `GET /api/approvals/{id}` - Get approval details

### Tickets
- `GET /api/tickets/mine` - Get user's tickets
- `GET /api/tickets/{id}` - Get ticket details

### Dev/Health
- `POST /api/dev/seed/reset` - Reset database (demo only)
- `GET /api/dev/health` - Health check
- `GET /api/dev/stats` - System statistics

## Demo Users

### Northstar Technologies (northstar)
- **NS-001** (Asha Rao) - employee - Account locked, VPN cert expired, low disk space
- **NS-002** (Rahul Sharma) - it_engineer - Can approve actions
- **NS-003** (Priya Menon) - it_manager
- **NS-004** (Vikram Rao) - tenant_admin

### Beacon Retail (beacon)
- **BC-001** (Neha Kapoor) - employee - Outdated VPN client, VPN service degraded
- **BC-002** (David Thomas) - it_engineer
- **BC-003** (Meera Nair) - tenant_admin

## P0 Tool Implementations

### ✅ Fully Implemented
1. **ID-01** - `unlock_own_account` - Self-service unlock after identity verification
2. **DEV-01** - `run_mock_safe_cleanup` - Safe temp file cleanup with exact disk delta
3. **NET-01** - `renew_mock_vpn_certificate` - IT approval required, outage-aware
4. **NET-02** - `update_mock_vpn_client` - Client version update, outage-aware
5. **NET-04** - VPN outage detection - Creates waiting_external ticket
6. **DEV-04** - `perform_mock_restart` - Mock device restart
7. **APP-01** - `restart_mock_app_and_cache` - App restart with health verification
8. **PRINT-02** - `retry_or_cancel_own_print_job` - Own job management only

### 🔧 Needs Tools
- **APP-04/ID-06** - `request_entitlement_grant` - Approval workflow (pending implementation)
- **SEC-01** - `create_security_incident` - Security escalation (pending implementation)
- **REQ-01** - `install_mock_approved_software` - Software installation (pending implementation)

## Features

### ✅ Implemented
- Demo login with HttpOnly session cookies
- Tenant isolation on every query
- Optimistic locking with version checks
- Idempotency keys for mutations
- Audit event logging
- Independent verification reads
- Guided navigation from catalog
- Approval workflow for privileged actions
- Cross-tenant access denial (403)
- Outage-aware resolution (NET-04)

### ⚠️ Limitations
- P1 issues navigate to catalog but create escalation tickets (not fully implemented)
- Free-text matching uses simple keyword search (no LLM)
- Mock identity challenge not implemented (ID-01 assumes verified)
- Conversation back/resume partially implemented

## Database

### Tables
All required tables from spec are implemented:
- tenants, users, accounts, sessions, devices, temporary_files
- vpn_profiles, services, applications, app_installations
- entitlements, mailboxes, printers, print_jobs
- security_events, tickets, ticket_events
- conversations, messages, cases
- action_intents, approval_requests, action_executions, audit_events

### Seeding
Seed data loaded from `/specs/agentic_bakery_helpdesk/demo_seed.json` (or fallback minimal seed).

## Testing

```bash
# Reset and reseed database
curl -X POST http://localhost:8000/api/dev/seed/reset \
  -H "Cookie: bakery_session=YOUR_SESSION"

# Demo login as Asha
curl -X POST http://localhost:8000/api/auth/demo-login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"NS-001"}'

# Get catalog
curl http://localhost:8000/api/catalog

# Start conversation
curl -X POST http://localhost:8000/api/conversations \
  -H "Cookie: bakery_session=YOUR_SESSION"

# Process turn (select issue)
curl -X POST http://localhost:8000/api/conversations/CONV-XXX/turns \
  -H "Cookie: bakery_session=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{"option_id":"ID-01"}'
```

## Environment Variables

```bash
DATABASE_URL=postgresql+psycopg://bakery:bakery@postgres:5432/bakery
ALLOW_DEMO_LOGIN=1  # Enable demo login
SPECS_PATH=/specs   # Path to spec files (or fallback to local)
CORS_ORIGINS=["http://localhost:3000"]
```

## Production Notes

- Set `ALLOW_DEMO_LOGIN=0` in production
- Replace demo login with real Cognito/OAuth
- Use proper secret key for sessions
- Enable HTTPS
- Add rate limiting
- Add comprehensive logging

## Known Gaps

1. **P1 tools** - Most P1 issues navigable but create generic tickets
2. **Free-text intent parsing** - Simple keyword match, no LLM
3. **Device selection** - Auto-selects if single device, needs multi-device picker
4. **Back navigation** - State saved but navigation needs refinement
5. **Attachment handling** - Metadata stored, no actual file upload
6. **Multi-issue splitting** - Planned, not fully implemented

## What Works End-to-End

✅ Account unlock (ID-01)
✅ Disk cleanup with verification (DEV-01)
✅ VPN cert renewal with approval (NET-01)
✅ VPN client update with outage check (NET-02 + NET-04)
✅ Device restart (DEV-04)
✅ App restart (APP-01)
✅ Print job retry/cancel (PRINT-02)
✅ Unknown issue → ticket creation
✅ Talk to IT → escalation ticket
✅ Cross-tenant denial
✅ Idempotent mutations
✅ Approval workflow

## License

Demo system for CloudiQS Helio evaluation.
