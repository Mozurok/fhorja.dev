# Recommended MCP server config stubs

Copy-to-`.mcp.json` starter stubs for the MCP servers Fhorja commonly uses, so adopters do not have to discover and wire each one out of band. These are examples to adapt, not an install step: nothing here runs until you copy it into your project's `.mcp.json` and approve the server.

## How to use

1. Copy the stub you want into your repo's `.mcp.json` (project-scoped, versioned, auto-read by Claude Code at startup), merging under the `mcpServers` key.
2. Fill the `env` values (tokens, project refs). Use `${VAR}` interpolation so secrets stay out of the file.
3. Start Claude Code and approve the pending server (project-scoped servers from `.mcp.json` appear as pending approval; the human approves, per the Fhorja human-gated trust posture, ADR-0046).

These stubs match Fhorja's own usage (`db-context-supabase` uses the Supabase MCP; the Figma MCP backs the design-system commands; Trigger.dev for background jobs). Your stack may differ; treat them as templates, add or drop servers as needed. No Fhorja command installs or enables an MCP server; that is always a human action.

See `wos/external-integration-patterns.md` for the conventions and `https://code.claude.com/docs/en/mcp` for the full reference.
