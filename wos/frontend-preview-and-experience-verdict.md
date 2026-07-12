# Frontend preview and the experience verdict

Lazy-loaded reference for serving a built frontend so a human can actually see it and record an experience verdict. The generalized experience-verdict floor (ADR-0091) and the pre-deploy experience-preview gate (ADR-0099) both require a human to view a real sample of a `user-facing-content` / `new-user-facing-surface` deliverable before it closes or ships. This topic documents the repeatable way to produce that sample; without it, every task improvises the serve step (the site dogfood improvised ngrok, hit a host-block, and by the time it worked the reviewer had walked back to their desk).

Load this when a task must produce a human-viewable preview of a built web frontend for an experience verdict. It is capability-routed and stack-agnostic in principle; the concrete recipes below are for the common static-build case (Astro, Vite, Next static export, plain `dist/`).

## The rule this serves

The experience-verdict floor does not accept machine-green evidence (lint, tests, a build exit 0) as a substitute for a human looking at the surface. So the task's job is to hand the human a URL they can open. This topic is the supported way to produce that URL. It is a serve recipe, not a new command: the closure and release gates reference it, and any command may run it.

## Local preview (reviewer is at the same machine)

Serve the built output and give the reviewer `http://localhost:<port>`.

- Prefer the framework's own preview of the production build over the dev server, so the reviewer sees what ships (minified assets, real routing), not the dev experience: `astro preview`, `vite preview`, `next start` after `next build`, etc.
- The dev server (`astro dev`, `vite`, `next dev`) is acceptable for a fast look but is not the shipped artifact; note which one the reviewer saw when recording the verdict.

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

- Write an `## Experience verdict` block (per the ADR-0091 floor) with `Overall: PASS` or `FAIL`, citing which URL and which build (dev vs preview vs the exact commit) the reviewer saw.
- A `FAIL` routes the specific gaps back into the task as normal follow-up work (a direction-adjust, a slice, or `pr-feedback-ingest`), not a silent re-try.
- For a `new-user-facing-surface`, also record the entry-path run (the way a real user reaches the surface), per the same floor.

## Do not

- Do not treat a build exit 0, a passing test, or a screenshot you generated as the experience verdict; the floor wants a human looking at a running sample.
- Do not send a tunnel link without confirming it returns the real page (the 403 host-block silently ships an error page as if it were the site).
- Do not leave a tunnel or preview server running past the review; stop it once the verdict is recorded.
