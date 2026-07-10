# Fhorja End-to-End walkthrough

Reproducible regression test that walks Fhorja through a canonical lifecycle slice on a synthetic project. Exists so any architectural change (new shared block, K.2 protocol update, fleet orchestrator, etc.) can be validated against a fixed command sequence rather than against ad-hoc spot-checks.

Per Epic K v2.1 post-K.8 hardening (2026-06-05). Anchors on the **K.2 cutover date 2026-06-04** -- substrate sections written ON or AFTER this date MUST carry the inline `<!-- wos:write owner=... -->` transaction header AND emit a `.wos/VERIFICATION_LOG.jsonl` line with valid SHA-256 hex per `commands/_shared/substrate-write-protocol.md`. The walkthrough's primary regression value is detecting K.2 non-compliance across all 8 retrofit writers (sync-task-state, slice-closure, decision-interview, implementation-plan, task-init, impact-analysis, what-next, capture-observation).

## What it tests

The walkthrough drives a curated 12-step spine over the 67-command registry (62 flat at `commands/<name>.md` + 5 folder-shaped K.8 personas at `commands/<slug>/SKILL.md`). The 12 spine commands cover the canonical project-lifecycle path (init -> plan -> implement -> sweep -> deliver -> close) plus three additional micro-steps (Step 7.5, 8.5, 12.5) that exercise the K.2 writers not otherwise hit by the main spine. The walkthrough validates:

1. **Artifact shapes** -- each command produces the expected output files with the canonical section structure per its `commands/<name>.md` contract (e.g. IMPACT_ANALYSIS.md follows the 12-item ordered list, IMPLEMENTATION_PLAN.md slices carry all 7 canonical fields including EARS exit criteria + work complexity).
2. **Substrate ownership** -- writes land in the right files per `wos/substrate-peers.md`; only declared owners apply mutations; co-writers emit PROPOSED blocks routed via Pattern A handoff.
3. **K.2 transaction-header protocol (cutover 2026-06-04)** -- every substrate write on a section modified at or after the cutover emits the inline `<!-- wos:write owner=... -->` header AND a `.wos/VERIFICATION_LOG.jsonl` line. `sha_after` MUST be 64-char lowercase hex (never null); `sha_before` is null only on first write to a fresh section per `commands/_shared/substrate-write-protocol.md ## Concrete computation`.
4. **Handoff routing** -- `### Handoff Run now:` line at the end of each command's output names a real command from the registry (caught by lint + assertion script greps).
5. **Substrate audit (K.4 + K.5)** -- `repo-consistency-sweep` Pre-flight invokes `scripts/scan-substrate-headers.sh` and `scripts/verify-log-validator.py` unconditionally (BEFORE Step 1 / Step 2 hash check) and reports accurate drift / invalid counts (`n/a` when scripts missing; `0` when present and no drift).

## What it does NOT test

- **K.8 personas** (`jtbd-switch-interviewer`, `color-contrast-architect`, `rls-auth-boundary-auditor`, `migration-safety-steward`, `post-deploy-verifier`). All five ship at L1 shadow per `wos/maturity-ladder.md` and emit PROPOSED-only via Pattern A handoff. They are validated via the K.7 eval harness (`evals/skill-evals/<persona>/evals.json`), NOT this E2E walkthrough.
- **Fleet orchestrators** (`atom-audit-fleet`, `screen-spec-fleet`, `task-init-fleet`, `external-research-fleet`, `verify-against-rubric-fleet`). Each has its own track (Phase 4 deferred for J.6 / J.7 -- both require Figma MCP).
- **Multi-repo paths** (`SOURCE_OF_TRUTH.md ## Repositories`). Single-repo only in v1.
- **Mode C parallel fanout** (would need a wide-diff scenario).
- **LLM output quality** (prose). Validates STRUCTURE: section headers, frontmatter, substrate-write headers, handoff targets, file presence + SHA correctness.

## Layout

