# Visual QA — HELIO SIGNAL

## Screenshot targets
Capture from running apps after rebuild (`docker compose … up -d --build web bakery-web`):

| Screen | URL | Width |
|--------|-----|-------|
| Login | http://localhost:3000/login | 1440, 390 |
| Home | http://localhost:3000/ | 1440 |
| Support guided | http://localhost:3000/support | 1440, 390 |
| Tickets | http://localhost:3000/tickets | 1440 |
| Approvals | http://localhost:3000/approvals | 1440 |
| Bakery login | http://localhost:3001/ | 1440 |
| Bakery helpdesk | http://localhost:3001/helpdesk | 1440 |

Store under `docs/ui-redesign/screenshots/` when captured.

## Critique loop (pass 1 — implementation)

| Issue | Fix applied |
|-------|-------------|
| Dark periwinkle default shell | Light porcelain default; ink sidebar |
| Generic four KPI home tiles | Editorial greeting + assistant feature panel + requests/device |
| Blue chatbot bubbles on support | Feature panel + choice tiles + diagnosis/ticket surfaces |
| Bakery blue gradient login | Split brand + persona chooser matching HELIO |
| Theme toggle without full dark polish | Removed fake toggle; light default only |

## Mobile pass (390px)
- App shell: drawer nav, sticky header, safe-area padding, body scroll lock
- Login: stacked brand + sticky Enter CTA
- Support: single-column options, sticky Confirm, collapsible workspace context
- Home/tickets: tighter spacing, 44px+ touch targets
- Bakery: side panel stacks under main content on small screens

## Known polish follow-ups
- Free-form chat bubbles still use some legacy Card/Badge patterns inside describe mode
- Bakery helpdesk option grid restyled but not fully component-parity with HELIO guided panel
- Dark ops theme not shipped (intentionally — no incomplete switch)
