# REVIEW_PREFERENCES

Project-level review preferences for `repo-consistency-sweep`. Lives at `projects/<client>__<project>/REVIEW_PREFERENCES.md` (gitignored, per-user). Created automatically on the first sweep run if absent; updated by `apply-sweep-triage` after the user triages each finding.

## How suppression works

When the sweep runs, it reads this file before reporting findings. A finding is **suppressed** if all of the following match:
- `bug_class` matches the finding's bug-class name
- `file_path` matches the finding's file path
- `file_hash` matches the current `git hash-object <file_path>` output (the file has not been modified since the decline)

When the file is modified (hash changes), the suppression ages out and the finding resurfaces on the next sweep.

## Declined findings

Findings the user explicitly declined as not actionable. Each row suppresses re-reporting until the file changes.

| date | bug_class | file_path | file_hash | reason |
|---|---|---|---|---|
<!-- Rows added by apply-sweep-triage; do not edit the header -->

## Applied findings

Findings the user acknowledged and fixed. Kept for historical reference; no suppression effect.

| date | bug_class | file_path | action_taken |
|---|---|---|---|
<!-- Rows added by apply-sweep-triage; do not edit the header -->

## Discussed findings

Findings marked for discussion. No suppression. Cleared when resolved.

| date | bug_class | file_path | note |
|---|---|---|---|
<!-- Rows added by apply-sweep-triage; do not edit the header -->
