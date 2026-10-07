import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from context import sections, load, build_index, package


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.text = "# Intro\nPreamble retained\n## Rule\nRequired exception with no query word.\n```md\n## fake\n```\n## Detail\ncache context detail\n## Old\ncache obsolete rule\n## New\nReplacement exception\n"
        (self.root/'rules.md').write_text(self.text)
        self.m = {"nodes": [{"id": i, "path": "rules.md", "section": h} for i, h in [
            ("pre", "@preamble"), ("rule", "## Rule"), ("detail", "## Detail"), ("old", "## Old"), ("new", "## New")]],
            "requires": [["rule", "old"], ["new", "rule"]], "supersedes": [["new", "old"]]}
        self.index = self.root/'index.sqlite'
        d, n, e = load(self.root, self.m); self.assertFalse(e)
        build_index(self.index, self.m, d, n)

    def test_fences_preamble_and_ambiguous_heading(self):
        parsed = sections(self.text)
        self.assertEqual(len(parsed), 5)
        self.assertNotIn("## fake", [p["heading"] for p in parsed])
        (self.root/'rules.md').write_text(self.text+'## Rule\nDuplicate\n')
        _, _, errors = load(self.root, self.m); self.assertTrue(errors)
        self.m["nodes"][1]["occurrence"] = 2
        _, _, errors = load(self.root, self.m); self.assertFalse(errors)

    def test_required_closure_and_supersession_cycle(self):
        result = package(self.root, self.m, "cache", ["rule"])
        self.assertEqual(result["required_ids"], ["new", "rule"])
        self.assertTrue(result["complete"])
        self.assertNotIn("old", result["candidate_ids"])
        self.assertEqual(len([p for p in result["passages"] if p["required"]]), 2)
        self.m["supersedes"].append(["old", "new"])
        with self.assertRaisesRegex(ValueError, "supersession cycle"):
            package(self.root, self.m, "cache", ["rule"])

    def test_backend_parity_and_query_punctuation(self):
        for query in ['cache', 'cache " OR *', '']:
            a = package(self.root, self.m, query, ["rule"])
            b = package(self.root, self.m, query, ["rule"], backend="sqlite", index=self.index)
            self.assertFalse(b["fallback"])
            for key in ["candidate_hash", "candidate_ids", "passages", "required_ids"]:
                self.assertEqual(a[key], b[key])

    def test_budget_overflow_preserves_all_required(self):
        r = package(self.root, self.m, "cache", ["rule"], budget=1)
        self.assertTrue(r["budget_exceeded"])
        self.assertEqual(len(r["passages"]), 2)
        self.assertTrue(all(p["required"] for p in r["passages"]))

    def test_changed_deleted_and_missing_index(self):
        (self.root/'rules.md').write_text(self.text.replace('detail', 'fresh detail'))
        r = package(self.root, self.m, "cache", ["rule"], backend="sqlite", index=self.index)
        self.assertEqual(r["fallback"], "stale index")
        self.assertIn("fresh detail", str(r["passages"]))
        (self.root/'rules.md').unlink()
        r = package(self.root, self.m, "cache", ["rule"], backend="sqlite", index=self.index)
        self.assertFalse(r["complete"])
        self.assertIn("missing required node: rule", r["errors"])
        r = package(self.root, self.m, "cache", ["rule"], backend="sqlite", index=self.root/'absent')
        self.assertEqual(r["fallback"], "missing index")

    def test_dangling_edge_and_escape(self):
        self.m["requires"].append(["rule", "absent"])
        self.assertFalse(package(self.root, self.m, "cache", ["rule"])["complete"])
        self.m["nodes"][0]["path"] = '../outside.md'
        with self.assertRaisesRegex(ValueError, "escapes root"):
            load(self.root, self.m)

    def test_serialized_optional_payload_fits_budget(self):
        required = package(self.root, self.m, "cache", ["rule"], budget=1)
        ceiling = required["required_chars"] + 5
        r = package(self.root, self.m, "cache", ["rule"], budget=ceiling)
        self.assertLessEqual(len(json.dumps(r["passages"], ensure_ascii=False)), ceiling)


    def test_optional_dependencies_are_atomic_bundles(self):
        self.m["requires"] = [["detail", "rule"]]
        r = package(self.root, self.m, "cache", [])
        self.assertEqual({p["id"] for p in r["passages"]}, {"detail", "rule"})
        ceiling = len(json.dumps([p for p in r["passages"] if p["id"] == "detail"], ensure_ascii=False))
        r = package(self.root, self.m, "cache", [], budget=ceiling)
        self.assertEqual(r["passages"], [])

    def test_corrupt_sql_payload_falls_back(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.index)) as db, db:
            db.execute("UPDATE passages SET body=NULL WHERE id='rule'")
        r = package(self.root, self.m, "cache", ["rule"], backend="sqlite", index=self.index)
        self.assertTrue(r["fallback"]); self.assertTrue(r["complete"])
        self.assertEqual(r["required_ids"], ["new", "rule"])

    def test_unrequested_supersession_cycle_is_invalid(self):
        self.m["supersedes"].append(["old", "new"])
        with self.assertRaisesRegex(ValueError, "supersession cycle"):
            package(self.root, self.m, "cache", [])



if __name__ == "__main__":
    unittest.main()
