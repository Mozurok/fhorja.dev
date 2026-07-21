# Active epistemic humility

Lazy-loaded reference topic. Load when authoring or reviewing a rule about what an agent may assert, when it must investigate instead, or how a recorded claim gets revised. This file is the full contract with rationale; the normative core is delivered through two surfaces landed by later slices of this doctrine's rollout: the shared block `commands/_shared/claim-grounding.md`, and one new subsection of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.

The posture in one sentence: not knowing is not a failure and not a conclusion, it is the start of an investigation.

This file has two parts and they are not the same kind of rule. **Part 1 is mechanized**: every rule names the check that enforces it, and a violation is catchable without human judgment. **Part 2 is not mechanized**: no script verifies any of it, and it is written down because losing it entirely would be worse than stating it honestly as unverified. Do not move a rule between parts without an ADR. A Part 2 rule cited as if it were a gate is a misuse of this file.

---

## Part 1: Mechanized rules

Every rule here is checkable by a script or by a reviewer reading a diff, and each names its enforcement point.

### 1.1 The obligation is keyed to the claim, not to the file set

The duty to investigate fires on a **load-bearing claim** that cannot be traced to the grounded set. It does not fire on which files a change happens to touch.

- Load-bearing claim: a claim a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is.
- Grounded set (enumerable, four members only): a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, a passing deterministic gate (ADR-0048).
- A claim supported only by model memory is **outside** the grounded set, including when the model happens to be right. The model's internal knowledge is not observable from markdown and bash, so it cannot be a member.

Enforced by: `commands/_shared/claim-grounding.md` at assertion time.
Why the file set is the wrong key: a fix inside a library the repository already imports leaves the file set unchanged while the claim about that library's behavior sits entirely outside the grounded set. That case is the one the import-and-diff scan in `commands/_shared/reference-grounding.md` structurally cannot see.

### 1.2 Two triggers, not one

- **Assertion-time trigger.** A load-bearing claim outside the grounded set routes to investigation or to abstention. It is not asserted.
- **Defense-time trigger.** New evidence entering the task that bears on an already-persisted claim opens that claim for revision.

These are orthogonal. The first prevents an ungrounded claim from entering; the second prevents a claim that already entered from becoming permanent. A system with only the first still accumulates frozen beliefs.

Enforced by: `commands/_shared/claim-grounding.md` (assertion), the `## Decision history` write rule in `wos/substrate-peers.md` (defense).

### 1.3 Status records provenance, never confidence

Where a claim carries a status, the status names **where the claim came from**:

- a `REFERENCES.md` entry title,
- a file path plus line,
- the gate output it came from.

A status SHALL NOT express a degree of certainty. There is no confidence field, no numeric threshold, and no self-assessment prompt anywhere in this contract.

A status whose referent slot is empty is read as **unknown**, not as a weak yes.

Why: a self-reported confidence signal is not usable as a control signal. Frontier models articulate uncertainty and then act as if certain, and they do not abstain more as the penalty for being wrong rises. A reliability estimate derived from how confident the text sounds is also manipulable. A referent is checkable by a human or a script; a feeling is not.

Enforced by: `commands/_shared/claim-grounding.md`, plus a static check in `evals/scripts/structural-evals.py`.

### 1.4 Where the status is mandatory

- **Persisted claims** (anything written into a task-memory artifact): status is mandatory, and it travels with the claim. A later command reading that claim reads its provenance too. The status is not dropped at the write boundary.
- **Chat-only claims**: status is required only when the claim crosses the grounding boundary and triggers a route. On an output where nothing crosses, the contract costs nothing.

Why the split: persistence is where provenance compounds, because the reader arrives without the context that produced the claim. A chat turn is read once, in context, where a status on an already-cited claim is noise.

### 1.5 Abstention is a routed continuation

When the system abstains, the output names the specific investigation that would settle the question **and** routes to the command that runs it.

A bare refusal is invalid output. Abstention that stalls the work has traded a wrong answer for no answer, which is not the goal.

