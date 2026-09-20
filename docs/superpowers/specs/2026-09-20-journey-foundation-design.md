# AstaLink Journey Foundation Full-Stack Design

- **Status:** Approved conversational design; pending written-spec review
- **Date:** 20 September 2026
- **Scope:** User-journey navigation, guided home, responsive application shell, supporting backend projections, route migration, verification, and cleanup
- **Feedback addressed:** O1-1 and O1-8 directly; establishes foundations used by later onboarding, chat, recommendation, market-safety, and continuity workstreams

## 1. Purpose

AstaLink currently exposes a collection of product modules. Its sidebar has section labels, but most features sit under one broad portfolio section, the default dashboard behaves like a market terminal, and mobile largely inherits desktop interaction patterns. Users must understand the product's internal feature map before they can decide where to go.

This workstream changes the product's organizing principle from system modules to the user's financial journey:

> Understand the current condition, record what happened, decide priorities, explore options, and monitor decisions.

The result must be a full-stack experience rather than a frontend reskin. The UI, API contracts, domain-state projections, failure behavior, route semantics, responsive behavior, tests, and obsolete-code removal must move together.

## 2. Intended Outcome and Success Criteria

### 2.1 Intended outcome

A new user should be able to understand AstaLink's major areas without knowing its agent architecture, while an experienced user should still reach a frequently used destination directly. Navigation should use questions and tasks present in the user's mind, not technical implementation terms.

The application should feel like a guided financial workspace:

1. **Beranda:** What is my condition and what should I do next?
2. **Catat & Kelola:** What happened to my money or business?
3. **Rencanakan:** What should this money be used for?
4. **Eksplorasi:** Which investment options deserve examination?
5. **Portofolio:** What happened after I made a decision?

`Tanya Asta` is a persistent cross-journey action rather than another peer menu category.

### 2.2 Success criteria

- The default post-login page is a guided home, not a market terminal.
- Desktop navigation exposes the journey hierarchy without presenting every page as a flat list.
- Mobile navigation exposes all five journey stages and keeps `Tanya Asta` reachable without consuming a stage slot.
- Primary mobile flows work at a 360 px viewport without horizontal page scrolling.
- User-facing navigation and summary payloads contain no `Layer 0`, `Layer 1`, graph, agent, optimizer, or pipeline terminology.
- Home shows one deterministic next action, data freshness, and useful partial content if a non-critical domain fails.
- Existing financial calculations remain in their current domain implementations; the new projection layer does not recalculate them.
- The market terminal remains functional after moving from `/dashboard` to `/market`.
- Obsolete routes, navigation definitions, components, exports, imports, and compatibility code are removed when their consumers have migrated.

## 3. Scope

### 3.1 Included

- A journey-based desktop sidebar.
- A five-stage mobile bottom navigation.
- A persistent `Tanya Asta` desktop action and mobile floating action button.
- A guided `/dashboard` home.
- Moving the existing market terminal to `/market`.
- A backend home projection endpoint and deterministic next-action composer.
- User-facing projection DTOs for readiness, allocation preview, recent activity, freshness, and section health.
- Responsive transformations for cards, tables, charts, forms, dialogs, and approvals.
- Responsive treatment for the journey destinations in this workstream: `/dashboard`, `/transactions`, `/business`, `/allocation`, `/recommendations`, `/market`, `/news`, `/portfolio`, `/approvals`, `/settings`, and the shared `/chatbot` shell.
- Role-aware navigation visibility while preserving server-side authorization.
- Route migration, link updates, regression protection, responsive verification, accessibility checks, and dead-code cleanup.

### 3.2 Excluded

- Rewriting the content or personality of chatbot responses.
- Automatically creating a first workspace for a new account.
- Changing investment recommendation methodology.
- Adding new market, manipulation, or legal data sources.
- Redesigning transaction-capture domain behavior.
- Replacing existing allocation, portfolio, market, legal, or transaction engines.
- A broad visual-brand redesign unrelated to navigation or responsive usability.

Those concerns belong to their respective workstreams. This design may expose stable extension points for them but must not implement them indirectly.

## 4. Information Architecture

### 4.1 Desktop navigation

The desktop application uses a persistent, collapsible journey sidebar:

