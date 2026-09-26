#!/usr/bin/env python3
"""Routing probe: does a shorter skill description still select the right command?

ADR-0135 set an aggregate ceiling on the Advertise stage and recorded, as its
first open item, that nothing in this repository measures whether a model still
routes correctly from a shorter description. It rejected trimming on sequencing
grounds: "a description trimmed until it stops routing fails silently, as 'the
model did not load the skill it needed', which reads as a model problem". This
script is that missing measurement.

WHAT IT DOES NOT DO: it does not call a model. Like run-evals.sh, it prepares the
prompts and scores the answers; running them is the caller's job (a subagent
fan-out, a judge harness, or a human pasting into a tool). Keeping the model out
of this file is what lets it run in CI to regenerate and score without a key.

## The design that matters

Two controls, both mandatory. Without them an accuracy number is unreadable.

  D_shuffled  Every identifier carries ANOTHER command's description. If the
              model still answers correctly, it is not reading the descriptions
              at all and every other number in the run is meaningless. This is
              the power check: run it first, and discard the run if it does not
              collapse.

  C_gut       Opener sentence only, routing marker removed. The floor: how much
              can be cut before selection degrades.

The identifiers are masked (cmd-01, cmd-02, ...) and command names are scrubbed
out of the description bodies. A first version of this probe skipped that step
and every condition scored 100 per cent, including a deliberately gutted one,
because names like `security-review` and `sync-task-state` answer the question
by themselves. The description was never under test. Masking is not cosmetic.

## Run it where the answers are not already loaded

Fhorja installs its skills, with FULL descriptions, into `~/.claude/skills` and
`~/.agents/skills` (and `~/.cursor/skills` under `--cursor-skills`, ADR-0228), which
between them reach Claude Code, Codex, Kimi and Cursor. A model running in any of
those environments already holds the complete text of every description while this
probe shows it a trimmed one, so it can recognise which skill a trimmed opener
belongs to and answer from what it already knows. That inflates every trimmed
condition, and the shuffled control does NOT catch it: with descriptions
swapped, a model reasoning from prior knowledge picks the wrong identifier just
the same, so the control still collapses and the run still looks clean.

Measured on 2026-08-17: emptying the skills directory moved one condition by a
single case out of 89, so the effect is small here. Small is not zero, and it is
only known because it was checked. When it matters, run the probe with the
skills directory emptied (`kimi --skills-dir /empty/dir`, or an equivalent) and
compare, rather than assuming.

## Usage

  # 1. emit prompts (JSON) for a chosen set of commands
  python3 evals/scripts/routing-probe.py emit --commands a,b,c --out probe.json

  # 2. run every prompt in probe.json through your agent harness, collecting
  #    {"label": ..., "got": [{"n": 1, "chosen": "cmd-07"}, ...]} per run

  # 3. score
  python3 evals/scripts/routing-probe.py score probe.json answers.json

Exit codes from `score`: 0 pass, 1 usage or data error, 2 the run is void
(the shuffled control did not collapse, so nothing can be concluded).
"""
import argparse, importlib.util, json, os, re, statistics as st, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# The shuffled control must collapse to NEAR CHANCE to call the instrument
# sensitive, and chance is 1/n_candidates, not a fixed fraction. The original
# 0.50 was chosen without reference to n: with 89 commands chance is 1.1 per
# cent, so 0.50 sat roughly 45x above it and would have called a run
# "collapsed" while the model answered correctly on half the cases with every
# description swapped. The ceiling below is 5x chance, which is about chance
# plus four standard errors at n=89, floored so a tiny command set does not
# produce an impossible bar. Every recorded run (ADR-0151 D-4, ADR-0153 D-1)
# scored 0.0 to 1.1 per cent, so this voids none of them.
CONTROL_CHANCE_MULTIPLE = 5
CONTROL_MAX_FLOOR = 0.05


def control_ceiling(n_candidates):
    """Void threshold for the shuffled control, as a function of pool size."""
    if not n_candidates or n_candidates < 2:
        return CONTROL_MAX_FLOOR
    return max(CONTROL_CHANCE_MULTIPLE / n_candidates, CONTROL_MAX_FLOOR)
# A condition must stay within this of the full-description baseline to pass.
TOLERANCE = 0.05


