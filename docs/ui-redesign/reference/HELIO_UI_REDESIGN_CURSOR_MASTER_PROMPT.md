# HELIO / AGENTIC BAKERY — COMPLETE FRONTEND REPLACEMENT
## Cursor master implementation prompt — design-led, production-quality overhaul

**YOU ARE NOT BEING ASKED TO RESKIN THE EXISTING UI. YOU ARE REPLACING THE PRESENTATION EXPERIENCE COMPLETELY.**

You are acting simultaneously as a world-class staff product designer, creative director, senior frontend architect, interaction designer, accessibility engineer, and rigorous QA lead. The deliverable is actual running code in this repository, not a Figma-style description, static screenshot, superficial component restyle, or an implementation plan. Execute the work, test it, inspect it visually, refine it, and report what was changed.

**VISUAL REFERENCE FILES:** If `HELIO_UI_VISUAL_REFERENCE.html` and `HELIO_*_DESIGN_PREVIEW.png` are supplied alongside this prompt, read/open them BEFORE implementing visual components. They are concrete art-direction examples for screen composition, colour, spacing, sidebar, cards and typography—not full-function code. The preview uses **illustrative sample data only** and is not the project backend; never copy sample counts, personas, tickets, statuses, arbitrary demo IDs, icon glyph placeholders, or nonfunctional buttons into the real app. Implement the style with actual Lucide icons, real dynamic API data, correct per-role navigation, production-grade interactions and all flows in this prompt. A visual preview is the initial composition target, not the ceiling: actively improve its details and polish.

## 0. First, understand the actual repository

This is a **working multi-service fictional enterprise IT-support demo**. It contains TWO user interfaces; redesign both as one coherent product family without breaking their independent integrations.

**A. HELIO main web** — `apps/web`, Next.js 15 / React 19 / TypeScript / Tailwind, port `3000`, auth and application data via FastAPI `agent-api` behind `/api-backend/*` (port `8001`). Current pages:
- `/login`
- `/` (employee overview)
- `/support` (guided helpdesk integration + free-form assistant)
- `/tickets` and `/tickets/[id]`
- `/devices`
- `/approvals`
- `/agent`
- `/evaluations`
- `/analytics`
- `/admin`
- `/knowledge`
- `/security`
- shared shell, notifications, demo status, role-based navigation.

**B. Agentic Bakery guided helpdesk** — `apps/bakery_web`, Next.js 14 / React 18 / TypeScript / Tailwind, port `3001`, separate FastAPI `bakery-api` on port `8002` and Postgres, with existing `/`, `/helpdesk`, `/it` UI routes. The HELIO web app also embeds the guided Bakery experience using `apps/web/components/guided-helpdesk-panel.tsx` and `apps/web/lib/bakery-client.ts` through `/bakery-api/*`. Preserve this integration; do not mistakenly use the HELIO API or session cookie as a substitute for the Bakery API/session.

Read before coding:
- root `README.md`, `compose.yaml`, `compose.bakery.yaml`, `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`
- `docs/qa/FEATURE_INVENTORY.md`, `docs/qa/FINAL_QA_REPORT.md`
- `apps/web/components/app-shell.tsx`, `apps/web/lib/api-client.ts`, `apps/web/lib/personas.ts`
- all current `apps/web/app/**/page.tsx` and components
- `apps/bakery_web/app/**/page.tsx`, `components/SidePanel.tsx`, `lib/api-client.ts`, `lib/types.ts`
- `specs/agentic_bakery_helpdesk/guided_flow_catalog.json`, `CURSOR_MASTER_SPEC.md`
- Bakery API routers, contracts, policies and actual capabilities.

**Critical reality check:** Bakery's catalog has **57 issues under 8 root categories**, but not every issue has a specialized automated remediation. Many correctly escalate to a real persisted ticket. Its currently verified flows include account unlock, safe disk cleanup, VPN certificate renewal, phishing escalation, policy/consent/approvals; a subset of other tools exists, while self password reset, some transitions, fully correct Back stack, Bedrock and some capabilities remain unavailable. Honor actual API truth. Never visually claim an unavailable operation is functioning, complete or live. Never send direct browser requests to enterprise mock DB or bypass the server.

These are **synthetic demo environments**. Always retain a tasteful but unmissable “Demo environment · Simulated enterprise data” disclosure. Do not call a simulated action a real corporate device operation. Never manufacture metrics, timers, statuses, approvals, audit records, or source evidence.

## 1. Product and creative direction — exactly ONE cohesive aesthetic

Internal design name: **HELIO / SIGNAL**.

The target is **high-end, editorially precise, luminous enterprise software**: the sophistication and confidence of an excellent modern productivity app, combined with the clarity of an operational control room. Think calm intelligence, tactile precision, beautiful spacing, exceptional typographic hierarchy, crisp tables, confident interaction feedback, and highly intentional composition. The design should feel unusually expensive and memorable without becoming an AI gimmick.

**Deliberately abandon the existing generic blue-tinted cards, stacked borders, unrefined spacing, and dark-periwinkle SaaS dashboard.** This must feel like a completely different product when opened side-by-side with the old UI.

