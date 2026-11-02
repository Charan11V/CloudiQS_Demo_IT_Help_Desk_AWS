# Release verification — HELIO SIGNAL redesign

## Commands
```bash
docker compose -f compose.yaml -f compose.bakery.yaml up -d --build
# HELIO:  http://localhost:3000
# Bakery: http://localhost:3001
```

## Checks run
| Check | Result |
|-------|--------|
| `apps/web` `tsc --noEmit` | Pass |
| Docker rebuild `web` + `bakery-web` | Pass (exit 0) |
| Bakery ticket fallback smoke (`scripts/_smoke_ticket_fallback.py`) | Pass |
| Visual: `/login` SIGNAL split + personas | Pass |
| Visual: `/` employee home (assistant panel, requests, device) | Pass |
| Visual: `/support` guided categories + context rail | Pass |

## Preserved contracts
- HELIO auth/session + role nav (`allowedHrefs`)
- Bakery embed via `/bakery-api` + `guided-helpdesk-panel`
- Bakery standalone cookie auth + approvals decision API
- No fabricated KPIs; demo disclosure retained
- Light theme default; incomplete dark toggle removed

## Limitations
- Free-form Describe mode retains some legacy message chrome
- Bakery helpdesk not fully isomorphic with HELIO guided panel components
- `apps/bakery_web` has no local `typescript` binary in this environment for CLI tsc
- Playwright E2E suite for redesign not added in this pass (manual visual + smoke instead)

## Architecture note
Design tokens + `components/helio/*` live in `apps/web`; bakery mirrors tokens in `globals.css` + `helio-mark.tsx` (no shared package — Docker-safe).
