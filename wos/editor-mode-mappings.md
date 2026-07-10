---
activation: model_decision
description: Editor mode translation to non-Claude-Code tools (Cursor, Copilot, Codex, Gemini CLI equivalents). Load only when working in a tool other than Claude Code.
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
