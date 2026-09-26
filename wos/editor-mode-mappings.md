---
activation: model_decision
description: Editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents), plus per-harness operational quirks. Load only when working in a tool other than Claude Code.
---

# Editor mode mappings

Maps the workflow's canonical mode vocabulary to equivalents in other AI tools.

| Workflow mode | Cursor | Claude Code | GitHub Copilot | OpenAI Codex | Gemini CLI | Notes |
|---|---|---|---|---|---|---|
| Ask | Ask | (no read-only mode; `plan` blocks edits) | Ask chat | Default chat | Default | Read-only discussion; no file writes |
| Plan | Plan | Plan | Plan | `/plan` | Plan (`/plan`) | Drafts a plan; no file writes |
| Agent | Agent | `acceptEdits`, or `default` with prompts | Agent mode | Codex agent | Agent / writeable | Writes files and runs tooling |
| Debug | Debug | (use `default` or `acceptEdits` with debugging context) | (use Ask with debugging context) | (use the default chat with debugging context) | (use default with debugging context) | Cursor-specific by name; in other tools, use the closest equivalent and note it in the Handoff `Reason:` |

Codex and Copilot rows read from https://learn.chatgpt.com/docs/cli/slash-commands and the VS Code agent docs on 2026-09-17, both HTTP 200. Three claims this table carried were wrong, not merely dated. Codex has a native plan mode, `/plan`, documented as "Switch to plan mode and optionally send a prompt"; the table said to use "Chat + ask for a plan". Copilot's Plan is a built-in agent role; the table said to use Ask. And "Chat" was never a Codex mode name, so the workaround it prescribed named a mode that does not exist.

The Gemini CLI plan cell read from https://developers.googleblog.com/plan-mode-now-available-in-gemini-cli/ on 2026-09-20: plan mode is native, on by default, and entered with `/plan` or Shift+Tab, so the "ask for a plan" workaround the cell carried was wrong. The Claude Code cells read from https://code.claude.com/docs/en/permission-modes and https://code.claude.com/docs/en/interactive-mode the same day: Shift+Tab cycles `default` (labeled Manual), `acceptEdits`, `plan`, and, when available, `bypassPermissions` and then `auto`, so neither `Agent` nor `Ask` is a mode name today. Whether either ever was is not something those pages say, and the cells are corrected to the current set rather than to a claim about the past, and `default` is not read-only because it prompts before a write rather than forbidding one.

There are two Codex commands with no row here, because neither has a workflow-mode equivalent. They are listed so the next reader does not conclude they were missed. `/goal` sets, edits, pauses, resumes, views or clears a task goal that persists across turns, which is the nearest native thing to a `TASK_STATE.md ## Objective`. `/import` imports a Claude Code or Cursor setup, projects and chats, which is the most relevant Codex feature to a cross-harness system.

When the user is in a tool that does not have a direct mode equivalent (for example, no native `Plan` mode), the workflow's behavior is unchanged: the model still drafts a plan, and its task-memory files land directly and marked `APPLIED` like in any other mode (ADR-0199). `PROPOSED` survives only for a block staged inside a section the command does not own (ADR-0034), which no mode changes. The mode names are about the agent's intent, not the tool's UI. The `Why this mode:` block in each command file describes intent, not tool features.

## Source currency

Last scanned: 2026-09-20
Cadence: 6 weeks

The harness claims in this file are vendor behavior, which moves. `scripts/check-doc-currency.sh` reads the two lines above and reports the age in lint. Move the date when the sources named in the file are reopened.

## Harness operational quirks

Verified per-harness operational guidance. An entry exists ONLY for a harness with dogfood-verified evidence; do not add speculative rows for other tools. Maintenance: harness behavior dates as vendors ship; update via PR, same convention as the primitives table in `wos/sub-agent-orchestration.md ## Harness equivalence` (mutual cross-link).

### Codex CLI

Evidence: bv3 dogfood session (2026-07-20/21): 48 manual approval escalations across 2 turns caused by writes outside the sandbox write-root; one Chrome headless call pending approval for 9555 seconds (54.2 percent of a 294 minute turn); 2 malformed nested patches from shell-redirected patching.

1. **Align the task-state folder with the sandbox write-root.** Before the first command of a session, confirm the Fhorja task folder (`projects/<client>__<project>/active/...`) lives inside the sandbox's writable root, or declare BOTH roots (product workspace and task-state repo) to the harness up front. Every canonical state write outside the write-root becomes a manual escalation; in bv3 this class alone produced 21 escalations in one turn and 27 in the next. The exact key is `sandbox_workspace_write.writable_roots` in `~/.codex/config.toml`, and naming it rather than describing it is the point: the 48 escalations below were a write-root mismatch, and a reader who has to go find the key is a reader who does not fix it. Per-agent, an agent's own TOML file can set `sandbox_mode`, and the parent's value applies only when the file omits it; sandbox and approval changes made live in the session (`/permissions`, `--yolo`) still reach the child even when the file sets a different default (https://learn.chatgpt.com/docs/agent-configuration/subagents).
2. **Front-load escalated-approval actions.** Fire the actions known to require escalated approval (browser or CDP access, network calls, installs) as one of the FIRST calls of the turn, while the human is present to approve. This is strictly a timing reordering, never a relaxation of any approval or evidence floor: when a live capture is layer-1 evidence of a runtime gate (ADR-0048) and no human is present, the turn escalates and stops. Never substitute a stored fixture for live evidence. Composition: when a web runtime-verify command exists, its browser step is what fires early in the turn under Codex CLI; a detached autonomous run applies the same rule via `wos/autonomous-track.md` Permissions. Cheaper than front-loading, where it applies: a rules layer pre-allows commands so they never escalate. Source: https://learn.chatgpt.com/docs/agent-configuration/subagents, 2026-09-17, HTTP 200.
3. **Write state via the native patch tool, never via shell redirect.** Invoke the harness's apply-patch tool directly; the `apply_patch < tmpfile` shell-redirect form never qualifies for approval-prefix reuse (every state write re-escalates) and produced 2 malformed nested patches in bv3. See the matching rule in `commands/_shared/substrate-write-protocol.md`.
4. **Bound a stalling apply_patch; diagnose before blaming the encoder.** The bv3 session lost 20-plus minutes to single apply_patch calls. Treat a patch call exceeding a sane wall-time as a stall: bound it with a timeout and fall back DELIBERATELY, knowing the trade from quirk 3 (the redirected form never reuses approval, so the fallback costs an escalation; prefer retrying the direct form with a smaller patch first). A timeout is a diagnosis signal, never a silent retry: before attributing the stall to the patch encoder, measure what the evidence actually supports: patch size (the observed stalls were large artifact patches), sandbox escalation state (the calls ran via `zsh -lc` under an escalated sandbox), and shell wrapping. The encoder claim from the bv3 forensics remains UNPROVEN; record what was measured. Distinct mechanism: the Fhorja script-side `WOS_TIMEOUT` (opt-in in `scripts/emit-substrate-write.sh`) bounds the sha helper inside substrate writes; it does not bound the harness's patch tool.
