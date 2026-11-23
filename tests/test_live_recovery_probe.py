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

    def test_live_probe_workflows_are_retired_with_permanent_audit(self):
        # The temporary write-capable acceptance workflows must no longer
        # be deployable from the protected default branch.
        self.assertFalse((ROOT / ".github/workflows/sfstack-live-recovery.yml").exists())
        self.assertFalse((ROOT / ".github/workflows" / NO_AI).exists())
        record = (ROOT / "docs/evidence/live-recovery-2026-11-23.md").read_text()
        self.assertIn("45144342739", record)
        self.assertIn("d3a66e308c3308e1fa1b52649ec5ef6b94b0957f5b5041f5053ecb8b5d45b618", record)
        self.assertIn("not a physical network partition", record)
        archive_manifest = ROOT / "docs/evidence/live-recovery-2026-11-23-manifest.json"
        self.assertTrue(archive_manifest.is_file())

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
