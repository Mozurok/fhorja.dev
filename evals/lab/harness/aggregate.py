#!/usr/bin/env python3
"""Reads runs/*/ (meta.json + events.jsonl + work/) and writes results/summary-v2.json
and results/summary-v2.md with time, tokens, cost and a few behavior counters per run.

Claude cost comes from the CLI's own total_cost_usd (API-equivalent estimate).
Codex cost is computed from token counts and harness/prices.json (USD per 1M tokens);
a model with no price there gets cost=null rather than a guess.
"""
import json, os, subprocess, sys
from pathlib import Path
from usage_ledger import discover, ledger
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "runs")
RESULTS = os.environ.get("RESULTS_DIR", os.path.join(ROOT, "results"))
SESSION_CACHE = {}
PRICES = json.load(open(os.path.join(ROOT, "harness", "prices.json")))
SKILLS_DIR = os.environ.get("FHORJA_SKILLS_DIR")
FHORJA_SKILLS = set(os.listdir(SKILLS_DIR)) if SKILLS_DIR and os.path.isdir(SKILLS_DIR) else set()


def events(path):
    if not os.path.exists(path):
        return
    for line in open(path, errors="replace"):
        line = line.strip()
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass


def claude_metrics(evs):
    m = {"turns": None, "cost_usd": None, "api_secs": None, "tokens": {}, "skills": Counter(), "mcp_calls": Counter(), "subagents": 0}
    for e in evs:
        if e.get("type") == "assistant":
            for c in (e.get("message") or {}).get("content") or []:
                if c.get("type") != "tool_use":
                    continue
                name = c.get("name", "")
                if name == "Skill":
                    m["skills"][(c.get("input") or {}).get("skill", "?")] += 1
                elif name.startswith("mcp__"):
                    m["mcp_calls"][name.split("__")[1]] += 1
                elif name in ("Agent", "Task"):
                    m["subagents"] += 1
        if e.get("type") == "result":
            u = e.get("usage") or {}
            m["turns"] = e.get("num_turns")
            m["cost_usd"] = e.get("total_cost_usd")
            m["api_secs"] = round((e.get("duration_api_ms") or 0) / 1000)
            # `usage` on the result event covers only the last turn; modelUsage sums the
            # whole session, subagents included, per model.
            mu = e.get("modelUsage") or {}
            m["tokens"] = {
                "input": sum(x.get("inputTokens", 0) for x in mu.values()),
                "cache_write": sum(x.get("cacheCreationInputTokens", 0) for x in mu.values()),
                "cache_read": sum(x.get("cacheReadInputTokens", 0) for x in mu.values()),
                "output": sum(x.get("outputTokens", 0) for x in mu.values()),
            } if mu else {
                "input": u.get("input_tokens", 0),
                "cache_write": u.get("cache_creation_input_tokens", 0),
                "cache_read": u.get("cache_read_input_tokens", 0),
                "output": u.get("output_tokens", 0),
            }
            m["model_usage"] = mu
            m["is_error"] = e.get("is_error")
            m["final_text"] = (e.get("result") or "")[-4000:]
    return m


def codex_metrics(evs, model):
    tok = Counter(); turns = 0
    m = {"skills": Counter(), "mcp_calls": Counter(), "final_text": ""}
    for e in evs:
        if e.get("type") == "turn.completed":
            turns += 1
            for k, v in (e.get("usage") or {}).items():
                if isinstance(v, (int, float)):
                    tok[k] += v
        item = e.get("item") or {}
        if e.get("type") == "item.completed":
            t = item.get("type")
            if t == "mcp_tool_call":
                m["mcp_calls"][item.get("server", "?")] += 1
            elif t == "command_execution":
                cmd = item.get("command", "")
                if "/.agents/skills/" in cmd and "SKILL.md" in cmd:
                    name = cmd.split("/.agents/skills/")[1].split("/")[0]
                    m["skills"][name] += 1
            elif t == "agent_message":
                m["final_text"] = (item.get("text") or "")[-4000:]
    m["turns"] = turns
    m["tokens"] = {
        "input": tok["input_tokens"] - tok["cached_input_tokens"],
        "cache_read": tok["cached_input_tokens"],
        "output": tok["output_tokens"],
        "reasoning_in_output": tok["reasoning_output_tokens"],
    }
    p = PRICES.get(model) or {}
    if all(p.get(k) is not None for k in ("input", "cached_input", "output")):
        t = m["tokens"]
        m["cost_usd"] = round((t["input"] * p["input"] + t["cache_read"] * p["cached_input"] + t["output"] * p["output"]) / 1e6, 4)
    else:
        m["cost_usd"] = None
    return m


