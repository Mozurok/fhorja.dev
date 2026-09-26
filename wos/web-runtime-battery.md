---
activation: model_decision
description: The serving discipline, the per-route battery and the taxonomy that web-runtime-verify classifies against: the ephemeral-port serve, page identity first with the G2 recovery, the overflow, keyboard, console, Lighthouse, axe and screenshot battery, the capture adapter and its run directory, the golden-baseline rule, the static mechanical-versus-judgment split, and the eight web codes. Load when running the web runtime gate; the command keeps the eight-step skeleton and this topic carries the adapter layer.
---

# Web runtime battery

Lazy-loaded reference for `web-runtime-verify`. It carries the serving
discipline, the per-route battery and the taxonomy this gate classifies
against, so the command keeps only the eight-step skeleton. Loaded when the
command runs, never inlined into the command. The serving mechanics themselves
stay in the ADR-0099 topic (`wos/frontend-preview-and-experience-verdict.md`);
this topic consumes them and never re-derives them.

## Serve and poll (ephemeral port)

Start the server per the ADR-0099 topic mechanics on an ephemeral free port; poll readiness (bounded, a few seconds); ALWAYS tear the server down at the end of the run, pass or fail. Under Codex CLI, fire this step as one of the FIRST actions of the turn while a human is present to approve escalations (`wos/editor-mode-mappings.md ## Harness operational quirks`; the 2h39 stall class).

## Page identity first, with G2 recovery

Rules 2 and 3 of the ADR-0099 topic's `## Serving discipline (both consumers)`, executed here. Before any other check, fetch the served page and assert the identity marker. WHEN the marker is absent or the port was already occupied (a stale server, another project), do NOT dry-fail: re-bind to a fresh free port, restart the serve, and re-run the identity check ONCE (the G2 recovery rule; a collision is an environment hazard, not a task blocker). A marker still absent after recovery is a real FAIL with the fetched evidence quoted: every later check would otherwise be verifying the wrong page, which is worse than no verification.

## The battery, once per route

WHEN a route list was supplied, run this whole step once per route in list order against the SAME served origin; with no route list it runs once over the single page and the output is what it is today. Step 3 is per route, not per run: fetch the route, assert THAT route's marker BEFORE its other checks, and on an absent marker or an occupied port fire the same G2 recovery (re-bind to a fresh FREE port, restart the serve, re-run that route's identity check ONCE) before any FAIL. A fixed port is invalid output on the first route and on every re-bind after it. A re-bind partway through the list changes the origin, so the report records every port used and which routes were probed on which. Record per route: the path requested, the HTTP status, and the observed response shape (content type, response size, and the identity evidence quoted from the body). Then run each check and capture its real output; a tool that is not installed reports `n/a (tool absent)` honestly, never a fabricated score:

- overflow sweep: probe horizontal overflow at 320, 768, 1280 and 2560 px (a headless viewport probe or a scrollWidth-vs-clientWidth check); quote the failing width and element when found;
- keyboard and focus walk: tab through the interactive elements; a focus trap, an unreachable control, or an invisible focus indicator is a finding;
- console capture: collect errors and warnings emitted on load and during the walk; zero errors is the bar, warnings are reported;
- Lighthouse and axe: run when available; report the scores and violations, or `n/a (tool absent)`; numeric thresholds belong to `performance-budget`, this gate reports the measurement;
- screenshot capture: capture one image of the route DURING this live run, through the same headless mechanism the overflow probe already uses (ADR-0099 topic mechanics, consumed from there and never re-derived), and write it into this run's directory as `<task-folder>/evidence/<slice-id>/WEB_RUNTIME_VERIFY_SHOTS/<slice>-<route-slug>.png`, where `<route-slug>` is the path with `/` replaced by `-` and the root route written as `index`. An image this run captured is evidence because the run produced it; a stored image standing in for a run is not evidence and stays prohibited by the G3 rule in `commands/web-runtime-verify.md`, which is why the file must be written by this run and its path reported only after the write. WHEN no capture mechanism is available the row reads `n/a (tool absent)` and names no path; a named path that does not exist on disk is invalid output.

## Evidence capture (the run directory)

