import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark import compare


class BenchmarkTests(unittest.TestCase):
    def test_real_backends_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'a.md').write_text('# Intro\nUnselected '+('noise '*100)+'\n## Required\nKeep this.\n## Optional\ncache answer\n')
            manifest = {"nodes": [{"id": i, "path": "a.md", "section": h} for i, h in [('req', '## Required'), ('opt', '## Optional')]]}
            r = compare(root, manifest, root/'index', ['cache'], ['req'], repeats=2)
            row = r['rows'][0]
            self.assertTrue(row['parity']); self.assertEqual(row['required_ids'], ['req'])
            self.assertLess(row['selected_payload_chars'], row['full_source_chars'])
            self.assertEqual(len(row['timings']['sqlite']['samples_seconds']), 2)


    def test_early_fallback_sample_invalidates_comparison(self):
        from unittest.mock import patch
        from context import package
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'a.md').write_text('## Required\nKeep this.\n')
            manifest = {"nodes": [{"id": "req", "path": "a.md", "section": "## Required"}]}
            calls = [0]
            def injected(*args, **kwargs):
                result = package(*args, **kwargs)
                if kwargs.get("backend") == "sqlite":
                    calls[0] += 1
                    if calls[0] == 1:
                        result["fallback"] = "injected first-sample failure"
                return result
            with patch('benchmark.package', side_effect=injected):
                with self.assertRaisesRegex(ValueError, "invalid sample"):
                    compare(root, manifest, root/'index', ['cache'], ['req'], repeats=2)



if __name__ == '__main__': unittest.main()