def repo_stats(work):
    def git(*a):
        r = subprocess.run(["git", "-C", work, *a], capture_output=True, text=True)
        return r.stdout.strip()
    commits = len(git("rev-list", "--all").splitlines()) if os.path.isdir(os.path.join(work, ".git")) else 0
    files = [f for f in git("ls-files").splitlines()
             if not f.startswith(("projects/", ".wos/")) and f not in ("CLAUDE.md", "AGENTS.md")]
    return {
        "commits": commits,
        "tracked_files": len(files),
        "fhorja_task_folder": os.path.isdir(os.path.join(work, "projects")),
    }


def main():
    rows = []
    for rid in sorted(os.listdir(RUNS)) if os.path.isdir(RUNS) else []:
        d = os.path.join(RUNS, rid)
        mp = os.path.join(d, "meta.json")
        if not os.path.exists(mp):
            continue
        meta = json.load(open(mp))
        evs = list(events(os.path.join(d, "events.jsonl")))
        m = claude_metrics(evs) if meta["cli"] == "claude" else codex_metrics(evs, meta["model"])
        if meta["cli"] == "codex":
            root_id = next((e.get("thread_id") for e in evs if e.get("type") == "thread.started"), "missing-root-id")
            session_dir = Path(ROOT) / "envs" / f"codex-{meta['arm']}" / "home" / ".codex" / "sessions"
            if str(session_dir) not in SESSION_CACHE:
                SESSION_CACHE[str(session_dir)] = discover(session_dir)
            sessions = dict(SESSION_CACHE[str(session_dir)])
            m["legacy_root_tokens"] = m["tokens"]
            if root_id in sessions and not sessions[root_id].get("model"):
                sessions[root_id] = {**sessions[root_id], "model": meta["model"]}
            accounting = ledger(sessions, root_id, PRICES, "2026-09-29")
            m["usage_ledger"] = accounting
            m["cost_usd"] = accounting["cost_usd"]
            u = accounting["observed_tokens"]
            m["tokens"] = {"input": u["input_tokens"] - u["cached_input_tokens"],
                           "cache_read": u["cached_input_tokens"], "output": u["output_tokens"],
                           "reasoning_in_output": accounting["observed_optional_tokens"]["reasoning_output_tokens"]}
            if root_id not in sessions:
                # Keep observed CLI tokens, but all-session cost remains unknown.
                m["tokens"] = m["legacy_root_tokens"]
            m["accounting_complete"] = accounting["complete"]
        m["metrics_version"] = 2
        m["skills"] = dict(m["skills"]); m["mcp_calls"] = dict(m["mcp_calls"])
        rows.append({**meta, **m, **repo_stats(os.path.join(d, "work"))})

    os.makedirs(RESULTS, exist_ok=True)
    json.dump(rows, open(os.path.join(RESULTS, "summary-v2.json"), "w"), indent=2)

    def mins(s): return f"{s/60:.1f}" if s is not None else "-"
    def usd(c): return f"{c:.2f}" if isinstance(c, (int, float)) else "n/d"
    lines = [
        "| run | wall (min) | turns | input | cache read | output | USD | Fhorja skills | MCP calls | commits | files | exit |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        t = r.get("tokens") or {}
        fh = sum(v for k, v in r["skills"].items() if k in FHORJA_SKILLS)
        lines.append(
            f"| {r['model']} {r['arm']} | {mins(r['wall_secs'])} | {r.get('turns') or '-'} | "
            f"{t.get('input', 0):,} | {t.get('cache_read', 0):,} | {t.get('output', 0):,} | {usd(r.get('cost_usd'))} | "
            f"{fh} | {sum(r['mcp_calls'].values())} | {r['commits']} | {r['tracked_files']} | "
            f"{'timeout' if r['timed_out'] else r['exit_code']} |"
        )
    open(os.path.join(RESULTS, "summary-v2.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