```text
AstaLink
[ Tanya Asta ]

Beranda

CATAT & KELOLA
├── Transaksi
└── Bisnis Saya

RENCANAKAN
└── Rencana Dana

EKSPLORASI
├── Ide Investasi
├── Pasar & Grafik
└── Berita Pasar

PORTOFOLIO
├── Kepemilikan & Kinerja
└── Persetujuan            [pending count]

Pengaturan
Admin                      [admin only]
```

Behavior:

- `Tanya Asta` is visually prominent and pinned near the top.
- Journey groups may collapse, but the group containing the active route opens automatically.
- A user's explicit expand/collapse choice persists for the session.
- Collapsed icon mode supplies accessible labels and tooltips.
- `Persetujuan` shows a badge only when a pending count is greater than zero.
- Admin navigation is hidden for non-admin users, but the backend remains the authorization boundary.
- Detail, intake, and audit routes are reached contextually and do not appear as primary navigation items.

### 4.2 Exact route map

| Journey area | User-facing destination | Route | Decision |
| --- | --- | --- | --- |
| Main | Beranda | `/dashboard` | New guided home |
| Global | Tanya Asta | `/chatbot` | Persistent action, not a menu group |
| Record | Transaksi | `/transactions` | Existing route |
| Record | Bisnis Saya | `/business` | Existing list; details are contextual |
| Plan | Rencana Dana | `/allocation` | Readiness, missing inputs, and allocation are one journey |
| Explore | Ide Investasi | `/recommendations` | Existing route with user-facing label change |
| Explore | Pasar & Grafik | `/market` | Existing dashboard terminal moved here |
| Explore | Berita Pasar | `/news` | Existing route |
| Portfolio | Kepemilikan & Kinerja | `/portfolio` | Existing route |
| Portfolio | Persetujuan | `/approvals` | Existing route with pending badge |
| Support | Pengaturan | `/settings` | Existing route and nested settings |
| Admin | Dokumen Regulasi | `/legal-docs` | Admin-only navigation and backend access |

Routes such as `/business/[businessId]`, `/allocation/intake/[businessId]`, `/allocation/investor`, and `/approvals/[auditId]` remain contextual. Internal audit routes remain absent from ordinary user navigation.

`/business/detail` is not a canonical destination and is removed from navigation. The canonical detail route is `/business/[businessId]`. The shortcut may remain temporarily only if repository search identifies a current consumer or an external deep-link compatibility need; otherwise it is removed. If retained during migration, it must have an explicit removal condition and must not appear in either desktop or mobile navigation.

`Kesiapan Finansial`, `Alokasi Modal`, and `Profil Investor` are not three peer menu items. They are steps within `Rencana Dana`:

```text
Check the condition
→ collect only decisive missing information
→ show the cash/stocks/business allocation
→ allow investment exploration when appropriate
```

### 4.3 Mobile navigation

Mobile uses a fixed five-stage bottom navigation:

| Tab | Primary route | Active on |
| --- | --- | --- |
| Beranda | `/dashboard` | `/dashboard` |
| Catat | `/transactions` | `/transactions`, `/business`, and business detail routes |
| Rencana | `/allocation` | `/allocation` and its nested routes |
| Jelajah | `/recommendations` | `/recommendations`, `/market`, and `/news` |
| Portofolio | `/portfolio` | `/portfolio`, `/approvals`, and approval details |

The primary route is the landing destination for a tab. Secondary destinations remain available through page-level navigation and the mobile overflow menu. The active tab follows the route family rather than requiring every secondary route to consume a bottom-navigation slot.

`Tanya Asta` is a labeled floating action above the bottom navigation. It must respect safe areas, never cover a primary page action, have an accessible name, and navigate to `/chatbot`. Carrying semantic page context into AI reasoning is deferred to the conversation workstream; this workstream may preserve a return route but must not invent a new chat-context contract.

### 4.4 Shared navigation configuration

Desktop and mobile navigation derive labels, route families, icons, role visibility, and active-state rules from one typed configuration. Rendering differs by viewport, but route knowledge must not be duplicated across components.

## 5. Guided Home

### 5.1 Purpose and hierarchy

The guided home answers three questions in order:

1. What is my current condition?
2. What changed recently?
3. What is the single best next action?

It contains:

1. Workspace context and last-updated time.
2. A financial snapshot: available cash, current-period business revenue when applicable, and sandbox portfolio value.
3. One prominent next-action card.
4. A readiness summary with decisive missing information.
5. An allocation preview when a valid analysis exists.
6. Recent cross-domain activity.
7. Pending approvals and quick actions.