def load_descriptions():
    """Reuse structural-evals' parser. The descriptions are YAML block scalars;
    a single-line parser returns the block indicator and reports ~2 chars per
    skill, which looks like a valid run. Never write a second parser."""
    spec = importlib.util.spec_from_file_location(
        "se", os.path.join(HERE, "structural-evals.py"))
    se = importlib.util.module_from_spec(spec)
    sys.modules["se"] = se
    spec.loader.exec_module(se)
    d, _ = se.skill_descriptions(None)
    return {k: v for k, v in d.items() if v}


def first_sentence(t):
    m = re.match(r"(.+?\.)(\s|$)", t.strip(), re.S)
    return (m.group(1) if m else t[:200]).strip()


def make_conditions(desc, names):
    """full / trim / gut / shuffled for the selected command names."""
    def trim(t):
        head = first_sentence(t)
        m = re.search(r"(Do not use[^.]*\.)", t, re.S)
        tail = m.group(1) if m else ""
        if len(tail) > 260:
            tail = tail[:257].rstrip() + "."
        return (head + " " + tail).strip()

    shifted = {n: names[(i + 1) % len(names)] for i, n in enumerate(names)}
    return {
        "A_full":     {n: desc[n] for n in names},
        "B_trim":     {n: trim(desc[n]) for n in names},
        "C_gut":      {n: first_sentence(desc[n]) for n in names},
        "D_shuffled": {n: desc[shifted[n]] for n in names},
    }


def scrub(text, own, names):
    for other in names:
        text = text.replace(other, "this command" if other == own else "another command")
    return text


def build_prompt(cond_name, mapping, order, cases, case_order, names):
    mask = {n: f"cmd-{i+1:02d}" for i, n in enumerate(order)}
    body = "\n\n".join(
        f"### {mask[n]}\n{scrub(mapping[n], n, names)}" for n in order)
    qs = "\n".join(f"{i+1}. {cases[ci]['prompt']}" for i, ci in enumerate(case_order))
    prompt = f"""You are routing a user request to exactly one command, using ONLY the command descriptions below.

The commands are deliberately unnamed. Every identifier is opaque (cmd-01, cmd-02, ...). The description text is the ONLY information you have. That is the point of this measurement.

Do NOT use any tool. Do NOT read any file. Judge only from the text in this message. If you use a tool, the measurement is invalid.

## Available commands

{body}

## Requests to route

{qs}

For each numbered request, pick the ONE identifier (cmd-NN) whose description best matches it. If genuinely torn, still pick one; do not abstain.

Return one entry per request number: the number, and the identifier you chose."""
    expected = [mask[cases[ci]["expect"]] for ci in case_order]
    return prompt, expected


def build_null_prompt(mapping, order, cases, case_order, names):
    """Same descriptions, cases that belong to NO command, abstention PERMITTED.

    The probe's ordinary prompt says "If genuinely torn, still pick one; do not
    abstain", and every case has exactly one right answer among the candidates.
    That measures whether the right command is picked and CANNOT measure whether
    a wrong one is picked when none applies, because the output space excludes
    the correct answer. Every description carries a `Do not use` clause whose
    only purpose is to stop a command firing on a request that is not its own,
    and nothing had ever tested one.

    Scored separately from routing accuracy on purpose. A model that abstains on
    every null case and a model that routes perfectly are different results, and
    averaging them would hide both.
    """
    mask = {n: f"cmd-{i+1:02d}" for i, n in enumerate(order)}
    body = "\n\n".join(
        f"### {mask[n]}\n{scrub(mapping[n], n, names)}" for n in order)
    qs = "\n".join(f"{i+1}. {cases[ci]['prompt']}" for i, ci in enumerate(case_order))
    prompt = f"""You are routing a user request to exactly one command, using ONLY the command descriptions below.

The commands are deliberately unnamed. Every identifier is opaque (cmd-01, cmd-02, ...). The description text is the ONLY information you have. That is the point of this measurement.

Do NOT use any tool. Do NOT read any file. Judge only from the text in this message. If you use a tool, the measurement is invalid.

## Available commands

{body}

## Requests to route

{qs}

For each numbered request, pick the ONE identifier (cmd-NN) whose description best matches it.

Some of these requests match NO command in the list. For those, answer `none`. Answering `none` is a correct answer, not a failure to decide, and several descriptions state explicitly when they should NOT be used. Do not stretch a description to cover a request it excludes.

Return one entry per request number: the number, and either the identifier you chose or `none`."""
    expected = ["none" for _ in case_order]
    return prompt, expected