```
evals/e2e/
  README.md             # this file
  walkthrough.md        # canonical 12-step spine + Step 7.5/8.5/12.5 micro-steps
                        # with expected artifacts + substrate writes + handoff per step
  bootstrap.sh          # idempotent setup: creates projects/wos__e2e-test/
                        # + /tmp/wos-e2e-fake-app/ (initialized as git repo)
  fake-app/             # tiny synthetic Flask signup endpoint (committed; bootstrap
                        # copies to /tmp/ where it can be modified by walkthrough slices)
    handlers/signup.py  # ~30 lines with intentional issues for repo-consistency-sweep
    README.md           # disclaimer
    requirements.txt
  assertions/           # per-step validators (post-execution checks)
    _lib.sh             # shared helpers (assert_file_exists, assert_section_present,
                        # assert_k2_header, assert_verification_log_valid,
                        # assert_substrate_drift_zero, resolve_task_dir, fail/pass_check/finish)
    01-project-bootstrap.sh        # Phase 1 shipped
    09-repo-consistency-sweep.sh   # Phase 1 shipped (THE critical assertion)
    README.md           # pattern + Phase 2 deferred list
```

## How to run

```bash
# 1. From the Fhorja repo root
cd ~/Documents/my_work_tasks

# 2. Bootstrap (idempotent; clobbers existing artifacts with --force)
bash evals/e2e/bootstrap.sh
# or:    bash evals/e2e/bootstrap.sh --force
# clean: bash evals/e2e/bootstrap.sh --clean    (remove without rebuild)

# 3. Open evals/e2e/walkthrough.md and execute the spine in a fresh
#    Claude Code or Cursor session. Each step lists:
#      - command + suggested mode (Ask / Plan / Agent)
#      - required inputs
#      - expected artifacts written + substrate writes + handoff target
#      - assertion script to validate the step (Phase 1 ships 01 + 09;
#        02-08.5 and 10-12.5 ship with Phase 2 alongside K.2 writer fixes)

# 4. After each numbered step, run its assertion script:
bash evals/e2e/assertions/0N-<command>.sh

# 5. Tear-down (single command via the bootstrap script)
bash evals/e2e/bootstrap.sh --clean
```

## When to re-run

- After modifying any shared block in `commands/_shared/`
- After modifying any K.1-K.8 substrate / persona artifact (`wos/substrate-peers.md`, `wos/maturity-ladder.md`, `commands/_shared/substrate-write-protocol.md`, any K.8 persona SKILL.md)
- After shipping a new fleet orchestrator (J.x slice)
- After modifying ADR-0025 (recommended-pipeline tier model that gates Step 03 task-init's `## Recommended pipeline` section), ADR-0026 (APPLIED-by-default in Agent mode that gates Step 07 inline closure), or ADR-0031 (EARS form that gates Step 06 exit criteria)
- After a Claude Code skill-cache invalidation event (e.g. running `scripts/sync-workflow-slash-commands.sh --with-skills` then restarting the session)
- Before a release tag

## Shipped vs deferred

| | Phase 1 | Phase 2 |
|---|---|---|
| walkthrough.md | shipped 2026-06-05 (rewritten with canonical contracts after cohort review) | refinements as Phase 2 surfaces edge cases |
| bootstrap.sh + fake-app/ | shipped | move app.py -> handlers/signup.py + port 5001 (Phase 1 fix-pack) |
| assertions/_lib.sh | shipped (regex tightened in Phase 1 fix-pack) | new helpers as steps ship |
| assertions/01-project-bootstrap.sh | shipped (single-repo `## Default workspace` assertion) | -- |
| assertions/09-repo-consistency-sweep.sh | shipped | -- |
| assertions/02-08.5 + 10-12.5 | not shipped | ship alongside K.2 writer fixes (each fix-agent produces its matching assertion stub for free) |

## References

- `wos/substrate-peers.md` -- ownership matrix + audit trail schema
- `commands/_shared/substrate-write-protocol.md` -- K.2 inline header + JSONL bash helpers
- `wos/maturity-ladder.md` -- L1-L5; K.8 personas at L1 shadow
- `commands/repo-consistency-sweep.md` -- current Step ordering with Pre-flight substrate audit before Step 1
- `scripts/scan-substrate-headers.sh` + `scripts/verify-log-validator.py` -- the K.4 + K.5 validators the walkthrough's Step 09 invokes
