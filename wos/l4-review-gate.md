# L3 -> L4 Manual Review Gate

The L3 -> L4 transition is the only ladder step in the Fhorja maturity model (see `wos/maturity-ladder.md`) that is **not** auto-graduated. L4 grants a persona full peer ownership equivalence with commands -- its writes participate in the same canonical artifacts, validation, and drift-guard treatment as first-party Fhorja commands. Because that bar is qualitative ("does this persona deserve to be trusted like Fhorja itself?"), promotion requires explicit user judgment over a structured review packet, anchored by ADR-0034 (lived-substrate ladder) and ADR-0036 (review-gate verdict shape).

This document defines the eligibility filter, the packet Fhorja assembles for the user, the judgment question, the verdict shape, the implications of L4, and the demotion path.

## Eligibility

A persona is eligible for L3 -> L4 review only when **all** of the following hold simultaneously at the moment the gate is opened:

- The persona has been at L3 for **>= 30 days** of wall-clock time since its L2 -> L3 auto-graduation timestamp.
- The persona has produced **>= 10 lived substrate writes** (artifact edits captured in the persona ledger) across **>= 3 distinct task folders** (projects/<client>__<project>/active/ or archive/ entries). Substrate writes inside a single task do not establish breadth; the >=3 task-folder floor exists specifically to filter personas that only "look mature" on one engagement.
- The persona has **zero K.5 errors** recorded in its ledger over the L3 window. K.5 errors are contract violations (wrong owned-section, schema-invalid output, refusal-protocol miss). Even a single K.5 in the L3 window resets eligibility.
- The persona has **zero SYSTEMIC clusters** flagged against it in K.7 trend analysis over the L3 window. A SYSTEMIC cluster means the persona has been implicated in a repeating defect class across runs (not a one-off). LOCAL or per-run K.7 findings do not block eligibility; only SYSTEMIC clusters do.

If any of the four conditions fail, the gate cannot be opened -- Fhorja surfaces the specific gap instead of presenting a review packet.

## Review packet

When eligibility passes, Fhorja assembles a review packet for the user. The packet is the sole source the user judges from; Fhorja never asks the user to remember context out-of-band. The packet contains:

- **Per-persona ledger** -- chronological record of every substrate write the persona made at L3, with task folder, artifact path, write timestamp, and post-write validation status. This is the lived evidence trail.
- **K.7 trend** -- defect-class trend lines for the persona over the L3 window, broken down into LOCAL vs SYSTEMIC, with the SYSTEMIC count explicit (must be 0 to reach this stage, but the trend slope still matters for judgment).
- **Fleet-run summary** -- aggregate behavior across multi-persona fleets the persona participated in: dispatch count, success rate, average artifact quality scoring (where available), and notable refusals or escalations.
- **Sample outputs** -- 3-5 representative artifact writes (full text, not snippets) chosen to span the breadth of the persona's owned-sections at L3. The user reads these as the qualitative anchor.

The packet is rendered once and kept stable across the review window (the user may take days to decide; the packet does not silently update underneath them).

## User judgment

The single question the user answers on the packet is:

> **Does this persona deserve full peer ownership equivalence -- commands-grade trust on its owned artifacts?**

L4 is not "L3 plus a little more autonomy." It is the explicit decision that the persona's substrate writes should be treated by Fhorja with the same operational weight as first-party command output: same validation, same drift-guard severity, same downstream consumer trust. The user is judging *equivalence*, not incremental improvement.

## Verdict shape

Per ADR-0036, the verdict is one of three:

- **APPROVE** -- promote persona to L4. Implications below take effect immediately on the next dispatch.
- **DECLINE** -- persona remains at L3 indefinitely. The gate is closed; the persona may be re-reviewed if conditions materially change (e.g., new fleet wins), but DECLINE is not a deferred-yes.
- **REQUEST_CHANGES** -- persona remains at L3, but with explicit recorded concerns (named in the verdict body) the persona must visibly address before the gate reopens. Fhorja tracks the named concerns and surfaces them in the next packet.

Verdict, rationale, and packet snapshot are persisted under the persona record.

## L4 implications

When APPROVE fires:

- **owned_sections expansion** -- the persona's owned_sections set expands from 1 (the single L3-permitted section) to 1+ (multiple sections it may now write canonically). The expansion list is locked in the verdict body, not open-ended.
- **Full validation** -- L4 persona output runs through the same schema and contract validators as command output. No "persona soft-mode" carveouts.
- **Alerts on REFUSE** -- when an L4 persona returns a REFUSE response, Fhorja treats it as a P3 operational alert (commands-grade personas should rarely refuse; refusal is a meaningful signal worth surfacing).
- **Drift-guard escalates to P2** -- any drift-guard finding against L4 persona output is auto-escalated to a P2 bug finding (vs P3/informational at L3). This is the teeth behind "commands-grade trust": the consequences of being wrong scale with the trust granted.

## Demotion

L4 is revocable. If an L4 persona later either records a K.5 error or accumulates a SYSTEMIC K.7 cluster, Fhorja **auto-demotes** the persona to L3 immediately, with a written rationale captured in the persona record (specific K.5 ID or SYSTEMIC cluster signature). No new review is needed for demotion -- the trust contract was conditional, and the conditions failed.

A demoted persona may re-enter the L3 -> L4 review cycle, but only after fresh eligibility is re-established from the demotion timestamp (new 30-day window, new 10/3 lived-write count, zero new K.5/SYSTEMIC since demotion). The prior APPROVE does not carry forward.

---

References: ADR-0034 (lived-substrate maturity ladder), ADR-0036 (review-gate verdict shape), `wos/maturity-ladder.md`.
