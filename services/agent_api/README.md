# HELIO Agent API

FastAPI service for the HELIO autonomous IT operations agent.

## Features

- **Session-based authentication** with HttpOnly cookies
- **Multi-tenant isolation** with Northstar and Beacon demo tenants
- **Real tool execution** calling enterprise mock API
- **Deterministic simulator** for golden-path demonstrations
- **Agent orchestration** with Strands Agents (Bedrock ready)
- **Evidence reconciliation** with source authority rules
- **Comprehensive testing** with pytest

## Architecture

```
app/
├── main.py                  # FastAPI application
├── config.py                # Configuration
├── db.py                    # Database connection
├── models.py                # SQLAlchemy models
├── auth/
│   └── session.py           # Session management
├── enterprise/
│   └── client.py            # Enterprise API client
├── tools/
│   ├── identity.py          # Identity tools
│   ├── devices.py           # Device tools
│   ├── network.py           # Network/VPN tools
│   ├── knowledge.py         # Knowledge base tools
│   ├── tickets.py           # Ticket tools
│   └── registry.py          # Tool registry
├── agent/
│   ├── factory.py           # Agent factory
│   ├── simulator.py         # Deterministic simulator
│   └── prompts/
│       └── helpdesk_supervisor_v1.md
├── evidence/
│   └── reconciler.py        # Evidence reconciliation
└── routers/
    ├── auth.py              # Authentication
    ├── health.py            # Health checks
    ├── workspace.py         # Workspace summary
    ├── conversations.py     # Conversations and runs
    ├── tickets.py           # Tickets
    ├── actions.py           # Actions and approvals
    ├── admin.py             # Admin operations
    ├── analytics.py         # Analytics
    └── dev.py               # Dev tools
```

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export APP_DB_PATH=/tmp/helio_app.sqlite
export ENTERPRISE_API_URL=http://localhost:8000
export MODEL_PROVIDER=simulator

# Run application
uvicorn app.main:app --reload --port 8001

# Run tests
pytest -v
```

### Docker

```bash
# Build
docker build -t helio-agent-api .

# Run
docker run -p 8001:8001 \
  -e ENTERPRISE_API_URL=http://enterprise-mock-api:8000 \
  -e MODEL_PROVIDER=simulator \
  -v helio_data:/data \
  helio-agent-api
```

## Configuration

Environment variables:

- `MODEL_PROVIDER`: `simulator`, `bedrock`, or `ollama` (default: `simulator`)
- `BEDROCK_MODEL_ID`: Bedrock model ID (when using bedrock provider)
- `AWS_REGION`: AWS region for Bedrock
- `DEMO_NOW`: Demo timestamp (default: `2026-10-31T10:00:00Z`)
- `APP_SESSION_SIGNING_KEY`: Session signing key (set in production)
- `APP_DB_PATH`: Application database path (default: `/data/app.sqlite`)
- `ENTERPRISE_API_URL`: Enterprise mock API URL
- `CONFIRM_RESET_DEMO`: Confirmation token for demo reset

## API Endpoints

### Authentication
- `POST /auth/demo-login` - Login with persona
- `POST /auth/logout` - Logout
- `GET /auth/session` - Get current session

### Health
- `GET /health/ready` - Health check with dependencies

### Workspace
- `GET /workspace/summary` - Workspace summary

### Conversations
- `POST /conversations` - Create conversation
- `GET /conversations` - List conversations
- `GET /conversations/{id}` - Get conversation
- `POST /conversations/{id}/runs` - Create agent run
- `GET /runs/{id}` - Get run details
- `GET /runs/{id}/events` - Get run events
- `GET /runs/{id}/tool-events` - Get tool events

### Tickets
- `GET /tickets` - List tickets
- `GET /tickets/{id}` - Get ticket

### Actions
- `GET /actions/approvals` - List approvals
- `POST /actions/approvals/{id}/decision` - Approve/reject
- `POST /actions/approvals/{id}/execute` - Execute approved action

### Admin
- `GET /admin/integrations` - Get integrations
- `GET /admin/policy` - Get policy
- `GET /admin/audit` - Get audit log

### Analytics
- `GET /analytics/tickets` - Ticket analytics
- `GET /analytics/agent-runs` - Agent run analytics

### Dev
- `GET /dev/status` - Dev status
- `POST /dev/reset-demo` - Reset demo data (requires confirmation)

## Testing

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

## Model Providers

### Simulator (Default)
Deterministic golden-path orchestration for demos. Calls REAL tools but follows scripted workflows.

### Bedrock (Production)
Uses Strands Agents with Amazon Bedrock. Requires AWS credentials and model access.

### Ollama (Local)
Uses Ollama for local model inference. Requires Ollama installation.

## Demo Personas

### Northstar
- `northstar-asha`: Employee (Asha)
- `northstar-rahul`: IT Engineer (Rahul)
- `northstar-priya`: IT Manager (Priya)
- `northstar-vikram`: Admin (Vikram)
- `northstar-arjun-security`: Security Analyst (Arjun)

### Beacon
- `beacon-neha`: Employee (Neha)
- `beacon-david`: IT Engineer (David)
- `beacon-james`: IT Manager (James)
- `beacon-meera`: Admin (Meera)
- `beacon-noah-security`: Security Analyst (Noah)

## License

Proprietary - CloudiQS job demonstration prototype.
