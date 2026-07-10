# Eval scenario 09: capture-references with multiple URLs

- **Tags**: capture-references, project-level-memory, deduplication, freshness-metadata
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `capture-references` correctly appends multiple external URLs to project-level `REFERENCES.md` with the canonical entry format (URL, accessed date, summary, optional verbatim key points, tags), deduplicates by URL when one already exists, and never invents content beyond what the source page contains.

This exercises:

- The centralized External web access rule (spec `## Cross-cutting workflow guardrails` → `### External web access (centralized)`).
- Project-level memory wiring (ADR-0007).
- The deduplication-by-URL invariant.
- The freshness metadata format that future `external-research` runs depend on.

## Setup

Assume `projects/acme__widget-pricing/` exists with a `PROJECT_CHARTER.md`. The project's `REFERENCES.md` already contains one entry for the Supabase docs (from a prior `project-bootstrap` run); the rest is empty:

```text
# REFERENCES

Project-level external references for `acme__widget-pricing`.

## Format reminder
... (canonical reminder block)

## Entries

## Backend stack
### Supabase JavaScript select
- URL: https://supabase.com/docs/reference/javascript/select
- Accessed: 2026-05-01
- Summary: Reference for the Supabase client library's .select() method, including filter chaining and response shape.
- Tags: supabase, backend, queries
```

## Input prompt

```text
Run @commands/capture-references.md

Project: acme__widget-pricing
Inputs:
  - https://supabase.com/docs/reference/javascript/select (already in REFERENCES.md from a prior run; expecting NO_OP-style dedup with optional Accessed-date refresh)
  - https://supabase.com/docs/guides/auth/row-level-security (RLS overview; new entry expected)
  - https://www.postgresql.org/docs/16/indexes-types.html (PostgreSQL 16 index types reference; new entry expected)
Tags: backend, supabase, postgres
Mode: Ask
```

## Expected response shape

- Response begins with capture-references' persona line.
- Response identifies the 3 URLs and classifies them: 1 already-captured (Supabase select), 2 new (RLS, Postgres indexes).
- The already-captured URL is handled per the deduplication rule: either treated as a no-op (`NO_OP_TRACE` for that specific entry) or as an `Accessed:` date refresh, depending on whether the prior accessed date is stale enough to warrant a refresh. Either is acceptable; the response must explicitly state which path it took for that URL.
- The 2 new URLs are appended to `REFERENCES.md` with the canonical entry format: title, URL, `Accessed: 2026-05-08` (today), one-paragraph summary grounded in what the page actually contains, optional verbatim key points (1-3 short quotes when worth preserving), tags (the user-supplied tags plus any source-specific ones).
- The proposed `### Artifact changes` shows `REFERENCES.md` PROPOSED with exactly the entries described above. No invented entries; no entries beyond the 3 URLs the user supplied.
- The summaries do NOT contain content the source page does not contain (no inferred "use this for X" recommendations beyond what the page states).
- Tags are normalized: lowercase, hyphenated, comma-separated. The user-supplied set is included; the response may add narrowly relevant tags (e.g., `rls` for the RLS page, `indexing` for the index types page).
- `### Handoff` block at the end. `Run now:` recommends one of: `task-init` (when the user is about to start a task that will use these references), `external-research` (when these references are part of a synthesis task), or `what-next` (when the next step is uncertain).

## Pass criteria

1. **Three URLs handled distinctly**: response classifies each URL as already-captured or new, and acts accordingly.
2. **Dedup on URL match**: the already-captured Supabase select URL does NOT produce a duplicate entry. Either `NO_OP_TRACE` for that URL or an `Accessed:` date refresh is acceptable; both are valid.
3. **New entries follow canonical format**: each new entry has title, URL, `Accessed: 2026-05-08`, summary (one paragraph), optional verbatim key points, tags. No fields missing.
4. **Summaries grounded in source content**: the RLS summary describes what Supabase's RLS docs actually say (policy creation, role-based access, etc.); the index summary describes Postgres index types (B-tree, Hash, GIN, GiST, BRIN, SP-GiST). Watch for invented or borrowed-from-training-data claims.
5. **Tag normalization**: tags are lowercase, hyphenated. The supplied tags appear; narrowly relevant tags may be added.
6. **No invented entries**: response does not append entries for URLs the user did not supply (no "while we were at it, here's the Postgres CREATE INDEX docs too").
7. **Handoff intact**: response ends with a complete Handoff. `Run now:` is a valid command.

## Failure modes to watch

- **Duplicate appended**: the response appends a second Supabase select entry instead of dedup'ing. Symptom: `REFERENCES.md` has two entries with the same URL.
- **Invented summaries**: the response paraphrases the URLs based on training memory rather than the actual page content. Tell-tale: very specific claims that the page does not literally state ("use unique indexes for primary keys" when the cited Postgres page covers index *types*, not when-to-use-each).
- **Missing freshness metadata**: an entry has no `Accessed:` field, or has a date that is not today's. The freshness metadata is load-bearing for downstream `external-research` runs.
- **Tag drift**: tags are inconsistent (some `Backend`, others `backend`; or hyphenation flips across entries). The lint does not catch this; reviewer or future scenarios would.
- **Fabricated key points**: `Key points:` includes quotes that are not actually in the source page. Verbatim quotes are optional; if used, they must be exact.
- **Premature routing**: response recommends `external-research` even when the user's intent was just to record references for future use. Routing should match user intent or default to `what-next`.

## Notes

- Related ADRs: [ADR-0007](../../docs/adr/0007-project-level-memory.md) (project-level memory layer; REFERENCES.md is its append-only second file).
- Related commands: `commands/capture-references.md`, `commands/external-research.md` (the synthesizer that consumes these entries), `commands/project-bootstrap.md` (the only other command that writes REFERENCES.md, and only on initial seeding).
- Related spec section: `## Cross-cutting workflow guardrails` → `### External web access (centralized)` (the rule that keeps web fetches funneled through capture-references and external-research, never ad-hoc).
- This scenario is single-turn but exercises a high-stakes integrity property (no dedup → silent reference inflation → eventual REFERENCES.md unusable). The dedup rule is the load-bearing test.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
