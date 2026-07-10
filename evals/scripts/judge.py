#!/usr/bin/env python3
# DEPRECATED 2026-06-04 -- superseded by commands/verify-against-rubric.md (sub-agent-based pattern; ADR-0033).
# This script is archival reference for ADR-0019 and is not invoked by any active command.
# Do not extend; use verify-against-rubric for new verification work.
# See: _internal/verify-against-rubric-design-2026-06.md for the consolidation rationale.
"""
LLM-as-judge for Fhorja eval scenarios.

Reads a scenario file (`evals/scenarios/<NN>-*.md`) and a model output, formats
the scenario's `## Pass criteria` as a rubric, pipes the rubric to a local AI
tool, and parses per-criterion verdicts (PASS / FAIL / UNCERTAIN) plus an
overall verdict. OPTIONAL second pass per ADR-0019; never replaces manual
review. UNCERTAIN verdicts always defer to human.

Usage:
  judge.py --scenario evals/scenarios/01-bootstrap-and-init.md --output response.txt
  cat response.txt | judge.py --scenario evals/scenarios/01-bootstrap-and-init.md
  judge.py --scenario ... --output ... --tool 'claude code --print'
  judge.py --scenario ... --output ... --json

Exit codes:
  0 = judge ran; verdicts in output (regardless of PASS/FAIL/UNCERTAIN)
  1 = invocation error (missing scenario, unreadable output, etc.)
  2 = tool call failed (subprocess returned non-zero or empty)
"""

from __future__ import annotations
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# Locked rubric wrapper per slice 07. Changes here require updating the slice
# history and the ADR-0019 references.
RUBRIC_WRAPPER = """You are evaluating a model response against numbered pass criteria.

Pass criteria:
{criteria_block}

Model response to evaluate:
{model_output}

For each numbered criterion, emit exactly one line in this format:
- Criterion N: PASS | FAIL | UNCERTAIN -- <one-sentence reasoning>

After all criteria, emit:
- Overall: PASS | FAIL | UNCERTAIN -- <one-sentence summary>

If a criterion's wording is ambiguous about what to check, emit UNCERTAIN with the ambiguity named. Do not invent criteria that are not in the numbered list. Do not score on aesthetic dimensions not in the criteria.
"""

VERDICT_LINE_RE = re.compile(
    r"^-\s+Criterion\s+(\d+)\s*:\s+(PASS|FAIL|UNCERTAIN)\s+--\s+(.+?)\s*$",
    re.MULTILINE,
)
OVERALL_LINE_RE = re.compile(
    r"^-\s+Overall\s*:\s+(PASS|FAIL|UNCERTAIN)\s+--\s+(.+?)\s*$",
    re.MULTILINE,
)


def extract_pass_criteria(scenario_text: str) -> list[str]:
    """Extract the numbered list under `## Pass criteria` from a scenario file."""
    lines = scenario_text.split("\n")
    in_section = False
    items: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "## Pass criteria":
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                if current:
                    items.append("\n".join(current).strip())
                    current = []
                break
            m = re.match(r"^(\d+)\.\s+(.+)$", line)
            if m:
                if current:
                    items.append("\n".join(current).strip())
                    current = []
                current.append(m.group(2))
            elif current:
                current.append(line)
    if current:
        items.append("\n".join(current).strip())
    return [re.sub(r"\n\s*\n", "\n", it).strip() for it in items if it.strip()]


def format_criteria_block(criteria: list[str]) -> str:
    return "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))


