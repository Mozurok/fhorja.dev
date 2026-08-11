# ADR-0127: The web and backend runtime gates reach the human flow, and the serving doctrine lives where it was assigned

- **Status**: Accepted
- **Date**: 2026-08-06
- **Tags**: closure-enforcement, runtime-gate, web-runtime-verify, api-runtime-verify, platform-runtime-floors, experience-verdict, page-identity, generalizes-adr-0106, conforms-adr-0112, consumes-adr-0099, dogfood-driven, kimi-dogfood

## Context

Two defects found in the same place by one cross-model dogfood run (Kimi K3 driving the full command chain over a spec whose every acceptance gate was web-runtime: WCAG 2.2 AA, no horizontal overflow 320 to 2560, Lighthouse mobile, LCP, CLS, zero console errors).

**The gate is unreachable from the human flow.** `web-runtime-verify` (ADR-0112) and `api-runtime-verify` exist as commands. Their only inbound references are `autonomous-readiness`, `autonomous-run`, and the `wos/command-roles.md` index. No command in the implement-to-close flow names either one. `wos/platform-runtime-floors.md` carries a runtime-gate floor for Godot (ADR-0085) and one for mobile (ADR-0106, itself a generalization of the Godot mechanism onto `app-runtime-verify` per ADR-0087), and stops. Web and backend HTTP have the verify command and no floor, so nothing makes a slice touching a servable frontend or an HTTP route reach for it.

The gap was not an oversight. ADR-0112 shipped the command with its "closure floor deliberately staged pending dogfood per the ADR-0106 precedent", and ADR-0106 is the precedent it names: the mobile gate shipped as a command first, a dogfood then shipped a fully broken biometric flow past `tsc --noEmit` with `app-runtime-verify` available but never required, and the floor followed with that evidence. This ADR is the scheduled second step for the web and backend siblings, taken with the dogfood evidence it was waiting for.

The run behaved exactly as that gap predicts. Its plan named "web-runtime-verify battery" in the slice's validation prose, because the planner had read the roles index. The executor then reimplemented the entire harness inside `implement-approved-slice`: preview server, readiness sleep, width sweep, keyboard walk, console capture, Lighthouse invocation. This is the same improvisation ADR-0112 was written to end, reappearing because ADR-0112 shipped the command without wiring it to a floor. `scripts/flow-audit.py` does not surface it: the command has three inbound references and reads as connected, because the auditor counts references without distinguishing the autonomous track from the human one.

**The serving doctrine is not where ADR-0112 put it.** ADR-0112 decision 3 reads: "Serving mechanics belong to `wos/frontend-preview-and-experience-verdict.md` (ADR-0099): one serving doctrine, two consumers (this machine gate and the ADR-0091 human experience verdict over the same served build). The command references, never duplicates." The mechanics that matter are the ephemeral-port rule (a fixed port is invalid output), the identity assertion as the FIRST check, the G2 automatic re-bind recovery on a collision or a stale server, and the guaranteed teardown. All four live in `commands/web-runtime-verify.md` Steps 2 to 4. None is in the topic. The topic's local-preview section says to prefer the framework's production preview and documents the Vite `allowedHosts` gotcha, and asks for a `200` check on the tunnel path only.

