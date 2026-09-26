# Maturity ledger -- <persona-id>

> One file per persona, recording every level change and the evidence behind it.
> Lives at `_internal/maturity-ladder/<persona-id>.md`, which is maintainer-local and
> gitignored: a fresh clone has no ledgers and starts its own from this template.
> The ladder itself is `wos/maturity-ladder.md`; the promotion gates live there, not here.

---

## Persona

- **Persona ID:** `<persona-id>`
- **Current level:** `<L1 | L2 | L3 | L4 | L5>`
- **Promotion path:** `<A | B | n/a>`  <!-- required at L3+ per ADR-0036 -->
- **Owned sections:** `<from wos/substrate-peers.md, or none>`

## Level history

One row per change, newest last. A demotion is a row like any other: the point of the
ledger is that a level went down and why, not only that it went up.

| Date | From | To | Path | Trigger | Evidence |
| --- | --- | --- | --- | --- | --- |
| `<YYYY-MM-DD>` | `<L1>` | `<L2>` | `<A/B/n-a>` | `<portfolio aggregation, review gate, demotion>` | `<dashboard file, packet path, run ids>` |

## Evidence for the current level

Copy the block the ladder asks for, filled with the numbers that were true when the
change was made. Do not update these in place later: a new level gets a new block.

```yaml
persona_id: <persona-slug>
current_level: <L1 | L2 | L3 | L4>
promotion_path: <A | B>
evidence:
  k7_iterations: <N>
  k7_delta_pass_rate_trend: <monotonic-up | flat | regressing | oscillating-above-floor>
  k7_latest_pass_rate: <float 0-1>
  verification_log_validator_errors_per_run: <float>
  fleet_run_count: <integer>
  fleet_run_folder_count: <integer>
  fleet_cohort_systemic_cluster_count: <integer>
  review_gate_user_decision: <pending | approved | declined>
  review_gate_date: <YYYY-MM-DD | null>
```

## Notes

Anything a future reader needs that the table cannot hold: a promotion that was
argued and declined, a run whose numbers qualified but whose output did not, a gate
that was waived and by whom. Write the awkward ones down; those are the entries
worth having.
