# Electric Violet Enterprise — redesign report

Date: 2026-11-01

## Summary

Replaced the SIGNAL blue system with an Electric Violet enterprise theme across HELIO `apps/web` and mirrored tokens/chrome in `apps/bakery_web`. Conversation logic, APIs, RBAC, and live metrics were not changed.

## New design tokens

Defined in `apps/web/app/globals.css` (and mirrored in `apps/bakery_web/app/globals.css`):

| Token | Value |
|-------|-------|
| `--signal` | `#8728F5` |
| `--royal` / `--aura` | `#B02AEF` |
| `--magenta` | `#E82D96` |
| `--deep-violet` / `--signal-hover` | `#5513BC` |
| `--ink` | `#191329` |
| `--ink-secondary` | `#625B70` |
| `--canvas` | `#F7F5FC` |
| `--surface` | `#FFFFFF` |
| `--stroke` | `#E8E2F1` |
| `--sidebar` | `#FBF9FF` (light rail) |
| `--gradient-brand` | `110deg #8728F5 → #B02AEF → #E82D96` |
| Utility | `.bg-brand-gradient` |

Semantic success / warning / danger / info remain non-purple. Docs: `docs/ui-redesign/02-design-system.md`.

## Reused components

- `HelioButton`, `Surface`, `PageHeader` (+ `gradient` variant), `StatusChip`, `SegmentedControl`, `EmptyState`, `HelioLogo`, `DemoIndicator`
- App shell fill-scroll for `/support` preserved
- Guided bakery client flows unchanged

## Pages redesigned (HELIO)

| Route | Notes |
|-------|-------|
| `/login` | Gradient brand panel |
| Shell | Light violet sidebar, role badge, magenta notification badge |
| `/support` | Flagship gradient chat header, gradient user bubbles, white assistant bubbles |
| `/` home | Token-aligned cards / accents |
| `/tickets`, `/tickets/[id]` | Semantic status chips, primary actions |
| `/devices` | Violet-soft icon tiles |
| `/approvals` | Distinct Approve (gradient) vs Reject (danger) |
| `/agent`, `/evaluations`, `/analytics`, `/admin`, `/knowledge`, `/security` | Token + status tone pass; analytics open-tickets KPI uses gradient accent |

## Bakery parity

- `apps/bakery_web` tokens, primary button gradient, login brand panel, helpdesk header, SidePanel avatar, logo mark

## Tests / QA

- Docker rebuild: `web` + `bakery-web` (compose bakery overlay)
- Typecheck: route restyle pass reported clean `tsc --noEmit` for apps/web
- Manual smoke: hard-refresh `/login`, `/support` guided chat, `/approvals` after rebuild
- Contrast: white on brand gradient; ink `#191329` on `#F7F5FC` canvas

## Limitations

- No Sales Qualifier reference PNG in repo; hex/gradient specs from the prompt were the source of truth
- Dark mode updated to violet-tinted tokens but remains secondary to light default
- Bakery helpdesk is not a full message-transcript UI; HELIO guided panel is the flagship chat surface
- Full Playwright e2e suite not re-run in this pass; visual + build verification only
