# Current-state inventory (pre–SIGNAL redesign)

## HELIO `apps/web` (Next 15 / React 19 / port 3000)

| Route | File | Notes |
|-------|------|--------|
| `/login` | `app/login/page.tsx` | Persona picker; `auth.login` |
| `/` | `app/(app)/page.tsx` | Employee overview |
| `/support` | `app/(app)/support/page.tsx` | Guided + free-form; embeds bakery panel |
| `/tickets`, `/tickets/[id]` | tickets pages | HELIO tickets API |
| `/devices` | devices page | Devices API |
| `/approvals` | approvals page | HELIO approvals (distinct from bakery) |
| `/agent` | agent page | Run activity |
| `/evaluations` | evaluations page | Eval suite |
| `/analytics` | analytics page | Aggregates |
| `/admin`, `/knowledge`, `/security` | respective pages | Role-gated |

**Shell:** `components/app-shell.tsx` — `allowedHrefs(role)` filters nav; default theme dark on `<html className="dark">`.

**API:** `lib/api-client.ts` → `/api-backend/*`. Bakery embed: `lib/bakery-client.ts` → `/bakery-api/*` + `guided-helpdesk-panel.tsx`.

**UI stack:** Tailwind + shadcn-style `components/ui/*`, Radix, Lucide, Framer Motion, TanStack Query, Sonner.

## Bakery `apps/bakery_web` (Next 14 / React 18 / port 3001)

| Route | File |
|-------|------|
| `/` | Login personas |
| `/helpdesk` | Guided flow + My Tickets |
| `/it` | Approvals |

**API:** `lib/api-client.ts` cookie session → `/api` → bakery-api `:8002`.

## Known gaps (preserve truthfully)
- Not all 57 catalogue issues have specialised tools; many escalate to real tickets.
- Back stack may reset rather than true history.
- Theme toggle currently class-only; redesign defaults to light SIGNAL.
- Do not mix HELIO and Bakery approval contracts.
