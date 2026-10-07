#!/usr/bin/env python3
"""Exercise the advisory diagnostic with isolated installations and deliberate faults.

Run: python3 scripts/tests/test-installed-skills-drift.py
All new installer destinations are explicit; HOME and CODEX_HOME are unchanged.
Optional FHORJA_DIAGNOSTIC_EVIDENCE_DIR retains actual subprocess output.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts/check-installed-skills-drift.sh"
INSTALL = REPO / "scripts/sync-workflow-slash-commands.sh"
SPEC = "WORKFLOW_OPERATING_SYSTEM.md"


class InstalledDrift(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fhorja-drift-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skills = self.root / "shared-skills"
        self.docs = self.root / "shared-docs"
        shutil.copytree(REPO / ".claude/skills", self.skills)
        self.copy_docs(self.docs)
        self.names = sorted(p.name for p in self.skills.iterdir() if (p / "SKILL.md").is_file())
        self.assertGreater(len(self.names), 0, "empty canonical control")
        self.env = dict(os.environ)
        for key in ("CLAUDE_SKILLS_DIR", "CODEX_SKILLS_DIR", "KIMI_SKILLS_DIR", "CURSOR_SKILLS_DIR"):
            self.env[key] = str(self.skills)
        for key in ("CLAUDE_WORKFLOW_DOCS_DIR", "CODEX_WORKFLOW_DOCS_DIR", "KIMI_WORKFLOW_DOCS_DIR", "WORKFLOW_DOCS_DIR"):
            self.env[key] = str(self.docs)
        self.env["KIMI_CODE_HOME"] = str(self.root / "kimi-home")
        for key in ("CURSOR_COMMANDS_DIR", "CLAUDE_COMMANDS_DIR", "CODEX_PROMPTS_DIR"):
            self.env[key] = str(self.root / key.lower())
        self.invocation = 0

    def copy_docs(self, destination):
        destination.mkdir()
        shutil.copy2(REPO / SPEC, destination / SPEC)
        shutil.copytree(REPO / "wos", destination / "wos")

    def run_check(self, *args, rc=0, script=CHECK):
        result = subprocess.run(["bash", str(script), *args], env=self.env,
                                text=True, capture_output=True, timeout=60)
        self.invocation += 1
        evidence = os.environ.get("FHORJA_DIAGNOSTIC_EVIDENCE_DIR")
        if evidence:
            directory = Path(evidence)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{self._testMethodName}-{self.invocation}.json").write_text(json.dumps({
                "command": ["bash", str(script), *args], "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr,
                "destinations": {k: v for k, v in self.env.items() if k.endswith("_DIR") or k == "KIMI_CODE_HOME"},
            }, indent=2) + "\n")
        self.assertEqual(result.returncode, rc, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout + result.stderr

    def fault(self, *args, script=CHECK):
        out = self.run_check(*args, script=script)
        self.assertNotIn("Installed-skills-drift: clean", out)
        return out

    def change_same_size(self, path):
        data = path.read_bytes()
        for i, byte in enumerate(data):
            if 65 <= byte <= 90 or 97 <= byte <= 122:
                changed = data[:i] + bytes([byte ^ 32]) + data[i + 1:]
                path.write_bytes(changed)
                self.assertEqual(path.stat().st_size, len(data))
                return
        self.fail("control contains no ASCII letter")

    def test_exact_control(self):
        out = self.run_check()
        self.assertIn("Installed-skills-drift: clean", out)
        self.assertIn("spec matches", out)
        self.assertIn("wos", out)
        self.assertIn("content matches", out)
        for adapter in ("Claude", "Cursor", "Codex", "Kimi"):
            self.assertIn(adapter, out)

    def test_literal_brackets_in_override(self):
        literal = self.root / "skills[fixture]"
        self.skills.rename(literal)
        for key in ("CLAUDE_SKILLS_DIR", "CODEX_SKILLS_DIR", "KIMI_SKILLS_DIR", "CURSOR_SKILLS_DIR"):
            self.env[key] = str(literal)
        self.assertIn("Installed-skills-drift: clean", self.run_check())

    def test_partial_canonical_catalog_never_clean(self):
        # A matched installed subset cannot validate an incomplete reference.
        candidate = self.root / "reference[fixture]"
        for relative in ("commands", ".claude/skills", "wos"):
            shutil.copytree(REPO / relative, candidate / relative)
        (candidate / "evals/scripts").mkdir(parents=True)
        (candidate / "scripts").mkdir()
        shutil.copy2(REPO / "evals/scripts/structural-evals.py", candidate / "evals/scripts")
        shutil.copy2(REPO / SPEC, candidate / SPEC)
        shutil.copy2(CHECK, candidate / "scripts/check-installed-skills-drift.sh")
        self.assertIn("Installed-skills-drift: clean",
                      self.run_check(script=candidate / "scripts/check-installed-skills-drift.sh"))
        shutil.rmtree(candidate / ".claude/skills/approve-plan")
        shutil.rmtree(self.skills / "approve-plan")
        self.assertTrue((candidate / "commands/approve-plan.md").is_file())
        out = self.fault(script=candidate / "scripts/check-installed-skills-drift.sh")
        self.assertIn("canonical", out)
        self.assertIn("approve-plan", out)

    def test_same_size_spec(self):
        self.change_same_size(self.docs / SPEC)
        self.assertIn("spec differs", self.fault())

    def test_same_size_topic(self):
        topic = next((self.docs / "wos").glob("*.md"))
        self.change_same_size(topic)
        out = self.fault("--verbose")
        self.assertIn("changed", out)
        self.assertIn(topic.name, out)

    def test_equal_count_replaced_path(self):
        topic = next((self.docs / "wos").glob("*.md"))
        name = topic.name
        topic.rename(topic.with_name("replacement-fixture.md"))
        out = self.fault("--verbose")
        for text in ("missing", "extra", name, "replacement-fixture.md"):
            self.assertIn(text, out)

    def test_nested_change(self):
        topic = next((self.docs / "wos/bug-classes").glob("*.md"))
        self.change_same_size(topic)
        self.assertIn("bug-classes/" + topic.name, self.fault("--verbose"))

    def test_nested_missing_and_extra(self):
        topic = next((self.docs / "wos/bug-classes").glob("*.md"))
        topic.rename(topic.with_name("extra-fixture.md"))
        out = self.fault("--verbose")
        self.assertIn("missing", out)
        self.assertIn("extra", out)
        self.assertIn("bug-classes/extra-fixture.md", out)

    def test_missing_docs(self):
        shutil.rmtree(self.docs)
        self.assertIn("not measured", self.fault())

    def test_missing_spec(self):
        (self.docs / SPEC).unlink()
        out = self.fault()
        self.assertIn("spec not measured", out)
        self.assertIn("content matches", out)

    def test_missing_wos(self):
        shutil.rmtree(self.docs / "wos")
        out = self.fault()
        self.assertIn("wos not measured", out)
        self.assertIn("spec matches", out)

    def test_invalid_spec_path(self):
        (self.docs / SPEC).unlink()
        (self.docs / SPEC).mkdir()
        self.assertIn("spec not measured", self.fault())

    def test_unreadable_topic(self):
        topic = next((self.docs / "wos/bug-classes").glob("*.md"))
        topic.chmod(0)
        self.addCleanup(topic.chmod, 0o644)
        try:
            topic.read_bytes()
        except PermissionError:
            self.assertIn("unreadable", self.fault("--verbose"))
        else:
            self.skipTest("runner can read chmod000 files; permission denial not established")

    def test_empty_skill_root(self):
        shutil.rmtree(self.skills)
        self.skills.mkdir()
        self.assertIn("no Fhorja skills", self.fault())

    def test_vendor_only_root(self):
        shutil.rmtree(self.skills)
        vendor = self.skills / "other-vendor"
        vendor.mkdir(parents=True)
        (vendor / "SKILL.md").write_text("---\nname: other-vendor\ndescription: other\n---\nbody\n")
        self.assertIn("no Fhorja skills", self.fault())

    def test_unrelated_vendor_preserves_control(self):
        vendor = self.skills / "other-vendor"
        vendor.mkdir()
        (vendor / "SKILL.md").write_bytes(b"\xff")
        self.assertIn("Installed-skills-drift: clean", self.run_check())

    def test_retired_workflow_skill(self):
        shutil.copytree(self.skills / self.names[0], self.skills / "retired-fixture")
        out = self.fault("--verbose")
        self.assertIn("1 extra workflow-tagged skill(s)", out)
        self.assertIn("retired-fixture", out)

    def test_unreadable_skill_keeps_independent_roots(self):
        claude = self.root / "claude-skills"
        shutil.copytree(self.skills, claude)
        self.env["CLAUDE_SKILLS_DIR"] = str(claude)
        path = claude / self.names[0] / "SKILL.md"
        path.chmod(0)
        self.addCleanup(path.chmod, 0o644)
        try:
            path.read_bytes()
        except PermissionError:
            out = self.fault()
            self.assertIn("1 unreadable", out)
            self.assertIn(f"{len(self.names)} Fhorja skill(s)", out)
        else:
            self.skipTest("runner can read chmod000 skills; permission denial not established")

    def test_missing_skill_root(self):
        shutil.rmtree(self.skills)
        self.assertIn("not measured", self.fault())

    def test_missing_one_skill(self):
        shutil.rmtree(self.skills / self.names[0])
        out = self.fault("--verbose")
        self.assertIn("not installed", out)
        self.assertIn(self.names[0], out)

    def test_partial_catalog(self):
        for name in self.names[24:]:
            shutil.rmtree(self.skills / name)
        out = self.fault()
        self.assertIn("24 Fhorja skill(s)", out)
        self.assertIn("0 body(ies) differ", out)
        self.assertIn("partial", out)

    def test_body_only_change(self):
        skill = self.skills / self.names[0] / "SKILL.md"
        skill.write_bytes(skill.read_bytes() + b"\nbody fixture\n")
        out = self.fault()
        self.assertIn("0 description(s) differ", out)
        self.assertIn("1 body(ies) differ", out)

    def test_missing_description(self):
        skill = self.skills / self.names[0] / "SKILL.md"
        skill.write_text("---\nname: fixture\n---\nbody\n")
        self.assertIn("malformed", self.fault("--verbose"))

    def test_invalid_utf8(self):
        (self.skills / self.names[0] / "SKILL.md").write_bytes(b"\xff")
        out = self.fault("--verbose")
        self.assertIn("unreadable", out)
        self.assertIn("spec matches", out)

    def test_missing_skill_file(self):
        (self.skills / self.names[0] / "SKILL.md").unlink()
        self.assertIn("not installed", self.fault("--verbose"))

    def test_shared_skills_distinct_docs(self):
        codex = self.root / "codex-docs"
        self.copy_docs(codex)
        self.env["CODEX_WORKFLOW_DOCS_DIR"] = str(codex)
        self.change_same_size(codex / SPEC)
        out = self.fault()
        self.assertIn(str(codex), out)
        self.assertIn("spec differs", out)
        self.assertIn("spec matches", out)
        self.assertNotIn(".agents/workflow-docs", out)

    def test_distinct_kimi_skill_override(self):
        kimi = self.root / "kimi-skills"
        shutil.copytree(self.skills, kimi)
        self.env["KIMI_SKILLS_DIR"] = str(kimi)
        shutil.rmtree(kimi / self.names[0])
        out = self.fault()
        self.assertIn(str(kimi), out)
        self.assertIn("not installed", out)

    def test_kimi_home_docs_default_and_empty_override(self):
        destination = Path(self.env["KIMI_CODE_HOME"]) / "workflow-docs"
        destination.parent.mkdir()
        self.copy_docs(destination)
        self.env.pop("KIMI_WORKFLOW_DOCS_DIR")
        self.assertIn(str(destination), self.run_check())
        self.env["KIMI_WORKFLOW_DOCS_DIR"] = ""
        self.assertIn(str(destination), self.run_check())

    def test_default_roots_and_kimi_precedence_embedded_process(self):
        # Execute the real embedded body with only expanduser isolated. This
        # proves default resolution without assigning HOME or CODEX_HOME;
        # other tests exercise the shell wrapper and explicit destinations.
        user_dir = self.root / "default-user"
        for relative in (".claude/skills", ".agents/skills"):
            destination = user_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.skills, destination)
        for brand in (".claude", ".cursor", ".codex", ".kimi"):
            (user_dir / brand).mkdir(exist_ok=True)
            self.copy_docs(user_dir / brand / "workflow-docs")
        body = CHECK.read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        prefix = ("import os,sys\n"
                  f"os.path.expanduser=lambda value: {str(user_dir)!r} if value=='~' else value\n"
                  f"sys.argv=['diagnostic', {str(REPO)!r}]\n")
        env = {k: v for k, v in self.env.items()
               if k not in {"CLAUDE_SKILLS_DIR", "CODEX_SKILLS_DIR", "KIMI_SKILLS_DIR", "CURSOR_SKILLS_DIR",
                            "CLAUDE_WORKFLOW_DOCS_DIR", "CODEX_WORKFLOW_DOCS_DIR", "KIMI_WORKFLOW_DOCS_DIR",
                            "WORKFLOW_DOCS_DIR", "KIMI_CODE_HOME"}}
        for phase in ("legacy", "both", "neither"):
            with self.subTest(phase=phase):
                if phase == "both":
                    (user_dir / ".kimi-code").mkdir()
                    self.copy_docs(user_dir / ".kimi-code/workflow-docs")
                elif phase == "neither":
                    shutil.rmtree(user_dir / ".kimi-code")
                    shutil.rmtree(user_dir / ".kimi")
                result = subprocess.run(["python3", "-c", prefix + body], env=env,
                                        text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
                brand = ".kimi" if phase == "legacy" else ".kimi-code"
                self.assertIn(str(user_dir / brand / "workflow-docs"), result.stdout)
                for adapter in ("Claude", "Cursor", "Codex", "Kimi"):
                    self.assertIn(adapter, result.stdout)
                if phase != "neither":
                    self.assertIn("Installed-skills-drift: clean", result.stdout)
                else:
                    self.assertNotIn("Installed-skills-drift: clean", result.stdout)
                    self.assertIn("not measured", result.stdout)

    def test_usage_errors(self):
        self.run_check("--unknown", rc=2)
        self.run_check("--verbose", "--unknown", rc=2)

    def test_real_temporary_install(self):
        # The real installer writes all four adapter payloads and opt-in Cursor skills.
        for key in ("CLAUDE_SKILLS_DIR", "CODEX_SKILLS_DIR", "KIMI_SKILLS_DIR", "CURSOR_SKILLS_DIR",
                    "CLAUDE_WORKFLOW_DOCS_DIR", "CODEX_WORKFLOW_DOCS_DIR", "KIMI_WORKFLOW_DOCS_DIR", "WORKFLOW_DOCS_DIR"):
            self.env[key] = str(self.root / key.lower())
        result = subprocess.run(["bash", str(INSTALL), "--cursor-skills"], env=self.env,
                                stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for key in ("CLAUDE_WORKFLOW_DOCS_DIR", "CODEX_WORKFLOW_DOCS_DIR", "KIMI_WORKFLOW_DOCS_DIR", "WORKFLOW_DOCS_DIR"):
            destination = Path(self.env[key])
            self.assertEqual((destination / SPEC).read_bytes(), (REPO / SPEC).read_bytes())
            expected = {p.relative_to(REPO / "wos").as_posix(): p.read_bytes()
                        for p in (REPO / "wos").rglob("*.md")}
            actual = {p.relative_to(destination / "wos").as_posix(): p.read_bytes()
                      for p in (destination / "wos").rglob("*.md")}
            self.assertEqual(actual, expected)
        self.assertIn("Installed-skills-drift: clean", self.run_check())


if __name__ == "__main__":
    unittest.main(verbosity=2)
