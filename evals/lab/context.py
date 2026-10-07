#!/usr/bin/env python3
"""Opt-in context package experiment. Markdown remains canonical."""
import argparse
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sections(text):
    """H2 boundaries outside backtick/tilde fences; preserve preamble and full text."""
    lines = text.splitlines(keepends=True)
    starts, fence = [(0, "@preamble")], None
    for n, line in enumerate(lines):
        m = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if m:
            mark = m[1]
            if fence is None:
                fence = (mark[0], len(mark))
            elif mark[0] == fence[0] and len(mark) >= fence[1] and not m[2].strip():
                fence = None
            continue
        if fence is None and re.match(r"^##\s+\S", line):
            starts.append((n, line.strip()))
    result = []
    counts = {}
    for i, (start, heading) in enumerate(starts):
        end = starts[i+1][0] if i+1 < len(starts) else len(lines)
        if start == end:
            continue
        counts[heading] = counts.get(heading, 0) + 1
        result.append({"heading": heading, "occurrence": counts[heading], "line": start+1,
                       "text": "".join(lines[start:end])})
    return result


def load(root, manifest):
    root = Path(root).resolve()
    if len({n["id"] for n in manifest["nodes"]}) != len(manifest["nodes"]):
        raise ValueError("duplicate node id")
    documents, nodes, errors = {}, {}, []
    for spec in manifest["nodes"]:
        p = (root/spec["path"]).resolve()
        if not p.is_relative_to(root):
            raise ValueError("source escapes root")
        if spec["path"] not in documents:
            try:
                text = p.read_text()
                documents[spec["path"]] = {"sha256": digest(text), "text": text, "sections": sections(text)}
            except (OSError, UnicodeError):
                documents[spec["path"]] = None
        doc = documents[spec["path"]]
        if doc is None:
            errors.append(f"missing source: {spec['id']}")
            continue
        candidates = [s for s in doc["sections"] if s["heading"] == spec["section"]]
        if "occurrence" in spec:
            candidates = [s for s in candidates if s["occurrence"] == spec["occurrence"]]
        if len(candidates) != 1:
            errors.append(f"missing or ambiguous section: {spec['id']}")
            continue
        nodes[spec["id"]] = {**spec, **candidates[0], "sha256": doc["sha256"]}
    return documents, nodes, errors


def closure(manifest, required, nodes):
    replacement, dependencies = {}, {}
    for new, old in manifest.get("supersedes", []):
        if old in replacement and replacement[old] != new:
            raise ValueError("conflicting supersession")
        replacement[old] = new
    for parent, child in manifest.get("requires", []):
        dependencies.setdefault(parent, []).append(child)
    included, reasons, errors = set(), {}, []
    def latest(n):
        seen = set()
        while n in replacement:
            if n in seen:
                raise ValueError("supersession cycle")
            seen.add(n); n = replacement[n]
        return n
    def visit(n, reason):
        n = latest(n)
        reasons.setdefault(n, []).append(reason)
        if n in included:
            return
        included.add(n)
        if n not in nodes:
            errors.append(f"missing required node: {n}")
            return
        for child in sorted(dependencies.get(n, [])):
            visit(child, f"required by {n}")
    for n in required:
        visit(n, "explicit required context")
    # Validate edges even when they are outside the requested closure.
    declared = {n["id"] for n in manifest["nodes"]}
    for ident in declared:
        latest(ident)
    for parent, child in manifest.get("requires", []) + manifest.get("supersedes", []):
        if parent not in declared or child not in declared:
            errors.append(f"dangling manifest edge: {parent} -> {child}")
    return sorted(included), reasons, sorted(set(errors)), set(replacement)


def terms(text):
    return re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)


def lexical_candidates(nodes, query, excluded, limit):
    wanted = set(terms(query))
    ranked = []
    for ident, n in nodes.items():
        if ident in excluded:
            continue
        words = set(terms(n["text"]))
        score = len(wanted & words)
        if score:
            ranked.append((ident, score))
    return [n for n, _ in sorted(ranked, key=lambda r: (-r[1], r[0]))[:limit]]