def shuffle_det(seq, seed):
    """Deterministic, non-linear permutation.

    Rotation is not good enough here and the failure is silent. If the command
    order and the case order are both rotations of the same sorted list, then
    expected[i] is i plus a constant, position alone predicts every answer, and
    a model can score 100 per cent without reading one description. That is
    exactly what a 89-command run produced before this function replaced
    rotation: every condition returned a perfect contiguous sequence, including
    the shuffled control.

    Hash-keyed ordering has no RNG (reruns reproduce byte for byte) and no
    arithmetic relationship between input and output position.
    """
    import hashlib
    return sorted(seq, key=lambda x: hashlib.sha256(f"{seed}:{x}".encode()).hexdigest())


def positional_confound(expected):
    """Fraction of the mapping explained by a single fixed offset.

    1.0 means expected[i] is i plus a constant for every case, so the run
    measures list position rather than routing.
    """
    n = len(expected)
    if n < 2:
        return 1.0
    nums = [int(e.split("-")[1]) for e in expected]
    offsets = [(nums[i] - (i + 1)) % n for i in range(n)]
    return max(Counter(offsets).values()) / n


def cmd_emit(args):
    desc = load_descriptions()
    names = sorted(n.strip() for n in args.commands.split(",") if n.strip())
    missing = [n for n in names if n not in desc]
    if missing:
        print(f"unknown command(s): {', '.join(missing)}", file=sys.stderr)
        return 1
    cases = json.load(open(args.cases))
    null_cases = json.load(open(args.null_cases)) if args.null_cases else []
    unknown = [c["expect"] for c in cases if c["expect"] not in names]
    if unknown:
        print(f"cases expect commands outside the set: {', '.join(unknown)}", file=sys.stderr)
        return 1

    conds = make_conditions(desc, names)

    runs = []
    for cond in ["A_full", "B_trim", "C_gut", "D_shuffled"]:
        for r in range(args.replicates):
            # Command order and case order get independent seeds, so the two are
            # not permutations of each other.
            o = shuffle_det(names, f"cmd-{r}")
            co = shuffle_det(list(range(len(cases))), f"case-{r}")
            p, exp = build_prompt(cond, conds[cond], o, cases, co, names)
            runs.append({"label": f"{cond}-r{r+1}", "cond": cond, "rep": r + 1,
                         "expected": exp, "prompt": p})

    # Refuse to emit a run whose answers are predictable from list position. This
    # check exists because the failure it catches looked like a perfect score.
    worst = max(positional_confound(r["expected"]) for r in runs)
    if worst > 0.25:
        print(f"REFUSING TO EMIT: {worst*100:.0f} per cent of the case-to-command mapping "
              f"is explained by one fixed offset.", file=sys.stderr)
        print("  A model can score full marks by answering in list order, without reading "
              "any description. Change the permutation seeds or the case set.", file=sys.stderr)
        return 2
    print(f"positional-confound check: worst run {worst*100:.0f} per cent "
          f"(refuses above 25), ok")

    if null_cases:
        o = shuffle_det(names, "null-order")
        for r in range(args.replicates):
            co = shuffle_det(list(range(len(null_cases))), f"null-case-{r}")
            p, exp = build_null_prompt(conds["A_full"], o, null_cases, co, names)
            runs.append({"label": f"E_null-r{r+1}", "cond": "E_null", "rep": r + 1,
                         "expected": exp, "prompt": p})
        print(f"null-case condition: {len(null_cases)} case(s) x {args.replicates} replicate(s); "
              "abstention permitted and scored separately")

    json.dump({"n_candidates": len(names), "runs": runs},
              open(args.out, "w"), ensure_ascii=False, indent=1)
    sizes = {k: sum(len(v) for v in c.values()) for k, c in conds.items()}
    base = sizes["A_full"]
    print(f"wrote {len(runs)} run(s) to {args.out}")
    for k in ["A_full", "B_trim", "C_gut"]:
        print(f"  {k:11} {sizes[k]:>7} chars  ({100*sizes[k]/base:5.1f}% of full)")
    return 0


