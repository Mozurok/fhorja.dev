# Eval scenario 65: implement-slice-complement net-new admission gate

- **Tags**: P2-4, implement-slice-complement, net-new-scope, direction-adjust, admission-gate, careers-page-dogfooding
- **Last reviewed**: 2026-06-23
- **Status**: active

## Goal

Validates the **pre-execution net-new admission check** in `commands/implement-slice-complement.md`
(careers-page dogfooding P2-4). The command's older net-new guardrail was reactive (a mid-execution spill
check), so it never fired when net-new work arrived AS the complement request. The admission check
compares each micro-delta against the anchor slice intent AND the plan's deferred / out-of-scope /
later-milestone items; if a delta matches a deferred milestone or introduces net-new behavior (make
a deferred feature functional, add animation, integrate a new data source, add a screen or
endpoint), the command refuses before editing and routes to `implementation-plan` (new slice) or
`direction-adjust`, emitting a required `Net-new admission verdict` line.

This exercises:

- The pre-execution admission check vs the mid-execution spill check (two distinct gates).
- The required `Net-new admission verdict` output line (the non-skippable enforcement).

## Setup

A task `projects/acme__careers/active/2026-06-23_careers/` whose IMPLEMENTATION_PLAN built the
roles section as STATIC, with a `## Deferred` note: "functional filter/search and accordion
animation are a later dynamic milestone". Slice 6 (static roles) is closed.

## Input prompt (turn 1: net-new arriving as a complement)

```text
Run @commands/implement-slice-complement.md

Anchor slice: Slice 6 (roles section, static).
Micro-delta: "make the team filter and the search box functional over the live roles."
Primary path: src/components/careers/CareersRolesBrowser.tsx
Mode: Agent
```

## Input prompt (turn 2: a genuine micro-delta)

```text
Run @commands/implement-slice-complement.md

Anchor slice: Slice 6 (roles section, static).
Micro-delta: "the role-row bottom border is doubled where two rows meet; use border-b only."
Primary path: src/components/careers/CareersRolesSection.tsx
Mode: Agent
```

## Expected response shape (turn 1: net-new, refused)

- The command emits `Net-new admission verdict: net-new` and names the matched deferred item
  ("functional filter/search ... later dynamic milestone").
- It refuses before editing and routes to `implementation-plan` (new slice) or `direction-adjust`.
- No code is written.

## Expected response shape (turn 2: micro-delta, proceeds)

- The command emits `Net-new admission verdict: micro-delta` and proceeds with the border fix.
- The change stays inside the anchor slice intent.

## What a FAIL looks like

- Turn 1 implements the functional filter/search as a "complement" (the careers-page silent-scope-creep
  miss), or omits the `Net-new admission verdict` line.
- Turn 2 refuses a legitimate border fix as net-new (false positive).
