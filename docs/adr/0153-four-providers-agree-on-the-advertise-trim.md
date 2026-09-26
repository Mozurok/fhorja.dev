# ADR-0153: Four independent providers agree on the Advertise trim, and installed skills are a confound the control cannot see

Date: 2026-08-17

Status: Accepted

## Context

ADR-0152 D-5 left one thing explicitly unclaimed: "What remains unbounded is model diversity and
prompt-shape diversity; a second model would strengthen this and has not been run." Every number in
ADR-0151 and ADR-0152 came from one model family, so the finding could have been a property of that
family rather than of the text.

The maintainer has Kimi, Codex and Grok CLIs installed alongside Claude. All four were run against
the committed case set.

## Decision

**D-1. The measurement across four providers.** One replicate per condition per provider, 89
commands, 89 cases, all descriptions present in every prompt, same case set as ADR-0152
(`evals/fixtures/routing-probe/cases-89.json`):

| Provider | A full | B trimmed to 47% | C opener only, 22% | D shuffled control |
|---|---|---|---|---|
| Claude (3 replicates) | 100.0% | 100.0% | 99.3% | 0.0% |
| Kimi | 98.9% | 100.0% | 97.8% | 0.0% |
| Codex | 98.9% | 98.9% | 97.8% | 0.0% |
| Grok | 98.9% | 100.0% | 100.0% | 1.1% |
| Kimi, skills directory emptied | 98.9% | not run | 96.6% | 1.1% |

Every control collapsed (maximum 1.1 per cent), so every provider was reading the descriptions.
Across providers: A spans 98.9 to 100, B spans 98.9 to 100, C spans 96.6 to 100. No provider
disagrees, and no provider degrades meaningfully as the description shrinks to 22 per cent of its
size.

**D-2. Installed skills are a confound, and the shuffled control cannot detect it.** Fhorja installs
its skills with FULL descriptions into `~/.claude/skills` (98), `~/.agents/skills` (99, read by Kimi
and Codex) and `~/.cursor/skills` (109). Every provider therefore held the complete text of every
description while being shown a trimmed one. A trimmed opener can then serve as a lookup key into
knowledge the model already has, rather than as the routing signal itself.

This was found by reading Kimi's reasoning trace, which named real commands (`cmd-32:
repo-consistency-sweep`) that appear nowhere in the prompt. It was not found by any control, and it
cannot be: with descriptions swapped, a model reasoning from prior knowledge picks the wrong
identifier exactly as a model reasoning from the text does, so `D_shuffled` collapses either way and
the run looks clean. A control that cannot distinguish two hypotheses must be stated as such rather
than cited as though it covered both.

**D-3. Measured, the confound is small.** Kimi was re-run with `--skills-dir` pointed at an empty
directory. C_gut moved from 97.8 to 96.6 per cent, one case out of 89, with 86 of 89 choices
identical between the two runs. The conclusion survives without the leak: a provider with no access
to the full text routes 86 of 89 from the opening sentence alone. Recorded as small rather than
absent, and only known because it was checked.

**D-4. ADR-0152 D-5 is superseded on model diversity.** The trim result is not a property of one
model family. Prompt-shape diversity remains unclaimed: all runs use the same prompt template, and a
different framing of the routing question has not been tried.

**D-5. The probe's docstring now carries the environment warning.** Anyone re-running this in a shell
where Fhorja skills are installed measures a partly-contaminated number, and the warning names the
three directories and the `--skills-dir` workaround, because the failure is invisible in the output.

## Consequences

- The evidence ADR-0135 item 2 demanded is now four-provider. Trimming the Advertise stage to roughly
  47 per cent of its size costs nothing measurable on this corpus for any of Claude, Kimi, Codex or
  Grok. This remains permission, not a plan: ADR-0152 D-6 still stands, the trim is a separate change,
  and the descriptions also serve human readers of the catalog, which no probe here measures.
- Four defects have now been found in this one measurement, each of which produced a HIGH score:
  command names leaking the answer (ADR-0151 D-2), list position predicting the answer (ADR-0152
  D-2), a scrub collision making two descriptions identical (ADR-0152 D-4), and installed skills
  supplying the full text (D-2 here). None was visible in the output. The pattern worth carrying
  forward is that on this kind of measurement a clean result is the thing to distrust.
- Reproducing the four-provider run is manual: `emit`, then feed each prompt to each CLI, then
  `score`. It is not wired into CI and should not be, since it costs four providers' tokens per run.