def cmd_score(args):
    probe = json.load(open(args.probe))
    runs = {r["label"]: r for r in probe["runs"]}
    n_candidates = probe.get("n_candidates")
    n_source = "recorded at emit"
    if not n_candidates:
        n_candidates = len({e for r in probe["runs"] for e in r["expected"]})
        n_source = "derived from distinct expected answers (probe predates n_candidates)"
    answers = json.load(open(args.answers))
    if isinstance(answers, dict) and "result" in answers:
        answers = answers["result"]

    by = {}
    for a in answers:
        r = runs.get(a.get("label"))
        if not r:
            continue
        m = {c["n"]: (c.get("chosen") or "").strip() for c in (a.get("got") or [])}
        exp = r["expected"]
        hits = sum(1 for i, e in enumerate(exp, 1) if m.get(i, "") == e)
        by.setdefault(r["cond"], []).append(hits / len(exp))

    if not by:
        print("no answers matched any run label", file=sys.stderr)
        return 1

    means = {k: st.mean(v) for k, v in by.items()}
    print("=" * 64)
    print("ROUTING PROBE")
    print("=" * 64)
    for k in ["A_full", "B_trim", "C_gut", "D_shuffled"]:
        if k not in means:
            continue
        reps = ", ".join(f"{x*100:.0f}%" for x in by[k])
        print(f"  {k:11} {means[k]*100:5.1f}%   [{reps}]")
    print()

    # Reported on its own, never folded into routing accuracy. It answers a
    # different question: whether a description declines a request it excludes.
    # A model that abstains on every null case and a model that routes perfectly
    # are different results, and one mean would hide both.
    if "E_null" in means:
        reps = ", ".join(f"{x*100:.0f}%" for x in by["E_null"])
        rate = means["E_null"]
        print(f"  E_null      {rate*100:5.1f}% correctly declined   [{reps}]")
        if rate >= 0.99:
            print("    Every null case was declined. Read that as the cases being too easy")
            print("    until an adversarial set (a request just outside a command's stated")
            print("    boundary) says otherwise; a control that never fires is not a control.")
        elif rate <= 0.20:
            print("    The `Do not use` clauses are not doing their job on this set. They are")
            print("    paid for in the Advertise stage of every session.")
        print()

    if "D_shuffled" not in means:
        print("VOID: the shuffled control was not run. It is not optional.")
        return 2
    ceiling = control_ceiling(n_candidates)
    if means["D_shuffled"] > ceiling:
        print(f"VOID: the shuffled control scored {means['D_shuffled']*100:.1f}%, "
              f"above the {ceiling*100:.1f}% ceiling "
              f"(chance {100.0/n_candidates:.1f}%, n={n_candidates}, {n_source}).")
        print("  The model answered correctly while every identifier carried another")
        print("  command's description, so it is not routing on this text. No other")
        print("  number in this run can be read. Fix the probe before trusting a trim.")
        return 2

    print(f"control collapsed to {means['D_shuffled']*100:.1f}% "
          f"(chance {100.0/n_candidates:.1f}%, ceiling {ceiling*100:.1f}%, "
          f"n={n_candidates}, {n_source}): the probe reads the descriptions.")
    if "A_full" not in means:
        print("  (no A_full baseline in this run; reporting only)")
        return 0
    fails = []
    for k in ["B_trim", "C_gut"]:
        if k not in means:
            continue
        drop = means["A_full"] - means[k]
        verdict = "within tolerance" if drop <= TOLERANCE else "DEGRADED"
        print(f"  {k}: {drop*100:+.1f} points vs full  ({verdict})")
        if drop > TOLERANCE:
            fails.append(k)
    print()
    print("Sample bounds the claim: this covers the commands passed to `emit`, one")
    print("model and one prompt shape. It licenses a pilot trim, not a corpus-wide one.")
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("emit", help="write the prompts to run")
    e.add_argument("--commands", required=True, help="comma-separated command names")
    e.add_argument("--cases", required=True, help="JSON: [{prompt, expect}, ...]")
    e.add_argument("--out", default="routing-probe.json")
    e.add_argument("--replicates", type=int, default=3)
    e.add_argument("--null-cases", help="JSON: [{prompt}, ...] requests that match NO command; "
                                        "adds the E_null condition, scored separately")
    e.set_defaults(func=cmd_emit)

    s = sub.add_parser("score", help="score collected answers")
    s.add_argument("probe")
    s.add_argument("answers")
    s.set_defaults(func=cmd_score)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
