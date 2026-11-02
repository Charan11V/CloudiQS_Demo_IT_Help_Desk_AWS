# HELIO Web Application

Next.js 15 App Router frontend for the HELIO Autonomous IT Operations platform.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS with custom design tokens
- **UI Components**: Radix UI primitives (shadcn-style)
- **Icons**: Lucide React
- **State Management**: TanStack Query
- **Tables**: TanStack Table
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts
- **Notifications**: Sonner
- **Fonts**: Inter + JetBrains Mono

## Design System

The application uses exact design tokens from the specification:

### Dark Theme (Primary)
- Background: `#0B101A`
- Sidebar: `#0D1420`
- Surface: `#111B29`, `#162334`, `#1B2B3D`
- Accent: `#8A9EFF` (periwinkle)
- Success: `#43D8AF`
- Warning: `#F3B562`
- Danger: `#F47F89`

## Development

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Type check
pnpm typecheck

# Lint
pnpm lint

# Build
pnpm build

# Run E2E tests
pnpm test:e2e
```

## Environment Variables

Create a `.env` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
DEMO_MODE=true
```

## Features

### Implemented Pages

1. **Login** (`/login`) - Persona chooser for demo authentication
2. **Overview** (`/`) - Employee workspace dashboard
3. **AI Support** (`/support`) - Chat interface with agent
4. **Tickets** (`/tickets`) - Ticket queue and detail views
5. **Devices** (`/devices`) - Hardware inventory
6. **Approvals** (`/approvals`) - Review pending actions
7. **Agent Activity** (`/agent`) - Run traces and diagnostics
8. **Analytics** (`/analytics`) - Metrics and KPIs
9. **Admin** (`/admin`) - System configuration
10. **Security** (`/security`) - Security findings
11. **Evaluations** (`/evaluations`) - Test runs
12. **Knowledge** (`/knowledge`) - KB search

### API Integration

All API calls use relative `/api-backend/*` paths which are proxied via Next.js rewrites to the FastAPI backend:

- In Docker: proxies to `http://agent-api:8001`
- Locally: proxies to `http://localhost:8001`

Requests include `credentials: 'include'` for HttpOnly cookie authentication.

## Docker Build

```bash
# Build image
docker build -t helio-web .

# Run container
docker run -p 3000:3000 -e AGENT_API_URL=http://agent-api:8001 helio-web
```

## Testing

E2E tests use Playwright:

1. Login flow with Asha persona
2. Navigation and logout
3. Support chat smoke test
4. Terminated user blocked

## Architecture

- **App Router**: Server and client components
- **Authentication**: Session-based via API cookies
- **API Client**: Centralized fetch wrapper with error handling
- **Layouts**: Nested layouts for authenticated routes
- **Components**: Reusable UI primitives in `/components/ui`

## Role-Based Navigation

Navigation items are filtered based on user role:

- **Employee**: Overview, Support, Tickets, Devices
- **IT Engineer**: + Approvals, Agent Activity
- **IT Manager**: + Analytics
- **Tenant Admin**: + Admin, Knowledge
- **Security Analyst**: + Security

## Design Principles

- Dark-first theme with light mode support
- 248px sidebar (72px collapsed)
- Max content width: 1500px
- Tabular numbers for metrics
- Accessible focus management
- Responsive: Desktop (1280+), Tablet (768-1279), Mobile (360-767)

## Known Limitations

- Some actions are disabled (marked in UI)
- Simulated enterprise data (synthetic)
- Offline simulator mode by default
- Demo authentication (not production-ready)
