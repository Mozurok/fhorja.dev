#!/usr/bin/env python3
"""Whole-session ledger over explicit session links; never add two usage views."""
import argparse
import hashlib
import json
import math
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")
OPTIONAL_FIELDS = ("cache_write_input_tokens", "reasoning_output_tokens")


def read_events(path):
    events, errors = [], []
    try:
        lines = Path(path).read_text().splitlines()
    except OSError as exc:
        return [], [str(exc)]
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            if not isinstance(e, dict):
                raise ValueError("event is not an object")
            events.append(e)
        except ValueError:
            errors.append(f"{Path(path).name}:{n}: malformed event")
    return events, errors


def valid_usage(u):
    return (isinstance(u, dict) and all(isinstance(u.get(k), int)
            and not isinstance(u[k], bool) and u[k] >= 0 for k in FIELDS)
            and u["cached_input_tokens"] <= u["input_tokens"]
            and all(k not in u or (isinstance(u[k], int) and not isinstance(u[k], bool)
                    and u[k] >= 0) for k in OPTIONAL_FIELDS))


def compaction_reconciles(events, rows, snapshots):
    compact = [r for r in rows if r["usage_category"] == "compaction"]
    if not compact:
        return False
    ordinary = [r for r in rows if r["usage_category"] != "compaction"]
    last_call = next((e for e in reversed(events)
                      if e.get("type") == "token_usage_record"), {})
    payload = last_call.get("payload")
    thread = payload.get("thread_token_usage") if isinstance(payload, dict) else None
    if not valid_usage(thread):
        return False
    fields = list(FIELDS) + [k for k in OPTIONAL_FIELDS
                            if k in thread or any(k in r["usage"] for r in rows + snapshots)]
    if any(k not in thread or any(k not in r["usage"] for r in rows + snapshots)
           for k in fields):
        return False
    return all(sum(r["usage"][k] for r in rows) == thread[k]
               and sum(r["usage"][k] for r in ordinary) ==
               sum(r["usage"][k] for r in snapshots) for k in fields)


