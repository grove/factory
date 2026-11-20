"""Strict subprocess client for the pinned public sfstack-contract interface.

No sfstack Python module or checkout resource is imported. The trusted host
installs a digest-pinned distribution before invoking this client. Every call
checks the distribution, interface, operation, status, and exit-code agreement.
Evidence is re-read by the CLI on every decision; decisions are never cached.
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from integrations.github.host_io import strict_json
from jsonschema import Draft202012Validator, FormatChecker

INTERFACE_VERSION = "1.1"
DISTRIBUTION_VERSION = "1.1.0"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


def _executable():
    # The host and CLI must share the same explicitly provisioned environment.
    # PATH may contain candidate-controlled executables and is not a resolver.
    command = Path(sys.executable).absolute().parent / "sfstack-contract"
    if not command.is_file() or not os.access(command, os.X_OK):
        raise ValueError("The pinned sfstack-contract CLI is not installed in the host Python environment.")
    return command


def invoke(operation, *arguments):
    executable = _executable()
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith("PYTHON")
                   and not any(word in key.upper() for word in
                               ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "GITHUB_", "ACTIONS_"))}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        # A neutral cwd plus a cleaned Python environment prevents candidate
        # files or inherited PYTHONPATH from supplying CLI implementation code.
        with tempfile.TemporaryDirectory(prefix="factory-cli-") as working:
            observed = subprocess.run(
                [str(Path(executable).resolve()), operation, *map(str, arguments)],
                cwd=working, env=environment, capture_output=True, text=True,
                check=False, timeout=60,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("The pinned sfstack-contract CLI could not complete.") from exc
    if observed.returncode not in (0, 2, 64) or len(observed.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ValueError("sfstack-contract returned an invalid exit code or oversized response.")
    try:
        response = strict_json(observed.stdout)
        expected = {0: "passed", 2: "blocked", 64: "invalid"}[observed.returncode]
        if (not isinstance(response, dict)
                or set(response) != {"interface_version", "distribution_version", "operation", "status", "result", "errors"}
                or response["interface_version"] != INTERFACE_VERSION
                or response["distribution_version"] != DISTRIBUTION_VERSION
                or response["operation"] != operation
                or response["status"] != expected
                or not isinstance(response["errors"], list)
                or any(not isinstance(error, str) for error in response["errors"])
                or (expected != "invalid" and response["errors"] != [])
                or (expected != "invalid" and not isinstance(response["result"], dict))):
            raise ValueError("Incompatible response envelope.")
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("Malformed or incompatible sfstack-contract response.") from exc
    if observed.returncode == 64:
        raise ValueError("Invalid sfstack-contract invocation: " + "; ".join(response["errors"]))
    return response


def _at(at):
    return at.isoformat().replace("+00:00", "Z")


def _json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return str(path)


@lru_cache(maxsize=32)
def _schema_validator(name, executable, modified_ns, size, interface, distribution):
    # Cache only immutable canonical resource data, keyed by the exact pinned
    # interface/distribution and installed entrypoint identity. Evidence,
    # authorization and workflow decisions are never cached.
    response = invoke("schema", "--name", name)
    result = response["result"]
    if response["status"] != "passed" or result.get("name") != name or not isinstance(result.get("schema"), dict):
        raise ValueError("Malformed canonical schema result from sfstack-contract.")
    Draft202012Validator.check_schema(result["schema"])
    return Draft202012Validator(result["schema"], format_checker=FormatChecker())


def validate_schema(value, name):
    executable = _executable()
    identity = executable.stat()
    validator = _schema_validator(name, str(executable), identity.st_mtime_ns, identity.st_size,
                                  INTERFACE_VERSION, DISTRIBUTION_VERSION)
    errors = sorted(validator.iter_errors(value), key=lambda error: str(list(error.path)))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{name} {location}: {first.message}")


def inspect_artifact(path, subject, run_id, at, max_age, expected_type=None, allow_nonpassing=False):
    context = {"subject": subject, "run_id": run_id, "max_evidence_age_seconds": max_age}
    with tempfile.TemporaryDirectory(prefix="factory-inspect-") as directory:
        context_path = _json(Path(directory) / "context.json", context)
        arguments = ["--path", str(Path(path).absolute()), "--context", context_path, "--at", _at(at)]
        if expected_type is not None:
            arguments.extend(["--type", expected_type])
        if allow_nonpassing:
            arguments.append("--allow-nonpassing")
        response = invoke("inspect", *arguments)
    result = response["result"]
    artifact, reasons = result.get("artifact"), result.get("reasons")
    if (not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons)
            or (response["status"] == "passed") != (not reasons)
            or (artifact is not None and not isinstance(artifact, dict))):
        raise ValueError("Malformed artifact-inspection result from sfstack-contract.")
    if artifact is None:
        raise ValueError("; ".join(reasons) or "sfstack artifact unavailable.")
    return artifact, reasons


def plan(workflow, run, at):
    response = invoke("plan", "--workflow", Path(workflow).resolve(), "--run", Path(run).resolve(), "--at", _at(at))
    result = response["result"]
    if (not isinstance(result.get("ready"), list)
            or any(not isinstance(step, str) for step in result["ready"])
            or result.get("status") not in {"ready", "complete", "blocked"}
            or (result["status"] == "blocked") != (response["status"] == "blocked")):
        raise ValueError("Malformed plan result from sfstack-contract.")
    return result


def render(skill, context):
    with tempfile.TemporaryDirectory(prefix="factory-render-") as directory:
        path = _json(Path(directory) / "context.json", context)
        response = invoke("render", "--skill", skill, "--context", path)
    result = response["result"]
    if (response["status"] != "passed" or result.get("skill") != skill
            or not isinstance(result.get("invocation_markdown"), str)
            or not result["invocation_markdown"].strip()):
        raise ValueError("Malformed invocation result from sfstack-contract.")
    return result["invocation_markdown"]


def consolidate(workflow, run, output_dir, at, out_run=None):
    arguments = ["--workflow", Path(workflow).resolve(), "--run", Path(run).resolve(),
                 "--out-dir", output_dir, "--at", _at(at)]
    if out_run is not None:
        arguments.extend(["--out-run", out_run])
    response = invoke("consolidate", *arguments)
    result = response["result"]
    if (result.get("status") not in {"passed", "failed", "blocked", "inconclusive"}
            or (result["status"] == "passed") != (response["status"] == "passed")
            or not isinstance(result.get("assessment"), str)):
        raise ValueError("Malformed quality-consolidation result from sfstack-contract.")
    return result


def evaluate_public_gate(request, policy, at):
    response = invoke("gate", "--request", Path(request).resolve(), "--policy", Path(policy).resolve(), "--at", _at(at))
    result = response["result"]
    if (result.get("decision") not in {"allowed", "blocked"}
            or (result["decision"] == "allowed") != (response["status"] == "passed")
            or not isinstance(result.get("reasons"), list)
            or any(not isinstance(reason, str) for reason in result["reasons"])
            or not isinstance(result.get("effect"), str)
            or not isinstance(result.get("scope"), str)):
        raise ValueError("Malformed authorization-gate result from sfstack-contract.")
    return response