The product has two complementary visual modes:
1. **Employee experience = “The Luminous Workspace.”** Primarily warm off-white and white surfaces, deep-ink sidebar and headlines, restrained electric indigo/cyan details, wide whitespace, clear conversational steps, immediate action. Welcoming and easy for a nontechnical employee.
2. **IT/manager/security/admin experience = “The Operations Deck.”** Still the same design language and typography, but tighter data density, stronger grids, command-like surfaces, richer status signaling. A dark, deep-navy optional operations theme may be offered; do NOT force dark mode everywhere. The default is the beautifully executed light theme.

Visual references are *qualities*, not templates to copy: refined typography and keyboard efficiency of Linear; compositional calm of Vercel; useful data density of Attio; polished interaction quality of Arc; friendly assistance of high-end consumer productivity software. **Do not clone any product or rebuild a stock shadcn dashboard.**

Signature brand motif: **“signal resolves into clarity.”** Draw an original, reusable SVG motif: 3–5 extremely thin, elegant curved paths enter from separate points, approach a shared focal node and straighten into a single focused line or luminous nucleus. At large size, use on login and one hero composition. At small size, abstract into the HELIO mark/agent avatar/step-progress indicator. Prefer crisp SVG strokes and subtle gradients to 3D blobs, stock photos, cartoons, astronauts, robots, holographic grids, or giant animated orbs. Graphics must be authored as code and scale cleanly. It should feel like a distinct identity, not a generic AI logo.

The overall light theme should feel like porcelain, graphite, ink, soft shadow, and optical light. **Premium, not neon; futuristic, not science-fiction; polished, not cluttered.**

## 2. Non-negotiable design tokens (implement as CSS variables)

Use the following values as the baseline aesthetic, with subtle adjustments for contrast and rendering if needed. Do not freestyle new random colours component by component.

### Light / default

| Token | Value | Purpose |
|---|---|---|
| `--canvas` | `#F6F7F9` | app background, faint warm-neutral |
| `--surface` | `#FFFFFF` | base cards, panes, inputs |
| `--surface-soft` | `#F0F3F7` | soft secondary surface |
| `--surface-hover` | `#EBF0F7` | interactive hover |
| `--ink` | `#141C2B` | primary text |
| `--ink-secondary` | `#566274` | secondary text |
| `--ink-tertiary` | `#8290A3` | metadata, hints |
| `--stroke` | `#E4E8EF` | understated borders |
| `--stroke-strong` | `#CED6E1` | inputs, separators |
| `--sidebar` | `#111927` | dark ink navigation |
| `--sidebar-hover` | `#202C3D` | nav hover |
| `--sidebar-ink` | `#F7F9FD` | nav active text |
| `--signal` | `#4D5FF5` | main action, selected states |
| `--signal-hover` | `#3B4EDB` | action hover |
| `--signal-soft` | `#EBEEFF` | selected item background |
| `--cyan` | `#24B7C9` | second signal colour, limited |
| `--aura` | `#A5A9FF` | subtle illustration only |
| `--success` | `#16886E` | success text |
| `--success-soft` | `#E8F7F1` | success surface |
| `--warning` | `#A76C19` | warning text |
| `--warning-soft` | `#FFF4E2` | warning surface |
| `--danger` | `#BF4059` | destructive state |
| `--danger-soft` | `#FEEDF0` | destructive surface |

### Dark mode (optional but fully functional if implemented)
`--canvas:#0B111B; --surface:#141E2C; --surface-soft:#1A2636; --surface-hover:#253347; --ink:#F6F8FC; --ink-secondary:#B3BECE; --ink-tertiary:#8493A8; --stroke:#2B394B; --stroke-strong:#41516A; --sidebar:#0A101A; --sidebar-hover:#1D293A; --signal:#9BA6FF; --signal-hover:#ADB6FF; --signal-soft:#262E56`. Semantic success/warning/danger must remain accessible in both themes.

### Typography
- Primary font: **Geist** if easy with current Next.js setup; otherwise use **Inter** correctly. Never reference a font variable whose imported font is different. No exotic font licensing dependencies.
- Display headings: 48–56px desktop, 34–40px mobile, weight around 600–650, tracking `-0.045em`, line-height 1.04–1.12.
- Page titles: 30–36px, medium/semibold, tracking `-0.035em`.
- Section headings: 18–22px, medium/semibold.
- Data figures: 28–40px, tracking tight, `font-variant-numeric:tabular-nums`.
- Body: 14–15px, comfortable 1.5–1.65 line-height. Dense data: 13px only when legible. Descriptions never below 12px. Use `font-mono` ONLY for IDs, log events, source fields, and code.
- User-facing copy must be concise, humane, specific. Replace generic “Your AI assistant is ready to assist you” boilerplate with purposeful language.