def session_records(events, session_id, default_model=None):
    """Prefer call records; cumulative token_count is a separate fallback view."""
    issues, rows, seen = [], [], {}
    thread_evidence, row_by_id = {}, {}
    has_calls = any(e.get("type") == "token_usage_record" for e in events)
    model = default_model
    previous = dict.fromkeys(FIELDS, 0)
    optional_previous = dict.fromkeys(OPTIONAL_FIELDS, 0)
    epoch = 0
    for n, e in enumerate(events):
        p = e.get("payload") or {}
        if not isinstance(p, dict):
            issues.append(f"{session_id}: malformed event payload at {n}")
            continue
        if e.get("type") in ("session_meta", "turn_context"):
            model = p.get("model") or model
        if e.get("type") == "compacted":
            # Compaction is not evidence that provider usage counters reset.
            pass
        kind = None
        identity_scope = "session"
        if has_calls and e.get("type") == "token_usage_record":
            u = p.get("usage")
            ident = p.get("response_id") or p.get("request_id") or p.get("call_id") or e.get("id")
            if ident is not None:
                identity_scope = "provider"
            if ident is None:
                if not e.get("timestamp"):
                    issues.append(f"{session_id}: call has no stable identity at {n}")
                    continue
                ident = e["timestamp"] + ":" + hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
            kind = "call"
        elif not has_calls and p.get("type") == "token_count":
            info = p.get("info") or {}
            u = info.get("total_token_usage") if isinstance(info, dict) else None
            if u is None:
                issues.append(f"{session_id}: token_count has no cumulative total")
                continue
            kind = "cumulative"
        else:
            continue
        if not valid_usage(u):
            issues.append(f"{session_id}: incomplete or invalid {kind} usage at {n}")
            continue
        chosen_model = p.get("model") or model
        if kind == "cumulative":
            if any(u[k] < previous[k] for k in FIELDS):
                issues.append(f"{session_id}: cumulative counter decreased; reset boundary unverified")
                epoch += 1
                previous = dict.fromkeys(FIELDS, 0)
                optional_previous = dict.fromkeys(OPTIONAL_FIELDS, 0)
            delta = {k: u[k] - previous[k] for k in FIELDS}
            previous = {k: u[k] for k in FIELDS}
            for key in OPTIONAL_FIELDS:
                if key in u:
                    if u[key] < optional_previous[key]:
                        issues.append(f"{session_id}: optional cumulative counter decreased: {key}")
                    delta[key] = u[key] - optional_previous[key]
                    optional_previous[key] = u[key]
            if not any(delta.values()):
                continue
            if not valid_usage(delta):
                issues.append(f"{session_id}: inconsistent cumulative delta")
                continue
            u = delta
            ident = f"cumulative:{epoch}:{n}"
        key = str(ident)
        category = "compaction" if kind == "call" and n + 1 < len(events) and \
            events[n + 1].get("type") == "compacted" else "ordinary"
        if kind == "call" and "thread_token_usage" in p:
            thread = p["thread_token_usage"]
            if not valid_usage(thread):
                issues.append(f"{session_id}: invalid thread usage evidence for {key}")
            else:
                attestation = json.dumps(thread, sort_keys=True)
                if key in thread_evidence and thread_evidence[key] != attestation:
                    issues.append(f"{session_id}: conflicting duplicate thread usage for {key}")
                thread_evidence[key] = attestation
        canonical = json.dumps({"usage": u, "model": chosen_model}, sort_keys=True)
        if key in seen:
            if seen[key] != canonical:
                issues.append(f"{session_id}: conflicting duplicate call {key}")
            elif category == "compaction":
                row_by_id[key]["usage_category"] = category
            continue
        seen[key] = canonical
        rows.append({"session_id": session_id, "call_id": key, "model": chosen_model,
                     "usage": u, "source_view": kind, "timestamp": e.get("timestamp"),
                     "identity_scope": identity_scope,
                     "usage_category": category})
        row_by_id[key] = rows[-1]
    if not rows:
        issues.append(f"{session_id}: no usable usage records")
    cumulative = [e for e in events if isinstance(e.get("payload"), dict)
                  and e["payload"].get("type") == "token_count"]
    if has_calls and cumulative:
        snapshots, snapshot_issues = session_records(cumulative, session_id, default_model)
        issues.extend(snapshot_issues)
        call_totals = {k: sum(r["usage"][k] for r in rows) for k in FIELDS}
        snapshot_totals = {k: sum(r["usage"][k] for r in snapshots) for k in FIELDS}
        reconciled_compaction = compaction_reconciles(events, rows, snapshots)
        if call_totals != snapshot_totals and not reconciled_compaction:
            issues.append(f"{session_id}: call and cumulative usage views do not reconcile")
        if reconciled_compaction:
            for row in rows:
                if row["usage_category"] == "compaction":
                    row["cumulative_reconciliation"] = "compaction-excluded-attested"
        for key in OPTIONAL_FIELDS:
            if any(r["usage"].get(key, 0) for r in snapshots):
                if not reconciled_compaction and (any(key not in r["usage"] for r in rows) or
                        sum(r["usage"].get(key, 0) for r in rows) !=
                        sum(r["usage"].get(key, 0) for r in snapshots)):
                    issues.append(f"{session_id}: optional usage views do not reconcile: {key}")
    return rows, sorted(set(issues))