It does not contain the full market chart, a complete ticker universe, detailed technical analysis, or internal pipeline terminology.

### 5.2 Metric semantics

Every displayed metric carries:

- its value and unit;
- an `as_of` timestamp;
- a source/domain identifier;
- a state of `ready`, `empty`, `stale`, or `error`;
- optional comparison text only when the comparison is supported by real data.

Personal and business money must not be silently combined. If a workspace does not support a metric, that card is omitted or replaced with a relevant metric rather than shown as zero.

### 5.3 Deterministic next action

The home projection chooses at most one next action. The composer uses explicit state, not an LLM. Applicable conditions are evaluated in this order:

1. Resolve a pending transaction confirmation or approval.
2. Supply a decisive readiness input that blocks a safe decision.
3. Address a readiness or liquidity safety blocker.
4. Review a completed allocation that has not yet been acknowledged.
5. Explore investment options when readiness allows it and the sandbox is empty.
6. Review the existing portfolio when holdings exist.
7. Fall back to a neutral action such as asking Asta or reviewing recent activity.

Each result includes a stable action kind, user-facing title, short rationale, destination route, and the rule identifier that produced it for audit and tests. The rule identifier is not shown to the user.

## 6. Backend Projection Architecture

### 6.1 Boundary

The experience layer reads a journey projection layer, which reads existing domain sources:

```text
App shell and guided home
            |
            v
Home Summary Service + Journey Status Composer
            |
            v
Transactions/Business · Allocation/Readiness · Portfolio/Approvals · Market/Legal
```

The projection layer may aggregate, label, order, and assess freshness. It must not recalculate revenue, profit, allocation weights, portfolio value, risk metrics, manipulation risk, or legal decisions.

### 6.2 Endpoint

The design introduces:

```http
GET /api/v1/journey/home?workspace_id=<uuid>
```

The request requires authentication and workspace ownership. The response contains:

```text
workspace
generated_at
financial_snapshot[]
readiness_summary
next_action
allocation_preview?
recent_activity[]
pending_approvals_count
section_health
```

Key DTO semantics:

- `financial_snapshot`: independently sourced metrics with value, currency/unit, `as_of`, source, change, and state.
- `readiness_summary`: `ready`, `needs_input`, `not_ready`, or `unavailable`, plus decisive gaps and continuation route.
- `next_action`: action kind, title, rationale, href, and internal rule identifier.
- `allocation_preview`: cash/stocks/business weights, user-facing confidence wording, analysis timestamp, and data gaps.
- `recent_activity`: normalized activity type, title, amount when relevant, status, `occurred_at`, and deep link.
- `section_health`: per-domain `ready`, `empty`, `stale`, or `error` state and safe user-facing fallback text.

The schema uses additive evolution during migration. Existing domain endpoints remain available to their current consumers until those consumers have moved.

### 6.3 Failure isolation

Authentication failure, failed ownership checks, and invalid workspaces fail the whole request with the appropriate HTTP status.

Non-critical domain failures do not fail the whole home request. The service returns successful sections and marks the failed section in `section_health`. For example, a market timeout must not hide cash, transaction, or readiness information.

Rules:

- No exception becomes a fabricated zero.
- Empty and unavailable are distinct.
- Stale data may remain visible if its timestamp and stale state are explicit.
- Retry controls appear only where a retry can change the state.
- Logs retain technical error details; the response returns safe user-facing language.

## 7. Responsive System

### 7.1 Breakpoints

- **Mobile, below 768 px:** bottom navigation, single-column priority flow, card representations for primary data tables, and bottom sheets or full-screen forms.
- **Tablet, 768–1023 px:** bottom navigation remains, content may use two columns, and dialogs are allowed when keyboard and touch targets remain usable.
- **Desktop, 1024 px and above:** persistent collapsible sidebar, multi-column content, desktop tables, and centered dialogs.

### 7.2 Transformations

- Home grids reorder by importance rather than merely wrapping by CSS position.
- Transaction and holding tables become cards on mobile. Primary information remains visible; secondary details open on demand.
- The market chart receives the available width. Watchlist and advanced indicators move into sheets or tabs.
- Desktop modals become bottom sheets or full-screen flows on mobile when keyboard or content height would obscure the primary action.
- Touch targets are at least 44 by 44 CSS pixels.
- The bottom navigation and floating Asta action account for device safe areas and content padding.
- Primary journeys have no horizontal page scrolling. Specialized internal/admin data tables may scroll inside an explicitly bounded region.