### Shapes, strokes, surfaces
- Radius: 20–24px for large feature panels; 14–16px for standard cards; 10–12px for controls; 8px for compact badges. No app-wide extreme pill treatment.
- Borders: normally 1px low-contrast `--stroke`. Allow some unbordered sections. **Do not outline every box.** Prefer separation through whitespace, background contrast and typography.
- Shadows: very soft and low; e.g. `0 12px 40px rgba(17,25,39,.055)` for raised content; `0 2px 8px rgba(17,25,39,.035)` for smaller elements. No dark shadow halos.
- Grid and rhythm: 4px base scale; predominantly 8/12/16/20/24/32/40/48. Large sections separated by ~32–44px.
- Content max width: ~1460px for operations, ~1320px for normal workspace; conversation reading width 720–800px.
- Sidebar desktop: 250–264px open, 72–76px collapsed. Top utility bar: 68–72px. Content padding 36–44px on desktop, 20–24px tablet, 16px phone.
- Icon set: Lucide, consistent 18/20px and mostly stroke-width 1.7–1.9. Never use random emojis as product UI icons.

### Controlled visual effects
- A **single atmospheric hero** on the employee workspace can have a soft diagonal wash of indigo-to-mist-cyan and an original SVG signal drawing placed partly off-canvas. It should be beautiful and quiet, not a generic full-card gradient.
- Keep content outside hero nearly entirely solid. Do not scatter gradients/glows across cards.
- Navigation active state should use a calm bright indicator and tight inner fill, not a loud full-width rounded purple tile.
- Prefer strong typography, generous negative space, thoughtful placement and polished status visualizations over ornament.

## 3. Motion and tactile interaction

Use existing Framer Motion where appropriate; CSS transitions for simple states. All motion should communicate state, not draw attention to itself.
- Page/surface entry: opacity and 8–12px vertical movement, 160–240ms, stagger only for first-load sections.
- Card hover: subtle translateY(-2px) and shadow/border adjustment, 140–180ms.
- Drawers: smooth 220–280ms with backdrop; no flying panels.
- Navigation indicator smoothly tracks selection; selected option cards use border/fill transition.
- Step change in guided support: outgoing step gently recedes, next step comes in with 6–10px motion. The **actual API state** remains the source of truth; animation must not introduce phantom messages.
- Sending/progress state: a small refined activity indicator; no fake streaming claims. Show genuine request/running state if an API reports it. Never simulate tool execution stages that did not occur.
- Action result: compact success transition then real ticket/action ID and next steps. Loading buttons lock duplicate submits.
- Respect `prefers-reduced-motion`; do not implement scroll-jacking or continuous CPU-heavy decorative motion.

## 4. New application information architecture

The main HELIO shell must visibly differ by role while retaining correct access control:

**Employee** (and permitted contractor): simple product navigation — `Home`, `Get help`, `My tickets`, `My devices`. Do not expose IT operational complexity. The primary task is **getting an issue resolved**, not reading dashboards.

**IT engineer**: workbench navigation — `Overview`, `Support queue / Tickets`, `Approvals`, `Agent activity`, `Evaluations`, plus any employee capabilities authorised in backend. Use crisp counters only if real data exists.

**IT manager**: IT engineer tools + `Analytics` with deeper visibility.

**Tenant admin**: approved console navigation + `Admin`, `Knowledge`, per actual role policies.

**Security analyst**: permitted `Security`, evidence/escalation views, relevant approvals and agent tooling. Respect exact backend ACL, not a visually assumed hierarchy. A security analyst should not automatically gain unrelated admin powers.

**Bakery standalone UI**: employee `/helpdesk`; operator `/it`. It should use the same brand tokens/components as HELIO, but must retain independent Bakery login, API adapter and auth semantics.

Desktop shell anatomy:
- Left: dark ink rail, small custom HELIO signal mark + wordmark, tenant label, elegant nav groups with clear active state, collapse action. Bottom: current identity/profile + role + compact demo status; switch/logout menu.
- Top: page location/breadcrumb, optional global command/search if backed by actual scope, context-aware primary action, notifications with actual unread count, avatar, theme control if fully implemented.
- Main: luminous soft canvas with carefully composed content; never place a meaningless card inside another card just to add padding.
- Notifications panel: usable keyboard navigable popover or right drawer, real data, unread/read semantics, empty and error states, direct deep links.
- Small screens: slide-out nav with focus trap and overlay, meaningful top bar; no horizontal overflow; content and chat controls remain easily reachable.

Implement correct theme persistence (local storage or cookies), initial class, hydration stability, system preference support if supported, and actual light/dark tokens. The current simple class toggle is not sufficient. If the full dark theme is not finished, do not show a fake switch.

## 5. Exact reference layouts — follow these compositions

### A. Employee home (`apps/web/app/(app)/page.tsx`)
At 1440px, think of a luxurious focused workspace, not four generic metrics boxes:

```
┌─ 256px deep-ink sidebar ─┬──────────────────────────────────────────────────────────────┐
│ HELIO   / signal mark   │ Breadcrumb / Home                   bell · tenant · avatar     │
│                          ├──────────────────────────────────────────────────────────────┤
│ Home     ●               │ Small eyebrow: YOUR WORKSPACE                                   │
│ Get help                  │ Large: Good morning, Asha.                                     │
│ My tickets                │ Subtitle: Let's get things running smoothly.                    │
│ My devices                │                                                                  │
│                          │ ┌─  high-impact luminous assistant feature panel  ────────────┐│
│                          │ │ HELIO ASSISTANT                    subtle signal line art    ││
│                          │ │ What can I help you fix today?                               ││
│                          │ │ [ Describe the issue or choose below...        ] [ Arrow ]   ││
│                          │ │ Account access · VPN · Laptop · Apps · Other issue           ││
│                          │ └──────────────────────────────────────────────────────────────┘│
│                          │                                                                  │
│                          │ [My open requests   compact list] [My device  factual details]   │
│                          │                                                                  │
│                          │ Recent activity / actionable service information               │
└──────────────────────────┴──────────────────────────────────────────────────────────────┘
```

