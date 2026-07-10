# ADR-0046: No auto-install, human-gated trust for third-party skills and plugins

- **Status**: Accepted
- **Date**: 2026-06-22
- **Tags**: agent-skills, supply-chain, security, human-in-the-loop, skill-vet, capture-references, additive

## Context

The WOS treats agent skills as a one-way generated output: `scripts/build-agent-skills.sh` compiles each canonical `commands/*.md` into `.claude/skills/<name>/SKILL.md`, and the only inbound check (`--check`) verifies the generated skill has not drifted from its canonical source. There was no concept of consuming, installing, or vetting a third-party skill or plugin, and no notion of skill supply-chain risk anywhere in the spec. That was safe while every skill on the surface was first-party.

It is no longer a hypothetical gap. By 2026 there are working install paths (Claude Code plugin marketplaces, ClawHub, skills.sh), and independent audits show the risk is real: a large fraction of marketplace skills carry vulnerabilities and a measurable fraction carry malicious payloads, with publishing gated only by a `SKILL.md` plus a host account (no signing, review, or sandbox). The sharpest finding is that scanning the visible artifact is insufficient: payloads ride in on test and auxiliary files and on hidden-Unicode or description-field instructions that body-only scanners skip, so a skill's documentation can misrepresent its behavior. This was surfaced and graded in the `2026-06-21_wos-improvement-research` task (W-04, W-11, W-16) and grounded in captured sources in the project `REFERENCES.md`.

The WOS already encodes human-gated trust elsewhere (ADR-0043 reference-grounding execution gate; the autonomous-track two human gates in ADR-0044). The open question was whether to add a third-party skill capability and, if so, under what trust posture.

## Decision

The WOS never auto-installs, auto-enables, or auto-trusts a third-party skill or plugin. Any external skill enters only through this path:

1. Capture: the skill's source is captured via `capture-references` (project-level `REFERENCES.md`, deduplicated by URL), so the origin is recorded before any inspection.
2. Vet: `skill-vet` performs a read-only inspection of the candidate (every file, not just `SKILL.md`: declared-vs-actual behavior, exfiltration and secret access, out-of-directory and agent-config writes, shell execution, hidden or zero-width Unicode, description-field injection, supply-chain manifest review) and returns a verdict of INSTALL, SANDBOX, or DECLINE.
3. Approve: a human approves the actual install or trust decision. `skill-vet`'s verdict is a recommendation, never an action.

`skill-vet` is read-only by contract: it never installs, enables, registers, moves, executes, or fetches. The detection contract behind it is recorded as the `skill-context-poisoning` bug-class so `repo-consistency-sweep` can catch the same patterns when skill or plugin files are in a repo's scope.

This decision is additive. It introduces one new command (`skill-vet`) and one new bug-class; it does not change the behavior of any existing command, and it does not make the WOS install or run anything.

## Consequences

### Positive

- Closes a concrete, externally-audited supply-chain gap with a posture consistent with the rest of the WOS (human-gated trust, ADR-0043, ADR-0044).
- The inspection reads every file and the description, so it catches the test-file and hidden-Unicode payloads that artifact-only scanners miss.
- `skill-vet` and the `skill-context-poisoning` bug-class reinforce each other: one is the pre-install gate, the other is the in-repo sweep.

### Negative

- `skill-vet` is a heuristic read, not a sandbox or a full scanner like SkillSpector. It can miss an obfuscated payload. The SANDBOX verdict exists precisely for the uncertain case; the command must not present itself as a guarantee of safety.
- Maintaining a new command carries the usual cost (four-registry registration, an eval scenario, drift guards).

### Neutral

- Today the WOS skill surface is 100% first-party, so the provenance-frontmatter idea (research item DEF-09) stays deferred until external skills actually enter the surface. This ADR governs the trust path; it does not add per-skill provenance metadata yet.

## Alternatives considered

### Alternative 1: build a full scanner (reimplement SkillSpector)

- Rejected. The WOS is markdown plus bash plus a small Python helper, with a zero-new-runtime-dependency stance (ADR-0027). A full static-plus-LLM scanner is a separate product. `skill-vet` is a focused, human-gated read that surfaces evidence and a verdict; depth beyond that is out of scope.

### Alternative 2: allow auto-install of skills with a passing vet

- Rejected. Auto-install on a heuristic verdict contradicts the WOS human-first posture (the same reason ADR-0044 forbids auto-merge). The human approves; the tool advises.

### Alternative 3: do nothing (keep skills first-party only)

- Rejected. The consumption surface already exists in the ecosystem and the maintainer will encounter third-party skills; leaving the WOS with no vetting path is the actual risk this ADR removes.

## References

- `projects/<client>__<project>/active/2026-06-21_wos-improvement-research/` (source research: `WOS_IMPROVEMENT_BACKLOG.md` W-04/W-11/W-16, `EXTERNAL_RESEARCH.md`) and the captured sources in the project `REFERENCES.md` (Snyk ToxicSkills, the VentureBeat test-file finding, Embrace The Red hidden-Unicode, the Claude Code plugins trust-the-source docs, NVIDIA SkillSpector).
- `commands/skill-vet.md` (the command this ADR governs) and `wos/bug-classes/skill-context-poisoning.md` (the in-repo detection contract).
- ADR-0043 (reference-grounding execution gate), ADR-0044 (autonomous two-gates, no auto-merge), ADR-0027 (zero-new-runtime-dependency stance), ADR-0010 (centralized external web access; `capture-references` is the only capture path).

## Notes

Locked in the `2026-06-21_implement-wos-improvement-backlog` task (decisions D6 to D12; W-16 conditional on W-04, satisfied). Status stays Proposed until the maintainer signs off, then Accepted. Provenance frontmatter (DEF-09) is the natural follow-up once a vetted external skill is actually adopted into the surface; that would be a new decision, not a patch to this ADR.
