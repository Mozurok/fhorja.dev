# ADR-0139: Retire the cache-breakpoint marker

Date: 2026-08-10

Status: Accepted

Supersedes: ADR-0014 (the cache-friendly command structure stands; the MARKER does not)

## Context

ADR-0014 introduced `<!-- cache-breakpoint -->` as the last line of every command body, on the
theory that a tool adapter would one day read it and emit `cache_control` at that point. The
marker was validated by `lint-commands.sh` with a hard fail on three properties: exactly one
per file, present, and positioned after `### Definition of done`. It landed in 98 commands and
the ADR itself conceded it was "a contract signal, not a runtime mechanism".

No adapter was ever written. ADR-0136 recorded that as an open item and treated the cache
amortization it implied as unrealized. This ADR closes the question the other way: the adapter
was never missing, it was impossible.

Three statements from the Claude Code prompt-caching documentation, verbatim:

- "Claude Code handles prompt caching for you, unless you disable it."
- "There is no per-file or per-segment caching."
- "Skills and commands inject their instructions as user messages at the point of invocation.
  Nothing earlier in the conversation changes."

Each independently defeats the marker:

1. **Caching is prefix-matched over the whole request**, from the start. A marker inside one
   file has no addressable position in that model. There is no per-file caching to point at.
2. **`cache_control` is a JSON field on a content block in the HTTP request**, not text. It has
   no representation inside a prompt, so no markdown token can become one.
3. **A command body arrives as a user message, after the cached prefix.** It is never the
   prefix, so no point inside it can be a breakpoint.
4. **Breakpoints cap at 4 per REQUEST.** 98 file-scoped markers do not map onto that at any
   granularity.
5. The host orders the request (system prompt, then project context, then conversation) to
   maximize the stable prefix. Whether a command body is cached is a property of the host, and
   the author of the file does not participate in that decision.

The open Agent Skills specification has no field for caching, and no public tool was found that
reads a markdown marker and emits `cache_control`. The tools that do exist (the LangChain
Anthropic caching middleware, and similar) operate on the message array at call time and choose
breakpoints by content stability, needing no marker.

## Decision

Remove the marker from all 98 commands and delete the lint rule that enforced it.

The `mandatory-context-bootstrap` shared block stops claiming an adapter is pending and states
what is true: the amortization is real but not controllable from here, because the host manages
caching and a command body sits after the cached prefix.

ADR-0014's underlying advice, keep the stable parts of a command early and the volatile parts
late, remains sound and is unaffected. What is retired is the marker and its gate.

## Consequences

- The most-linted item in the repository is gone: three hard-fail properties across 98 files,
  enforcing a contract with no possible consumer. It recovers roughly 245 chars and, more to the
  point, removes a rule that could never be satisfied in the sense it claimed.
- Cost reasoning about the bootstrap floor no longer waits on a mechanism that cannot arrive.
  The floor is what a command carries; whether the host caches it is the host's business.
- Should the commands ever be served as prompts by a first-party MCP server or API, where this
  repository's own code assembles the request, an adapter becomes technically possible. It would
  still not want this marker: it would choose breakpoints by content stability across the
  assembled request, as the existing tools do, and a per-file marker is the wrong granularity
  for a per-request budget of four.
- Historical mentions in CHANGELOG, ROADMAP and the `_internal/` snapshots are left alone. They
  record what was true when written, which is what a changelog is for.
