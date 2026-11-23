#!/usr/bin/env python3
"""Preview or propose a SHA-pinned sfstack Factory installation in another repo.

This tool copies reviewed caller workflows. It never runs candidate code,
configures GitHub settings/secrets, executes a model, or merges a pull request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

TEMPLATE_ROOT = Path(__file__).resolve().parent / "onboarding_templates"
FILES = (
    ".github/ISSUE_TEMPLATE/factory-work-item.md",
    ".github/workflows/sfstack-issue-label.yml",
    ".github/workflows/sfstack-pr-signal.yml",
    ".github/workflows/sfstack-quality-events.yml",
    ".github/workflows/sfstack-quality-required.yml",
    ".github/workflows/sfstack-quality.yml",
    ".github/workflows/sfstack-software.yml",
)
REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,126}\Z")
PR_BRANCH = "chore/install-sfstack-factory"
REPO_TOKEN = "__SFSTACK_TARGET_REPOSITORY__"
BRANCH_TOKEN = "__SFSTACK_TARGET_BRANCH_JSON__"
PLAN_SHA_TOKEN = "__SFSTACK_FACTORY_PLAN_SHA__"
SHA = re.compile(r"[a-f0-9]{40}\Z")


class InstallationError(ValueError):
    """Refuse an ambiguous or unsafe installation instead of guessing."""


def validate_identity(repository, default_branch):
    if not REPOSITORY.fullmatch(repository) or any(x in {".", ".."} for x in repository.split("/")):
        raise InstallationError("Expected a GitHub repository in OWNER/NAME form.")
    if (not BRANCH.fullmatch(default_branch) or ".." in default_branch
            or "//" in default_branch or default_branch.endswith(("/", ".", ".lock"))):
        raise InstallationError("Unsupported default branch name; select a safe exact branch ref.")


def render(repository, default_branch, factory_revision):
    """Render only reviewed, fixed-path templates; never interpret issue text."""
    validate_identity(repository, default_branch)
    if not SHA.fullmatch(factory_revision):
        raise InstallationError("Choose an exact reviewed 40-character Factory SHA with --factory-revision.")
    result = {}
    for name in FILES:
        template = TEMPLATE_ROOT / name
        if not template.is_file() or template.is_symlink():
            raise InstallationError("Missing or unsafe reviewed installation template: " + name)
        content = template.read_text(encoding="utf-8")
        expected_repo = int(name.endswith("sfstack-issue-label.yml"))
        expected_branch = int(name.endswith("sfstack-quality-events.yml"))
        expected_plan_sha = 3 if name.endswith("sfstack-issue-label.yml") else 0
        if (content.count(REPO_TOKEN) != expected_repo
                or content.count(BRANCH_TOKEN) != expected_branch
                or content.count(PLAN_SHA_TOKEN) != expected_plan_sha):
            raise InstallationError("Unexpected template placeholder layout: " + name)
        content = (content.replace(REPO_TOKEN, repository)
                   .replace(BRANCH_TOKEN, json.dumps(default_branch))
                   .replace(PLAN_SHA_TOKEN, factory_revision))
        if REPO_TOKEN in content or BRANCH_TOKEN in content or PLAN_SHA_TOKEN in content:
            raise InstallationError("An installation template still contains a placeholder.")
        result[name] = content
    # Every reusable Factory workflow or source checkout is pinned to an exact
    # immutable reviewed 40-byte SHA, never @main, @latest, a tag, or user input.
    label = result[".github/workflows/sfstack-issue-label.yml"]
    pins = re.findall(r"grove/factory/\.github/workflows/sfstack-software\.yml@([^\s]+)", label)
    source = re.findall(r"(?m)^\s+ref:\s*([a-f0-9]{40})\s*$", label)
    if len(pins) != 1 or not SHA.fullmatch(pins[0]) or pins[0] not in source:
        raise InstallationError("Label source and reusable Software controller must share one immutable SHA.")
    for name in ("sfstack-software.yml", "sfstack-quality.yml", "sfstack-quality-events.yml"):
        text = result[".github/workflows/" + name]
        matches = re.findall(r"uses:\s*grove/factory/\.github/workflows/[^\s@]+@([^\s]+)", text)
        if len(matches) != 1 or not SHA.fullmatch(matches[0]):
            raise InstallationError("Unpinned Factory reusable workflow: " + name)
    quality = result[".github/workflows/sfstack-quality.yml"]
    events = result[".github/workflows/sfstack-quality-events.yml"]
    def pin(text):
        return re.search(r"uses:\s*grove/factory/\.github/workflows/[^\s@]+@([a-f0-9]{40})", text).group(1)
    if pin(quality) != pin(events):
        raise InstallationError("Quality and event coordinator must use the same reviewed Factory SHA.")
    required = result[".github/workflows/sfstack-quality-required.yml"]
    if ("name: sfstack quality\n" not in required
            or not re.search(r"(?m)^\s+ref:\s*[a-f0-9]{40}\s*$", required)):
        raise InstallationError("Missing immutable native required-Quality gate.")
    if f"github.repository == '{repository}'" not in label:
        raise InstallationError("Issue-label workflow is not bound to the exact target repository.")
    if f"branches: [{json.dumps(default_branch)}]" not in events:
        raise InstallationError("Event coordinator is not bound to the exact target branch.")
    return result


def manifest(repository, branch, files):
    return {"repository": repository, "default_branch": branch, "profile": "python-unittest",
            "mode": "review-before-activation", "files": {
                name: hashlib.sha256(content.encode("utf-8")).hexdigest()
                for name, content in sorted(files.items())},
            "limits": [
                "The pinned Factory checks execute Python unittest discovery in tests/.",
                "Only exact files under docs/, examples/, tests/, or root README.md may be edited.",
                "Ordinary project CI, credentials, branch protection, and two issue labels are NOT installed.",
                "No secrets, GitHub settings, candidate code, model, or merge are touched by preview/render.",
            ]}


def write_bundle(destination, files, metadata):
    """Emit a fresh reviewable bundle; never overwrite a prior result."""
    if destination.exists() or destination.is_symlink():
        raise InstallationError("Output directory already exists; select a new path.")
    destination.mkdir(parents=True)
    for name, content in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (destination / "install-plan.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def command(args, cwd):
    """Execute trusted fixed-argument Git/gh operations; never a shell command."""
    # Never execute project-supplied Git hooks or signing commands while onboarding.
    safe_args = (["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                  "-c", "commit.gpgsign=false", *args[1:]] if args[0] == "git" else args)
    result = subprocess.run(safe_args, cwd=cwd, text=True, capture_output=True, check=False, timeout=90)
    if result.returncode:
        # stderr from GitHub or project hooks can include sensitive text; never
        # include it verbatim in an installation exception or issue comment.
        raise InstallationError(f"Command {args[0]} failed (exit {result.returncode}); inspect locally.")
    return result.stdout.strip()


def expected_remote(remote, repository):
    allowed = (f"https://github.com/{repository}", f"git@github.com:{repository}",
               f"ssh://git@github.com/{repository}")
    return remote.removesuffix(".git").casefold() in {value.casefold() for value in allowed}


def prepare_target(checkout, repository, branch, files):
    """Refuse stale, dirty, unowned, or already-installed Git checkouts."""
    if checkout.is_symlink() or not checkout.is_dir():
        raise InstallationError("Target must be a real existing Git checkout.")
    root = checkout.resolve()
    if Path(command(["git", "rev-parse", "--show-toplevel"], root)).resolve() != root:
        raise InstallationError("Target must be the root of its Git checkout.")
    if command(["git", "status", "--porcelain=v1", "--untracked-files=all"], root):
        raise InstallationError("Target checkout must be clean before creating an installation PR.")
    if command(["git", "branch", "--show-current"], root) != branch:
        raise InstallationError("Checkout must be on the selected default branch.")
    remote = command(["git", "remote", "get-url", "origin"], root)
    if not expected_remote(remote, repository):
        raise InstallationError("Git origin does not match the selected GitHub repository.")
    for name in files:
        cursor = root
        for part in Path(name).parts:
            cursor /= part
            if cursor.is_symlink():
                raise InstallationError("Destination path traverses a symlink: " + name)
        if cursor.exists():
            raise InstallationError("Destination already contains a Factory caller: " + name)
    # This read is about directory and test inventory, never actual execution.
    tests = root / "tests"
    if tests.is_symlink() or not tests.is_dir() or not any(
            x.is_file() and not x.is_symlink() for x in tests.rglob("test_*.py")):
        raise InstallationError("Python-unittest profile requires substantive tests/test_*.py files.")
    return root


def open_installation_pr(checkout, repository, base_branch, files):
    """One explicitly requested local branch/commit/push/PR; never merge."""
    root = prepare_target(checkout, repository, base_branch, files)
    # Fetch before any edits; a stale local base must never be promoted to a PR.
    command(["git", "fetch", "--no-tags", "origin", base_branch], root)
    if command(["git", "rev-parse", "FETCH_HEAD"], root) != command(["git", "rev-parse", "HEAD"], root):
        raise InstallationError("Local default branch is stale; update it before generating a PR.")
    if subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/" + PR_BRANCH],
                      cwd=root, check=False, timeout=10).returncode == 0:
        raise InstallationError("Installation branch already exists; inspect it instead of overwriting.")
    command(["git", "switch", "-c", PR_BRANCH], root)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    command(["git", "add", "--", *files], root)
    command(["git", "commit", "-m", "chore: install SHA-pinned sfstack Factory callers"], root)
    command(["git", "push", "-u", "origin", PR_BRANCH], root)
    body = ("Install reviewed SHA-pinned Software/Quality Factory callers and the issue template.\n\n"
            "This PR does not set secrets, Actions permissions, branch rules or labels, "
            "and does not launch an AI job. Review the files and configure trusted "
            "Python unittest CI and the required native sfstack quality gate before enabling labels.\n\n"
            "Getting started: https://github.com/grove/factory/blob/main/docs/getting-started-new-repository.md\n")
    return command(["gh", "pr", "create", "--repo", repository, "--base", base_branch,
                    "--head", PR_BRANCH, "--title", "chore: install sfstack Factory callers",
                    "--body", body], root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="Exact GitHub OWNER/NAME")
    parser.add_argument("--default-branch", default="main", help="Target's protected default branch")
    parser.add_argument("--factory-revision", required=True,
                        help="Full reviewed immutable Factory SHA that includes AI planning support")
    parser.add_argument("--profile", default="python-unittest", choices=["python-unittest"])
    parser.add_argument("--output", type=Path, help="Write a new offline bundle (no GitHub writes)")
    parser.add_argument("--checkout", type=Path, help="Existing clean checkout; required for --create-pr")
    parser.add_argument("--create-pr", action="store_true", help="Explicitly branch, push, and open a target PR")
    args = parser.parse_args(argv)
    if args.output and args.create_pr:
        parser.error("--output and --create-pr are separate modes.")
    if args.create_pr and not args.checkout:
        parser.error("--create-pr requires --checkout to an existing GitHub clone.")
    try:
        files = render(args.repository, args.default_branch, args.factory_revision)
        result = manifest(args.repository, args.default_branch, files)
        result["factory_planning_revision"] = args.factory_revision
        if args.create_pr:
            result["pr_url"] = open_installation_pr(args.checkout, args.repository, args.default_branch, files)
        elif args.output:
            write_bundle(args.output, files, result)
            result["output"] = str(args.output)
        else:
            result["preview_only"] = True
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, "onboard-repository: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
