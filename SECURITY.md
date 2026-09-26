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

## Task substrate handling

`projects/` accumulates third-party work in plain text: briefs, decisions, code excerpts,
interview notes. It is gitignored by design (ADR-0007) and MUST NOT be committed to this or
any repository.

Whoever operates this workflow declares a backup destination and a maximum acceptable backup
age, and measures both. `scripts/check-substrate-retention.sh` reads those two values from a
gitignored sidecar and reports size, active and archived task counts, the age of the most
recent backup, and how many archived tasks are older than the declared limit. It measures and
stops there.

Fhorja never copies `projects/` anywhere. No script in this repository may copy, upload, or
transmit it, and the retention checker is forbidden from reading task file contents or
printing a project folder name.

Keeping or discarding an archived task is the operator's decision. The repository measures it
and never decides it.

Out of scope for this repository, and stated here so nobody assumes otherwise: choosing,
paying for, and configuring a backup destination; encryption and key custody; off-site copies;
deciding which archived tasks to delete; any contractual obligation to a client about their
material; hardware redundancy.