So the second consumer, the human experience verdict, reads the topic and finds no identity rule at all. In the run: the durable preview started for the verdict failed with `Another astro preview server is already running (PID 14200)`, a leftover from an earlier verification step in the same session. The failure notification arrived after `AskUserQuestion` had already been asked. The human recorded PASS against a server nobody had asserted the identity of. It happened to be serving the current build. This is the second occurrence of the wrong-page class in this project; the archived 2026-07-16 run recorded the first (a different project's server answering on the default port), and its LEARNINGS entry was consumed by this run's plan, which asserted `document.title` in the machine battery and not at the human handoff.

## Decision

**1. Generalize the runtime-gate floor to web and backend HTTP.** Add two floors to `wos/platform-runtime-floors.md`, each with the three per-command variants the file already uses (`implement-approved-slice` inline-close, `slice-closure`, `task-close` backstop), written to the same shape as the mobile floor that generalized the Godot one:

- **Web-runtime-gate floor**, keyed on the `web-runtime-target` tag on the slice or task, or the heuristic backstop: the slice's declared scope touched a servable frontend surface (a page, route, component, template, or style file) in a project whose manifest declares a web build or preview script. It requires a real `web-runtime-verify` PASS cited, or an explicit one-line skip reason.
- **Backend-runtime-gate floor**, keyed on the `http-runtime-target` tag, or the heuristic backstop: the slice's declared scope touched an HTTP route handler, controller, or router definition. It requires a real `api-runtime-verify` PASS cited, or an explicit one-line skip reason.

Both inherit the ADR-0098 bounded-versus-permanent skip rule and the ADR-0085 three-way-verdict rule (a BLOCKED verdict is neither a PASS nor a skip). Both stand down under the Godot signature, matching how the mobile floor already yields.

The trigger is deliberately narrower than "the slice touched a file the browser can render". A repo with no web build or preview script never fires the heuristic, and a docs-only or config-only slice never fires it either. The tag remains the precise control; the heuristic exists so a plan that assigns no tag does not silently disable the gate, which is the failure mode recorded against the mobile floor.

**2. Move the serving doctrine into the topic ADR-0112 assigned it to.** `wos/frontend-preview-and-experience-verdict.md` gains a `## Serving discipline (both consumers)` section carrying the four rules as the canonical statement: ephemeral free port never a fixed one, page identity asserted before the URL is trusted or handed over, the G2 re-bind recovery on a collision or stale server, and teardown owned by the run that started the server. `commands/web-runtime-verify.md` keeps its step sequence and cites the topic as the source of those rules rather than restating them as its own, which is what "references, never duplicates" asked for.

**3. The identity assertion binds at the moment of handoff.** The topic states that the human is handed a URL only after that exact URL has been fetched and its identity marker confirmed in the same turn as the ask. A verdict recorded against a URL whose identity was asserted earlier in the session, or asserted against a different server, does not satisfy the ADR-0091 floor. This is the rule the run had no way to know: it asserted identity correctly inside its machine battery and never at the handoff, which is where the stale server was.

## Consequences

### Positive

- The web gate stops being improvised per session. This was ADR-0112's stated purpose and the floor is what makes it reachable.
- The wrong-page class is closed on the path where it actually bit twice, the human handoff, not only on the machine path that already had the rule.
- One mechanism now covers four surfaces (Godot, mobile, web, backend HTTP) with one shape, so a fifth surface is a fill-in rather than a design.

### Negative

- Two more floors to evaluate on every closing command. Mitigated the way the file already mitigates it: `wos/platform-runtime-floors.md` is lazy-loaded on signature match and inert otherwise, so a task with no web or HTTP surface pays nothing.
- A repo with a web build script and a genuinely unservable slice will fire the heuristic and need a one-line skip reason. Accepted: a one-line skip is cheaper than a silently disabled gate.

### Neutral

- No new command. Both verify commands already exist and are unchanged except for the citation direction in `web-runtime-verify`.
- The Godot and mobile floors are untouched.

## References

- Generalizes ADR-0106 (mobile-runtime-gate), which generalized ADR-0085 (Godot runtime-gate) onto ADR-0087.
- Conforms `commands/web-runtime-verify.md` to ADR-0112 decision 3; consumes ADR-0099's topic as the single serving doctrine.
- Binds to ADR-0091 (generalized experience verdict) and inherits ADR-0098's bounded-versus-permanent skip rule.
- Dogfood evidence: Kimi K3 session `a6f1a135`, 2026-08-06, `beaufort__landing-page/archive/2026-08-06_astro-landing-page-c/`. Prior occurrence of the wrong-page class: the archived 2026-07-16 run's `LEARNINGS.md`.
