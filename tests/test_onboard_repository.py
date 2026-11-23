"""No-network safety tests for target repository onboarding."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import onboard_repository as onboarding


class OnboardRepositoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_all_seven_reviewed_files_render_without_mutable_controller_refs(self):
        files = onboarding.render("Example/target", "main")
        self.assertEqual(set(onboarding.FILES), set(files))
        label = files[".github/workflows/sfstack-issue-label.yml"]
        self.assertIn("github.repository == 'Example/target'", label)
        self.assertNotIn("github.repository == 'grove/sfstack'", label)
        self.assertIn("issues:", label)
        self.assertIn("types: [labeled]", label)
        self.assertIn("factory:plan", label)
        self.assertIn("factory:run", label)
        self.assertIn("COPILOT_GITHUB_TOKEN", label)
        self.assertIn("branches: [\"main\"]", files[".github/workflows/sfstack-quality-events.yml"])
        self.assertIn("name: sfstack quality", files[".github/workflows/sfstack-quality-required.yml"])
        self.assertIn("## Files to change", files[".github/ISSUE_TEMPLATE/factory-work-item.md"])
        self.assertIn("## Acceptance criteria", files[".github/ISSUE_TEMPLATE/factory-work-item.md"])
        for name, content in files.items():
            with self.subTest(name=name):
                self.assertNotIn(onboarding.REPO_TOKEN, content)
                self.assertNotIn(onboarding.BRANCH_TOKEN, content)
                for target in re.findall(r"uses:\s*grove/factory/\.github/workflows/[^\s@]+@([^\s]+)", content):
                    self.assertRegex(target, r"\A[a-f0-9]{40}\Z")
                self.assertNotIn("@main", content)
                self.assertNotIn("@latest", content)

    def test_custom_default_branch_is_escaped_and_exact(self):
        files = onboarding.render("another/target-repo", "release/v2")
        self.assertIn('branches: ["release/v2"]', files[".github/workflows/sfstack-quality-events.yml"])
        self.assertIn("github.repository == 'another/target-repo'", files[".github/workflows/sfstack-issue-label.yml"])
        self.assertNotIn("branches: [main]", files[".github/workflows/sfstack-quality-events.yml"])

    def test_repo_and_branch_injection_are_rejected(self):
        for repo in ("", "wrong", "../repo", "owner/../repo", "owner/repo'", "owner/repo\nother", "owner/r/extra"):
            with self.subTest(repo=repo), self.assertRaises(onboarding.InstallationError):
                onboarding.render(repo, "main")
        for branch in ("", "../main", "main..other", "bad]", "main\ninject", "release//v1", "x.lock"):
            with self.subTest(branch=branch), self.assertRaises(onboarding.InstallationError):
                onboarding.render("owner/repo", branch)

    def test_output_bundle_is_new_and_byte_verified_without_network(self):
        target = self.root / "bundle"
        files = onboarding.render("org/repo", "main")
        metadata = onboarding.manifest("org/repo", "main", files)
        with patch.object(onboarding, "command", side_effect=AssertionError("Must not access GitHub")):
            onboarding.write_bundle(target, files, metadata)
        self.assertEqual(set(files), {
            path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
        } - {"install-plan.json"})
        record = json.loads((target / "install-plan.json").read_text())
        self.assertEqual(metadata, record)
        import hashlib
        for name in files:
            self.assertEqual(record["files"][name], hashlib.sha256((target / name).read_bytes()).hexdigest())
        with self.assertRaisesRegex(onboarding.InstallationError, "already exists"):
            onboarding.write_bundle(target, files, metadata)

    def test_default_preview_never_writes_or_invokes_remote(self):
        output = io.StringIO()
        with patch.object(onboarding, "open_installation_pr", side_effect=AssertionError("No PR")), redirect_stdout(output):
            self.assertEqual(0, onboarding.main(["--repository", "example/repo"]))
        result = json.loads(output.getvalue())
        self.assertTrue(result["preview_only"])
        self.assertEqual(len(onboarding.FILES), len(result["files"]))
        self.assertNotIn("pr_url", result)

    def seed_checkout(self):
        root = self.root / "project"
        root.mkdir()
        def git(*args):
            return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                                   *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-b", "main", "--quiet")
        (root / "tests").mkdir()
        (root / "tests/test_example.py").write_text("import unittest\nclass Basic(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1, 1)\n")
        (root / "README.md").write_text("Fixture\n")
        git("add", ".")
        git("commit", "--quiet", "-m", "Initial fixture")
        git("remote", "add", "origin", "https://github.com/example/repo.git")
        return root

    def test_pr_creation_requires_clean_exact_clone_and_does_not_overwrite(self):
        root = self.seed_checkout()
        files = onboarding.render("example/repo", "main")
        self.assertEqual(root, onboarding.prepare_target(root, "example/repo", "main", files))
        (root / "untracked.txt").write_text("unsafe")
        with self.assertRaisesRegex(onboarding.InstallationError, "clean"):
            onboarding.prepare_target(root, "example/repo", "main", files)
        (root / "untracked.txt").unlink()
        with self.assertRaisesRegex(onboarding.InstallationError, "does not match"):
            onboarding.prepare_target(root, "other/repo", "main", files)
        (root / ".github/workflows").mkdir(parents=True)
        (root / ".github/workflows/sfstack-quality.yml").write_text("Existing workflow")
        subprocess.run(["git", "add", ".github/workflows/sfstack-quality.yml"], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Prior workflow"], cwd=root, check=True)
        with self.assertRaisesRegex(onboarding.InstallationError, "already contains"):
            onboarding.prepare_target(root, "example/repo", "main", files)

    def test_explicit_create_pr_prepares_only_installation_files_without_merging(self):
        root = self.seed_checkout()
        files = onboarding.render("example/repo", "main")
        original = onboarding.command
        calls = []
        def simulate(args, cwd):
            calls.append(args)
            if args[:2] == ["git", "fetch"] or args[:2] == ["git", "push"]:
                return ""
            if args == ["git", "rev-parse", "FETCH_HEAD"]:
                return original(["git", "rev-parse", "HEAD"], cwd)
            if args[:3] == ["gh", "pr", "create"]:
                return "https://github.com/example/repo/pull/1"
            if args[:2] == ["git", "commit"]:
                return original(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args[1:]], cwd)
            return original(args, cwd)
        # Simulate all external network operations while exercising real local git.
        with patch.object(onboarding, "command", side_effect=simulate):
            url = onboarding.open_installation_pr(root, "example/repo", "main", files)
        self.assertEqual("https://github.com/example/repo/pull/1", url)
        self.assertEqual("chore/install-sfstack-factory", original(["git", "branch", "--show-current"], root))
        self.assertEqual({path for path in files}, {
            name for name in original(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root).splitlines()
        })
        self.assertTrue(any(c[:3] == ["gh", "pr", "create"] for c in calls))
        self.assertFalse(any("merge" in c for call in calls for c in call))

    def test_no_tests_or_unsafe_remote_refuses_live_creation(self):
        root = self.seed_checkout()
        files = onboarding.render("example/repo", "main")
        (root / "tests/test_example.py").unlink()
        with self.assertRaisesRegex(onboarding.InstallationError, "clean"):
            onboarding.prepare_target(root, "example/repo", "main", files)
        subprocess.run(["git", "checkout", "--", "tests/test_example.py"], cwd=root, check=True)
        subprocess.run(["git", "remote", "set-url", "origin", "https://example.invalid/owner/repo"], cwd=root, check=True)
        with self.assertRaisesRegex(onboarding.InstallationError, "origin does not match"):
            onboarding.prepare_target(root, "example/repo", "main", files)


if __name__ == "__main__":
    unittest.main()