Use a large expressive typographic header, a gorgeous lead assistant panel, highly useful contextual secondary info. Resist existing four “account status/device count/open tickets/VPN status” equal square tiles. If data is absent, use truthful empty states. Do not hardcode “VPN Check Required” or “Active” without deriving status from real data. The assistant input navigates to `/support` with prefill or another correct supported mechanism; never imply it submitted if it only navigated. Quick issue pills navigate to real guided support paths/mode; if deep-link preselection requires nonexistent API support, land on the corresponding guided starting experience without fabricating a selected backend state.

### B. AI Support / guided helpdesk (`apps/web/app/(app)/support/page.tsx`, `guided-helpdesk-panel.tsx`, `apps/bakery_web/app/helpdesk/page.tsx`)
**This is the hero experience, and it must be the most polished screen.** Do not build a conventional chat page with a giant blue bot bubble and a pile of buttons.

Desktop composition: 70–74% main conversation + 26–30% contextual right rail. Right rail collapses/opens intelligently, becomes a drawer on small screens. Narrower reading area inside main panel. Soft page background. Main conversation height integrated with viewport; composer always accessible.

Main header: “Get help” / “Let's work through this together” + discreet `Guided` / `Describe it` segmented modes (preserve both existing real backends). Above conversation, small source-of-truth `Demo` / mode indicator. Guided mode must not appear as a free-form LLM agent if it is the deterministic catalog engine.

Guided starting state:
- A tasteful HELIO assistant presence mark; large short question “What do you need help with?”
- Display the **8 categories returned by the backend**, in a responsive 2-column grid of elegant option tiles with a subtle category icon, title, optional short description, and arrow. Do not hardcode the 57 issues in frontend JSX. Render real `response.options` dynamically.
- Place one secondary free-text affordance below: “Can't find it? Describe the issue instead.” This must call the documented `free_text` path rather than being a dead end.
- Global controls (Back / Start over / Something else / Talk to IT / Cancel / Resume) are shown only if currently supported/returned; never invent an interactive Back stack; explain when “Back” actually resets.

Next guided steps:
- Visually preserve journey context using a **quiet breadcrumb/progress trail** e.g. `Account & access › Password › Account locked` based on real response `breadcrumb`.
- Present each question in a clean conversation step, not inside a 3-level nested card.
- Render single-select and multiple-select steps differently and correctly. Single selection may still require explicit Confirm when `require_confirm` or backend contract requires it; multiple selection must show a persistent `Continue (N selected)` action. Never auto-send before the user confirms when server contract requires explicit selection.
- A choice tile uses real `option.id` while showing `label` and optional description; keyboard radio/checkbox interactions; selected/focused/disabled states; prevent duplicate calls.
- Keep free-text accessible at every safe point, but not in a way that obscures the primary guided question.
- Render one current-step view backed by API `state`. Do not create imaginary historical bubbles from the latest response; if actual conversation history exists via backend endpoint, use it. If not, show a **journey summary** based only on reliable breadcrumbs and real user selections in this browser session, without pretending server persistence exists.

Diagnosis state:
- Attractive editorial “Here's what I found” panel. Separate hypothesis from verified observations. Source evidence appears as compact, legible rows with field/value/source and exact original data, not invented indicators.
- Labels like `Observed`, `Likely cause`, `Needs verification` should reflect semantics and confidence when available. Never portray hypothesis as confirmed.
- Clear action path: `Suggested fix`, `Requires your approval`, `Needs an IT reviewer`, or `I'll create a ticket` depending on real response.

Action / consent state:
- **Do not use a cheerful green “Run now” button immediately on an impactful action.** Show a proper action review panel: target, exact proposed change, possible impact, simulated demo disclosure, required permission, consent. For user consent, show explicit confirm and correct actual API POST; if IT approval needed, show Pending with reviewer/expiry if supplied, never assume completed.
- Status sequence based strictly on backend: `Proposed` → `Consent requested` → `Approval pending` → `Ready to execute` → `Executing` → `Completed / Rejected / Failed / Expired`. Only display states actually evidenced. Backend prevents execute before consent; UI must too.
- During execution, prevent duplicates; show errors and retry when safe; do not alter state locally as if success occurred.
- Result state should be wonderfully designed: small positive illustration, actual action/ticket ID, what changed in the **synthetic** dataset, observed postcondition if API exposes it, and a “Was this resolved?” or “Need more help?” next step only when workflow can handle it.

Ticket escalation:
- When issue not cataloged / beyond safe automation / policy-blocked, provide clear supportive copy and a real `Create ticket / Talk to IT` flow. Display actual persisted ticket ID, assignment and status from API. No fake ticket ID. An unsupported issue is **not** “automatically fixed.”

