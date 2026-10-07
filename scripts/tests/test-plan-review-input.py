#!/usr/bin/env python3
"""Exercise the real installed-capable review assembler, without a model call."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HELPER = Path(os.environ.get("TEST_REVIEW_INPUT_HELPER", Path(__file__).resolve().parents[1] / "build-plan-review-input.sh"))
D1 = "### D-1 retry boundary\nRetry only once.\n\n"
P1 = "### P-1 helper\nUse a local helper.\nEvidence: canonical.md:1\nImpact: normal\nStatus: provisional\n\n"
BRIEF = "Preserve money values.\n\n```text\n## This is user input, not a section\nD-99 is an example.\n```\n\n"
PLAN = "# Plan\n\n## Slices\n### 01: bounded repair\n- Decision-ref: D-1; rests on provisional P-1\n- Exit criterion: WHEN repair lands it SHALL preserve retry count.\n\n## Author notes\nPLAN_HISTORY_SENTINEL\n"
DECISIONS = "# Decisions\n\n## Locked decisions\n" + D1 + "### D-2 unrelated\nUNRELATED_LOCKED_SENTINEL\n\n## Provisional decisions\n" + P1 + "### P-2 unrelated\nUNRELATED_PROVISIONAL_SENTINEL\n\n## History\nAUTHOR_HISTORY_SENTINEL\n"


class ReviewInputTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        self.task = self.base / "task"
        self.task.mkdir()
        self.write("IMPLEMENTATION_PLAN.md", PLAN)
        self.write("DECISIONS.md", DECISIONS)
        self.write("README.md", "# Readme\n\n## Brief\n" + BRIEF + "## History\nREADME_HISTORY_SENTINEL\n")

    def write(self, name, text):
        (self.task / name).write_text(text)

    def run_helper(self):
        return subprocess.run(["bash", str(HELPER), str(self.task)], cwd=self.base, text=True, capture_output=True)

    def accepted(self):
        r = self.run_helper()
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def refused(self, fragment):
        r = self.run_helper()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertEqual(r.stdout, "")
        self.assertIn(fragment, r.stderr)

    def test_exact_cited_bytes_hashes_and_history_exclusion(self):
        result = self.accepted()
        rubric = result["rubric"]
        for block in (D1, P1, BRIEF):
            self.assertIn(block, rubric)
        for sentinel in ("PLAN_HISTORY_SENTINEL", "UNRELATED_LOCKED_SENTINEL", "UNRELATED_PROVISIONAL_SENTINEL", "AUTHOR_HISTORY_SENTINEL", "README_HISTORY_SENTINEL"):
            self.assertNotIn(sentinel, json.dumps(result))
        self.assertEqual(result["artifact"]["path"], str((self.task / "IMPLEMENTATION_PLAN.md").resolve()))
        self.assertEqual(result["artifact"]["sha256"], hashlib.sha256((self.task / "IMPLEMENTATION_PLAN.md").read_bytes()).hexdigest())
        self.assertEqual(result["brief_source"], "README.md ## Brief")
        self.assertEqual(result["sources"]["DECISIONS.md"], hashlib.sha256((self.task / "DECISIONS.md").read_bytes()).hexdigest())

    def test_missing_cited_decision(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1;", "D-88;"))
        self.refused("not found: cited decision D-88")

    def test_colon_headings_exact_identifier_and_repeated_citations(self):
        d10 = "### D-10: amount units\nPreserve 1.00 and trailing spaces.  \n\n"
        self.write("DECISIONS.md", DECISIONS.replace("### D-1 retry", "### D-1: retry").replace("### D-2 unrelated", d10 + "### D-2 unrelated"))
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1;", "D-10;").replace("## Author notes", "### 02: same rule\n- Decision-ref: D-10\n## Author notes"))
        rubric = self.accepted()["rubric"]
        self.assertIn(d10, rubric)
        self.assertNotIn("Retry only once.", rubric)
        self.assertEqual(rubric.count("### D-10: amount units"), 1)

    def test_fenced_examples_inside_selected_entry_remain_exact(self):
        d1 = D1 + "```md\n### D-99 example\nExample bytes.  \n```\n\n"
        self.write("DECISIONS.md", DECISIONS.replace(D1, d1))
        self.assertIn(d1, self.accepted()["rubric"])

    def test_missing_task_is_not_success(self):
        r = subprocess.run(["bash", str(HELPER), str(self.base / "absent")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not found: task folder", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_missing_plan_decisions_or_slices(self):
        for name in ("IMPLEMENTATION_PLAN.md", "DECISIONS.md"):
            with self.subTest(name=name):
                path = self.task / name
                saved = path.read_text()
                path.unlink()
                self.refused("not found: " + name)
                path.write_text(saved)
        self.write("IMPLEMENTATION_PLAN.md", "# Plan\n## Slices\nnone\n")
        self.refused("not found: plan slices")

    def test_duplicate_decision_section_slice_or_field(self):
        mutations = [
            ("DECISIONS.md", DECISIONS.replace(D1, D1 + D1), "duplicate decision: D-1"),
            ("DECISIONS.md", DECISIONS + "\n## Locked decisions\nNone\n", "duplicate section"),
            ("IMPLEMENTATION_PLAN.md", PLAN.replace("## Author notes", "### 01: duplicate\n- Decision-ref: D-1\n## Author notes"), "duplicate slice"),
            ("IMPLEMENTATION_PLAN.md", PLAN.replace("- Exit criterion:", "- Decision-ref: D-2\n- Exit criterion:"), "duplicate Decision-ref"),
        ]
        for name, text, error in mutations:
            with self.subTest(error=error):
                self.write("DECISIONS.md", DECISIONS)
                self.write("IMPLEMENTATION_PLAN.md", PLAN)
                self.write(name, text)
                self.refused(error)

    def test_wrong_section_and_proposed_only_refs(self):
        for text in (
            DECISIONS.replace(D1, "").replace("## Provisional decisions\n", "## Provisional decisions\n" + D1),
            DECISIONS.replace("D-1 retry boundary", "D-1 PROPOSED"),
            DECISIONS.replace(D1, "<!-- PROPOSED by decision-interview:\n" + D1 + "-->\n"),
        ):
            with self.subTest(text=text):
                self.write("DECISIONS.md", text)
                r = self.run_helper()
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertEqual(r.stdout, "")

    def test_fenced_and_commented_fake_entries_are_not_authorization(self):
        for wrapper in ("```md\n{}\n```\n", "~~~~markdown\n{}\n~~~~\n", "<!--\n{}\n-->\n"):
            with self.subTest(wrapper=wrapper):
                self.write("DECISIONS.md", DECISIONS.replace(D1, wrapper.format(D1)))
                self.refused("not found: cited decision D-1")

    def test_fenced_refs_do_not_select_unrelated_decisions(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("- Decision-ref: D-1; rests on provisional P-1\n", "The exit preserves D-1.\n```md\n- Decision-ref: D-2\n```\n"))
        rubric = self.accepted()["rubric"]
        self.assertIn(D1, rubric)
        self.assertNotIn("UNRELATED_LOCKED_SENTINEL", rubric)
        self.assertNotIn(P1, rubric)

    def test_content_fallback_with_named_decision_and_unnamed_refusal(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("- Decision-ref: D-1; rests on provisional P-1\n", "This repair keeps D-1.\n"))
        self.assertIn(D1, self.accepted()["rubric"])
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("- Decision-ref: D-1; rests on provisional P-1\n", "This repair keeps the existing retry rule.\n"))
        self.refused("no explicit decision trace")

    def test_explicit_no_locked_decisions(self):
        self.write("DECISIONS.md", "# Decisions\n## Locked decisions\nNone locked in this task.\n")
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1; rests on provisional P-1", "none locked; nothing to trace"))
        self.assertIn("None cited; no locked decisions to trace.", self.accepted()["rubric"])

    def test_missing_brief_reports_absence(self):
        self.write("README.md", "# Readme\n## History\nREADME_HISTORY_SENTINEL\n")
        result = self.accepted()
        self.assertIsNone(result["brief_source"])
        self.assertIn("brief: none found", result["rubric"])
        self.assertNotIn("README_HISTORY_SENTINEL", result["rubric"])

    def test_task_local_brief_pointer_and_missing_target(self):
        self.write("BRIEF.md", BRIEF)
        for pointer in ("BRIEF.md", "See `BRIEF.md`.", "[Intake](BRIEF.md)", "[Intake](./BRIEF.md)"):
            with self.subTest(pointer=pointer):
                self.write("README.md", "# Readme\n## Brief\n" + pointer + "\n## History\nREADME_HISTORY_SENTINEL\n")
                result = self.accepted()
                self.assertEqual(result["brief_source"], "BRIEF.md")
                self.assertIn(BRIEF, result["rubric"])
        (self.task / "BRIEF.md").unlink()
        self.refused("not found: BRIEF.md")

    def test_brief_pointer_escape(self):
        self.write("README.md", "## Brief\n[Brief](BRIEF.md)\n")
        (self.base / "outside.md").write_text("OUTSIDE_HISTORY_SENTINEL")
        (self.task / "BRIEF.md").symlink_to(self.base / "outside.md")
        self.refused("brief pointer escapes task")

    def test_unsupported_brief_pointer_refuses(self):
        self.write("README.md", "## Brief\n[Brief](../BRIEF.md)\n")
        self.refused("unsupported brief pointer")

    def test_unlabeled_provisional_missing_fields_and_malformed_reference(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("rests on provisional P-1", "P-1"))
        self.refused("unlabeled provisional")
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1;", "D-invalid;"))
        self.refused("malformed Decision-ref")
        self.write("IMPLEMENTATION_PLAN.md", PLAN)
        self.write("DECISIONS.md", DECISIONS.replace("Evidence: canonical.md:1\n", ""))
        self.refused("missing provisional field Evidence")

    def test_replaced_or_superseded_citation_refuses(self):
        self.write("DECISIONS.md", DECISIONS.replace("### P-2 unrelated\n", "### P-2 unrelated\nReplaces: P-1\n"))
        self.refused("superseded citation: P-1")
        self.write("DECISIONS.md", DECISIONS.replace("### D-2 unrelated\n", "### D-2 unrelated\nSupersedes: D-1\n"))
        self.refused("superseded citation: D-1")

    def test_maintainer_supersedes_provisional_refuses_but_confirmation_does_not(self):
        self.write("DECISIONS.md", DECISIONS.replace("Retry only once.", "Retry only once.\nSupersedes: P-1"))
        self.refused("superseded citation: P-1")
        self.write("DECISIONS.md", DECISIONS.replace("Retry only once.", "Retry only once.\nConfirms: P-1"))
        self.assertIn(P1, self.accepted()["rubric"])

    def test_provisional_reference_transports_its_locked_confirmation(self):
        confirmation = "### D-1 confirmed helper\nConfirms: P-1\nUse only the local helper.\n\n"
        self.write("DECISIONS.md", DECISIONS.replace(D1, confirmation))
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1; rests on provisional P-1", "rests on provisional P-1"))
        rubric = self.accepted()["rubric"]
        self.assertIn(confirmation, rubric)
        self.assertIn(P1, rubric)

    def test_superseded_locked_confirmation_refuses(self):
        self.write("DECISIONS.md", DECISIONS.replace("Retry only once.", "Retry only once.\nConfirms: P-1").replace("### D-2 unrelated\n", "### D-2 unrelated\nSupersedes: D-1\n"))
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1; rests on provisional P-1", "rests on provisional P-1"))
        self.refused("superseded confirmation: D-1")

    def test_exit_references_join_explicit_field_and_exclude_examples(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("preserve retry count.", "preserve D-2 and `D-77` as an example."))
        rubric = self.accepted()["rubric"]
        self.assertIn(D1, rubric)
        self.assertIn("### D-2 unrelated", rubric)
        self.assertIn("01: D-1, D-2, P-1", rubric)
        self.assertNotIn("UNRELATED_PROVISIONAL_SENTINEL", rubric)

    def test_missing_and_stale_exit_references_refuse_with_explicit_field(self):
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("preserve retry count.", "preserve D-88."))
        self.refused("not found: cited decision D-88")
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("preserve retry count.", "preserve D-2."))
        self.write("DECISIONS.md", DECISIONS.replace("## Provisional decisions", "### D-3 replacement\nSupersedes: D-2\nNew rule.\n\n## Provisional decisions"))
        self.refused("superseded citation: D-2")

    def replacement_fixture(self):
        confirmation = "### D-1 confirmed helper\nConfirms: P-1\nUse only the local helper.\n\n"
        p2 = P1.replace("P-1 helper", "P-2 replacement").replace("Use a local helper.", "Replaces: P-1\nUse a bounded local helper.")
        self.write("DECISIONS.md", DECISIONS.replace(D1, confirmation).replace("### P-2 unrelated\nUNRELATED_PROVISIONAL_SENTINEL\n", p2))
        self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1; rests on provisional P-1", "rests on provisional P-2"))
        return confirmation, p2

    def test_replacement_head_transports_locked_confirmation(self):
        confirmation, p2 = self.replacement_fixture()
        rubric = self.accepted()["rubric"]
        self.assertIn(confirmation, rubric)
        self.assertIn(p2, rubric)
        self.assertNotIn(P1, rubric)
        self.assertNotIn("UNRELATED_LOCKED_SENTINEL", rubric)

    def test_replacement_ancestry_refuses_missing_origin_and_fork(self):
        self.replacement_fixture()
        text = (self.task / "DECISIONS.md").read_text()
        self.write("DECISIONS.md", text.replace("Replaces: P-1", "Replaces: P-99"))
        self.refused("not found: replacement origin P-99")
        fork = P1.replace("P-1 helper", "P-3 fork").replace("Use a local helper.", "Replaces: P-1\nUse a different helper.")
        self.write("DECISIONS.md", text.replace("## History", fork + "## History"))
        self.refused("ambiguous replacement: P-1")

    def test_replacement_confirmation_superseded_and_cycle_refuse(self):
        self.replacement_fixture()
        text = (self.task / "DECISIONS.md").read_text()
        self.write("DECISIONS.md", text.replace("### D-2 unrelated\n", "### D-2 unrelated\nSupersedes: D-1\n"))
        self.refused("superseded confirmation: D-1")
        self.write("DECISIONS.md", text.replace("Use a local helper.", "Replaces: P-2\nUse a local helper."))
        # A cited cycle has no live head; existing stale-citation rejection holds it.
        self.refused("superseded citation: P-2")

    def test_unrelated_replacement_history_stays_out_of_rubric(self):
        self.write("DECISIONS.md", DECISIONS.replace("### P-2 unrelated\n", "### P-2 unrelated\nReplaces: P-98\n"))
        result = self.accepted()
        self.assertNotIn("UNRELATED_PROVISIONAL_SENTINEL", result["rubric"])

    def test_complete_metadata_values_and_duplicates(self):
        mutations = [
            ("Impact: normal", "Impact: normal-invalid"),
            ("Status: provisional", "Status: provisional\nStatus: confirmed"),
            ("Impact: normal", "Impact: normal\nImpact: high"),
            ("Evidence: canonical.md:1", "Evidence: canonical.md:1\nEvidence: elsewhere.md:8"),
        ]
        for old, new in mutations:
            with self.subTest(new=new):
                self.write("DECISIONS.md", DECISIONS.replace(old, new))
                self.refused("provisional metadata")
        self.write("DECISIONS.md", DECISIONS.replace("Impact: normal\nStatus: provisional", "Impact: normal. Status: provisional."))
        self.assertIn("Impact: normal. Status: provisional.", self.accepted()["rubric"])

    def test_valid_reference_mixed_with_dangling_or_malformed_identifier(self):
        for token in ("D-", "P-", "D-1_extra", "D-1.2", "D-1-"):
            with self.subTest(token=token):
                self.write("IMPLEMENTATION_PLAN.md", PLAN.replace("D-1;", "D-1, " + token + ";"))
                self.refused("malformed Decision-ref")

    def test_rubric_carries_evidence_verdict_rules(self):
        rubric = self.accepted()["rubric"]
        self.assertIn("needs_revision for unresolved", rubric)
        self.assertIn("Evidence: none found", rubric)
        self.assertIn("Impact: high", rubric)

    def test_neighbor_write_annotation_is_not_selected_entry(self):
        # Last cited entry immediately precedes the next section annotation.
        self.write("DECISIONS.md", DECISIONS.replace("### D-2 unrelated\nUNRELATED_LOCKED_SENTINEL\n\n", "").replace("## Provisional decisions", "<!-- wos:write owner=author section='## Provisional decisions' run_id=AUTHOR_HISTORY_SENTINEL -->\n## Provisional decisions"))
        rubric = self.accepted()["rubric"]
        self.assertNotIn("AUTHOR_HISTORY_SENTINEL", rubric)
        self.assertIn(D1, rubric)

    def test_lookalike_locked_section_is_not_authorization(self):
        self.write("DECISIONS.md", DECISIONS.replace("## Locked decisions\n", "## Locked decisions draft\n"))
        self.refused("not found: section Locked decisions")

    def test_unclosed_fence_refuses(self):
        self.write("DECISIONS.md", DECISIONS + "\n```md\n### D-9\n")
        self.refused("unclosed fence or comment")


if __name__ == "__main__":
    unittest.main()
