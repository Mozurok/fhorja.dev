#!/usr/bin/env python3
"""Exercise the native gate against real isolated Git worktrees, without models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import runpy
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(os.environ.get("TEST_FLEET_RESULT_HELPER", ROOT / "scripts/validate-implement-fleet-result.sh"))


class FleetResultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "product"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "integration")
        self.git(self.repo, "config", "user.name", "Test Maintainer")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        self.git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "seed.txt").write_text("base\n")
        self.git(self.repo, "add", "seed.txt")
        self.git(self.repo, "commit", "-m", "base")
        self.base = self.git(self.repo, "rev-parse", "HEAD")
        self.wt = self.root / "worker"
        self.git(self.repo, "worktree", "add", "-b", "worker", str(self.wt), self.base)
        self.tip = self.commit("a.txt", "first\n")
        (self.wt / ".fleet-out").mkdir()
        self.note = self.wt / ".fleet-out/01_worker.md"
        self.note.write_text("# Slice 01\nVerified a.txt.\n")
        self.carrier = self.wt / ".fleet-out/worker-01.json"
        self.context = self.root / "expected.json"
        self.payload = {"worker_id": "worker-01", "slice_id": "01", "status": "satisfied",
                        "files_touched": ["a.txt"], "build_status": "pass", "test_status": "pass",
                        "worktree_path": str(self.wt), "commit_sha": self.tip,
                        "slice_note_path": ".fleet-out/01_worker.md"}
        self.expected = {"worker_id": "worker-01", "slice_id": "01", "base_ref": self.base,
                         "product_repo_path": str(self.repo), "worktree_path": str(self.wt),
                         "scope_files": ["a.txt"], "payload_path": str(self.carrier),
                         "slice_note_path": ".fleet-out/01_worker.md"}

    def git(self, root, *args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, name, text):
        path = self.wt / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.git(self.wt, "add", "--", name)
        self.git(self.wt, "commit", "-m", "worker change")
        return self.git(self.wt, "rev-parse", "HEAD")

    def run_gate(self, raw=None, carrier=None):
        carrier = carrier or self.carrier
        carrier.write_text(raw if raw is not None else json.dumps(self.payload))
        self.context.write_text(json.dumps(self.expected))
        return subprocess.run(["bash", str(HELPER), str(carrier), str(self.context)],
                              cwd=self.root, text=True, capture_output=True)

    def ready(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIs(value["merge_ready"], True)
        return value

    def refused(self, text):
        result = self.run_gate()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(text, result.stderr)

    def test_valid_actual_commit_note_and_independent_hashes(self):
        value = self.ready()
        self.assertEqual(value["commit_sequence"], [self.tip])
        self.assertEqual(value["files_touched"], ["a.txt"])
        self.assertEqual(value["slice_note_sha256"], hashlib.sha256(self.note.read_bytes()).hexdigest())
        self.assertEqual(value["expected_sha256"], hashlib.sha256(self.context.read_bytes()).hexdigest())
        self.assertEqual(value["payload_sha256"], hashlib.sha256(self.carrier.read_bytes()).hexdigest())

    def test_all_success_handles_required_and_typed(self):
        original = copy.deepcopy(self.payload)
        for key in ("worker_id", "slice_id", "slice_note_path", "worktree_path", "commit_sha"):
            for value in (None, "", "   ", False, 1, []):
                with self.subTest(key=key, value=value):
                    self.payload = copy.deepcopy(original)
                    self.payload[key] = value
                    self.refused("invalid string")
            self.payload = copy.deepcopy(original)
            del self.payload[key]
            self.refused("invalid string")

    def test_worker_and_slice_identity_are_independent(self):
        self.payload["worker_id"] = "other"
        self.refused("identity mismatch")
        self.payload["worker_id"] = "worker-01"
        self.payload["slice_id"] = "02"
        self.refused("identity mismatch")

    def test_wrong_carrier_refused(self):
        result = self.run_gate(carrier=self.wt / ".fleet-out/other.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("carrier identity mismatch", result.stderr)

    def test_carrier_symlink_refused(self):
        other = self.root / "other.json"
        other.write_text(json.dumps(self.payload))
        self.carrier.symlink_to(other)
        result = self.run_gate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("must not be a symlink", result.stderr)

    def test_non_satisfied_states_representable_but_hold_wave(self):
        for status in ("needs_revision", "max_iterations_reached", "scope_violation", "failed", "interrupted", "timed_out"):
            self.payload = {"worker_id": "worker-01", "slice_id": "01", "status": status,
                            "files_touched": [], "build_status": "not_run", "test_status": "not_run"}
            if status == "failed":
                self.payload["error"] = {"error_class": "missing-input", "error_message": "No base",
                                         "error_evidence": "HEAD mismatch", "recoverable": False}
            result = self.run_gate()
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIs(json.loads(result.stdout)["merge_ready"], False)

    def test_failed_requires_nested_error_with_strict_boolean(self):
        self.payload["status"] = "failed"
        self.payload["error_class"] = "missing-input"
        self.refused("error.error_class")
        self.payload["error"] = {"error_class": "missing-input", "error_message": "No base",
                                 "error_evidence": "HEAD mismatch", "recoverable": 1}
        self.refused("error.recoverable")

    def test_satisfied_cannot_claim_failures(self):
        for field, value in (("build_status", "fail"), ("test_status", "fail"), ("test_status", "partial"),
                             ("out_of_scope_writes", ["secret.txt"]),
                             ("error", {"error_class": "unknown", "error_message": "oops", "error_evidence": "error", "recoverable": False})):
            original = copy.deepcopy(self.payload)
            self.payload[field] = value
            self.refused("contradicts")
            self.payload = original

    def test_not_run_checks_remain_representable(self):
        self.payload.update(build_status="not_run", test_status="not_run")
        self.ready()

    def test_nonexistent_or_abbreviated_commit_refused(self):
        self.payload["commit_sha"] = "0" * 40
        self.refused("Git check failed")
        self.payload["commit_sha"] = self.tip[:8]
        self.refused("full commit ID")

    def test_base_ancestry_and_actual_head_required(self):
        self.payload["commit_sha"] = self.base
        self.refused("not worktree HEAD")
        self.payload["commit_sha"] = self.tip
        self.expected["base_ref"] = self.tip
        self.refused("no commit after base")

    def test_unrelated_base_and_merge_history_refused(self):
        other = self.root / "branch-worker"
        self.git(self.repo, "worktree", "add", "-b", "branch-worker", str(other), self.base)
        (other / "b.txt").write_text("branch\n")
        self.git(other, "add", "b.txt")
        self.git(other, "commit", "-m", "branch change")
        branch_tip = self.git(other, "rev-parse", "HEAD")
        self.expected["base_ref"] = branch_tip
        self.refused("Git check failed")
        self.expected["base_ref"] = self.base
        self.git(self.wt, "merge", "--no-ff", "-m", "merge branch", branch_tip)
        self.payload.update(commit_sha=self.git(self.wt, "rev-parse", "HEAD"), files_touched=["a.txt", "b.txt"])
        self.expected["scope_files"] = ["*.txt"]
        self.refused("not linear from base")

    def test_wrong_or_product_worktree_refused(self):
        self.payload["worktree_path"] = str(self.repo)
        self.refused("worktree identity mismatch")
        self.expected["worktree_path"] = str(self.repo)
        self.refused("distinct worktree")

    def test_unrelated_repository_refused(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        self.git(foreign, "init")
        self.expected["product_repo_path"] = str(foreign)
        self.refused("does not belong")

    def test_note_missing_empty_escape_symlink_and_identity(self):
        self.note.unlink()
        self.refused("No such file")
        self.note.write_text(" ")
        self.refused("empty slice note")
        outside = self.root / "outside.md"
        outside.write_text("other task")
        self.payload["slice_note_path"] = str(outside)
        self.refused("escapes")
        self.payload["slice_note_path"] = ".fleet-out/01_worker.md"
        self.note.unlink()
        self.note.symlink_to(outside)
        self.refused("escapes")
        self.note.unlink()
        self.note.write_text("right note")
        other = self.note.with_name("02_other.md")
        other.write_text("wrong slice")
        self.payload["slice_note_path"] = str(other)
        self.refused("note identity mismatch")

    def test_actual_paths_must_equal_claimed_paths(self):
        self.payload["files_touched"] = []
        self.refused("actual committed paths")
        self.payload["files_touched"] = ["a.txt", "invented.txt"]
        self.refused("actual committed paths")

    def test_out_of_scope_commit_refused(self):
        self.expected["scope_files"] = ["b.txt"]
        self.refused("outside scope")

    def test_return_folder_cannot_be_committed(self):
        self.payload["commit_sha"] = self.commit(".fleet-out/leaked.md", "must never integrate")
        self.payload["files_touched"] = ["a.txt", ".fleet-out/leaked.md"]
        self.refused("return or Git path")

    def test_reverted_intermediate_out_of_scope_commit_refused(self):
        self.commit("outside.txt", "transient\n")
        self.git(self.wt, "rm", "outside.txt")
        self.git(self.wt, "commit", "-m", "revert transient")
        self.payload["commit_sha"] = self.git(self.wt, "rev-parse", "HEAD")
        self.payload["files_touched"] = ["a.txt", "outside.txt"]
        self.refused("outside scope")

    def test_linear_multiple_commits_are_all_integrated(self):
        second = self.commit("b.txt", "second\n")
        self.payload.update(commit_sha=second, files_touched=["a.txt", "b.txt"])
        self.expected["scope_files"] = ["*.txt"]
        value = self.ready()
        self.assertEqual(value["commit_sequence"], [self.tip, second])
        for commit in value["commit_sequence"]:
            self.git(self.repo, "cherry-pick", commit)
        self.assertEqual((self.repo / "a.txt").read_text(), "first\n")
        self.assertEqual((self.repo / "b.txt").read_text(), "second\n")
        self.assertFalse((self.repo / ".fleet-out").exists())

    def test_two_disjoint_workers_integrate_without_return_files(self):
        first = self.ready()
        other = self.root / "worker-two"
        self.git(self.repo, "worktree", "add", "-b", "worker-two", str(other), self.base)
        (other / "b.txt").write_text("second\n")
        self.git(other, "add", "b.txt")
        self.git(other, "commit", "-m", "second worker")
        (other / ".fleet-out").mkdir()
        (other / ".fleet-out/02_worker.md").write_text("# Slice 02\nVerified b.txt.\n")
        self.carrier = other / ".fleet-out/worker-02.json"
        self.payload.update(worker_id="worker-02", slice_id="02", files_touched=["b.txt"],
                            worktree_path=str(other), commit_sha=self.git(other, "rev-parse", "HEAD"),
                            slice_note_path=".fleet-out/02_worker.md")
        self.expected.update(worker_id="worker-02", slice_id="02", worktree_path=str(other),
                             scope_files=["b.txt"], payload_path=str(self.carrier), slice_note_path=".fleet-out/02_worker.md")
        second = self.ready()
        for value in (first, second):
            for commit in value["commit_sequence"]:
                self.git(self.repo, "cherry-pick", commit)
        self.assertEqual(self.git(self.repo, "ls-files").splitlines(), ["a.txt", "b.txt", "seed.txt"])

    def test_dirty_tracked_and_untracked_files_refused(self):
        (self.wt / "a.txt").write_text("uncommitted")
        self.refused("uncommitted tracked")
        (self.wt / "a.txt").write_text("first\n")
        (self.wt / "extra.txt").write_text("untracked")
        self.refused("uncommitted non-return")

    def test_index_flags_cannot_hide_post_commit_changes(self):
        for flag in ("assume-unchanged", "skip-worktree"):
            self.git(self.wt, "update-index", "--" + flag, "a.txt")
            (self.wt / "a.txt").write_text("changed after validation\n")
            with self.subTest(flag=flag):
                self.refused("index hides tracked paths")
            self.git(self.wt, "update-index", "--no-" + flag, "a.txt")
            (self.wt / "a.txt").write_text("first\n")

    def test_deletion_mode_only_and_spaces_are_real_scoped_paths(self):
        self.git(self.wt, "rm", "seed.txt")
        (self.wt / "a.txt").chmod(0o755)
        (self.wt / "with spaces.txt").write_text("spaces\n")
        self.git(self.wt, "add", "--", "a.txt", "with spaces.txt")
        self.git(self.wt, "commit", "-m", "scoped changes")
        self.payload.update(commit_sha=self.git(self.wt, "rev-parse", "HEAD"),
                            files_touched=["a.txt", "seed.txt", "with spaces.txt"])
        self.expected["scope_files"] = ["a.txt", "seed.txt", "with spaces.txt"]
        self.ready()

    def test_valid_failed_worker_holds_whole_local_consumer_wave(self):
        head_before = self.git(self.repo, "rev-parse", "HEAD")
        ready = self.run_gate()
        self.payload = {"worker_id": "worker-01", "slice_id": "01", "status": "max_iterations_reached",
                        "files_touched": [], "build_status": "not_run", "test_status": "partial"}
        held = self.run_gate()
        results = [ready, held]
        # The local consumer implements the documented pre-merge barrier. This does
        # not establish model obedience to the command in a hosted fleet.
        if all(r.returncode == 0 and json.loads(r.stdout)["merge_ready"] is True for r in results):
            for r in results:
                for commit in json.loads(r.stdout)["commit_sequence"]:
                    self.git(self.repo, "cherry-pick", commit)
        self.assertEqual(held.returncode, 3, held.stderr)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), head_before)
        self.assertFalse((self.repo / "a.txt").exists())

    def test_rename_checks_both_endpoints(self):
        self.git(self.wt, "mv", "seed.txt", "renamed.txt")
        self.git(self.wt, "commit", "-m", "rename")
        self.payload.update(commit_sha=self.git(self.wt, "rev-parse", "HEAD"),
                            files_touched=["a.txt", "seed.txt", "renamed.txt"])
        self.expected["scope_files"] = ["a.txt", "renamed.txt"]
        self.refused("outside scope: seed.txt")
        self.expected["scope_files"].append("seed.txt")
        self.ready()

    def test_malformed_duplicate_nonfinite_json_and_wrong_types(self):
        for raw in ("prose", "[]", '{"status":"satisfied","status":"failed"}', '{"x":NaN}'):
            result = self.run_gate(raw=raw)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(result.stdout, "")
        for value in ("a.txt", [False], ["a.txt", "a.txt"], ["../a.txt"]):
            self.payload["files_touched"] = value
            self.refused("array" if value != ["../a.txt"] else "relative path")

    def test_absent_inputs_never_report_ready(self):
        result = subprocess.run(["bash", str(HELPER), str(self.root / "absent"), str(self.context)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_schema_and_gate_contract_mutations(self):
        check = runpy.run_path(str(ROOT / "evals/scripts/structural-evals.py"))["check_fleet_result_contract"]
        fixture = self.root / "contract"
        (fixture / "commands").mkdir(parents=True)
        source = (ROOT / "commands/implement-fleet.md").read_text()
        target = fixture / "commands/implement-fleet.md"
        target.write_text(source)
        self.assertEqual(check(str(fixture)), (True, []))
        for old, new in (('"required": ["slice_note_path", "worktree_path", "commit_sha"]', '"required": []'),
                         ('"required": ["error"]', '"required": []'),
                         ('"not": {"required": ["error"]}', '"not": {"required": ["unrelated"]}'),
                         ('"build_status": {"enum": ["pass", "not_run"]}', '"build_status": {"enum": ["pass", "not_run", "fail"]}'),
                         ('"test_status": {"enum": ["pass", "not_run"]}', '"test_status": {"enum": ["pass", "not_run", "partial"]}'),
                         ('"maxItems": 0', '"maxItems": 1'),
                         ('"required": ["worker_id", "status", "slice_id", "files_touched", "build_status", "test_status"]',
                          '"required": ["worker_id", "status", "slice_id", "files_touched", "build_status", "test_status", "commit_sha"]'),
                         ('scripts/validate-implement-fleet-result.sh <payload.json> <expected.json>', 'missing-helper'),
                         ('for EVERY expected worker', 'for some workers')):
            self.assertIn(old, source)
            target.write_text(source.replace(old, new))
            passed, findings = check(str(fixture))
            self.assertFalse(passed, findings)
        barrier_only = "\n".join(line.replace('`max_iterations_reached`, ', '') if line.startswith('- **Step 8:') else line for line in source.splitlines())
        target.write_text(barrier_only)
        self.assertFalse(check(str(fixture))[0])
        # Actual host schema enforcement remains unverified; these are local
        # conditional structure and native guard controls, not a schema engine.


if __name__ == "__main__":
    unittest.main(verbosity=2)