Right context rail:
- Current employee identity and tenant.
- Own device with actual properties and concise status when available.
- `Your current journey`: step breadcrumb, workflow status.
- `Recent tickets` / `Related knowledge`, **only if actual API is available**; otherwise use purposeful explanatory state or omit.
- A minimalist `Evidence` accordion if data exists. Useful high trust, not a junk drawer.

Standalone Bakery `/helpdesk` should share visual styling and step components, keeping its current `conversation_id`, `assistant_message`, `options`, `selection_mode`, `selection_hint`, `confirm_label`, `finding`, `action_proposal`, `ticket`, `controls`. Use `bakery-web` API client and cookie, not HELIO API. Current `/helpdesk` contains a My Tickets subview; redesign and preserve that function. On refresh, use `GET /api/conversations/{id}` when a valid scoped ID is available and supported, rather than silently discarding state; handle expired sessions correctly and never reuse another persona's conversation.

Free-form HELIO AI mode:
- Refined message history: narrow transcript column; assistants have a small mark + name; user replies as minimal right-aligned tinted surface. No giant blank cards around bubbles.
- As real runs execute, show `Thinking / Checking sources / Request completed` only if represented by actual run events or states. Keep polling/optimistic updates, restore pending/run state safely, avoid duplicate createRun side effects.
- Display `headline`, `summary`, `findings`, `suggested_steps` from actual output with great hierarchy and useful embedded action cards. The step actions `open_ticket`, `request_approval`, `safe_instruction`, `view_evidence`, `escalate` must remain correctly wired.
- `Suggested prompts` are contextually relevant to the available workspace; a starting prompt can send the real message, not just decorate the page.
- Sticky composer with multiline input that grows up to a sensible max, keyboard hint `Enter to send · Shift+Enter newline`, disabled/loading state, accessible Send. Add attachments only if supported by real backend; otherwise no fake paperclip.

### C. Ticket list (`/tickets`)
- Page title + small informative summary + obvious `Get help / New request` action.
- One excellent data surface with high-quality filter row: actual search if supported, status filter, priority/category where API permits, sort if supported. URL search params for durable filters where helpful.
- Table on desktop with polished spacing, row hover, status/priority chips, identifier typography, requester or category if available, updated date. Real data only. Mobile becomes intelligent stacked ticket rows, not horizontally scrolling 8-column tables.
- Empty state, loading skeleton, error with retry, large datasets (pagination if API supports or performant client filtering with clear scope).

### D. Ticket details (`/tickets/[id]`)
- Incident heading, status/priority, copy-ID, back link; summary and description.
- Information hierarchy: left “What happened” plus activity timeline if API has it; right ticket facts (`ticket ID`, owner, priority, category, created/updated, status). Cross-link to related action/approval where API exposes IDs.
- IT-specific controls may only appear if API really supports them; no pretend `Resolve`, `Assign`, or comment button unless persisted by backend. If current Bakery ticket API only supports read, be explicit about read-only.
- Restricted/cross-tenant nonexistent ticket must have respectful 403/404 presentation and never leak resource existence.

### E. Devices (`/devices`)
- A real asset-inventory view, with large clear device names and honest status, platform, OS, model, ownership, and measured health properties only when supplied.
- For 1–3 personal devices: beautifully composed horizontal asset cards. For IT larger lists: dense table, search/filter if supported. Include a subtle original device outline icon, not stock images.
- Any `Run diagnostic` / `Troubleshoot` CTA routes to actual supported support workflow, not a simulated success state.

### F. IT approvals (`/approvals`, Bakery `/it`)
- Queue-led operations surface with high signal. Top heading `Approvals`, actual pending count and clear risk explanation; sticky tabs if status API supports them.
- Rows: request type/action, employee/requester, target resource, tenant-scoped metadata, impact, expiry, policy/eligibility. Present dense but elegant, not giant gray cards.
- Clicking a row opens a focused details drawer with provenance, action description, risk, policy summary, consent state if available, timestamp, pending status, reason field.
- Strong **Approve** and **Reject** separation; reject uses subdued destructive emphasis. Both require explicit reason if actual backend policy requires it, otherwise follow contract; confirmation before irreversible approval/execute. Approval and actual execution are NOT always the same step; obey backend semantics. `Approved` must not be conflated with `executed`.
- Show pending/busy/expired/rejected/failed. No optimistic final-state fabrication; refetch after server mutation. Show 403/409 conflicts gracefully.
- Bakery API POST `/api/approvals/{id}/decision` takes `{approved, reason?}`. HELIO API has a different contract: preserve its `approvals` client semantics. Never mix them.

### G. Agent activity (`/agent`)
- Stunning operator timeline: real run list, run ID, initiation time, status, actor, duration only when present. Clicking a run opens trace details where API allows.
- A vertical process timeline / inspection drawer for actual tool events, with careful monospace IDs, source badges, timings when real, success/failure. Redact secrets and restricted data. Do not show pretend streamed chain-of-thought or internal reasoning.
- Empty data = `No runs recorded in this environment yet` + link to available workflow; not fake logs.

