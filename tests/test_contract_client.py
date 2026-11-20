"""The host rejects incompatible or internally contradictory CLI responses."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.github import contracts


class ContractClientTests(unittest.TestCase):
    @staticmethod
    def response(**changes):
        response = {
            "interface_version": "1.1", "distribution_version": "1.1.0",
            "operation": "gate", "status": "blocked", "errors": [],
            "result": {"decision": "blocked", "effect": "integration.modify", "scope": "fixture",
                       "reasons": ["No authorization grant."]},
        }
        response.update(changes)
        return response

    def observed(self, response, code=2):
        return subprocess.CompletedProcess([], code, json.dumps(response), "")

    @patch("integrations.github.contracts._executable", return_value="/trusted/bin/sfstack-contract")
    def test_negative_gate_remains_an_inspectable_negative_decision(self, _which):
        with patch("integrations.github.contracts.subprocess.run", return_value=self.observed(self.response())):
            result = contracts.evaluate_public_gate("request.json", "policy.json", datetime.now(timezone.utc))
        self.assertEqual("blocked", result["result"]["decision"])

    @patch("integrations.github.contracts._executable", return_value="/trusted/bin/sfstack-contract")
    def test_wrong_version_operation_or_exit_agreement_fails_closed(self, _which):
        cases = [
            (self.response(interface_version="2.0"), 2),
            (self.response(distribution_version="1.0.0"), 2),
            (self.response(operation="plan"), 2),
            (self.response(status="passed"), 2),
            (self.response(), 0),
            (self.response(), 1),
            (self.response(errors=["unexpected diagnostic"]), 2),
        ]
        for response, code in cases:
            with self.subTest(response=response, code=code):
                with patch("integrations.github.contracts.subprocess.run", return_value=self.observed(response, code)):
                    with self.assertRaises(ValueError):
                        contracts.invoke("gate")

    @patch("integrations.github.contracts._executable", return_value="/trusted/bin/sfstack-contract")
    def test_json_duplicate_keys_or_extra_output_is_rejected(self, _which):
        raw = json.dumps(self.response())
        for text in (raw + "\n" + raw, raw[:-1] + ', "status": "passed"}', "not-json"):
            with self.subTest(text=text):
                with patch("integrations.github.contracts.subprocess.run",
                           return_value=subprocess.CompletedProcess([], 2, text, "")):
                    with self.assertRaises(ValueError):
                        contracts.invoke("gate")

    @patch("integrations.github.contracts._executable", return_value="/trusted/bin/sfstack-contract")
    def test_claimed_allowed_decision_cannot_disagree_with_negative_envelope(self, _which):
        response = self.response()
        response["result"]["decision"] = "allowed"
        with patch("integrations.github.contracts.subprocess.run", return_value=self.observed(response)):
            with self.assertRaises(ValueError):
                contracts.evaluate_public_gate("request.json", "policy.json", datetime.now(timezone.utc))

    @patch("integrations.github.contracts._executable", return_value="/trusted/bin/sfstack-contract")
    def test_cli_runs_outside_candidate_and_without_python_or_credential_injection(self, _which):
        with patch.dict("os.environ", {"PYTHONPATH": "/candidate", "PYTHONHOME": "/candidate", "GH_TOKEN": "fixture"}):
            with patch("integrations.github.contracts.subprocess.run", return_value=self.observed(self.response())) as run:
                contracts.invoke("gate")
        args, kwargs = run.call_args
        self.assertEqual("/trusted/bin/sfstack-contract", args[0][0])
        self.assertNotIn("PYTHONPATH", kwargs["env"])
        self.assertNotIn("PYTHONHOME", kwargs["env"])
        self.assertNotIn("GH_TOKEN", kwargs["env"])
        self.assertNotEqual(str(ROOT), kwargs["cwd"])
        self.assertEqual(60, kwargs["timeout"])

    def test_missing_cli_is_explicitly_blocked(self):
        with patch("integrations.github.contracts.sys.executable", "/nonexistent-factory-environment/bin/python"):
            with self.assertRaisesRegex(ValueError, "not installed"):
                contracts.invoke("version")

    def test_executable_resolution_uses_current_python_environment_instead_of_path(self):
        with patch("integrations.github.contracts.sys.executable", "/trusted/bin/python"):
            with patch("pathlib.Path.is_file", return_value=True), patch("os.access", return_value=True):
                with patch.dict("os.environ", {"PATH": "/candidate/bin"}):
                    self.assertEqual(Path("/trusted/bin/sfstack-contract"), contracts._executable())

    def test_cached_schema_is_canonical_and_refreshes_when_installation_changes(self):
        contracts._schema_validator.cache_clear()
        self.addCleanup(contracts._schema_validator.cache_clear)
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "sfstack-contract"
            executable.write_text("first installed command")
            schema = {"type": "object", "required": ["id"],
                      "properties": {"id": {"type": "integer"}}, "additionalProperties": False}
            response = {"status": "passed", "result": {"name": "fixture", "schema": schema}}
            with patch.object(contracts, "_executable", return_value=executable):
                with patch.object(contracts, "invoke", return_value=response) as invoke:
                    contracts.validate_schema({"id": 1}, "fixture")
                    with self.assertRaises(ValueError):
                        contracts.validate_schema({"id": "invalid"}, "fixture")
                    invoke.assert_called_once_with("schema", "--name", "fixture")
                    executable.write_text("changed installed command identity")
                    contracts.validate_schema({"id": 2}, "fixture")
                    self.assertEqual(2, invoke.call_count)

    def test_host_has_no_private_sfstack_python_imports(self):
        forbidden = {"common", "factory", "contract_cli", "quality_report", "render_invocation", "sfstack_contracts_data"}
        for path in (ROOT / "integrations/github").glob("*.py"):
            with self.subTest(path=path.name):
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                    if isinstance(node, ast.ImportFrom):
                        self.assertNotIn((node.module or "").split(".")[0], forbidden)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertNotIn(alias.name.split(".")[0], forbidden)


if __name__ == "__main__":
    unittest.main()