def ledger(sessions, root_id, prices, pricing_date=None, declared_children=()):
    """sessions maps ID to parent/model/events/errors/hash. Only linked nodes count."""
    issues, selected = [], {root_id}
    changed = True
    while changed:
        changed = False
        for sid, s in sessions.items():
            if sid not in selected and s.get("parent") in selected:
                selected.add(sid); changed = True
    for child in declared_children:
        if child not in selected:
            issues.append(f"missing declared child session: {child}")
    records, hashes = [], {}
    for sid in sorted(selected):
        if sid not in sessions:
            issues.append(f"missing session: {sid}")
            continue
        s = sessions[sid]
        issues.extend(s.get("errors", []))
        rows, errors = session_records(s.get("events", []), sid, s.get("model"))
        records.extend(rows); issues.extend(errors)
        hashes[sid] = s.get("sha256")
    unique, seen = [], {}
    for row in records:
        key = (row["call_id"] if row["identity_scope"] == "provider" else
               (row["session_id"], row["call_id"]))
        canonical = json.dumps({"usage": row["usage"], "model": row["model"]}, sort_keys=True)
        if key in seen:
            if seen[key] != canonical:
                issues.append(f"conflicting duplicate usage across sessions: {row['call_id']}")
            continue
        seen[key] = canonical
        unique.append(row)
    records = unique
    totals = dict.fromkeys(FIELDS, 0)
    observed_cost = 0.0
    optional_totals = {"cache_write_input_tokens": 0, "reasoning_output_tokens": 0}
    for row in records:
        u = row["usage"]
        for k in FIELDS:
            totals[k] += u[k]
        for k in optional_totals:
            if k not in u or optional_totals[k] is None:
                optional_totals[k] = None
            else:
                optional_totals[k] += u[k]
        if u.get("cache_write_input_tokens", 0):
            issues.append("nonzero cache-write pricing semantics unavailable")
        p = prices.get(row["model"]) if isinstance(prices, dict) and isinstance(row["model"], str) else None
        p = p if isinstance(p, dict) else {}
        keys = ("input", "cached_input", "output")
        if not all(isinstance(p.get(k), (int, float)) and not isinstance(p[k], bool)
                   and math.isfinite(p[k]) and p[k] >= 0 for k in keys):
            issues.append(f"unknown pricing: {row['model']}")
            row["cost_usd"] = None
        else:
            cost = ((u["input_tokens"] - u["cached_input_tokens"]) * p["input"]
                    + u["cached_input_tokens"] * p["cached_input"]
                    + u["output_tokens"] * p["output"]) / 1e6
            row["cost_usd"] = cost; observed_cost += cost
    if not pricing_date:
        issues.append("pricing date unavailable")
    issues = sorted(set(issues))
    compactions = [r for r in records if r["usage_category"] == "compaction"]
    reconciliations = [{"session_id": sid, "kind": "compaction-excluded-attested",
                        "proof": "All calls match thread usage; ordinary calls match cumulative usage."}
                       for sid in sorted({r["session_id"] for r in compactions
                                          if r.get("cumulative_reconciliation")})]
    return {"ledger_version": 2, "root_session": root_id,
            "sessions": sorted(selected), "session_graph": {sid: sessions.get(sid, {}).get("parent") for sid in sorted(selected)},
            "raw_sha256": hashes, "pricing_date": pricing_date, "rates": prices,
            "records": records, "observed_tokens": totals,
            "compaction_tokens": {k: sum(r["usage"][k] for r in compactions) for k in FIELDS},
            "reconciliations": reconciliations,
            "observed_optional_tokens": optional_totals,
            "observed_priced_cost_usd": observed_cost, "cost_usd": None if issues else observed_cost,
            "complete": not issues, "issues": issues,
            "limits": ["Undeclared missing descendants cannot be proven absent from available traces.",
                       "Token-equivalent cost is not a provider invoice or human/compute cost."]}


def discover(session_dir):
    sessions = {}
    for path in sorted(Path(session_dir).rglob("*.jsonl")):
        events, errors = read_events(path)
        meta = next((e.get("payload", {}) for e in events if e.get("type") == "session_meta"), {})
        sid = meta.get("id")
        if not sid:
            continue
        entry = {"parent": meta.get("parent_thread_id"), "model": meta.get("model"),
                 "events": events, "errors": errors,
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if sid in sessions:
            if sessions[sid]["sha256"] != entry["sha256"]:
                sessions[sid]["errors"].append(f"conflicting session copies: {sid}")
        else:
            sessions[sid] = entry
    return sessions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("session_dir", type=Path); p.add_argument("root_id")
    p.add_argument("--prices", type=Path, required=True)
    p.add_argument("--pricing-date", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expect-child", action="append", default=[])
    a = p.parse_args()
    result = ledger(discover(a.session_dir), a.root_id, json.loads(a.prices.read_text()), a.pricing_date, a.expect_child)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["complete", "sessions", "observed_tokens", "cost_usd", "issues"]}))


if __name__ == "__main__":
    main()
