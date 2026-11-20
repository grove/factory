#!/usr/bin/env python3
"""Verify and install the exact sfstack distribution used by this controller.

The core wheel is a vendored distribution built from the recorded sfstack
commit, not a source checkout or a claim that a PyPI release exists. All runtime
dependencies are version- and hash-pinned. Run this in a virtual environment
locally; Actions setup-python provides the isolated job's Python installation.
"""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "sfstack.lock.json"
VERSION = "1.1.0"
INTERFACE = "1.1"


def regular(path):
    """Reject links in a dependency path before reading or installing it."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_relative_to(ROOT):
        raise ValueError("Dependency path must be inside the controller checkout.")
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if part.is_symlink():
            raise ValueError("Dependency paths cannot contain symlinks.")
    if not path.is_file():
        raise ValueError("Missing dependency file: " + str(path.relative_to(ROOT)))
    return path


def verified_inputs():
    lock = json.loads(regular(LOCK).read_text(encoding="utf-8"))
    if (lock.get("schema_version") != 1
            or lock.get("interface_version") != INTERFACE
            or lock.get("distribution_version") != VERSION
            or lock.get("source", {}).get("repository") != "https://github.com/grove/sfstack"
            or not re.fullmatch(r"[0-9a-f]{40}", lock.get("source", {}).get("commit", ""))):
        raise ValueError("Unsupported or incomplete sfstack distribution lock.")
    artifact = lock["artifact"]
    expected_path = f"vendor/sfstack_contracts-{VERSION}-py3-none-any.whl"
    if (artifact.get("path") != expected_path
            or not re.fullmatch(r"[0-9a-f]{64}", artifact.get("sha256", ""))):
        raise ValueError("Expected the locked versioned sfstack wheel and SHA-256.")
    wheel = regular(ROOT / expected_path)
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != artifact["sha256"]:
        raise ValueError("sfstack wheel SHA-256 differs from the reviewed lock.")
    with zipfile.ZipFile(wheel) as archive:
        info = Parser().parsestr(archive.read(
            f"sfstack_contracts-{VERSION}.dist-info/METADATA").decode("utf-8"))
    if info["Name"] != "sfstack-contracts" or info["Version"] != VERSION:
        raise ValueError("Wheel metadata differs from the locked distribution.")
    dependencies = regular(ROOT / "requirements-runtime.txt")
    expected_dependencies = lock.get("dependencies_sha256", "")
    if (not re.fullmatch(r"[0-9a-f]{64}", expected_dependencies)
            or hashlib.sha256(dependencies.read_bytes()).hexdigest() != expected_dependencies):
        raise ValueError("Runtime dependency lock differs from sfstack.lock.json.")
    return lock, wheel, dependencies


def isolated_environment():
    return {key: value for key, value in os.environ.items()
            if not key.startswith("PYTHON")}


def install(lock, wheel, dependencies):
    with tempfile.TemporaryDirectory(prefix="factory-contracts-") as directory:
        requested = Path(directory) / "requirements.txt"
        requested.write_text(
            dependencies.read_text(encoding="utf-8")
            + f"\nsfstack-contracts @ {wheel.as_uri()} --hash=sha256:{lock['artifact']['sha256']}\n",
            encoding="utf-8",
        )
        subprocess.run(
            [sys.executable, "-I", "-m", "pip", "install", "--disable-pip-version-check",
             "--force-reinstall", "--require-hashes", "--only-binary=:all:", "-r", str(requested)],
            cwd=directory, env=isolated_environment(), check=True,
        )
        executable = Path(sysconfig.get_path("scripts")) / ("sfstack-contract.exe" if os.name == "nt" else "sfstack-contract")
        observed = subprocess.run(
            [str(executable), "version"], cwd=directory,
            env=isolated_environment(), capture_output=True, text=True, timeout=60,
            check=True,
        )
        response = json.loads(observed.stdout)
        if (response.get("interface_version") != INTERFACE
                or response.get("distribution_version") != VERSION
                or response.get("operation") != "version"
                or response.get("status") != "passed"
                or response.get("errors") != []
                or response.get("result") != {"interface_version": INTERFACE,
                                               "distribution_version": VERSION}):
            raise ValueError("Installed sfstack-contract does not match the locked interface.")
        # setup-python normally already supplies this path. Make the public
        # console entrypoint explicit for later Actions steps as well.
        if os.environ.get("GITHUB_PATH"):
            with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as stream:
                stream.write(str(executable.parent) + "\n")
        print(f"Installed sfstack-contract {VERSION}, interface {INTERFACE}, from {lock['source']['commit']}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify distribution, provenance and dependency hashes without installing")
    args = parser.parse_args()
    try:
        lock, wheel, dependencies = verified_inputs()
        if args.verify_only:
            print(f"Verified {wheel.name} and its complete dependency lock.")
        else:
            install(lock, wheel, dependencies)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            subprocess.SubprocessError) as exc:
        parser.exit(1, f"Cannot install the pinned sfstack contract interface: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