### H. Evaluations (`/evaluations`)
- Quality lab visual style. Clean run list with real pass/fail/partial outcomes and progress when available.
- Launch actual curated suite using existing API, prevent double-run, show actual returned job status, helpful completion/error. Charts only if supported by real data. Do not imply tests passed before run completion.
- Differentiate safety gate failures, contract failures and subjective quality, if fields exist; avoid invented numerical scores.

### I. Analytics (`/analytics`)
- Take great care: a premium analytics page uses strong number typography, thin understated charts, excellent legends, calibrated date labels and comparisons with clear bases, and well-spaced data tables.
- Keep real ticket/runs APIs. Top row: 3–4 meaningful measured KPIs; second row: asymmetric 60/40 layout with ticket distribution and run outcomes; bottom: trend/table detail if data available.
- Do not invent historical time-series, latency distributions or savings. When only aggregate totals exist, render precisely those; show `No historical series available` where appropriate.
- Chart tooltips are readable, colour semantics consistent, accessible text equivalents; no neon gradients, fake pies or zero-as-missing data.

### J. Knowledge (`/knowledge`)
- Search-first knowledge interface with large excellent search input, results list with title, relevant excerpt, classification, source, timestamp where supplied.
- Navigation/filter by knowledge category only when API supports it. Great empty, no-results and loading states. Search supports keyboard Enter.
- Clicking a document must use a supported route/preview or explicit safe external link; don't create dead clickable results.

### K. Security (`/security`)
- Serious and calm. Risk shouldn't look celebratory. Page composed of truthful investigation indicators, findings grouped by severity/source, escalations and their statuses, relevant evidence.
- Risk/severity semantically encoded by colour PLUS text/icon, never by colour alone. Controls must respect analyst/tenant policies. Do not expose confidential raw cross-tenant records.

### L. Admin (`/admin`)
- A polished configuration workbench with horizontal side sections or subnav: Integrations, Policies, Users, Audit. **Use actual backend endpoints.**
- Integrations list with mock-connected versus actual-connected distinction, source freshness when supplied; test connection with genuine endpoint and error states.
- Policy editor reads actual editable policies. Explain dangerous changes, disabled capabilities, revision/save confirmations and server-authoritative results. Never enable prohibited MFA reset, wipe or admin-role elevation through UI.
- User list and audit log: compact highly readable tables, role badges, search/filter if implemented, tenant scoping. Never show admin edit affordances without backend support.

### M. Login / persona chooser (both frontends)
- Make the first impression genuinely excellent. **Split 52/48 desktop**: left deep-ink branded editorial scene with exquisite original signal-flow illustration and ~50px headline “Clarity, when work gets complicated.” A restrained one-sentence product value proposition; small trust/demo label anchored at bottom. Right warm neutral background containing the persona selection experience on a centered ~460px column.
- Tenant switch: an elegant compact segmented control (`Northstar` / `Beacon`). Changing tenants resets selected persona.
- Persona options: beautifully spaced selectable rows with simple initial avatars, name, role, perhaps subtle `Employee / IT / Security` descriptor. Active row has strong focus/selection styling; terminated persona is disabled and visibly explained.
- CTA clearly says `Enter demo workspace` and stays disabled until a valid persona is selected. No real login credentials or production auth misrepresentation.
- Mobile stacks left into compact brand header and keeps persona choice immediately reachable.
- Bakery standalone should use matching branding but its own `user_id` mapping. Do not assume `northstar-asha` equals `NS-001` without validating the real mapping.

## 6. Reusable component architecture

Create a coherent small library of brand-aware primitives rather than individually styling every page. Possible location in each app: `components/ui-v2` and `components/helio` or a carefully wired shared workspace package. If using a shared package, make both independent Docker build contexts able to access it; **do not break Docker for the sake of a monorepo refactor**. Shared tokens + documented component parity is acceptable if package wiring would be risky.

Build/use:
- `HelioLogo` + `SignalIllustration` (original SVG)
- `AppShell`, `NavigationRail`, `Topbar`, `MobileNav`, `IdentityMenu`, `DemoIndicator`
- `PageHeader`, `Eyebrow`, `SectionHeader`, `Surface`, `FeaturePanel`, `EmptyState`, `ErrorState`, `Skeleton`
- `Button` with primary/secondary/quiet/destructive, loading and icon variants
- `IconButton` with accessible label, `TextField`, `Textarea`, `Select`, `Checkbox`, `Radio`, `SegmentedControl`
- `StatusChip` with strictly typed semantic states, `PriorityChip`, `ContextBadge`, `Count`/`Metric`
- `DataTable`, responsive `RecordList`, `FilterToolbar`, pagination only if supported
- `DetailDrawer`, `ConfirmDialog`, `Toast`, `Tooltip`, keyboard-safe `Dropdown`, `Tabs`
- `AssistantComposer`, `SupportQuestion`, `ChoiceTile`, `ChoiceGroup`, `StepTrail`, `DiagnosticFinding`, `EvidenceRow`, `ActionReview`, `ApprovalTimeline`, `TicketReceipt`
- `SourceInfo` and `ActivityTimeline` for real data.

