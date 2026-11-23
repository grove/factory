"""Fail-closed boundaries for the opt-in live GitHub post-ACK probe."""
from collections import Counter
from pathlib import Path
import unittest
from unittest.mock import Mock

from evals.live_recovery_probe import (
    CANARY, ISSUE, MUTATIONS, NO_AI, REPO, DropAfterRealPost,
)

ROOT = Path(__file__).resolve().parents[1]


class LiveRecoveryBoundaryTests(unittest.TestCase):
    def fake(self):
        wrapper = DropAfterRealPost.__new__(DropAfterRealPost)
        wrapper.api = Mock()
        wrapper.api.post.return_value = {"created": True}
        wrapper.counts = Counter()
        wrapper.dropped = set()
        return wrapper

    def test_every_fault_is_injected_only_after_a_real_accepted_post(self):
        api = self.fake()
        for kind in MUTATIONS:
            with self.subTest(kind=kind):
                path = "repos/" + REPO + kind
                previous = api.api.post.call_count
                with self.assertRaisesRegex(OSError, "post-ACK"):
                    api.post(path, {"nonce": "safe"})
                self.assertEqual(previous + 1, api.api.post.call_count)
                self.assertEqual(1, api.counts[kind])
                with self.assertRaisesRegex(ValueError, "Duplicate mutable POST"):
                    api.post(path, {"nonce": "safe"})
                self.assertEqual(previous + 1, api.api.post.call_count)
        self.assertEqual(set(MUTATIONS), api.dropped)

    def test_immutable_git_objects_do_not_inject_an_error(self):
        api = self.fake()
        for kind in ("/git/blobs", "/git/trees", "/git/commits"):
            self.assertEqual({"created": True},
                             api.post("repos/" + REPO + kind, {"safe": True}))
        self.assertEqual(Counter(), api.counts)

    def test_workflows_are_manually_triggered_no_ai_and_isolated(self):
        live = (ROOT / ".github/workflows/sfstack-live-recovery.yml").read_text()
        noai = (ROOT / ".github/workflows/" + NO_AI).read_text()
        for content in (live, noai):
            self.assertIn("  workflow_dispatch:", content)
            self.assertNotIn("  pull_request:", content)
            self.assertNotIn("pull_request_target:", content)
            self.assertNotIn("  push:", content)
            self.assertNotIn("COPILOT_GITHUB_TOKEN", content)
            self.assertNotIn("sfstack-build.lock.yml", content)
            self.assertNotIn("sfstack-review.lock.yml", content)
        self.assertIn("github.actor == 'grove'", live)
        self.assertIn("inputs.issue-number == 9", live)
        self.assertIn("sfstack-quality-publication-", live)
        self.assertIn("contents: write", live)
        self.assertIn("pull-requests: write", live)
        self.assertIn("checks: write", live)
        self.assertIn("actions: write", live)
        self.assertIn("  permissions: {}", noai)
        self.assertNotIn("checks: write", noai)
        self.assertNotIn("actions: write", noai)
        self.assertIn("sleep 60", noai)

    def test_dummy_scope_and_nonapproval_cleanup_are_explicit(self):
        self.assertEqual(REPO, "grove/factory")
        self.assertEqual(ISSUE, 9)
        self.assertEqual(CANARY, "docs/live-recovery-probe.md")
        code = (ROOT / "evals/live_recovery_probe.py").read_text()
        self.assertIn('conclusion="failure"', code)
        self.assertIn('{"state": "closed"}', code)
        self.assertIn('closed.get("merged_at")', code)
        self.assertNotIn("merge_authorized = True", code)
        self.assertNotIn("merge_pull_request(", code)
        self.assertIn("SoftwareHost(api, c).publish(", code)


if __name__ == "__main__":
    unittest.main()
