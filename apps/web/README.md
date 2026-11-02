# CloudiQS Web

Next.js App Router frontend for the CloudiQS enterprise IT helpdesk demo.

## Stack

- Next.js (App Router) + TypeScript
- Tailwind CSS
- TanStack Query
- Lucide icons
- Sonner toasts

## Development

```bash
pnpm install
pnpm dev
```

Environment variables are documented in `.env.example`. Prefer Docker Compose from the repository root for the full stack.

## Pages

| Route | Purpose |
|---|---|
| `/login` | Demo persona sign-in |
| `/` | Home / workspace summary |
| `/support` | Get help (guided + free-text support) |
| `/tickets` | Ticket list and detail |
| `/devices` | Assigned devices |
| `/approvals` | Approval review (IT roles) |
| `/admin` | Tenant administration |
| `/security` | Security findings |
| `/analytics` | Operational metrics |
| `/evaluations` | Evaluation runs |

## API integration

Browser calls use `/api-backend/*`, rewritten by Next.js to the agent API (`http://agent-api:8001` in Docker, `http://localhost:8001` locally). Session auth uses HttpOnly cookies with `credentials: 'include'`.

## Role-based navigation

- **Employee:** Home, Get help, Tickets, Devices
- **IT Engineer / Manager:** + Approvals
- **Tenant Admin:** + Admin
- **Security Analyst:** + Approvals, Security

## Notes

- Demo data is synthetic.
- Default orchestration mode is the offline simulator unless Bedrock credentials are configured.
