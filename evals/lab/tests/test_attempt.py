import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from attempt import (canonical, strict_json, same, resolve_policy, freeze, verify,
                     guarded_launch, seal_evidence, verify_evidence, adapter_declared, ROLES)


def policy():
    values = dict(provider="local", model="synthetic", effort="test", timeout_seconds=10,
                  max_calls=1, max_actual_usd=None, max_equivalent_usd=100,
                  limit_mode="monitored", accept_last_response_overrun=True)
    return resolve_policy({k: {"value": v, "source": "synthetic local fixture"} for k, v in values.items()})


class AttemptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {}
        for role in ROLES:
            path = self.root / (role + ".txt")
            path.write_text(role)
            self.files[role] = [path]
        self.path = self.root / "attempt.json"
        self.policy = policy()

    def freeze(self):
        return freeze(self.path, "local-1", self.policy, self.files)

    def test_guarded_local_callback_runs_only_after_verified_freeze(self):
        binding = self.freeze()
        calls = []
        self.assertEqual(guarded_launch(binding, lambda: calls.append("called") or 42), 42)
        self.assertEqual(calls, ["called"])
        record = verify(binding)
        self.assertEqual(record["effective_policy"], self.policy)
        self.assertEqual(set(record["artifacts"]), ROLES)

    def test_unauthorized_starting_source_change_refuses_before_model_callback(self):
        binding = self.freeze()
        original_record = self.path.read_bytes()
        self.files['source'][0].write_text('changed before dispatch')
        calls = []
        with self.assertRaises(ValueError):
            guarded_launch(binding, lambda: calls.append('entered'))
        self.assertEqual(calls, [])
        self.assertEqual(self.path.read_bytes(), original_record)

    def test_effective_override_preserves_value_and_origin(self):
        entries = {k: {"value": v, "source": self.policy["sources"][k]}
                   for k, v in self.policy["values"].items()}
        resolved = resolve_policy(entries, {"max_equivalent_usd": {"value": 1000, "source": "synthetic override"}})
        binding = freeze(self.path, "synthetic-override", resolved, self.files)
        recorded = verify(binding)["effective_policy"]
        self.assertEqual(recorded["values"]["max_equivalent_usd"], 1000)
        self.assertEqual(recorded["sources"]["max_equivalent_usd"], "synthetic override")
        self.assertEqual(entries["max_equivalent_usd"]["value"], 100)

    def test_missing_or_tampered_metadata_never_invokes_callback(self):
        binding = self.freeze()
        calls = []
        good = self.path.read_bytes()
        for fault in (b"", b"{", good + b" "):
            with self.subTest(fault=fault[:12]):
                self.path.write_bytes(fault)
                with self.assertRaises(ValueError):
                    guarded_launch(binding, lambda: calls.append("called"))
        self.path.unlink()
        with self.assertRaises(OSError):
            guarded_launch(binding, lambda: calls.append("called"))
        self.assertEqual(calls, [])

    def test_recomputed_internal_content_cannot_replace_independent_digest(self):
        binding = self.freeze()
        value = strict_json(self.path.read_bytes())
        value["effective_policy"]["values"]["max_equivalent_usd"] = 1000
        self.path.write_text(json.dumps(value))
        calls = []
        with self.assertRaises(ValueError):
            guarded_launch(binding, lambda: calls.append(True))
        self.assertEqual(calls, [])

    def test_every_frozen_artifact_role_blocks_changed_inputs_before_launch(self):
        binding = self.freeze()
        for role, files in self.files.items():
            path = files[0]
            raw = path.read_bytes()
            path.write_bytes(raw + b"changed")
            calls = []
            with self.subTest(role=role), self.assertRaises(ValueError):
                guarded_launch(binding, lambda: calls.append(True))
            self.assertEqual(calls, [])
            path.write_bytes(raw)
        verify(binding)

    def test_existing_attempt_and_historical_bytes_are_never_overwritten(self):
        historical = self.root / "auto.json"
        historical.write_bytes(b"historical\x00bytes")
        binding = self.freeze()
        raw = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.freeze()
        self.assertEqual(self.path.read_bytes(), raw)
        self.assertEqual(historical.read_bytes(), b"historical\x00bytes")
        verify(binding)

    def test_policy_has_no_inferred_values_or_missing_origins(self):
        for fault in ("missing", "source", "bool", "nonfinite"):
            value = copy.deepcopy(self.policy)
            if fault == "missing":
                del value["values"]["max_calls"]
            elif fault == "source":
                value["sources"]["max_calls"] = ""
            elif fault == "bool":
                value["values"]["timeout_seconds"] = True
            else:
                value["values"]["max_actual_usd"] = float("inf")
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                freeze(self.path, "bad", value, self.files)
        self.assertFalse(self.path.exists())

    def test_missing_artifact_role_cannot_be_frozen(self):
        del self.files["prompt"]
        with self.assertRaises(ValueError):
            self.freeze()

    def test_source_identity_and_duplicates_are_explicit(self):
        self.files["source"] *= 2
        with self.assertRaises(ValueError):
            self.freeze()

    def test_json_round_trip_and_exact_nested_types(self):
        value = {"nested": [None, True, False, -1, 1, 1.0, {"z": -1, "a": []}]}
        self.assertEqual(strict_json(canonical(value)), value)
        self.assertTrue(same({"a": 1, "b": [2]}, {"b": [2], "a": 1}))
        for a, b in [(True, 1), (1, 1.0), ([1, 2], [2, 1]), (float("inf"), float("inf"))]:
            self.assertFalse(same({"nested": a}, {"nested": b}))
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":1e999}'):
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_receipt_binds_post_implementation_source_and_captured_artifacts(self):
        binding = self.freeze()
        source = self.files["source"][0]
        source.write_text("legitimate implementation output")
        artifact = self.root / "browser.json"
        artifact.write_text('{"schemaVersion":2}')
        artifacts = {"browser": [artifact]}
        receipt = seal_evidence(self.root / "receipt.json", binding, artifacts, [source])
        recorded = verify_evidence(receipt, binding, artifacts, [source])
        self.assertEqual(recorded["attempt_id"], "local-1")
        for target in (source, artifact, Path(receipt["path"]), self.files["scorer"][0]):
            raw = target.read_bytes()
            target.write_bytes(raw + b" ")
            with self.subTest(target=target.name), self.assertRaises(ValueError):
                verify_evidence(receipt, binding, artifacts, [source])
            target.write_bytes(raw)
        with self.assertRaises(FileExistsError):
            seal_evidence(self.root / "receipt.json", binding, artifacts, [source])

    def test_receipt_rejects_wrong_attempt_and_source_set(self):
        binding = self.freeze()
        artifact = self.root / "result.json"
        artifact.write_text('{}')
        artifacts = {"domain": [artifact]}
        receipt = seal_evidence(self.root / "receipt.json", binding, artifacts, self.files["source"])
        for other in ([], self.files["driver"]):
            with self.assertRaises(ValueError):
                verify_evidence(receipt, binding, artifacts, other)
        wrong = dict(binding, attempt_id="other")
        with self.assertRaises(ValueError):
            verify_evidence(receipt, wrong, artifacts, self.files["source"])

    def test_entry_identity_never_uses_path_or_inline_interpreter_shortcuts(self):
        entry = self.root / 'entry.py'; entry.write_text('print("entry")')
        self.assertTrue(adapter_declared([sys.executable, str(entry)], [entry]))
        self.assertTrue(adapter_declared([str(entry)], [entry]))
        for command, files in [
            ([sys.executable, '-c', 'print("inline")', str(entry)], [sys.executable, entry]),
            ([sys.executable, '-m', 'module', str(entry)], [sys.executable, entry]),
            ([sys.executable, '-u', str(entry)], [entry]),
            ([entry.name], [entry]),
            ([sys.executable, entry.name], [entry]),
            (['python3', str(entry)], [entry]),
        ]:
            with self.subTest(command=command):
                self.assertFalse(adapter_declared(command, files))


if __name__ == "__main__":
    unittest.main()
