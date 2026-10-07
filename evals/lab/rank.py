#!/usr/bin/env python3
"""Frozen-pool ranking comparison; learned imports are optional and local."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import time
from pathlib import Path

from context import terms


def candidate_hash(candidates):
    return hashlib.sha256(json.dumps([(p["id"], p["text"]) for p in candidates], ensure_ascii=False).encode()).hexdigest()


def ordered(candidates, scores):
    try:
        scores = [float(s) for s in scores]
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid ranking score type") from exc
    if len(scores) != len(candidates) or any(not math.isfinite(s) for s in scores):
        raise ValueError("invalid or incomplete ranking scores")
    return [p["id"] for p, _ in sorted(zip(candidates, scores), key=lambda r: (-float(r[1]), r[0]["id"]))]


def metrics(ranking, relevant, k=2):
    relevant = set(relevant)
    found = ranking[:k]
    recall = len(set(found) & relevant)/len(relevant) if relevant else None
    dcg = sum(1/math.log2(n+2) for n, ident in enumerate(found) if ident in relevant)
    ideal = sum(1/math.log2(n+2) for n in range(min(k, len(relevant))))
    return {"recall_at_2": recall, "ndcg_at_2": dcg/ideal if ideal else None,
            "top1_relevant": bool(ranking and ranking[0] in relevant)}


def lexical(query, candidates):
    q = set(terms(query))
    return [len(q & set(terms(p["text"]))) for p in candidates]


def load_ranker(arm, model=None, revision=None):
    start = time.perf_counter()
    if arm == "deterministic":
        revision = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        return lexical, {"arm": arm, "revision": revision, "setup_seconds": time.perf_counter()-start}
    if not model or not revision:
        raise ValueError("learned arms require explicit model and revision")
    if arm == "laya":
        import laya
        agent = laya.load(model, device="cpu", revision=revision)
        def score(query, candidates):
            values = []
            for passage in candidates:
                question = {"relevance": {"type": "noul", "instructions":
                    "Does this passage contain information useful for answering this request? Request: " + query}}
                result = agent.predict(passage["text"], question, max_len=1024)
                values.append(float(result["answers"]["relevance"]["noul"]))
            return values
        metadata = {"package": importlib.metadata.version("laya"), "resolved_revision": agent.revision}
    elif arm == "cross-encoder":
        from sentence_transformers import CrossEncoder
        encoder = CrossEncoder(model, revision=revision, device="cpu", max_length=512, trust_remote_code=False)
        def score(query, candidates):
            values = encoder.predict([(query, p["text"]) for p in candidates], batch_size=8, show_progress_bar=False)
            return [float(v) for v in values]
        metadata = {"package": importlib.metadata.version("sentence-transformers")}
    else:
        raise ValueError("unknown arm")
    return score, {"arm": arm, "model": model, "revision": revision,
                   "setup_seconds": time.perf_counter()-start, "device": "cpu", **metadata}


def compare(cases, arm, model=None, revision=None, scorer=None):
    metadata = {"arm": arm}
    try:
        for case in cases:
            ids = [p["id"] for p in case["candidates"]]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate candidate id")
            if set(ids) & set(case.get("required_ids", [])):
                raise ValueError("required context overlaps optional pool")
            if not case["relevant_ids"] or not set(case["relevant_ids"]).issubset(ids):
                raise ValueError("missing or unknown relevance labels")
        if scorer is None:
            scorer, metadata = load_ranker(arm, model, revision)
        if cases:
            warm_hash = candidate_hash(cases[0]["candidates"])
            t = time.perf_counter()
            scorer(cases[0]["query"], cases[0]["candidates"])
            metadata["first_inference_seconds"] = time.perf_counter()-t
            if warm_hash != candidate_hash(cases[0]["candidates"]):
                raise ValueError("ranker mutated warm-up candidate pool")
        rows = []
        for case in cases:
            before = candidate_hash(case["candidates"])
            start = time.perf_counter()
            values = scorer(case["query"], case["candidates"])
            duration = time.perf_counter()-start
            if before != candidate_hash(case["candidates"]):
                raise ValueError("ranker mutated candidate pool")
            ranking = ordered(case["candidates"], values)
            # Required context is outside the pool and is copied unchanged.
            rows.append({"case": case["id"], "language": case["language"],
                         "candidate_hash": before, "required_ids": list(case.get("required_ids", [])),
                         "scores": [float(v) for v in values], "ranking": ranking,
                         "warm_inference_seconds": duration,
                         **metrics(ranking, case["relevant_ids"])})
        return {"status": "measured", **metadata, "rows": rows,
                "limits": ["Diagnostic development fixtures, not held-out product outcomes.",
                           "Required context is invariant; ranking operates only on the optional pool."]}
    except (ImportError, OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        return {"status": "unavailable", **metadata, "error": str(exc), "rows": []}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cases", type=Path)
    p.add_argument("--arm", choices=["deterministic", "laya", "cross-encoder"], required=True)
    p.add_argument("--model"); p.add_argument("--revision")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); cases = json.loads(a.cases.read_text())["cases"]
    result = compare(cases, a.arm, a.model, a.revision)
    result.update(python=platform.python_version(), architecture=platform.machine(),
                  fixture_sha256=hashlib.sha256(a.cases.read_bytes()).hexdigest())
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    summary = {k: result.get(k) for k in ["status", "arm", "model", "setup_seconds", "first_inference_seconds", "error"]}
    if result["rows"]:
        summary["mean_recall_at_2"] = sum(r["recall_at_2"] for r in result["rows"])/len(result["rows"])
        summary["mean_warm_seconds"] = sum(r["warm_inference_seconds"] for r in result["rows"])/len(result["rows"])
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
