**Runtime verification skeleton (shared).** Every runtime gate in this workflow runs the same eight steps and the same four cross-cutting rules; only the adapter battery differs, and it is loaded from this command's own `wos/<surface>-runtime-battery.md` topic.

1. Restate the slice, its acceptance behavior (the EARS exit criterion when present), and how the target was run or served. If the real output is not available, STOP and request it; do not proceed on an asserted result.
2. Read or record the real output. Quote the load-bearing lines verbatim; never paraphrase an error and never fabricate output.
3. Run the adapter battery from the topic this command names.
4. Classify each observation with exactly one taxonomy code from the adapter, one line per observation: the quoted symptom, the code, the most likely cause.
5. Verdict per acceptance criterion: `observed`, `not-observed`, or `unverified` (output not shown), each grounded in the captured evidence.
6. Gate decision: PASS, FAIL, or BLOCKED, stated in one line with its reason.
7. Write the report into the active task folder under this command's own artifact name, carrying the run mechanism, the quoted output, the classification table, the per-criterion verdict and the gate decision.
8. Adoption per slice: a slice on this surface either runs this gate or records an explicit skip with its reason; a silent absence is not a skip.

Cross-cutting rules, all four normative:
- Evidence, not trust (ADR-0048): the run's actual output MUST be shown. A result claimed but not shown is `unverified`, never PASS, exactly like an asserted "tests pass".
- Bounded retry (`wos/gate-conditions.md` interactive bounded retry): in a hold-until-pass loop, cap consecutive failed runs at a small N (default 3 to 8). At the cap, record the failure with the evidence already captured and route the fix (`incident-triage` when the fix is unclear, `implement-slice-complement` when it is bounded and known). Do NOT repeat the same run, and do NOT hold the session waiting for a human: the cap ends the repetition, not the chain (D-6, D-7).
- Layer placement: a PASS here is Layer-1 runtime evidence; it does not skip Layer 2 (`review-hard`, `repo-consistency-sweep`) or Layer 3 (human approval).
- Verify, then route the fix; do not fix here. A FAIL routes to `incident-triage` (to size an unclear fix) or `implement-slice-complement` (a bounded known fix inside the slice intent). Reopening a signed-off decision routes to `post-review-pivot`.

