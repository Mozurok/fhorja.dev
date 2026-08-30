#!/usr/bin/env python3
"""Replace engagement-identifying nouns in the historical record with neutral ones.

Substitutes exact strings, never line numbers, so the same script runs unchanged against the
staging tree and the public mirror. Idempotent by construction: a second pass finds no source
string and reports TOTAL 0. Workflow telemetry (agent counts, token counts, wall-clock, atom and
route counts) is preserved verbatim; only product nouns are replaced. See ADR-0164.

Usage: python3 scripts/redact-engagement-provenance.py FILE [FILE...]
"""

import sys

REPLACEMENTS = [
    (
        'on the client driver-app (5 Figma URLs, 26 parallel agents',
        'on a private design handoff (5 Figma frames, 26 parallel agents',
    ),
    (
        'The first lived test on the client driver-app validated',
        'The first lived test on that handoff validated',
    ),
    (
        'fanned out across 5 Figma URLs)',
        'fanned out across 5 Figma frames)',
    ),
    (
        '(the client driver-app screen-spec-fleet: 26 parallel agents',
        '(the design-handoff screen-spec-fleet run: 26 parallel agents',
    ),
    (
        'plus the client screen-spec-fleet artifact set',
        'plus the screen-spec-fleet artifact set',
    ),
    (
        'screen-spec-fleet pilot on a client driver-app handoff). 5 Figma URLs (driver onboarding + active-job flow) processed',
        'screen-spec-fleet pilot on a private design handoff). 5 Figma frames processed',
    ),
    (
        '`JOURNEY.md` reconstruction of the onboarding+job flow',
        '`JOURNEY.md` reconstruction of the traced flow',
    ),
    (
        'Lands the Phase 6 client-pilot follow-up artifacts',
        'Lands the Phase 6 design-handoff follow-up artifacts',
    ),
    (
        '(25-agent mega-batch: client-pilot 100% coverage prep)',
        '(25-agent mega-batch: catalog 100% coverage prep)',
    ),
    (
        'Lands the client-pilot 100% catalog-coverage preparation',
        'Lands the 100% catalog-coverage preparation',
    ),
    (
        'reflecting the client-pilot domain coverage gaps',
        'reflecting the domain coverage gaps',
    ),
    (
        'grounded against a specific client-pilot user-journey trace',
        'grounded against a specific real user-journey trace',
    ),
    (
        'review of a lived client-pilot session that fanned research',
        'review of a lived private-project session that fanned research',
    ),
    (
        'A 2026-06-09 review of a lived client-pilot session confirmed',
        'A 2026-06-09 review of a lived private-project session confirmed',
    ),
    (
        '- 2026-06-09 client-pilot session review',
        '- 2026-06-09 private-project session review',
    ),
    (
        'described in the changelog as client-pilot',
        'described in the changelog as catalog',
    ),
    (
        'orphaned since a 25-agent client-pilot coverage mega-batch',
        'orphaned since a 25-agent catalog coverage mega-batch',
    ),
]


def redact(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    count = 0
    for source, target in REPLACEMENTS:
        hits = text.count(source)
        if hits:
            text = text.replace(source, target)
            count += hits
    if count:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    return count


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    total = 0
    for path in argv:
        count = redact(path)
        print("%s: %d replacement(s)" % (path, count))
        total += count
    print("TOTAL %d" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
