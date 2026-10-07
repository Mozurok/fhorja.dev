#!/usr/bin/env python3
"""Version 3 scorer with independent domain inputs and explicit prospective binding."""
import argparse
import json
import math
from pathlib import Path

from attempt import canonical, same, strict_json, fixture, snapshot, validate_binding, verify, verify_evidence, write_new

WIDTHS = [320, 768, 1280, 2560]
EVALUATORS = [Path(__file__).with_name("behavior.py").resolve(),
              Path(__file__).with_name("attempt.py").resolve(), Path(__file__).resolve()]


def successful_rc(value):
    return type(value) is int and value == 0


def domain_coverage(behavior, cases_path, source_files, candidate_command):
    coverage = dict(csv=False, budget=False)
    try:
        canonical(behavior)
        allowed_fields = {"schema_version", "producer", "fixture_sha256", "candidate_command",
                          "timeout_seconds", "limits", "binding", "csv", "budget",
                          "error", "cleanup_incomplete", "passed", "completed"}
        spec, sha = fixture(cases_path, ("csv", "budget"))
        if (not isinstance(behavior, dict) or type(behavior.get("schema_version")) is not int
                or behavior["schema_version"] != 2 or behavior.get("producer") != "independent-harness"
                or not set(behavior) <= allowed_fields
                or "error" in behavior
                or ("cleanup_incomplete" in behavior and behavior["cleanup_incomplete"] is not False)
                or any(key in behavior and behavior[key] is not True for key in ("passed", "completed"))
                or behavior.get("fixture_sha256") != sha
                or candidate_command is None
                or not same(behavior.get("candidate_command"), candidate_command)
                or not validate_binding(behavior.get("binding"), cases_path, source_files, EVALUATORS, candidate_command)):
            return coverage
        for feature in coverage:
            expected = [c for c in spec["cases"] if c["feature"] == feature]
            evidence = behavior.get(feature)
            if (not isinstance(evidence, dict) or evidence.get("completed") is not True
                    or not set(evidence) <= {"completed", "cases", "passed", "error", "cleanup_incomplete"}
                    or ("passed" in evidence and evidence["passed"] is not True)
                    or "error" in evidence
                    or ("cleanup_incomplete" in evidence and evidence["cleanup_incomplete"] is not False)):
                continue
            rows = evidence.get("cases")
            if not isinstance(rows, list) or not expected or len(rows) != len(expected):
                continue
            coverage[feature] = all(
                isinstance(row, dict) and row.get("case_id") == case["case_id"]
                and row.get("executed") is True and row.get("passed") is True
                and successful_rc(row.get("exit_code")) and "error" not in row
                and ("cleanup_incomplete" not in row or row["cleanup_incomplete"] is False)
                and "expected" in row and "observed" in row
                and same(row["expected"], case["expected"]) and same(row["observed"], case["expected"])
                for row, case in zip(rows, expected))
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return coverage


def prospective_valid(prospective, source_files, exit_codes, browser, behavior, cases_path):
    try:
        artifacts = prospective["artifacts"]
        if not {"commands", "browser"} <= set(artifacts) or set(artifacts) - {"commands", "browser", "behavior"}:
            return False
        verify_evidence(prospective["receipt"], prospective["attempt"], artifacts, source_files)
        record = verify(prospective["attempt"], check_artifacts=False)
        if (not snapshot(EVALUATORS).items() <= record["artifacts"]["scorer"].items()
                or not same(snapshot([cases_path]), record["artifacts"]["cases"])):
            return False
        for name, value in (("browser", browser), ("behavior", behavior)):
            if name in artifacts:
                if len(artifacts[name]) != 1 or not same(strict_json(Path(artifacts[name][0]).read_bytes()), value):
                    return False
            elif value is not None:
                return False
        observed = {}
        for path in artifacts["commands"]:
            path = Path(path)
            if path.suffix != ".rc" or path.stem in observed:
                return False
            observed[path.stem] = strict_json(path.read_bytes())
        return set(observed) == set(exit_codes) and same(observed, exit_codes)
    except (OSError, ValueError, TypeError, KeyError):
        return False


