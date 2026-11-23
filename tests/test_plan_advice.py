"""Deterministic fail-closed validation for untrusted Copilot planning prose."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from integrations.github import plan_advice


SCOPE = {
    "version": 1, "repository": "fixture/software", "issue": 7,
    "issue_digest": "f" * 64, "base_sha": "a" * 40,
    "allowed_paths": ["examples/answer.py", "tests/test_answer.py"],
    "acceptance_criteria": [
        "Existing behavior must fail the new assertion in a real RED run.",
        "Repaired behavior passes the identical regression and full suite.",
    ], "repair_mode": "defect", "regression_file": "tests/test_answer.py",
}

PROPOSAL = {
    "version": 1,
    "steps": [
        {"file": "examples/answer.py",
         "action": "Find and correct the return path that produces the incorrect observable answer."},
        {"file": "tests/test_answer.py",
         "action": "Add a Python unittest test that asserts the public answer equals its required value."},
    ],
    "verification": [
        {"criterion": 1,
         "method": "Run tests/test_answer.py as true test-only RED on unchanged code before applying any repair."},
        {"criterion": 2,
         "method": "Run exact tests/test_answer.py against the repaired tree for GREEN and then run the full test suite."},
    ],
    "risks": ["The new test may assert implementation details rather than the public behavior."],
    "questions": ["Do legacy consumers depend on the incorrect answer in a documented integration?"],
}


class PlanAdviceTests(unittest.TestCase):
    def test_structured_plan_is_genuinely_new_advice(self):
        proposal = plan_advice.validate(json.dumps(PROPOSAL), SCOPE)
        self.assertEqual(PROPOSAL, proposal)
        markdown = plan_advice.display(SCOPE, proposal, 1234)
        self.assertIn("Implementation steps", markdown)
        self.assertIn("Proposed verification", markdown)
        self.assertIn("Risks and limitations", markdown)
        self.assertIn("Open questions", markdown)
        self.assertIn("not new authorization", markdown)
        self.assertNotIn("Existing behavior must fail the new assertion", markdown)

    def test_malformed_duplicates_and_out_of_scope_are_rejected(self):
        cases = [
            "not json",
            '{"version":1,"version":1}',
            "x" * (plan_advice.MAX_RESPONSE + 1),
            json.dumps({**PROPOSAL, "steps": [{**PROPOSAL["steps"][0], "file": ".github/workflows/backdoor.yml"},
                                            PROPOSAL["steps"][1]]}),
            json.dumps({**PROPOSAL, "steps": PROPOSAL["steps"][:1]}),
            json.dumps({**PROPOSAL, "verification": PROPOSAL["verification"][:1]}),
            json.dumps({**PROPOSAL, "verification": [{**PROPOSAL["verification"][0], "criterion": 2},
                                                    PROPOSAL["verification"][1]]}),
            json.dumps({**PROPOSAL, "risks": []}),
            json.dumps({**PROPOSAL, "extra_permission": "write"}),
            json.dumps({**PROPOSAL, "verification": [
                {"criterion": 1, "method": SCOPE["acceptance_criteria"][0]},
                PROPOSAL["verification"][1]]}),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:75]), self.assertRaises((ValueError, UnicodeError)):
                plan_advice.validate(raw, SCOPE)

    def test_source_previews_are_read_only_and_limited(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "examples").mkdir()
            (root / "examples/answer.py").write_text("answer = 41\n" + "# " + "x" * 5000)
            (root / "tests").mkdir()
            (root / "tests/test_answer.py").write_text("import unittest\n")
            excerpts = plan_advice.preview_sources(root, SCOPE["allowed_paths"])
            self.assertEqual(2, len(excerpts))
            self.assertTrue(excerpts[0]["truncated"])
            self.assertLessEqual(len(excerpts[0]["excerpt"]), plan_advice.MAX_SNIPPET)
            self.assertEqual("existing", excerpts[1]["status"])

    def test_symlink_or_binary_sources_cannot_enter_the_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "examples").mkdir()
            (root / "examples/answer.py").symlink_to("/etc/hosts")
            with self.assertRaisesRegex(ValueError, "symlink"):
                plan_advice.preview_sources(root, SCOPE["allowed_paths"])
            (root / "examples/answer.py").unlink()
            (root / "examples/answer.py").write_bytes(b"bad\x00byte")
            with self.assertRaises(ValueError):
                plan_advice.preview_sources(root, SCOPE["allowed_paths"])

    def test_nondefect_mode_allows_nonred_verification_but_not_extra_files(self):
        scope = {**SCOPE, "repair_mode": "change", "regression_file": ""}
        check = {**PROPOSAL, "verification": [
            {"criterion": 1, "method": "Run targeted unittest assertions and compare the required public output."},
            {"criterion": 2, "method": "Execute full unittest discovery to detect any unintended regressions."},
        ]}
        self.assertEqual(check, plan_advice.validate(json.dumps(check), scope))

    def test_empty_or_unsafe_plan_fields_rejected(self):
        for bad in ("", "short", "Line\nwith new row", "<!--fake-marker-->"):
            attempt = {**PROPOSAL, "steps": [{**PROPOSAL["steps"][0], "action": bad},
                                            PROPOSAL["steps"][1]]}
            with self.subTest(action=bad), self.assertRaises(ValueError):
                plan_advice.validate(json.dumps(attempt), SCOPE)


if __name__ == "__main__":
    unittest.main()