def build_index(path, manifest, documents, nodes):
    """Rebuild a disposable index; caller supplies a task-local output path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("DROP TABLE IF EXISTS meta; DROP TABLE IF EXISTS passages; DROP TABLE IF EXISTS search;"
                         "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);"
                         "CREATE TABLE passages (id TEXT PRIMARY KEY, body TEXT);"
                         "CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, text, tokenize='unicode61 remove_diacritics 0');")
        db.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("version", "1"), ("manifest", digest(json.dumps(manifest, sort_keys=True))),
            ("sources", json.dumps({p: d["sha256"] if d else None for p, d in documents.items()}, sort_keys=True))])
        db.executemany("INSERT INTO passages VALUES (?, ?)", [(i, json.dumps(n, ensure_ascii=False)) for i, n in nodes.items()])
        db.executemany("INSERT INTO search VALUES (?, ?)", [(i, n["text"]) for i, n in nodes.items()])


def package(root, manifest, query, required, budget=20000, limit=8, backend="files", index=None):
    if budget < 0 or limit < 0:
        raise ValueError("budget and limit must be nonnegative")
    documents, nodes, errors = load(root, manifest)
    required_ids, reasons, closure_errors, obsolete = closure(manifest, required, nodes)
    errors.extend(closure_errors)
    fallback, indexed = None, None
    excluded = set(required_ids) | obsolete
    candidate_ids = lexical_candidates(nodes, query, excluded, limit)
    if backend == "sqlite":
        try:
            if index is None or not Path(index).is_file():
                raise ValueError("missing index")
            uri = Path(index).resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as db:
                metadata = dict(db.execute("SELECT key, value FROM meta"))
                current = json.dumps({p: d["sha256"] if d else None for p, d in documents.items()}, sort_keys=True)
                if metadata.get("version") != "1" or metadata.get("sources") != current or metadata.get("manifest") != digest(json.dumps(manifest, sort_keys=True)):
                    raise ValueError("stale index")
                indexed = {i: json.loads(body) for i, body in db.execute("SELECT id, body FROM passages")}
                if indexed != nodes:
                    raise ValueError("index content mismatch")
                q = " OR ".join('"' + t.replace('"', '""') + '"' for t in sorted(set(terms(query))))
                matches = {row[0] for row in db.execute("SELECT id FROM search WHERE search MATCH ?", (q,))} if q else set()
                # Common score makes the index comparison independent of ranking.
                ids = lexical_candidates({i: nodes[i] for i in matches}, query, excluded, limit)
                if ids != candidate_ids:
                    raise ValueError("tokenizer candidate mismatch")
                candidate_ids = ids
        except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            fallback = str(exc)
    elif backend != "files":
        raise ValueError("unknown backend")
    selected = []
    for ident in required_ids:
        if ident in nodes:
            selected.append({**nodes[ident], "required": True, "inclusion": reasons[ident]})
    required_body_chars = sum(len(n["text"]) for n in selected)
    required_chars = len(json.dumps(selected, ensure_ascii=False))
    used = required_chars
    for ident in candidate_ids:
        bundle, bundle_reasons, bundle_errors, _ = closure(manifest, [ident], nodes)
        errors.extend(bundle_errors)
        if bundle_errors:
            continue
        present = {n["id"] for n in selected}
        additions = [{**nodes[i], "required": False,
                      "inclusion": ["optional lexical match"] if i == ident else bundle_reasons[i]}
                     for i in bundle if i not in present]
        size = len(json.dumps(selected + additions, ensure_ascii=False))
        if size <= budget:
            selected.extend(additions)
            used = size
    return {"schema_version": 1, "backend": backend, "fallback": fallback,
            "source_hashes": {p: d["sha256"] if d else None for p, d in documents.items()},
            "manifest_hash": digest(json.dumps(manifest, sort_keys=True)),
            "required_ids": required_ids, "candidate_ids": candidate_ids,
            "candidate_hash": digest(json.dumps([(i, digest(nodes[i]["text"])) for i in candidate_ids])),
            "passages": selected, "required_chars": required_chars,
            "required_body_chars": required_body_chars, "selected_payload_chars": used,
            "budget_chars": budget, "budget_exceeded": required_chars > budget,
            "complete": not errors, "errors": sorted(set(errors)),
            "limits": ["Budget covers serialized passages; envelope metadata is separate.",
                       "Character budget is not a model-token budget.", "Index validation reads canonical sources."]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path); p.add_argument("manifest", type=Path)
    p.add_argument("query"); p.add_argument("--required", action="append", default=[])
    p.add_argument("--backend", choices=["files", "sqlite"], default="files")
    p.add_argument("--index", type=Path); p.add_argument("--build", action="store_true")
    p.add_argument("--budget", type=int, default=20000)
    a = p.parse_args(); m = json.loads(a.manifest.read_text())
    if a.build:
        if a.index is None:
            p.error("--build requires --index")
        documents, nodes, errors = load(a.root, m)
        if errors:
            p.error("; ".join(errors))
        build_index(a.index, m, documents, nodes)
    print(json.dumps(package(a.root, m, a.query, a.required, a.budget, backend=a.backend, index=a.index), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