def score(exit_codes, browser=None, behavior=None, *, cases_path=None, source_files=None, candidate_command=None, prospective=None):
    missing = []
    exit_codes = exit_codes if isinstance(exit_codes, dict) else {}
    b = browser if isinstance(browser, dict) else {}
    try:
        canonical(b)
    except (TypeError, ValueError):
        b = {}
    routes = b.get("routes", [])
    routes = routes if isinstance(routes, list) else []
    expected = b.get("expectedRoutes", [])
    actual = [r.get("route") for r in routes if isinstance(r, dict)]
    complete = (
        type(b.get("schemaVersion")) is int and b["schemaVersion"] == 2
        and ("fatal" not in b or b["fatal"] is False)
        and "error" not in b and ("cleanup_incomplete" not in b or b["cleanup_incomplete"] is False)
        and isinstance(expected, list) and bool(expected) and "/" in expected
        and all(isinstance(r, str) and bool(r) for r in expected + actual)
        and len(expected) == len(set(expected)) and len(actual) == len(routes)
        and len(actual) == len(set(actual)) and set(actual) == set(expected)
        and all(r.get("ok") is True and type(r.get("status")) is int
                and 200 <= r["status"] < 300 and "error" not in r
                and ("cleanup_incomplete" not in r or r["cleanup_incomplete"] is False) for r in routes)
        and isinstance(b.get("consoleErrors"), list))
    if not complete:
        missing.append("completed successful route and console probes")
    widths = b.get("widthProbes", {})
    widths = widths if isinstance(widths, dict) else {}
    width_ok = complete and same(b.get("requestedWidths"), WIDTHS) and set(widths) == set(expected) and all(
        isinstance(widths[r], list) and all(type(w) is int for w in widths[r])
        and sorted(widths[r]) == WIDTHS for r in expected) and isinstance(b.get("overflow"), list)
    if not width_ok:
        missing.append("all requested viewport probes")
    axe = b.get("axe", {})
    done = b.get("axeCompleted", [])
    axe_ok = (complete and isinstance(axe, dict) and set(axe) == set(expected)
              and isinstance(done, list) and all(isinstance(r, str) for r in done)
              and len(done) == len(expected) and set(done) == set(expected)
              and all(isinstance(axe[r], list) for r in expected))
    if not axe_ok:
        missing.append("completed axe probes")
    coverage = domain_coverage(behavior, cases_path, source_files or [], candidate_command)
    if not all(coverage.values()):
        missing.append("independently selected fixture, cases and unchanged source behavior assertions")
    bound = prospective is not None and prospective_valid(prospective, source_files or [], exit_codes, browser, behavior, cases_path)
    if prospective is not None and not bound:
        missing.append("matching prospective attempt and captured evidence")
    lh = b.get("lighthouse", {})
    lh = lh if isinstance(lh, dict) else {}
    lh_success = (complete and bool(lh) and "error" not in lh
                  and all(key not in lh or lh[key] is True for key in ("completed", "passed"))
                  and ("cleanup_incomplete" not in lh or lh["cleanup_incomplete"] is False))
    if not lh_success:
        missing.append("successful Lighthouse probe")
    def threshold(key, value):
        v = lh.get(key)
        return lh_success and type(v) in (int, float) and value <= v <= 100 and math.isfinite(v)
    scores = {
        "build": 5 if successful_rc(exit_codes.get("build")) else 0,
        "typecheck": 3 if successful_rc(exit_codes.get("typecheck")) else 0,
        "lint": 2 if successful_rc(exit_codes.get("lint")) else 0,
        "test": (3 if all(coverage.values()) else 1.5) if successful_rc(exit_codes.get("test")) else 0,
        "console": 2 if complete and not b["consoleErrors"] else 0,
        "overflow": 2 if width_ok and not b["overflow"] else 0,
        "axe": 1 if axe_ok and not any(axe[r] for r in expected) else 0,
        "lighthouse": int(complete and threshold("performance", 80)) + int(complete and threshold("accessibility", 90)),
    }
    if prospective is not None and not bound:
        scores = dict.fromkeys(scores, 0)
        coverage = dict.fromkeys(coverage, False)
        complete = width_ok = axe_ok = False
    return {
        "scorer_version": 3, "exit_codes": exit_codes,
        "tests_cover_csv": coverage["csv"], "tests_cover_budget": coverage["budget"],
        "browser_completed": complete, "viewport_completed": width_ok, "axe_completed": axe_ok,
        "demo_loaded": b.get("demoLoaded") is True,
        "demo_verification": b.get("demoVerification", "unverified"),
        "provenance_status": "bound" if bound else "invalid" if prospective is not None else "unbound",
        "attempt_id": prospective["attempt"]["attempt_id"] if bound else None,
        "missing_evidence": missing, "score_a": scores, "total_a": sum(scores.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quality_dir", type=Path)
    parser.add_argument("app", type=Path)
    parser.add_argument("package_manager")
    parser.add_argument("dirty", type=int)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--prospective", type=Path, help="independently held attempt and receipt bindings")
    parser.add_argument("--candidate-command", type=Path, help="independently held JSON argv for domain evaluation")
    args = parser.parse_args()
    rc = {}
    for name in ("install", "build", "typecheck", "lint", "test"):
        try:
            value = strict_json((args.quality_dir / "logs" / f"{name}.rc").read_bytes())
            rc[name] = value if type(value) is int else None
        except (OSError, ValueError):
            rc[name] = None
    def read(name):
        try:
            return strict_json((args.quality_dir / name).read_bytes())
        except (OSError, ValueError):
            return None
    prospective = strict_json(args.prospective.read_bytes()) if args.prospective else None
    candidate_command = strict_json(args.candidate_command.read_bytes()) if args.candidate_command else None
    out = score(rc, read("browser.json"), read("behavior.json"), cases_path=args.cases,
                source_files=args.source, candidate_command=candidate_command, prospective=prospective)
    out.update(package_manager=args.package_manager, uncommitted_changes=args.dirty)
    write_new(args.quality_dir / "auto-v3.json", out)
    print(json.dumps(out, allow_nan=False))


if __name__ == "__main__":
    main()