### 7.3 UI states

Every data-bearing surface implements:

- **Loading:** a skeleton that resembles the final layout while navigation remains usable.
- **Empty:** an explanation of value and one primary action to begin.
- **Stale:** the last known value, its timestamp, a stale label, and refresh only when supported.
- **Error:** failure isolated to its section with a useful alternative or retry.

## 8. Migration Strategy

The migration keeps the application usable after every step:

1. Add regression coverage for the existing dashboard terminal, active navigation rules, and domain endpoints used by home.
2. Extract the current dashboard terminal into focused reusable components and mount it at `/market`.
3. Add the home projection schemas, service, deterministic next-action composer, endpoint, and backend tests.
4. Replace `/dashboard` with the guided home.
5. Replace duplicated navigation knowledge with the shared typed journey configuration.
6. Add the desktop journey sidebar, mobile bottom navigation, and floating Asta action.
7. Update internal links and active-state route families.
8. Apply the approved responsive transformations to in-scope pages.
9. Remove obsolete navigation structures, unused dashboard code, orphan routes, dead exports/imports, and temporary compatibility code after all consumers and tests have migrated.

The market terminal is moved, not copied. There must not be two independently evolving terminal implementations.

No redirect is invented for a route that did not previously exist. `/dashboard` intentionally changes meaning to the guided home; `/market` becomes the canonical terminal route. Existing internal links are updated in the same migration.

## 9. Cleanup Policy

Cleanup is a completion requirement, not optional polish:

- Delete unused implementation instead of commenting it out.
- Keep comments only when they explain a non-obvious constraint or decision.
- Verify consumers with repository search before deleting a route, export, or component.
- Do not leave multiple sources for the same calculation.
- A compatibility layer must have a current consumer, a documented reason, and a concrete removal condition.
- Remove unused imports and exports and run static checks after migration.
- Update route documentation and user-facing labels.
- Preserve unrelated user changes in the working tree.

Git history is the archive for removed code.

## 10. Verification

### 10.1 Backend

- Unit tests for every next-action precedence rule and fallback.
- Projection tests for personal and business workspaces.
- Authentication and workspace-ownership tests.
- Tests distinguishing empty, unavailable, stale, and error states.
- Partial-failure tests for each non-critical domain source.
- Schema tests that prevent internal technical terminology from entering user-facing DTO fields.
- Regression tests proving confirmed transaction, allocation, portfolio, and approval values still come from their existing domain sources.

### 10.2 Frontend

- Tests for route-family active states, role visibility, pending badges, and group expansion.
- Tests proving desktop and mobile navigation consume the same typed configuration.
- Home tests for loading, empty, ready, stale, partial-error, and unauthorized states.
- Route tests for `/dashboard` and `/market`.
- Static TypeScript and lint checks.

### 10.3 Responsive and accessibility

- Visual checks at representative widths: 360, 768, 1024, and 1440 px.
- No primary-flow horizontal overflow at 360 px.
- Keyboard traversal, visible focus, semantic labels, dialog focus management, escape/close behavior, and reduced-motion checks.
- Safe-area verification for bottom navigation and the floating Asta action.
- Touch-target verification on mobile.

### 10.4 End-to-end journeys

- Open the app and understand the guided home.
- Record and confirm a transaction, then observe updated activity and supported summary metrics.
- Continue from a readiness gap to Rencana Dana and return to the home state.
- Move from Ide Investasi to Pasar & Grafik and then to Portofolio.
- Resolve a pending approval and observe the badge and next action update.
- Use every mobile bottom tab and open Tanya Asta without losing the ability to return.

## 11. Completion Definition

The workstream is complete only when:

- the approved desktop and mobile journey navigation is present;
- `/dashboard` is the guided home and `/market` is the sole terminal page;
- the home projection is authenticated, ownership-safe, deterministic, and failure-isolated;
- responsive patterns work at the agreed breakpoints;
- all specified tests and checks pass;
- user-facing UI and DTOs avoid internal architecture terms;
- no obsolete duplicate terminal, navigation config, orphan route, commented-out implementation, or unused import/export remains in the changed scope;
- product route documentation reflects the new journey.
