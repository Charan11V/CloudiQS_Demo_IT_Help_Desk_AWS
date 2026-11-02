# HELIO design system — Electric Violet Enterprise

Internal name: **HELIO / SIGNAL**. Visual theme: **Electric Violet Enterprise** (violet → magenta brand gradient on a cool lavender canvas). Motif: “signal resolves into clarity.”

Source of truth: `apps/web/app/globals.css`. Always use CSS vars (`var(--signal)`), never hardcoded hex.

## Light tokens (default)

| Token | Value | Use |
|-------|-------|-----|
| `--canvas` | `#F7F5FC` | App background |
| `--surface` | `#FFFFFF` | Cards, panes |
| `--surface-soft` | `#F3EBFF` | Secondary surface |
| `--surface-hover` | `#EBE0FA` | Hover |
| `--ink` | `#191329` | Primary text |
| `--ink-secondary` | `#625B70` | Secondary text, labels |
| `--ink-tertiary` | `#8A8299` | Meta only |
| `--stroke` / `--stroke-strong` | `#E8E2F1` / `#D4CCE3` | Card borders / inputs |
| `--sidebar` / `--sidebar-hover` | `#FBF9FF` / `#F3EBFF` | Nav rail |
| `--signal` | `#8728F5` | Primary action, links, focus |
| `--signal-hover` / `--deep-violet` | `#5513BC` | Action hover |
| `--signal-soft` | `#F3EBFF` | Selected bg, icon tiles |
| `--royal` / `--aura` | `#B02AEF` | Gradient mid, accents |
| `--magenta` | `#E82D96` | Gradient end, demo dot |
| `--info-blue` / `--cyan` | `#2B6CFF` | Info status only |
| `--success` / soft | `#16886E` / `#E8F7F1` | Success status |
| `--warning` / soft | `#A76C19` / `#FFF4E2` | Warning status |
| `--danger` / soft | `#BF4059` / `#FEEDF0` | Danger, Reject |
| `--gradient-brand` | `110deg #8728F5 → #B02AEF → #E82D96` | `.bg-brand-gradient` |

Dark mode (`.dark`) overrides the same tokens with lifted violets (`--signal` `#B57AFF`, canvas `#120E1C`).

## Usage rules
- Cards: `Surface` → white, `border-[var(--stroke)]`, radius 16–24.
- Primary buttons (`HelioButton` default) use the brand gradient; one primary per view. Destructive uses `--danger-soft` / `--danger`, so Approve vs Reject stay distinct.
- Gradient accent (`bg-brand-gradient text-white`): at most one hero KPI card per page, only for real metrics.
- `StatusChip` tones are semantic: `success` (resolved/approved/healthy), `warning` (pending/in progress/queued), `danger` (failed/rejected/high severity), `info` (new/assigned/running). Do not use `signal` (violet) for every status.
- Labels on cards use `--ink-secondary`; `--ink-tertiary` is for timestamps/IDs only.

## Layout
- Sidebar 250–264px / 72–76px collapsed; top bar 68–72px
- Content pad 36–44px desktop; max width ~1320–1460px
- Radii: 20–24 feature, 14–16 cards, 10–12 controls
- Shadows: `--shadow-raised` (`0 12px 40px rgba(25,19,41,.08)`), `--shadow-soft` (violet tint)

## Typography
Inter (mapped as Geist vars). Display 48–56 / page 30–36 / section 18–22 / body 14–15.

## Motion
160–240ms entry; 140–180ms hover; respect `prefers-reduced-motion`.

## Components (apps/web `components/helio`)
HelioLogo, SignalIllustration, Button, Surface, PageHeader, StatusChip, SegmentedControl, EmptyState, ErrorState, Skeleton, DemoIndicator, ChoiceTile, AssistantComposer.

Reference previews: `docs/ui-redesign/reference/`.
