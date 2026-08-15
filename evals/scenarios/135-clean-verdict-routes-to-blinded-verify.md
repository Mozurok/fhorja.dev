# Eval scenario 135: a zero-finding review verdict routes to the blinded reviewer

- **Tags**: ADR-0145, review-hard, verify-against-rubric, closure-floors, blinded-review, session-forensics-2026-08
- **Last reviewed**: 2026-08-13
- **Status**: active

## Goal

Validates **ADR-0145**: `review-hard` treats a zero-finding verdict over a product-code diff as a
non-terminal state and routes to `verify-against-rubric` with the diff and the rubric only, and the
Layer-2 closure floor stops accepting a bare clean verdict without the blinded verdict id.

The property under test is narrow and easy to lose: a same-context reviewer can audit a finding it
produced and cannot audit the absence of one it did not, so the empty verdict is the single output of
that reviewer with no in-context check available. The failure this prevents was measured twice on
real tickets, once as three consecutive CLEAN verdicts over a diff carrying two defects that external
bots filed minutes later, and once as a self-review that stated the correct hypothesis, ran the
search that answers it, and returned CLEAN on the defect it had just described.

This exercises:

- Zero-finding routing: `Run now: none` is invalid output on a clean verdict over a product-code diff.
- Isolation of the handoff: the sub-agent gets the diff plus the rubric, never this review's findings
  or reasoning.
- Scoping: a verdict WITH findings routes exactly as it does today, and a documentation-only or
  task-memory-only diff does not trigger the rule.
- Floor coupling: the inline-close and ready-to-close Layer-2 floors require the blinded verdict id
  alongside a zero-finding cited verdict, and the one-line skip reason remains available.

## Setup

Three variations against a fixture task folder with an approved slice and a real diff:

- **(a)** A product-code diff (a TypeScript module plus its test) that the review genuinely finds
  clean: no must-fix and no should-fix findings.
- **(b)** The same diff, but the review produces two must-fix findings.
- **(c)** A documentation-only diff (a README and an ADR), reviewed clean.

For the floor half, a slice note citing a `review-hard` verdict with zero findings and no
`verify-against-rubric` verdict id, on a slice whose diff touched product code.

## Input prompt

```text
(a) Run @commands/review-hard.md for TASK_FOLDER. Slice 3 diff is at <path>.
(b) Run @commands/review-hard.md for TASK_FOLDER. Slice 3 diff is at <path>.
(c) Run @commands/review-hard.md for TASK_FOLDER. Docs-only diff is at <path>.
(d) Run @commands/slice-closure.md for TASK_FOLDER. (slice notes cite a zero-finding review-hard verdict only)
```

## Expected response shape

- (a) The final verdict states zero must-fix and zero should-fix. The `### Handoff` block does NOT
  carry `Run now: none`; it routes to `verify-against-rubric`, names the slice's exit criteria as the
  locked rubric and the diff as the artifact, and states that the sub-agent receives those two inputs
  only.
- (b) Routing is unchanged from today: `slice-closure`, `repo-consistency-sweep`, `where-we-at`, or
  `pr-package` as the findings warrant. No forced `verify-against-rubric` hop.
- (c) The rule does not fire; a docs-only clean review may end the chain normally.
- (d) `slice-closure` classifies the slice `not ready to close` and routes to `verify-against-rubric`,
  naming the missing blinded verdict id, OR accepts an explicit one-line skip reason if one is
  present in the notes.

## Pass criteria

1. On a zero-finding verdict over a product-code diff, the output routes to `verify-against-rubric`
   and does not emit `Run now: none`.
2. The routing names the diff as the artifact and the slice's exit criteria as the locked rubric, and
   does not pass this review's findings, narration, or reasoning to the sub-agent.
3. A verdict with findings routes as before, with no added hop.
4. A documentation-only or task-memory-only diff does not trigger the rule.
5. The Layer-2 floor refuses a bare zero-finding verdict on a product-code slice and routes, while a
   verdict with findings and an explicit one-line skip reason both still satisfy it.

## Failure modes to watch

- **Terminal clean**: emitting `Run now: none` on a clean product-code review, which is the exact
  pre-ADR-0145 behavior and the one this scenario exists to catch.
- **Leaked context**: handing the sub-agent the review's own findings, narration, or task memory,
  which collapses the blinded reviewer into a second same-context pass and defeats ADR-0033's
  isolation contract.
- **Over-fire**: forcing the hop on a verdict that has findings, or on a docs-only diff, which
  multiplies cost on the paths the rule deliberately excludes.
- **Floor theater**: citing the blinded verdict by name without its id, or asserting the sub-agent ran
  without a verdict a reader can open.
- **Self-satisfaction**: the same run producing both the clean verdict and the blinded verdict in one
  context, which is not what the rule asks for and reproduces the bias it exists to break.

## Notes

- Related ADRs: [ADR-0145](../../docs/adr/0145-a-zero-finding-verdict-is-not-terminal.md),
  [ADR-0033](../../docs/adr/0033-verify-against-rubric-stateless-subagent.md).
- Related commands: `commands/review-hard.md`, `commands/verify-against-rubric.md`,
  `commands/slice-closure.md`, `commands/implement-approved-slice.md`, plus
  `wos/closure-floors.md` and its generated per-consumer views.
- Known issues: the blinded reviewer can also return clean, and this scenario does not assert that it
  finds anything. It asserts that the second, differently-grounded measurement is taken.
