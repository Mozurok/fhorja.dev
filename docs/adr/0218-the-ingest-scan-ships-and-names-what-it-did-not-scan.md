# ADR-0218: The ingest scan ships, and names what it did not scan

- **Status**: Accepted
- **Date**: 2026-09-22
- **Supersedes**: nothing. It adds one entry to the ADR-0214 shipping list and completes ADR-0096 on an install.
- **Tags**: ingest-scan, asi06, install-payload, workflow-root, d-3, adr-0096, adr-0214, adr-0217

## Context

ADR-0096 put a first-pass poisoning scan, `scripts/ingest-scan.py`, in front of content that enters
task memory from outside: fetched pages, MCP ingest, issue threads. Four commands and one shared
block, which reaches four more, tell the model to run it.

Measured on 2026-09-22 while working through backlog B31, which asks which of the scripts the commands
name should ship. Twenty distinct scripts are named in commands. Two shipped. The scan was not one of
them, so on every install that is not a clone of this repository the step found no script, and no
command said what to do then. The scan was skipped, and nothing recorded that it had been.

The script also failed the second D-3 test. Empty input printed `VERDICT: CLEAN` with exit 0, so a
fetch that returned nothing, or a pipe that broke, was recorded as scanned and clean. A missing file
raised a traceback. It had no test.

ADR-0217 found the same shape one day earlier with the outcome helper. That makes two, so a check for
the class is worth its cost.

## Decision

`ingest-scan.py` refuses empty input and an unreadable file by name, with exit 2. It joins
`SHIPPED_SCRIPTS`. Each command that runs it resolves it against the workflow root, and when it is
absent or exits 2 the command says the content was NOT scanned rather than recording it as clean.
`scripts/tests/test-ingest-scan.sh` covers the refusals and the flags, and runs in CI.

`check_workflow_root_scripts_ship` reads every "resolve `scripts/x` against the WORKFLOW ROOT" promise in
the commands and fails when `x` is not in `SHIPPED_SCRIPTS`.

## Consequences

### Positive

- The ASI06 scan runs on an install, and a run that could not scan says so.
- A future command that promises a workflow-root script the installer does not ship fails the build.

### Negative

- The check reads two phrasings of the promise. A command that names a script another way, or just runs
  `scripts/x` with no resolution clause, is outside it. Seventeen of the twenty named scripts are in that
  position today, which is what the rest of B31 measures one script at a time.
- The scan is still a first pass. ADR-0096's limits stand: detecting an injection reliably needs a model
  in the loop, and this is not that.

### Neutral

- The install test probes each shipped script with its own argument shape, so adding a script means adding
  its probe.
