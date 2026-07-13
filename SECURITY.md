# Security policy

## Scope

This repository is a workflow operating system distributed as markdown documents and bash scripts. It does not execute application code, handle user data, or run as a network service. The traditional definition of "security vulnerability" therefore has limited applicability here.

The maintainer takes seriously, however:

- **Malicious patterns in command files**: a markdown command that instructs an LLM to perform destructive actions, leak environment variables, or bypass safety mechanisms.
- **Bash script vulnerabilities**: command injection, path traversal, or unintended file overwrites in scripts under `scripts/`.
- **Supply chain risks in CI**: third-party GitHub Actions used in workflows under `.github/workflows/`.
- **Sensitive content leak in published commits**: client names, absolute paths, secrets, or any private information committed by mistake.

## Out of scope

- Security of the user's product code that the workflow is applied to. The workflow does not validate or improve product security; that is the user's responsibility.
- Security of the LLM provider (Cursor, Claude Code, Anthropic API, etc.). Report those to the respective vendor.
- Security of derivative SaaS or hosted versions of this workflow built by third parties. Security of those services is the operator's responsibility.

## Reporting a vulnerability

If you find a vulnerability that fits the in-scope categories above:

1. **Do not open a public issue.**
2. Use [GitHub Security Advisory](https://github.com/Mozurok/fhorja.dev/security/advisories/new) to report privately, or email the maintainer at the address listed on the GitHub profile.
3. Include:
   - Description of the issue
   - Affected file(s) or command(s)
   - Reproduction steps if applicable
   - Suggested fix if you have one

The maintainer will acknowledge receipt within 14 days (best effort) and will work on a fix on a best-effort basis. There is no formal SLA.

## Disclosure policy

The maintainer prefers coordinated disclosure: report privately, fix is developed, public advisory is published with credit to reporter (unless reporter prefers anonymity), users are notified via GitHub Security Advisory and CHANGELOG.md.

## Best practices for users

If you adopt this workflow:

- **Never commit `projects/` to a public fork**. The default `.gitignore` excludes it; ensure your fork preserves this.
- **Never paste real client names, absolute paths from your home directory, or sensitive payloads into command outputs that you save publicly**. The workflow is markdown-based and treats all content as text; it does not redact automatically.
- **Review commands before running them in Agent mode**. The maintainer cannot vouch for safety of forks or modified versions.
- **Keep your editor (Cursor, Claude Code) updated**. Command execution semantics depend on editor version.