Use existing Radix primitives, TanStack Query/Table, React Hook Form/Zod, Lucide, Sonner, Framer Motion where these are already present in HELIO. Add dependencies only when they demonstrably improve the design, and keep package versions compatible with each app. Bakery currently has a smaller dependency set; do not import React 19-only code into its React 18 application. Prefer a proper shared token specification over a brittle UI dependency maze.

Keep **API clients and types separate from display components**. Build adapters only where actual backend structures differ; add contract tests. Normalize design-facing statuses but preserve server payloads and IDs in requests. Keep request and response shapes exact. All network calls must use existing proxies and `credentials: 'include'`. Do not rewrite backend business logic or mutate fixtures as part of a visual task.

## 7. Data integrity, permission, and functional guarantees

These are release blockers, not optional polish:

1. The existing FastAPI services, Postgres/SQLite persistence, security/policy gates, consent and approval sequence, ticket IDs, demo resets and API contracts must continue to work. UI does not decide authorization.
2. Both tenant experiences remain isolated. Switching personas/tenants must not display previous cached tickets, device data, notification counts or conversations. Clear/invalidate queries and per-persona UI state on logout/switch.
3. Employees cannot open IT/admin/security routes through direct URL or navigation. Show proper access denied or redirect consistent with backend. Never rely exclusively on hidden nav items.
4. No hardcoded `57` issue options or issue lists. Fetch real root and subsequent options from guided engine.
5. No fake success, loading, approval, action execution, “device fixed” notice, or manually fabricated KPI.
6. Keep all actual flow controls operational (`back`, `start_over`, `something_else`, `talk_to_it`, cancel/resume where supported). Handle unsupported behavior truthfully rather than silently faking it.
7. Retry logic must avoid double mutations and respect idempotency. Buttons should lock while processing, show genuine errors and allow safe recovery.
8. Human consent and IT approval must be explicit, properly separated, and checked server-side. Especially respect own-account/own-device permissions and no cross-tenant disclosure.
9. Preserve visibly accurate `Offline Simulator` versus live Bedrock/provider modes. Never claim live AWS/Amazon Bedrock, real MFA reset, remote wipe, production integrations, or actual user-device modifications unless they genuinely exist.
10. Do not remove existing capabilities to simplify a screen. If page/capability cannot be made visually acceptable without backend change, present graceful truth-based unavailable states and document the gap.
11. Every button, filter, link, tab and switch that *looks* interactive must work or be clearly noninteractive; no dead decorative affordances.
12. Dates: distinguish synthetic demo scenario time from actual current time. No false “just now,” SLA countdown, or “currently online” inferred from arbitrary fixture timestamps.
13. Treat any API content as untrusted. Render as text, sanitize rich content where necessary, do not interpolate raw HTML or leak keys/cookies.

## 8. Responsive, accessibility, and performance requirements

- Design and actually test at widths 375px, 430px, 768px, 1024px, 1440px and 1920px. Screens with densely populated data must remain usable on phones. No clipped critical action controls.
- Reach WCAG 2.2 AA contrast for normal text where practical; keyboard access, `:focus-visible`, correctly labeled form controls, screen reader-friendly errors, `aria-live` for important status, proper focus restoration after dialogs/drawers.
- Buttons should have comfortable touch targets (~44px on mobile). Use native semantics over div-click controls.
- Skeletons should match real layout and minimize layout shift; visible loading, empty, error, forbidden and success states for each page. Error retries must work.
- Client components only where interaction is needed. Preserve React Query caching/refetch semantics; don't cause recursive renders or accidental query loops. Guard against double submission.
- Avoid loading a heavy animation library for every small control; CSS is enough for hover. Lazy load heavy charts or below-the-fold elements when sensible.
- Icon-only buttons need clear `aria-label` and tooltips. Status colour is always paired with a readable label.
- Full light/dark appearance must include browser form controls, dialogs, menus, skeletons, charts and toasts; not just the page background.

## 9. Mandatory implementation approach — DO THE WORK, not only planning

**Phase 1 — Audit and map (before changing files).**
1. Inventory every route, component, API method, role requirement and user action in both frontends. Identify currently unimplemented/disconnected interactions and backend gaps. Save `docs/ui-redesign/01-current-state-inventory.md`.
2. Establish a functional baseline with any currently runnable typecheck, build, existing tests and Playwright screenshots. Do not fail merely because of historical issues; record them.
3. Identify existing semantic status values and bakery response variants; write UI state matrix. Confirm actual 8 root categories / 57 issues without hardcoding them.

**Phase 2 — Define visual source of truth.**
4. Create `docs/ui-redesign/02-design-system.md` with the exact tokens, component states, typography, layouts, motion, examples and screenshot targets from this prompt. Add a small in-app dev-only design-system showcase or Storybook-like route if practical and safe.
5. Implement CSS variables, fonts, layout primitives, illustrations, skeletons, accessibility utilities. Make one showcase page excellent before mass migrating.

**Phase 3 — Build the showcase screens to a high design standard.**
6. First implement login, employee Home, and the entire guided Support journey. These set the visual bar. Render both with representative REAL fixture-backed states. Do not spread a weak pattern to 12 pages.
7. For Guided Support, manually/automatically walk several journeys including root, category, subcategory, single/multiple choice, diagnosis, ticket, consent, pending approval, success/failure, free-text unmatched and a forbidden operation. Handle all returned components beautifully.
8. Make the Bakery standalone frontend visually consistent with embedded HELIO guided support while preserving separate routing/auth/contract.

