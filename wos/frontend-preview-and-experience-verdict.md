# Frontend preview and the experience verdict

Lazy-loaded reference for serving a built frontend so a human can actually see it and record an experience verdict. The generalized experience-verdict floor (ADR-0091) and the pre-deploy experience-preview gate (ADR-0099) both require a human to view a real sample of a `user-facing-content` / `new-user-facing-surface` deliverable before it closes or ships. This topic documents the repeatable way to produce that sample; without it, every task improvises the serve step (the site dogfood improvised ngrok, hit a host-block, and by the time it worked the reviewer had walked back to their desk).

Load this when a task must produce a human-viewable preview of a built web frontend for an experience verdict. It is capability-routed and stack-agnostic in principle; the concrete recipes below are for the common static-build case (Astro, Vite, Next static export, plain `dist/`).

## The rule this serves

The experience-verdict floor does not accept machine-green evidence (lint, tests, a build exit 0) as a substitute for a human looking at the surface. So the task's job is to hand the human a URL they can open. This topic is the supported way to produce that URL. It is a serve recipe, not a new command: the closure and release gates reference it, and any command may run it.

## Serving discipline (both consumers)

Four rules govern every serve in this topic, whether the consumer is the machine gate (`web-runtime-verify`) or the human experience verdict (ADR-0091). This section is the canonical statement of them, per ADR-0112 decision 3 and ADR-0127: one serving doctrine, two consumers, referenced rather than re-derived. A command that restates them in its own words has re-derived them, and a session that improvises them has already lost the protection.

1. **Ephemeral free port, never a fixed one.** Probe for a free port or let the OS assign one, per run. A hardcoded port is invalid: the machine you are on may already be serving something else there, and the something else is frequently another project of yours. The real port appears in whatever the run reports.
2. **Page identity is asserted before the URL is trusted.** Fetch the served page and confirm a marker that distinguishes THIS build from any other page this machine might serve: the `<title>`, a unique selector, a text snippet the slice itself introduced. Until that assertion passes, nothing observed at that URL is evidence of anything.
3. **A collision is an environment hazard, not a task failure.** WHEN the identity marker is absent, or the port turns out to be occupied, do not dry-fail and do not accept what answered: re-bind to a fresh free port, restart the serve, and re-run the identity check once. A marker still absent after that recovery is a real failure, reported with the fetched body quoted.
4. **The run that starts a server owns its teardown.** Stop it when the run ends, pass or fail. A server left alive outlives the build it was serving and becomes the thing that answers on the next run's port, which is how rule 2 gets defeated by your own previous step rather than by a stranger.

Rules 1 to 3 are what `web-runtime-verify` Steps 2 to 4 execute; that command consumes them from here. Rule 4 is the one the human path forgets most, because the preview for a human is deliberately long-lived and the instinct is to leave it up.

## The identity assertion binds at the moment of handoff

The human verdict has its own version of rule 2, and it is stricter, because the gap between asserting and handing over is where a stale server slips in.

Assert the identity of the exact URL you are about to hand over, in the same turn as the ask, and quote what came back. An assertion made earlier in the session does not carry: the server may have died, a leftover from a previous step may have taken the port, or the build may have been rebuilt since. A verdict recorded against a URL whose identity was not confirmed at handoff does not satisfy the ADR-0091 floor, however green the machine battery was, because the machine battery may have been run against a different server than the human saw.

The failure this closes is on the record twice in one project. A 2026-07-16 run tested a different project's site on a default port and caught it only because the reported focus order named foreign elements. A 2026-08-06 run asserted identity correctly inside its machine battery, then started a long-lived preview for the human on the same fixed port; that start failed on a collision with the run's own leftover server from an earlier step, the failure notification arrived after the question had been asked, and the human recorded PASS against a server nobody had checked. It happened to be serving the right build.

## Local preview (reviewer is at the same machine)

Serve the built output and give the reviewer `http://localhost:<port>`, on a port picked per the serving discipline above, after the handoff-time identity assertion.

- Prefer the framework's own preview of the production build over the dev server, so the reviewer sees what ships (minified assets, real routing), not the dev experience: `astro preview`, `vite preview`, `next start` after `next build`, etc.
- The dev server (`astro dev`, `vite`, `next dev`) is acceptable for a fast look but is not the shipped artifact; note which one the reviewer saw when recording the verdict.
- The framework preview may refuse to start when one of its own is already running (`astro preview` reports the live PID and exits). Treat that as rule 3: re-bind, do not adopt the incumbent. What is already listening is the one thing you have no evidence about.

## Remote preview (reviewer is away from the machine)

When the reviewer is not at the machine (the common real case: "I'm not at the computer, send me a link"), expose the local server through a tunnel and send the public URL.

- A tunnel (ngrok, cloudflared, or the framework host's share feature) points a public URL at the local port.
- Record in the verdict which URL and which build the reviewer saw.

## The host-check gotcha (why the naive tunnel 403s)

Vite-based preview servers (this includes `astro preview`) reject requests whose `Host` header is not in an allow-list. A tunnel presents its own public hostname, so the preview server answers `403 This host is not allowed` and the reviewer sees an error page, not the site. This is the single failure that ate the site-dogfood preview.

Two fixes:

1. Allow the tunnel host on the preview server. In the framework config, set the preview server's allowed-hosts to include the tunnel hostname (Vite: `preview.allowedHosts`; Astro forwards to Vite). This keeps the reviewer on the real preview build.
2. Serve the static output with a plain file server that has no host check, then tunnel that. `python3 -m http.server <port> --directory dist` (or any static server) serves `dist/` with no `Host` allow-list, so a tunnel to it just works. Use this for a pure static build (no server routes); it is the fastest unblock. Do not use it when the app has server-rendered routes or middleware the file server would not run.

Pick fix 1 when the preview build has server behavior; pick fix 2 for a static `dist/`. Either way, verify the reviewer got a `200` and the real page, not the framework error page, before treating the link as delivered.

## Recording the verdict

The preview exists to feed a recorded human verdict, not to replace it. After the reviewer looks:

- Write an `## Experience verdict` block (per the ADR-0091 floor) with `Overall: PASS` or `FAIL`, citing which URL and which build (dev vs preview vs the exact commit) the reviewer saw, plus the handoff-time identity assertion output for that URL.
- A `FAIL` routes the specific gaps back into the task as normal follow-up work (a direction-adjust, a slice, or `pr-feedback-ingest`), not a silent re-try.
- For a `new-user-facing-surface`, also record the entry-path run (the way a real user reaches the surface), per the same floor.

## Do not

- Do not treat a build exit 0, a passing test, or a screenshot you generated as the experience verdict; the floor wants a human looking at a running sample.
- Do not send a tunnel link without confirming it returns the real page (the 403 host-block silently ships an error page as if it were the site).
- Do not leave a tunnel or preview server running past the review; stop it once the verdict is recorded.
- Do not serve on a fixed port, and do not adopt whatever is already answering on one. Both are the same mistake seen from two sides.
- Do not ask for the verdict before the identity assertion on that exact URL has come back, and do not read a start-failure notification that arrives after the ask as retroactively harmless.
