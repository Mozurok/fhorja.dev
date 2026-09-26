# ADR-0174: The eval workspace stays versioned; only new outputs stop growing

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: evals, evidence, versioning, repository-size, personas, adr-0036

## Context

`evals/workspace/` holds 374 tracked files, 2.3 MB, frozen since 2026-07-10. Measured 2026-08-29: 17 `benchmark.json` (68 KB), 51 `eval.json` (228 KB), 102 `grading.json` (408 KB), 102 `timing.json` (408 KB), and 102 `outputs/output.md` (1.2 MB).

Two thirds of that weight is raw model prose in the output files, and the obvious reading is that a documentation repository should not carry megabytes of captured model output.

The obvious reading is wrong here, and the reason is checkable rather than a matter of taste. `wos/maturity-ladder.md` and ADR-0036 assert that five personas reached L3 on specific evidence. The per-persona ledgers that record those promotions live under `_internal/maturity-ladder/`, which is gitignored, so they are not in the repository at all. The `benchmark.json` files and the `grading` to `benchmark` chain under `evals/workspace/` are the only committed evidence behind those claims. Deleting them trades 2.3 MB for an assertion nobody outside this machine can falsify.

A claim that cannot be checked is worth less than the disk it saves.

## Decision

`evals/workspace/` stays versioned. What changes is growth, not the past.

`evals/workspace/**/outputs/` joins `.gitignore`. Git ignores `.gitignore` for files it already tracks, so the 102 existing `output.md` files stay versioned as a frozen snapshot, and a future run of `scripts/run-skill-evals.sh` adds no new model prose to the tree. The structured evidence, `eval.json`, `grading.json`, `timing.json` and `benchmark.json`, keeps being versioned for new runs too: it is small, it is the part a reader can verify a promotion against, and it is not prose.

No file leaves the index in this decision. `git rm --cached` over the existing outputs is exactly the deletion this ADR exists to prevent, and the slice that implemented it carries an exit criterion asserting the tracked count is unchanged.

The policy is written into `evals/skill-evals/README.md`, next to the workspace tree it describes, so someone adding a run reads it where they are rather than in an ADR they have no reason to open.

## Consequences

### Positive

- The L3 promotion claims stay checkable by anyone who clones the repository.
- The 1.2 MB of prose stops being a growing number. The next run adds kilobytes of JSON, not megabytes of text.
- The rule is legible: structured evidence is versioned, captured prose is not, and the existing prose is a dated snapshot.

### Negative

- 2.3 MB stays in the history, and history is forever. Anyone who considers that too much is arguing for the rejected alternative below, and the ADR says what it would cost.
- The frozen outputs and future runs now follow different rules, which needs the README paragraph to not read as an accident.

### Neutral

- Nothing is deleted, so nothing needs undoing if a successor ADR decides otherwise.
- The gitignore pattern is scoped to `outputs/`, so a future artifact placed elsewhere in the workspace is a decision someone makes, not something the pattern silently swallows.

## Alternatives considered

### Alternative 1: unversion evals/workspace entirely

- Add the whole directory to `.gitignore` and `git rm --cached` its contents.
- Rejected: it destroys the only committed evidence behind the L3 promotions that `wos/maturity-ladder.md` and ADR-0036 assert, because the per-persona ledgers are already gitignored. The repository would keep making the claim and lose the ability to support it.

### Alternative 2: unversion .claude/skills/ and generate it at install time

- The generated skills are the other large tracked surface; build them on the user's machine instead of shipping them.
- Rejected: `docs/FAQ.md` promises that cloning is sufficient, and generating at install time breaks it. The per-edit regeneration cost is the price of a surface the user receives ready to use, which is the trade the repository already chose.

### Alternative 3: keep a MANIFEST of sha256 hashes and drop the files

- Version a manifest so the evidence is attestable without the bytes.
- Rejected for now, not on principle: a hash proves a file was not altered, not what it said, so a reader could verify integrity and still be unable to check the promotion. It is a reasonable successor once the promotion claims are recorded somewhere tracked in full. Written down here so that ADR needs no archaeology.

## References

- [ADR-0036](./0036-k7-oscillation-and-l3-evidence-weighting.md): the L3 evidence weighting these files support.
- `wos/maturity-ladder.md`: the promotion gates, and the ledger path that is gitignored.
- `evals/skill-evals/README.md`: where the policy is written for the person adding a run.

## Notes

Revisit when the workspace grows again, which under this decision means new structured evidence rather than new prose. If it does grow past what a clone should carry, Alternative 3 is the first thing to reach for.
