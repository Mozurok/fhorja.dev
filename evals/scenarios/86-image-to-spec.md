# Eval scenario 86: image-to-spec generates a proposed-only spec from a raw image (no Figma)

- **Tags**: design-cluster, image-to-spec, proposed-only, mode-selection, no-figma-call
- **Last reviewed**: 2026-06-30
- **Status**: active

## Goal

Validates `image-to-spec` (the raw-image entry point to the design cluster). The command reads a user-supplied image, selects a mode (`--component`, `--screen`, or auto-detect), and emits a spec doc shaped like the matching template, with every observation marked `(proposed)` because there is no Figma source of truth. It must not call the Figma MCP, generate into Figma, fetch the web, or produce code.

This exercises:

- Mode selection: an explicit flag is honored; with no flag the command auto-detects and states the choice plus a one-line reason.
- Proposed-only marking: nothing is `confirmed`; visible copy is the only verbatim content, and numeric or visual values are proposed estimates.
- The no-Figma, no-web, no-code boundary: the command reads the image and writes a spec, nothing else.
- Template fidelity: component mode follows `COMPONENT_SPEC.md`, screen mode follows `SCREEN_SPEC.md`.

## Setup

The maintainer has a single PNG of a mobile screen (an athlete earnings dashboard: a name/sport header, a total-earnings card with a paid/pending progress bar, a list of deal items with a brand-logo chip plus status plus amount, and a bottom tab nav). There is no Figma file for it. The project has a foundations set (`color.md`, `spacing.md`) under the workspace.

## Input prompt

```text
I only have this screenshot, no Figma. Generate a spec from it.
Image: ./mockups/earnings-dashboard.png
Project workspace: ./
```

## Expected response shape

- The command states the chosen mode: with no flag given, it auto-detects `screen` (a full layout with header, content, and a bottom tab nav) and gives the one-line reason.
- It states up front that the whole spec is `(proposed)` because there is no Figma ground truth.
- It produces a `SCREEN_SPEC.md`-shaped doc: an ASCII layout sketch, components used (each mapped to a design-system component or flagged as a candidate), observed spacing (mapped to the existing spacing tokens where possible, marked proposed), data dependencies, verbatim copy, accessibility notes, interactions, and error states.
- Every numeric or visual observation carries `(proposed)`. Copy legible in the image is quoted verbatim; spacing and dimensions are proposed estimates.
- The spec is written to `docs/app/screens/...` and a `SCREEN_MAP.md` row is added with source `image` (no Figma node ID).
- No Figma MCP call, no generate-into-Figma, and no web fetch appears anywhere in the run.
- The Handoff routes to a real command (for example `component-spec` / `screen-spec` to upgrade against Figma when one is available, `design-spec-review`, or `implementation-plan`), per the Global output contract.

## What a FAIL looks like

- Any observation is marked `confirmed`, or the run implies a Figma source it does not have.
- The command calls the Figma MCP, routes the image into Figma via `generate_figma_design`, or fetches the web.
- The command emits component code instead of a spec doc (Fhorja is spec-first; image-to-spec produces a spec).
- The mode is neither stated nor auto-detected, or the wrong template shape is produced for the chosen mode.
- Numeric values (spacing, dimensions) are presented as exact rather than proposed estimates.
- The Handoff is missing, or its `Run now` line names a command with no `commands/<name>.md` file.