`NO_OP` and abstention are different results. `NO_OP` means there is no work to do. Abstention means there is work to do and the grounding to do it is missing.

### 1.6 Revision is append-only and provenance-capped

- A revision **records**; it never overwrites the prior claim text.
- The right to override a persisted claim is capped by provenance: a later assertion overrides only when its provenance rank is at least as high. The seven-level `## Evidence priority` list in `WORKFLOW_OPERATING_SYSTEM.md` is the cap function, not only a reading order.
- Two contradicting claims at **equal** provenance rank escalate to the user. The system does not pick a winner.
- Lifecycle position matters: in-task a recorded revision annotates without blocking; at `task-close` an unresolved revision blocks closure.

Why the position split: a gate authored for one lifecycle position and applied at every position is a category error. Blocking every checkpoint on an open revision converts a reliability mechanism into ceremony.

### 1.7 Cost floor

An output whose load-bearing claims are all grounded pays close to nothing. The boundary test is a membership lookup against an already-enumerated set, not a new retrieval.

The failure mode to design against is a status label that costs tokens and changes no control flow. If crossing the boundary does not route, the label is ceremony and is not required.

### 1.8 An unfired gate is not evidence

The absence of a fired gate SHALL NOT be read as evidence that grounding existed. Silence means the check did not fire; it does not mean the check passed.

---

## Part 2: Dispositions (not mechanized, not verified by any check)

Nothing below is enforced by a script, a lint rule, or an eval. It is recorded because these are the parts of the posture that have no mechanical form, and dropping them would leave the doctrine as bookkeeping. Treat this part as guidance to an agent and a reviewer, never as a gate, and never cite it as a reason to block.

- **Prefer finding out over sounding right.** When an answer can be checked cheaply, check it rather than reason toward it. The cost of a grep is almost always lower than the cost of a confident wrong claim.
- **A confident, internally consistent record is not evidence of truth.** It is evidence that searching stopped. Read a tidy prior decision as a question about when it was last tested, not as a settled fact.
- **State the shape of your ignorance, not just its existence.** "I do not know" carries little; "I do not know whether this library changed its default in v3, and the way to find out is the changelog" carries the next step.
- **Hold the strongest version of the position you are about to reject.** A rejected alternative described weakly was not actually considered.
- **Report the check that failed, including when the failing check was your own.** A verification that produced a wrong number is worth surfacing; suppressing it protects nothing but appearances.
- **Do not manufacture doubt either.** Hedging a claim that was actually verified is the mirror-image failure. Fallibilism says knowledge does not require certainty, so a checked claim needs no qualifier.

---

## Grounding

The rules above are derived from sources captured in the project `REFERENCES.md` (2026-07-20) and synthesized in the task's `EXTERNAL_RESEARCH.md`. The load-bearing ones:

- Rule 1.1's claim-keyed boundary comes from the knowledge-boundary partition in Divide-Then-Align, adapted to the one axis this system can observe.
- Rule 1.3's prohibition on confidence gating rests on the measured dissociation between verbalized confidence and abstention behavior, and on the manipulability of reliability estimated from epistemic language.
- Rule 1.5's routed-continuation shape follows the definition of abstention as withholding without compromising performance, and the pragmatist framing of doubt as the opening of inquiry.
- Rule 1.6's provenance cap comes from provenance-capped belief updating; its scoping to claims where evidence can conflict comes from the finding that belief updating buys nothing where evidence never conflicts.
- Part 2 exists because virtue epistemology takes the agent's intellectual character, not the isolated belief, as the primary object of evaluation, and the field records criticism of forcing a choice between reliable-faculty and cultivated-trait accounts.

## What this does not change

- `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority` keeps its wording and its ordering. This topic reuses that list as a cap function; it does not rewrite it.
- ADR-0043's reference-grounding execution gate and its import-and-diff detection keep working for the case they already cover. Rule 1.1 retires the file set as the doctrine's key, not that gate from the repository.
- ADR-0086's read-the-comment-thread obligation is unchanged.
- No command is added. This topic is delivered through folds into existing surfaces.
