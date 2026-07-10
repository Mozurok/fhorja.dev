# FRONTEND_SYSTEM_DESIGN

Template for the `frontend-system-design` command. Fill every section; mark a section `not applicable` with a one-line reason rather than deleting it. Cover web and mobile where the surface spans both. Cite a source for every number or mark it `PROPOSED-pending-baseline`. For `--interview` mode, the same sections map to RADIO (Requirements, Architecture, Data, Interface, Optimizations); write to `FRONTEND_SYSTEM_DESIGN_INTERVIEW.md` instead.

- Surface: [feature or screen being designed]
- Platforms: [web | mobile | both]
- Stack (from SOURCE_OF_TRUTH.md / DECISIONS.md): [framework and key libraries, or "to be confirmed"]
- Mode: [RFC | interview]

## 1. Problem statement and context
[The user or business problem this surface solves. Scope boundaries. Who consumes it.]

## 2. Requirements
Functional:
- [requirement]
Non-functional:
- [latency, scale, offline, accessibility target, device tiers]
Core vs nice-to-have:
- [what ships first]
Success metrics:
- [user-observable, measurable]

## 3. High-level architecture
[Components and their relationships: view layer, state or store, data-access or networking layer, server or BFF. The rendering surface boundary. A small diagram or component list.]

## 4. Data model
[Entities and fields. Server-originated vs client-only. Cache shape and invalidation.]

## 5. API and interface contract
[Transport (REST, GraphQL, WebSocket, SSE). Payload shape. Pagination (cursor vs offset). Error and retry semantics. Inter-component contracts.]

## 6. Rendering and delivery
[Rendering strategy per surface (SSR, SSG, ISR, streaming, server components, client-side) with the TTFB, SEO, or personalization rationale. CDN or edge. For mobile: navigation and screen-load strategy.]

## 7. State management
[Local vs global vs server-cache state. Real-time sync transport when relevant. Optimistic updates.]

## 8. Performance
[Numeric budget. Web: Core Web Vitals (LCP, INP, CLS) + bundle size. Mobile: startup/TTI, frame budget, list performance. State the percentile and the measurement source. Mark unmeasured thresholds PROPOSED-pending-baseline. Reference PERFORMANCE_BUDGET.md when it exists.]

## 9. Accessibility and i18n
[Conformance target. Keyboard and focus handling. Localization needs. Reference ACCESSIBILITY_AUDIT.md when it exists.]

## 10. Security
[Client-boundary threats: XSS, CSRF, CSP, token handling. When a BFF is in play, confirm tokens stay server-side.]

## 11. Rollout and migration
[Feature flags. Incremental adoption. Backward compatibility. Deploy independence.]

## 12. Trade-offs and alternatives
[The options considered and why the chosen design wins. Name the rejected options and the reason. This section must not be empty.]
