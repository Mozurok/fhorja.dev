#!/usr/bin/env bash
# check-skill-budget.sh: how many generated skills survive the host's compaction budget.
#
# THE HOST CONTRACT, quoted from https://code.claude.com/docs/en/skills, read
# 2026-09-17, HTTP 200:
#   "Claude Code re-attaches the most recent invocation of each skill after the
#    summary, keeping the first 5,000 tokens of each. Re-attached skills share a
#    combined budget of 25,000 tokens."
#   "Claude Code fills this budget starting from the most recently invoked skill,
#    so older skills can be dropped entirely after compaction if you have invoked
#    many in one session."
#
# WHY THIS EXISTS. build-agent-skills.sh models the PER-SKILL 5,000-token cap
# (REINJECTION_CAP_CHARS) and front-loads a brief for bodies that exceed it. Nothing
# modelled the COMBINED budget, under which whole skills vanish. Measured 2026-09-17:
# only 5 to 7 of the 98 skills fit 25,000 tokens, and that range is stable under both
# chars-per-token assumptions in use here, so it does not rest on the estimate. The
# ordinary spine invokes seven commands, so a normal session saturates the budget and
# silently loses its earliest skill after the first compaction.
#
# ADVISORY. Fhorja cannot change the host's budget; it can only report the headroom
# and let a shrink be a deliberate decision. Always exits 0.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS="$ROOT/.claude/skills"

PER_SKILL_TOK=5000
COMBINED_TOK=25000
CHARS_PER_TOK=4          # the repo's own convention, same as REINJECTION_CAP_CHARS

[ -d "$SKILLS" ] || { echo "Skill-budget: not measured (no generated skills)"; exit 0; }

python3 - "$SKILLS" "$PER_SKILL_TOK" "$COMBINED_TOK" "$CHARS_PER_TOK" <<'PY'
import sys, glob, os
skills_dir, per_tok, comb_tok, cpt = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
files = glob.glob(os.path.join(skills_dir, "*", "SKILL.md"))
if not files:
    print("Skill-budget: not measured (no SKILL.md found)"); raise SystemExit(0)
sizes = sorted(os.path.getsize(f) / cpt for f in files)
over = sum(1 for s in sizes if s > per_tok)

def fits(order):
    budget, n = comb_tok, 0
    for s in order:
        cost = min(s, per_tok)
        if budget - cost < 0:
            break
        budget -= cost; n += 1
    return n

worst, best = fits(sorted(sizes, reverse=True)), fits(sizes)
rng = f"{worst}" if worst == best else f"{worst} to {best}"
print(f"Skill-budget: {len(sizes)} skill(s), {over} over the {per_tok}-token per-skill cap; "
      f"{rng} fit the host's {comb_tok}-token combined budget (advisory; the spine invokes 7, "
      f"so a normal session saturates it and drops its earliest skill after compaction)")
PY
exit 0
