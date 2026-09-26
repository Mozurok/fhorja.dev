# scripts/audit

Read-only baseline auditor for this repository. It writes nothing except the two
report files under `docs/audit/`.

## Run it

```sh
scripts/audit/run-baseline.sh                    # report date defaults to today
scripts/audit/run-baseline.sh 2026-08-13         # explicit report date
scripts/audit/run-baseline.sh 2026-08-13 0cbb0f2 # pin the public launch commit
```

That writes `docs/audit/<date>-baseline.json` and `docs/audit/<date>-baseline.html`,
then prints a plain-text summary of mismatches on stdout.

## Files

| File | Role |
|---|---|
| `run-baseline.sh` | Wrapper: JSON first, then HTML rendered from that JSON. |
| `baseline_audit.py` | All 18 checks. Emits the JSON artifact of record. |
| `render_baseline_html.py` | Renders the JSON as one self-contained page. |
| `lib_repo.py` | Shared read-only readers (command inventory, frontmatter, count markers, git). |

Python stdlib only, no third-party dependency, no network access.

## Contract

- **JSON is the artifact of record.** The HTML is a view of it and adds no facts.
  No HTML markup is hand-written; the page is generated.
- **Facts only.** No check ranks severity, proposes a fix, or interprets a finding.
- **Never silently skips.** A check that cannot run records
  `{"status": "could_not_run", "reason": "..."}` and the pass continues.
- **Deterministic.** Every key is byte-stable for an unchanged tree except
  `meta.run_timestamp` and `meta.working_tree_dirty_paths`. Pin the timestamp with
  `SOURCE_DATE_EPOCH` to diff two runs byte for byte:

  ```sh
  SOURCE_DATE_EPOCH=1000000000 python3 scripts/audit/baseline_audit.py --out a.json
  SOURCE_DATE_EPOCH=1000000000 python3 scripts/audit/baseline_audit.py --out b.json
  diff a.json b.json
  ```

- **Reuses the repository's own guards** rather than reimplementing them.
  `lint-commands.sh`, `build-agent-skills.sh --check`,
  `sync-shared-blocks.sh --dry-run`, and `reconcile-counts.sh --check` run as part
  of the pass and their verdicts land under the `reused_gates` key. Checks 1, 2,
  3, and 7 overlap them on purpose, so a disagreement between the two is visible
  rather than hidden. Pass `--no-gates` to `baseline_audit.py` to skip them.

## Flags

`baseline_audit.py`

| Flag | Effect |
|---|---|
| `--out PATH` | Write the JSON report to PATH. |
| `--stdout-json` | Print the JSON on stdout instead of the mismatch summary. |
| `--launch-ref REF` | Pin the public launch commit. Without it, the script resolves the oldest commit whose subject matches `cut v1.0.0` and records how it resolved. |
| `--no-gates` | Skip the reused repository guards. |

`render_baseline_html.py`

| Flag | Effect |
|---|---|
| `--json PATH` | The audit JSON to render. |
| `--out PATH` | Where to write the page. |

## Checks

| # | Key | What it reports |
|---|---|---|
| 1 | `check_01_counts` | Command count per surface; every count marker against disk. |
| 2 | `check_02_registry_integrity` | The three registries both ways; cluster membership; the two taxonomies. |
| 3 | `check_03_shared_block_drift` | Each inlined copy against `commands/_shared/`; blocks with no consumer. |
| 4 | `check_04_cross_reference_integrity` | Path references that resolve, break, or point outside the tree; unreferenced templates, topics, scripts. |
| 5 | `check_05_adr_coverage` | Files against the index, numbering, superseded status, command citations. |
| 6 | `check_06_eval_coverage` | Scenario coverage per command and per cluster, from two signals. |
| 7 | `check_07_skills_conformance` | Built Agent Skills: frontmatter, body lines, description length. |
| 8 | `check_08_token_footprint` | Approximate tokens per command and per install profile. |
| 9 | `check_09_claim_consistency` | Prose claims, license, and harness names against disk. |
| 10 | `check_10_staleness` | Last commit date per command file. |
| 11 | `check_11_reference_graph` | Nodes, edges, fan-in and fan-out. |
| 12 | `check_12_reachability` | Walk from the commands named in `wos/entry-points.md`. |
| 13 | `check_13_cluster_coupling` | Intra and cross-cluster edges, and the cluster matrix. |
| 14 | `check_14_churn` | Commits and lines changed, all time and since launch. |
| 15 | `check_15_cochange_coupling` | Command pairs sharing three or more commits. |
| 16 | `check_16_section_vocabulary` | Heading frequency and who is missing each majority heading. |
| 17 | `check_17_external_surface` | Commands whose own text names a fetch or network mechanism. |
| 18 | `check_18_near_duplicate_text` | Paragraph pairs above a Jaccard threshold. |

## Known method limits

Recorded here and in the JSON, not glossed over:

- Token counts are `characters // 4`, the same heuristic `scripts/measure-tokens.py`
  uses. Not a tokenizer result.
- Churn and staleness come from one `git log -M --numstat` pass. A rename is
  normalized to the new path only in the commit that performed it, so a renamed
  file's history reads as shorter than it is. One rename exists in this history.
- Check 17 matches text, not runtime behavior. A command naming `WebFetch` is
  inventory, not proof that it fetches.
- Check 18 compares paragraphs after removing frontmatter, fenced code, and every
  region propagated from `commands/_shared/`.
