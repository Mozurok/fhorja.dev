---
activation: model_decision
description: The natural-voice rule for all human-facing Fhorja prose. Which AI-tell patterns to avoid (slash disjunctions, not-just-X-but-Y parallelism, vocabulary cliches, decorative bold, emoji, Title Case) and how to rewrite each so output reads like a person wrote it. Load when writing or reviewing human-facing text (PR descriptions, commit messages, team updates, delivery assets, slice notes, docs) or when auditing existing prose for AI tells.
---

# wos/natural-voice.md

The normative core of this rule is inline in `WORKFLOW_OPERATING_SYSTEM.md` under `## Global output contract` -> `### Natural voice (no AI tells)`. This file is the full catalog: the patterns to avoid, why each one reads as machine-written, and a natural rewrite for each. Load it when you are writing human-facing prose or auditing text for tells. Day-to-day command execution does not need it.

Scope: any prose a human reads. PR descriptions, commit bodies, team and status updates, delivery assets, slice notes, ADR prose, docs, and the command files themselves. It does not govern code, identifiers, enums, or fenced examples.

## The rule, in one line

Write the way a careful engineer writes in a code review: plain, direct, specific. If a sentence only sounds polished, cut it.

## Patterns to avoid

### 1. Slash disjunctions in prose

The forward slash standing in for "or" (or "and") is a strong tell. It is fine inside code, paths, and fixed enums; it reads as machine-written in a sentence.

- Avoid: `notify the team on Slack / Discord / Teams / email`
- Avoid: `the request / response cycle`, `pass this to the parser and/or the validator`
- Prefer: `notify the team on Slack, Discord, Teams, or email`
- Prefer: `the request and response cycle`, `pass this to the parser, the validator, or both`

Not a tell (leave alone): code-like enums with no spaces (`LOW/MEDIUM/HIGH`, `PROPOSED/APPLIED/SKIP`), file paths (`commands/foo.md`), units (`req/s`), and pipe-separated token sets in templates (`Ask | Plan | Agent | Debug`).

### 2. "Not just X, but Y" parallelism

The setup-and-elevation construction (`not just X, but Y`; `it's not about X, it's about Y`; `rather than just`; `more than just`) is one of the most recognizable machine cadences. State the point directly.

- Avoid: `This doesn't just describe the next phase. It hands off into the next action.`
- Prefer: `This hands off directly into the next action.`
- Avoid: `It's not about speed, it's about correctness.`
- Prefer: `Correctness matters more than speed here.`

Drop the reflexive rule-of-three too: when three parallel items add nothing over one, use one.

### 3. Vocabulary cliches

A small set of words shows up far more in machine text than in human writing. Replace them with the plain word.

| Avoid | Prefer |
| --- | --- |
| leverage | use |
| utilize | use |
| seamless, seamlessly | (cut, or name the actual behavior) |
| robust | (name the property: tested, validated, handles X) |
| comprehensive | complete, or just say what is covered |
| crucial | important, or cut |
| delve into | look at, dig into |
| it's worth noting, importantly | (cut; if it matters, just say it) |
| furthermore, moreover | also, and |

### 4. Decorative bold, emoji, and Title Case

- Bold is for genuine emphasis or a defined term, not for decorating every other noun. When half a paragraph is bold, none of it is emphasized.
- No emoji in normative or delivery prose. The advisory scanner flags any it finds.
- Headers use sentence case, not Title Case: `## Work complexity`, not `## Work Complexity`.

## What is NOT a tell (do not overcorrect)

- The repo's `--` (double hyphen) stand-in for the em-dash is the chosen replacement; keep using it. The literal em-dash character is the banned one (hard lint failure).
- Code, identifiers, enum tokens, file paths, CLI flags, and fenced code blocks are exempt.
- Domain terms that happen to be on the list are fine when accurate. An audit that genuinely covers everything can be called complete; the goal is plain and honest, not a banned-word hunt.

## Enforcement (tiered)

- Hard block (fails the build): the em-dash character, via `FORBIDDEN_PATTERNS` in `scripts/lint-commands.sh`.
- Advisory (warns, never fails): everything in this catalog, via `scripts/check-natural-voice.sh`, surfaced on the lint `Natural-voice:` summary line under `--verbose` / `--strict`. A human triages each hit.

Why the rest is advisory and not a hard byte-level ban: patterns like a spaced slash, `robust`, or `comprehensive` have legitimate uses (enums, mode templates, accurate domain terms). A hard ban would false-positive on honest prose and create churn for no quality gain. The advisory keeps regressions visible without blocking real writing.