def call_tool(tool_cmd: str, prompt: str) -> str:
    """Pipe prompt to the AI tool via subprocess; return stdout."""
    try:
        completed = subprocess.run(
            shlex.split(tool_cmd),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError as e:
        print(f"Error: tool not found: {e}", file=sys.stderr)
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print(f"Error: tool call timed out after 180s", file=sys.stderr)
        sys.exit(2)
    if completed.returncode != 0:
        print(f"Error: tool returned {completed.returncode}", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        sys.exit(2)
    if not completed.stdout.strip():
        print("Error: tool returned empty stdout", file=sys.stderr)
        sys.exit(2)
    return completed.stdout


def parse_verdicts(judge_response: str, n_criteria: int) -> tuple[dict[int, dict], dict]:
    """Parse per-criterion lines and the overall line. Missing criteria -> UNCERTAIN."""
    per_criterion: dict[int, dict] = {}
    for m in VERDICT_LINE_RE.finditer(judge_response):
        idx = int(m.group(1))
        verdict = m.group(2)
        reasoning = m.group(3).strip()
        per_criterion[idx] = {"verdict": verdict, "reasoning": reasoning}
    for i in range(1, n_criteria + 1):
        if i not in per_criterion:
            per_criterion[i] = {
                "verdict": "UNCERTAIN",
                "reasoning": "judge did not address this criterion",
            }
    om = OVERALL_LINE_RE.search(judge_response)
    if om:
        overall = {"verdict": om.group(1), "reasoning": om.group(2).strip()}
    else:
        verdicts = [v["verdict"] for v in per_criterion.values()]
        if "FAIL" in verdicts:
            overall = {"verdict": "FAIL", "reasoning": "at least one criterion FAIL; judge did not emit Overall line"}
        elif "UNCERTAIN" in verdicts:
            overall = {"verdict": "UNCERTAIN", "reasoning": "at least one criterion UNCERTAIN; judge did not emit Overall line"}
        else:
            overall = {"verdict": "PASS", "reasoning": "all criteria PASS; judge did not emit Overall line"}
    return per_criterion, overall


def emit_markdown(scenario_path: Path, per_criterion: dict[int, dict], overall: dict, raw_response: str) -> str:
    out = []
    out.append(f"# Judge verdict: {scenario_path.name}")
    out.append("")
    out.append("Per ADR-0019, this is an OPTIONAL second pass; UNCERTAIN defers to human review; FAIL is advisory; PASS is advisory and may be spot-checked.")
    out.append("")
    out.append("## Per-criterion verdicts")
    out.append("")
    for idx in sorted(per_criterion.keys()):
        v = per_criterion[idx]
        out.append(f"- Criterion {idx}: **{v['verdict']}** -- {v['reasoning']}")
    out.append("")
    out.append(f"## Overall: **{overall['verdict']}**")
    out.append("")
    out.append(overall["reasoning"])
    out.append("")
    out.append("## Raw judge response (for audit)")
    out.append("")
    out.append("```")
    out.append(raw_response.rstrip())
    out.append("```")
    return "\n".join(out)


def emit_json(scenario_path: Path, per_criterion: dict[int, dict], overall: dict, raw_response: str) -> str:
    return json.dumps(
        {
            "scenario": scenario_path.name,
            "per_criterion": per_criterion,
            "overall": overall,
            "raw_response": raw_response,
            "policy": "OPTIONAL second pass per ADR-0019; UNCERTAIN defers to human; FAIL advisory; PASS advisory",
        },
        indent=2,
    )


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge for Fhorja eval scenarios.")
    parser.add_argument("--scenario", required=True, help="Path to evals/scenarios/<NN>-*.md")
    parser.add_argument("--output", help="Path to model output file. If omitted, read from stdin.")
    parser.add_argument(
        "--tool",
        default="claude code --print",
        help='Shell command that takes the rubric on stdin and emits the judge response on stdout. Default: "claude code --print".',
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.is_file():
        print(f"Error: scenario not found: {scenario_path}", file=sys.stderr)
        sys.exit(1)

    scenario_text = scenario_path.read_text(encoding="utf-8")
    criteria = extract_pass_criteria(scenario_text)
    if not criteria:
        print(f"Error: no `## Pass criteria` numbered list found in {scenario_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_file():
            print(f"Error: output file not found: {output_path}", file=sys.stderr)
            sys.exit(1)
        model_output = output_path.read_text(encoding="utf-8")
    else:
        model_output = sys.stdin.read()
    if not model_output.strip():
        print("Error: model output is empty", file=sys.stderr)
        sys.exit(1)

    prompt = RUBRIC_WRAPPER.format(
        criteria_block=format_criteria_block(criteria),
        model_output=model_output,
    )

    raw_response = call_tool(args.tool, prompt)
    per_criterion, overall = parse_verdicts(raw_response, len(criteria))

    if args.json:
        print(emit_json(scenario_path, per_criterion, overall, raw_response))
    else:
        print(emit_markdown(scenario_path, per_criterion, overall, raw_response))


if __name__ == "__main__":
    main()
