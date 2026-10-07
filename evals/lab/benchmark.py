#!/usr/bin/env python3
"""Measure current full payload versus identical file/SQLite context packages."""
import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from context import load, build_index, package


def compare(root, manifest, index, queries, required, repeats=5, budget=20000):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    start = time.perf_counter()
    documents, nodes, errors = load(root, manifest)
    if errors:
        raise ValueError("; ".join(errors))
    build_index(index, manifest, documents, nodes)
    setup = time.perf_counter()-start
    full_chars = sum(len(d["text"]) for d in documents.values())
    full_bytes = sum(len(d["text"].encode()) for d in documents.values())
    rows = []
    for query in queries:
        packages, timings = {}, {}
        reference = package(root, manifest, query, required, budget)
        matched_paths = sorted({p["path"] for p in reference["passages"]})
        matched_chars = sum(len(documents[p]["text"]) for p in matched_paths)
        for arm in ["full", "matched-files", "files", "sqlite"]:
            durations = []
            for _ in range(repeats):
                start = time.perf_counter()
                if arm in ("full", "matched-files"):
                    # Fresh reads, same canonical sources, no package selection.
                    paths = sorted(documents) if arm == "full" else matched_paths
                    result = "".join((Path(root)/p).read_text() for p in paths)
                else:
                    result = package(root, manifest, query, required, budget, backend=arm, index=index)
                duration = time.perf_counter()-start
                if arm in ("files", "sqlite"):
                    keys = ["passages", "required_ids", "candidate_ids", "candidate_hash"]
                    if (not result["complete"] or result["fallback"] or
                            any(result[k] != reference[k] for k in keys)):
                        raise ValueError("backend comparison invalid sample: parity, missing context or fallback")
                durations.append(duration)
            packages[arm] = result
            timings[arm] = {"samples_seconds": durations, "median_seconds": statistics.median(durations)}
        a, b = packages["files"], packages["sqlite"]
        same = all(a[k] == b[k] for k in ["passages", "required_ids", "candidate_ids", "candidate_hash"])
        if not same or not a["complete"] or not b["complete"] or b["fallback"]:
            raise ValueError("backend comparison invalid: parity, missing context or fallback")
        # Transport metadata differs; compare the common selected payload separately.
        payload = json.dumps(a["passages"], ensure_ascii=False)
        rows.append({"query": query, "parity": same, "timings": timings,
                     "full_source_chars": full_chars, "full_source_bytes": full_bytes,
                     "matched_full_file_chars": matched_chars, "matched_source_paths": matched_paths,
                     "selected_payload_chars": len(payload), "selected_payload_bytes": len(payload.encode()),
                     "selected_payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                     "required_ids": a["required_ids"], "candidate_ids": a["candidate_ids"],
                     "budget_exceeded": a["budget_exceeded"], "required_chars": a["required_chars"]})
    return {"schema_version": 1, "index_setup_seconds": setup, "repeats": repeats,
            "source_hashes": {p: d["sha256"] for p, d in documents.items()}, "rows": rows,
            "selection": "No backend promoted by this diagnostic; SQL must earn its extra maintenance.",
            "limits": ["Local retrieval latency, not model prefill or accepted-delivery latency.",
                       "Character and byte sizes, not observed model tokens.",
                       "Full corpus dump is a naive bound; matched-files uses the same selected document identities.",
                       "Native agents may already read sections selectively; this does not measure their actual context.",
                       "Strict freshness validation reads all indexed canonical sources."]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path); p.add_argument("manifest", type=Path)
    p.add_argument("--index", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p.add_argument("--query", action="append", required=True)
    p.add_argument("--required", action="append", default=[])
    p.add_argument("--repeats", type=int, default=5); p.add_argument("--budget", type=int, default=20000)
    a = p.parse_args()
    result = compare(a.root, json.loads(a.manifest.read_text()), a.index, a.query, a.required, a.repeats, a.budget)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
