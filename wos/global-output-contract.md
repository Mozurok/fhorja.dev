---
activation: model_decision
description: Calibration vignettes for Work complexity + Why the Handoff block is mandatory. Load when calibrating complexity or debugging handoff shape.
---

# wos/global-output-contract.md

Lazy reference for non-normative subsections of `## Global output contract` in the spec. The normative core (Standard command output layout, Tool-call placement contract, Vocabulary, Natural voice, Task-memory write policy, Every command should end with, Work complexity definitions, Adaptive handoff with Mode A/B) stays inline because it is consulted at every command run. This file holds the explanatory and calibration material that agents only need when humans are calibrating risk levels or onboarding contributors to the contract.

Load this file when:
- you need the full **Calibration examples (non-normative)** vignettes for `LOW` / `MEDIUM` / `HIGH` work complexity
- you need the **Why this is mandatory** rationale behind the strict `### Handoff` requirement
- a contributor or new user asks "why does every response have to end with this fenced block?"

Single-task day-to-day execution does not need this file: every command's `Operating rules:` and `### Definition of done (command output)` already enforce the rules, and the spec keeps the normative templates and capability-routing definitions inline.

---

## Calibration examples (non-normative)

These vignettes illustrate how the same rubric is applied; they do not replace judgment for the task at hand.

- **LOW**: Fix a typo in one markdown doc; rename a local variable with no API surface; adjust a single failing unit test where the contract is obvious from surrounding tests.
- **LOW**: Add logging around one code path already covered by integration tests; small config flag default with rollback documented in the PR.
- **MEDIUM**: Ship a user-facing API change plus a backward-compatible DB migration and deploy ordering notes; touch 3-6 modules with clear integration seams.
- **MEDIUM**: Refactor duplicated logic into a shared helper with behavior preserved by a focused test suite; moderate blast radius if a branch is missed.
- **HIGH**: Change authorization or tenant isolation rules; alter cryptography, secrets handling, or payment-impacting paths; coordinated edits across many packages with weak test signal.
- **HIGH**: Production incident with incomplete traces, unclear root cause, and time pressure; any fix where a wrong assumption creates safety or compliance exposure.

When two vignettes seem to fit, prefer the higher complexity if mistake cost is asymmetric.

The capability-routing definitions of `LOW` / `MEDIUM` / `HIGH` / `N/A` themselves remain inline in the spec `## Global output contract` → `### Work complexity (capability routing)` because they are consulted at every command's `Recommended work complexity:` decision. These vignettes are the supporting calibration set, not the rubric itself.

## Why the Handoff block is mandatory

The workflow does not stop at describing the next phase; it hands off directly into the next action.

Models sometimes stop after large `### Artifact changes` payloads; that breaks resumability. Never truncate the response before a complete `### Handoff`.

This reduces:
- ambiguity (the next concrete invocation is spelled out)
- context waste (no re-explaining what was just decided)
- repeated routing (each command's recommendation is the next command's pre-filled prompt)
- "what do I do now?" pauses (the user does not have to translate a phase recommendation into a command invocation)

The adaptive handoff (Mode A compact, Mode B full) replaces the previous fixed `Paste this next:` body. Mode A (~50 tokens) is the default within the same session because the context window already contains everything; Mode B (~150-250 tokens) adds a `Resume context:` block with only what cannot be re-derived from task files, used when context loss is likely (new chat, post-compaction, resume-from-state, handoff to another person).

These motivations live here rather than in the spec because the rules themselves (Adaptive handoff, Mode selection rule) are already in the spec `## Global output contract`. Agents enforcing the contract only need the rules; the rationale is for humans deciding whether to relax or extend them.