Capture the evidence in this run rather than asking a human to paste it. Every artifact this run produces goes under the task folder in a per-slice run directory, `<task-folder>/evidence/<slice-id>/`, and every path written there is cited in the slice notes and in the report this command writes. The run directory lives in the task folder because it has to survive the session, which the session scratchpad does not; the evidence is then still on disk when the task is reviewed at the end.

The capture mechanism is a browser automation MCP, and the artifacts are the four reads such a server exposes today. Playwright MCP is the reference implementation: `browser_snapshot` for the accessibility tree, `browser_console_messages` for the console, `browser_network_requests` for the network log, and `browser_start_tracing` with `browser_stop_tracing` for the trace bundle. Chrome DevTools MCP adds `performance_start_trace` for LCP, INP and CLS. Record in the report which server answered and which tool produced each file. The gate stays capability-routed: any server exposing the same four reads is an equal substitute, and the report names whichever one ran.

Write the artifacts as `snapshot.txt`, `console.log`, `network.har` and `trace.zip` under the run directory, one set per route with the route slug in the filename, and keep `WEB_RUNTIME_VERIFY_SHOTS/` inside that same run directory so the screenshots sit beside the run that produced them. Capture raw and unedited. The tool that captured a file never narrates the verdict over it: the grader reads the file back off disk, which is what stops a captured artifact from being summarized into the result it was meant to check.

WHEN no browser automation MCP is reachable, the verdict is BLOCKED naming the missing capability (`no browser automation MCP reachable: no accessibility snapshot, console log, network log or trace`), and that BLOCKED routes to `incident-triage` as a CONFIG failure so the capability is installed and this gate re-run. It is never a silent PASS, and it is never a stop that waits for a human to paste a log. An unverified run reported as verified is the failure this gate exists to prevent.

## Golden baseline (visual checks)

A screenshot with no bug-free reference to compare it against is an artifact, not a check. Measured: median precision of 34 to 50 per cent with no reference screenshot, against 100 per cent with one. So a visual criterion needs a declared golden baseline, stored at `<task-folder>/evidence/baseline/<route-slug>.png` and named in the report, and the check is the comparison against that file, never the screenshot on its own.

WHEN no baseline exists for a route, still capture the screenshot and write it, then record that route's visual row as `unverified: no golden baseline` and say in the report that this run's image is the candidate baseline a human can promote. An `unverified` visual row is never an observed acceptance behavior.

## Mechanical and judgment criteria (static split)

The split is declared here, per battery rule, and is never decided per run. A per-run classification would have the agent judging its own capability at the point where the verdict is decided, which is the self-assessment this workflow rules out everywhere else.

| battery rule | class | decided from |
|---|---|---|
| page identity, with the G2 recovery | mechanical | the fetched body and the asserted marker |
| overflow sweep at 320, 768, 1280 and 2560 | mechanical | `scrollWidth` against `clientWidth`, or the viewport probe |
| keyboard and focus walk | mechanical | the captured accessibility snapshot and the focus order it reports |
| console capture | mechanical | the captured console log |
| Lighthouse and axe | mechanical | the tool's own output, or `n/a (tool absent)` |
| screenshot appearance: layout, spacing, visual regression | judgment | a human reading the image against the golden baseline |

A mechanical row is decided here with no human in the loop, and it gates. A judgment row is reported with its artifact path and routed to the experience verdict (ADR-0091), whose attester, run or human, is recorded per ADR-0179; it does not gate on its own, and it is never recorded as observed. WHEN the slice's acceptance behavior IS the judgment row, that criterion is `unverified` and the gate is BLOCKED with that reason, because no mechanical evidence for it exists.

## Taxonomy: web adapter

Tag every finding with one taxonomy code: `PAGE_IDENTITY_MISMATCH` (wrong page after recovery), `SERVE_FAILURE` (build will not serve or never becomes ready), `CONSOLE_ERROR`, `OVERFLOW` (horizontal overflow at a probed width), `FOCUS_DEFECT` (trap, unreachable control, missing indicator), `A11Y_VIOLATION` (axe finding), `PERF_MEASUREMENT` (a Lighthouse metric worth surfacing; budget judgment stays with `performance-budget`), or `CLEAN`.

The taxonomy stays these eight codes with a route qualifier; a probed route that never returns a usable response is a `SERVE_FAILURE` scoped to that route, and the other routes still get their own lines.
