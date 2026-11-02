# Agentic Bakery Pro - Web UI

Next.js 14 frontend for the Agentic Bakery Pro guided IT helpdesk system.

## Features

- **Demo Mode**: Simulated enterprise IT helpdesk with persistent demo banner
- **Role-Based Access**: Employee, IT Engineer, IT Manager, and Tenant Admin personas
- **Guided Navigation**: Dynamic categories from backend catalog (never hardcoded)
- **Conversational Interface**: Option chips, free text input, and control buttons
- **Action Workflow**: Consent, approval requests, and execution tracking
- **My Tickets**: View personal tickets with status tracking
- **IT Queue**: Approval management for IT engineers
- **Cookie-Based Auth**: Credentials included in all API requests

## Tech Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Lucide React** (icons)

## Prerequisites

- Node.js 20+
- Backend API running at `http://localhost:8002`

## Installation

```bash
npm install
```

## Configuration

### Environment Variables

Create `.env.local` (optional):

```bash
# API endpoint (defaults to /api with rewrites)
NEXT_PUBLIC_BAKERY_API_URL=http://localhost:8002

# For Docker deployment
BAKERY_API_URL=http://bakery-api:8000
```

### API Rewrites

The app uses Next.js rewrites in `next.config.js`:
- In Docker: `/api/*` → `http://bakery-api:8000/*`
- Locally: `/api/*` → `http://localhost:8002/*`

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Docker Build

```bash
docker build -t bakery-web .
docker run -p 3000:3000 -e BAKERY_API_URL=http://bakery-api:8000 bakery-web
```

## Project Structure

```
apps/bakery_web/
├── app/
│   ├── page.tsx              # Login page
│   ├── layout.tsx            # Root layout
│   ├── globals.css           # Global styles
│   ├── helpdesk/
│   │   └── page.tsx          # Main helpdesk interface
│   └── it/
│       └── page.tsx          # IT approval queue
├── components/
│   ├── DemoModeBanner.tsx    # Persistent demo mode indicator
│   └── SidePanel.tsx         # User info & navigation
├── lib/
│   ├── api-client.ts         # API wrapper with credentials
│   └── types.ts              # TypeScript interfaces
├── package.json
├── next.config.js            # API rewrites
├── tailwind.config.ts
├── tsconfig.json
└── Dockerfile
```

## Demo Personas

| ID | Name | Role | Tenant |
|----|------|------|--------|
| NS-001 | Asha Rao | Employee | Northstar |
| NS-002 | Rahul Sharma | IT Engineer | Northstar |
| NS-003 | Priya Menon | IT Manager | Northstar |
| NS-004 | Vikram Rao | Tenant Admin | Northstar |
| BC-001 | Neha Kapoor | Employee | Beacon |
| BC-002 | David Thomas | IT Engineer | Beacon |

## API Integration

All API calls use `credentials: 'include'` for cookie-based authentication.

### Key Endpoints

- `POST /api/auth/demo-login` - Demo login
- `GET /api/me` - Current user info
- `GET /api/catalog` - Dynamic categories
- `POST /api/conversations` - Start conversation
- `POST /api/conversations/{id}/turns` - Send option/text/control
- `GET /api/tickets/mine` - My tickets
- `GET /api/approvals/pending` - IT pending approvals
- `POST /api/approvals/{id}/decision` - Approve/reject
- `POST /api/actions/{id}/consent` - Consent to action
- `POST /api/actions/{id}/execute` - Execute action

## Features by Page

### Login (`/`)
- Select demo persona
- Cookie-based session creation
- Redirects to `/helpdesk` on success

### Helpdesk (`/helpdesk`)
- Welcome with dynamic categories from backend
- Breadcrumb navigation
- Option selection (chips/cards)
- Free text input (always available)
- Controls: Back, Start Over, Something Else, Talk to IT
- Finding cards (diagnosis with evidence)
- Action proposals (consent/approval workflow)
- Ticket creation with real IDs
- Side panel: user info, devices, navigation

### My Tickets
- List of user's tickets
- Status, priority, team assignment
- Creation date
- Real-time status from backend

### IT Queue (`/it`)
- Pending approval requests
- Requester details
- Action description and impact
- Target resource information
- Approve/Reject with optional reason
- Real-time execution when approved

## Conversation Flow

1. **POST /api/conversations** - Start new conversation
2. **Response includes**: categories, options, state, assistant message
3. **User selects option** → **POST /conversations/{id}/turns** with `option_id`
4. **User types text** → **POST /conversations/{id}/turns** with `free_text`
5. **User clicks control** → **POST /conversations/{id}/turns** with `control`
6. **Action proposed** → User consents → **POST /actions/{id}/consent**
7. **Approval required** → IT reviews → **POST /approvals/{id}/decision**
8. **Execute when allowed** → **POST /actions/{id}/execute**

## Design Principles

- **Never hardcode 57 issues** - Always fetch from `/api/catalog`
- **Dynamic options** - Render `response.options` from backend
- **Cookie credentials** - All requests include `credentials: 'include'`
- **Real IDs** - Display actual `ticket_id`, `conversation_id`, `action_id` from API
- **Demo transparency** - Persistent banner shows "simulated enterprise systems"
- **No fake metrics** - Only show data from backend responses
- **Restrained enterprise SaaS** - Professional, not flashy

## Production Deployment

For production with Docker Compose:

```yaml
services:
  bakery-web:
    build: ./apps/bakery_web
    ports:
      - "3000:3000"
    environment:
      - BAKERY_API_URL=http://bakery-api:8000
    depends_on:
      - bakery-api
```

## Troubleshooting

### CORS Issues
- Ensure backend allows credentials from frontend origin
- Check `Access-Control-Allow-Credentials: true` header

### 401 Unauthorized
- Cookie may have expired
- Redirects to login page automatically

### API Rewrites Not Working
- Check `BAKERY_API_URL` environment variable
- Verify backend is running and accessible

## License

Internal CloudiQS Project