**Phase 4 — Convert the whole product.**
9. Build Ticket list/detail, Devices, Approvals; then Agent Activity, Evaluations, Analytics; then Knowledge, Security, Admin; finally all nav, notification, empty/error and mobile details.
10. Delete/retire old styles, patterns and redundant components after replacing them. No pages should look like the old UI or contain old gray-card leftovers. Do not leave unused design systems colliding in global CSS.

**Phase 5 — screenshot-based critique and correction loop.**
11. Start both actual frontends and backend services using existing repo scripts/Docker as available. Capture screenshots from actual rendered app at minimum: main login, Bakery login, employee Home, guided root, guided nested question, finding, action consent, ticket receipt, IT approvals, ticket detail, analytics, admin and security. Include desktop and phone variants.
12. Inspect screenshot composition, alignment, density, truncation, contrast, spacing, shadows, hover/focus and scroll behavior. **This is where design quality gets achieved.** Critique weak screens like a demanding art director; iterate until the screens look like one coherent premium design, not assembled templates.
13. Create `docs/ui-redesign/03-visual-qa.md` with a screenshot index, what was visually wrong and the exact improvements made. Keep reference images under an appropriate `docs/ui-redesign/screenshots/` directory; avoid committing huge binaries if repository conventions forbid.

**Phase 6 — functional, regression and security testing.**
14. Run typecheck/lint/build for both frontends. Fix failures; never disable strict validation or add `ignoreBuildErrors` as a shortcut. Existing `apps/web/next.config.ts` suppresses some errors; remove those suppressions if feasible and fix genuine issues rather than hiding them. Report pre-existing blockers transparently.
15. Implement Playwright E2E in both fronts for login, role navigation, theme/mobile nav, guided conversation selections, free text, ticket creation, consent, pending approval, IT approval/rejection, forbidden role, logout, expired session, cross-tenant isolation and errors. Reuse real local API/fixture scenario where safe. Test controls and semantics, not CSS implementation details.
16. Run bakery's existing security/workflow suite (`tests/bakery/**` and documented scripts), HELIO tests, and any relevant smoke tests; use isolated/resettable data and never mutate the user's important state accidentally.
17. Record test outcomes and remaining genuine backend limitations in `docs/ui-redesign/04-release-verification.md`.

**Phase 7 — handoff.**
18. Provide a concise final report with changed file list, architectural decisions, before/after screenshot paths, design system and route coverage, tested working flows, commands to run both UIs, and any limitations. Be explicit about what is actually complete.

## 10. Objective acceptance criteria — no shortcuts

You have succeeded only when all are true:
- **First-glance transformation:** when viewed at 1440×900, HELIO login, Home, Support and IT Approvals look unmistakably rebuilt; more polished, purposeful, composed and premium than the originals.
- **Visual consistency:** one identifiable brand, colour semantics, typography, spacing system, typography hierarchy, icon language, motion and component states across `apps/web` and `apps/bakery_web`.
- **Support-first experience:** an average employee can start with category options, narrow the problem, enter free text, consent, escalate and see actual results without navigating a cluttered admin dashboard.
- **Operator efficiency:** an IT engineer can review risk and approve/reject actual pending actions with minimal scanning and clear consequences.
- **Nothing fake:** every displayed state and every mutation corresponds to backend data, or is clearly marked a simulated/demo result; unsupported operations are never presented as complete.
- **Real operational quality:** correct sessions, tenant/role isolation, working navigation, functional buttons, responsive design, keyboard interactions, loading/error/empty/forbidden states, no TypeScript errors introduced.
- **Screenshots have been reviewed and improved**, not merely generated.

## 11. Creative quality gate — what to avoid in EVERY PR

Reject and redesign your own work if it contains:
- A generic `bg-gray-50` app with 12 identical white cards and default shadcn controls.
- A rainbow of status gradients, translucent glass everywhere, glowing borders or overproduced motion.
- A dark-purple chatbot page with oversized assistant bubble and unsorted answer chips.
- A dashboard made from four same-size KPI blocks regardless of the user's role.
- Tiny gray text, excessive border nesting, huge empty dead zones, or repeated meaningless section descriptions.
- Prominent controls that do nothing, guessed API fields, fabricated metrics or approvals.
- Unreadable wide tables on mobile, sticky composer covering the last message, or bottom buttons outside the viewport.
- A one-file `page.tsx` that combines all network mutations, UI state, styling and conditional screens when it can be decomposed safely.
- Documentation claiming completion when working routes or tests are missing.

## 12. Execution instruction

Begin by reading and auditing the repo; then execute ALL phases as far as the environment permits. **Do not ask me which design direction to use. The design direction, brand identity, palettes, layout principles, functional scope and visual priorities are specified above.** Make informed independent design decisions within this system. Preserve the core helpdesk business rules and backend integrations. Do not stop after producing a plan or one attractive screen. Work until the old frontend experience has been replaced comprehensively, validated with real user journeys and reviewed with actual screenshots. Show the final outcome, not an aesthetic adjective checklist.
