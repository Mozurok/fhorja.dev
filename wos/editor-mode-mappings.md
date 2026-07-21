---
activation: model_decision
description: Editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents), plus per-harness operational quirks. Load only when working in a tool other than Claude Code.
---

# Editor mode mappings

Maps the workflow's canonical mode vocabulary to equivalents in other AI tools.

| Workflow mode | Cursor | Claude Code | GitHub Copilot | OpenAI Codex | Gemini CLI | Notes |
|---|---|---|---|---|---|---|
| Ask | Ask | Default chat / Ask | Ask chat | Chat | Default | Read-only discussion; no file writes |
| Plan | Plan | Plan | (use Ask + ask for a plan) | (use Chat + ask for a plan) | (use default + ask for a plan) | Drafts a plan; no file writes |
| Agent | Agent | Agent | Agent mode | Codex agent | Agent / writeable | Writes files and runs tooling |
| Debug | Debug | (use Agent or Ask with debugging context) | (use Ask with debugging context) | (use Chat with debugging context) | (use default with debugging context) | Cursor-specific by name; in other tools, use the closest equivalent and note it in the Handoff `Reason:` |

When the user is in a tool that does not have a direct mode equivalent (for example, no native `Plan` mode), the workflow's behavior is unchanged: the model still drafts a plan and produces `PROPOSED` artifacts; the user reviews and re-runs in Agent mode for application. The mode names are about the agent's intent, not the tool's UI. The `Why this mode:` block in each command file describes intent, not tool features.

## Harness operational quirks

Verified per-harness operational guidance. An entry exists ONLY for a harness with dogfood-verified evidence; do not add speculative rows for other tools. Maintenance: harness behavior dates as vendors ship; update via PR, same convention as the primitives table in `wos/sub-agent-orchestration.md ## Harness equivalence` (mutual cross-link).

### Codex CLI

Evidence: bv3 dogfood session (2026-07-20/21): 48 manual approval escalations across 2 turns caused by writes outside the sandbox write-root; one Chrome headless call pending approval for 9555 seconds (54.2 percent of a 294 minute turn); 2 malformed nested patches from shell-redirected patching.

1. **Align the task-state folder with the sandbox write-root.** Before the first command of a session, confirm the Fhorja task folder (`projects/<client>__<project>/active/...`) lives inside the sandbox's writable root, or declare BOTH roots (product workspace and task-state repo) to the harness up front. Every canonical state write outside the write-root becomes a manual escalation; in bv3 this class alone produced 21 escalations in one turn and 27 in the next.
2. **Front-load escalated-approval actions.** Fire the actions known to require escalated approval (browser or CDP access, network calls, installs) as one of the FIRST calls of the turn, while the human is present to approve. This is strictly a timing reordering, never a relaxation of any approval or evidence floor: when a live capture is layer-1 evidence of a runtime gate (ADR-0048) and no human is present, the turn escalates and stops. Never substitute a stored fixture for live evidence. Composition: when a web runtime-verify command exists, its browser step is what fires early in the turn under Codex CLI; a detached autonomous run applies the same rule via `wos/autonomous-track.md` Permissions.
3. **Write state via the native patch tool, never via shell redirect.** Invoke the harness's apply-patch tool directly; the `apply_patch < tmpfile` shell-redirect form never qualifies for approval-prefix reuse (every state write re-escalates) and produced 2 malformed nested patches in bv3. See the matching rule in `commands/_shared/substrate-write-protocol.md`.
4. **Bound a stalling apply_patch; diagnose before blaming the encoder.** The bv3 session lost 20-plus minutes to single apply_patch calls. Treat a patch call exceeding a sane wall-time as a stall: bound it with a timeout and fall back DELIBERATELY, knowing the trade from quirk 3 (the redirected form never reuses approval, so the fallback costs an escalation; prefer retrying the direct form with a smaller patch first). A timeout is a diagnosis signal, never a silent retry: before attributing the stall to the patch encoder, measure what the evidence actually supports: patch size (the observed stalls were large artifact patches), sandbox escalation state (the calls ran via `zsh -lc` under an escalated sandbox), and shell wrapping. The encoder claim from the bv3 forensics remains UNPROVEN; record what was measured. Distinct mechanism: the Fhorja script-side `WOS_TIMEOUT` (opt-in in `scripts/emit-substrate-write.sh`) bounds the sha helper inside substrate writes; it does not bound the harness's patch tool.
