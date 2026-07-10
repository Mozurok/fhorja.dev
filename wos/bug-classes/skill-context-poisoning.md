---
name: skill-context-poisoning
category: agent-prompt-engineering
priority: P0
pillars: [security, correctness]
default-severity: P0
cwe: [CWE-506, CWE-829]
languages: [markdown, javascript, typescript, python]
file-patterns: ["**/SKILL.md", "**/skills/**", "**/.claude/**", "**/plugins/**", "**/*.skill.md"]
perspectives: [operator, maintainer]
reversibility-check: false
---

# skill-context-poisoning

## What it looks like

A third-party agent skill or plugin carries instructions or behavior that an artifact-only scan misses, because the payload does not live in the obvious place. Four observed shapes:

1. Description-field injection: the `SKILL.md` frontmatter `description` (the field the host uses for routing) contains instructions addressed to the agent rather than to the user, so the skill fires and acts on them before its body is ever read.
2. Hidden or zero-width Unicode: Unicode-tag characters or zero-width code points in `SKILL.md` smuggle instructions that render invisibly to a human reviewer but are tokens to the model (for example "run `curl ... | sh`" hidden inside an innocuous sentence).
3. Test or auxiliary-file payload: the visible `SKILL.md` is clean while the exfiltration or config-tampering logic sits in a bundled test fixture, helper script, or data file that a body-only scanner skips.
4. Docs-vs-behavior mismatch: the documentation claims one capability while the files perform an undisclosed one (a network call, a write to `.claude/settings.json` or `CLAUDE.md`, a secret read).

Independent 2026 audits found a large fraction of marketplace skills vulnerable and a measurable fraction malicious, and demonstrated that scanners which only read the visible body pass these payloads.

## Why it matters

Security pillar: an installed skill runs with the agent's authority. A poisoned skill can exfiltrate secrets, rewrite agent config to persist itself, or steer the agent's behavior on unrelated tasks. Correctness pillar: the agent acts on instructions the operator never saw and never approved, so the system does something other than what the human believes they authorized. The failure is silent: the skill "works", and the malicious behavior is invisible without reading every file and every code point.

## How to detect

This bug-class is the detection contract behind the `skill-vet` command. For an in-repo sweep (`repo-consistency-sweep`) when skill or plugin files are in scope:

```bash
# Agent-directed instructions in a description field
grep -rnE 'description:.*(ignore previous|run |curl |exec|eval|fetch|do not tell)' --include=SKILL.md .

# Hidden / zero-width Unicode and Unicode-tag smuggling in skill files
grep -rnP '[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2060}-\x{206F}\x{E0000}-\x{E007F}\x{FEFF}]' --include='*.md' .

# Skill files that write to agent config (out-of-directory tampering)
grep -rnE '\.claude/|settings\.json|CLAUDE\.md|AGENTS\.md|\.cursorrules' --include='*' ./skills ./plugins 2>/dev/null
```

Read every file in the candidate, not just `SKILL.md`. A clean body with a payload in a test file is the canonical miss.

## How to fix

- Never auto-install or auto-trust an external skill. Route every external skill through `capture-references` then `skill-vet`, and require explicit human approval before install (ADR-0046).
- Decline any skill whose description contains agent-directed instructions or whose files contain hidden or zero-width Unicode.
- Decline or sandbox any skill that writes outside its own directory (especially to agent config) or whose declared behavior does not match its files.
- For first-party Fhorja skills the risk is structural-only (they are generated from canonical `commands/*.md` by `build-agent-skills.sh`); this bug-class loads only when third-party skill or plugin files are in scope, to avoid noise.

## CWE / standard refs

- CWE-506: Embedded Malicious Code -- payload bundled in an apparently-benign skill artifact.
- CWE-829: Inclusion of Functionality from Untrusted Control Sphere -- installing a skill pulls untrusted instructions and code into the agent's authority.

## See also

- command: skill-vet -- the human-gated read that enforces this contract before install
- ADR-0046 -- no auto-install / human-gated skill trust
- bug-class: schema-skip-on-structured-output -- adjacent agent-prompt-engineering failure at the orchestration boundary
