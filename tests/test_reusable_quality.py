"""Cross-repository Quality reuse retains caller-scoped authority.

The reusable workflow's controller checkout must be bound to the callee SHA,
but checks and run provenance must be verified against the caller repository.
"""
from pathlib import Path
import unittest

from integrations.github.automation import Host, QUALITY

ROOT = Path(__file__).resolve().parents[1]


class FakeAPI:
    def __init__(self, *, path=".github/workflows/sfstack-quality.yml",
                 repo="grove/sfstack", head="a" * 40, attempt=1):
        self.run = {
            "id": 9876, "run_attempt": attempt,
            "workflow_id": 1234, "path": path, "event": "workflow_dispatch",
            "repository": {"full_name": repo},
            "head_repository": {"full_name": repo},
            "head_branch": "main", "head_sha": head,
        }

    def get(self, path):
        if path == "repos/grove/sfstack":
            return {"full_name": "grove/sfstack", "default_branch": "main"}
        if path == "repos/grove/sfstack/actions/workflows/sfstack-quality.yml":
            return {"id": 1234, "path": ".github/workflows/sfstack-quality.yml"}
        if path == "repos/grove/sfstack/actions/runs/9876":
            return self.run
        raise AssertionError("Unexpected GitHub API request: " + path)


def context():
    return {
        "repository": "grove/sfstack", "run_id": "9876",
        "run_attempt": "1", "workflow_sha": "a" * 40,
        "ref": "refs/heads/main", "event_name": "workflow_dispatch",
    }


class ReusableQualityBoundaryTests(unittest.TestCase):
    def test_caller_run_identity_is_accepted_for_the_named_shim_only(self):
        # The factory code is checked out from job.workflow_sha. GITHUB_WORKFLOW_SHA
        # and GitHub Actions run identity remain bound to the caller's sfstack main.
        api = FakeAPI()
        repo, run = Host(api, context()).trusted_context(QUALITY, {"workflow_dispatch"})
        self.assertEqual("main", repo["default_branch"])
        self.assertEqual("grove/sfstack", run["repository"]["full_name"])
        self.assertEqual(9876, run["id"])

    def test_mismatched_caller_workflow_event_revision_or_repository_fails_closed(self):
        attempts = [
            ({"path": ".github/workflows/fake.yml"}, {}),
            ({"workflow_id": 1235}, {}),
            ({"head_sha": "b" * 40}, {}),
            ({"head_branch": "feature"}, {}),
            ({"event": "pull_request"}, {}),
            ({"repository": {"full_name": "grove/factory"}}, {}),
            ({}, {"ref": "refs/heads/feature"}),
            ({}, {"event_name": "pull_request"}),
            ({}, {"workflow_sha": "b" * 40}),
            ({}, {"run_attempt": "2"}),
        ]
        for run_patch, context_patch in attempts:
            with self.subTest(run_patch=run_patch, context_patch=context_patch):
                api = FakeAPI()
                api.run.update(run_patch)
                current = context()
                current.update(context_patch)
                with self.assertRaises(ValueError):
                    Host(api, current).trusted_context(QUALITY, {"workflow_dispatch"})

    def test_reusable_callee_source_and_nested_workflow_are_sha_bound(self):
        source = (ROOT / ".github/workflows/sfstack-quality.yml").read_text()
        self.assertIn("  workflow_call:\n", source)
        self.assertIn("  workflow_dispatch:\n", source)
        self.assertIn("      COPILOT_GITHUB_TOKEN:\n        required: true", source)
        self.assertIn("    uses: $/.github/workflows/sfstack-review.lock.yml", source)
        self.assertNotIn("uses: ./.github/workflows/sfstack-review.lock.yml", source)
        self.assertNotIn("ref: $" + "{{ github.workflow_sha }}", source)
        # Exactly five controller checkouts. Candidate checkout must still
        # target the authenticated caller repository at the pinned PR head.
        self.assertEqual(5, source.count("repository: $" + "{{ job.workflow_repository }}"))
        self.assertEqual(5, source.count("ref: $" + "{{ job.workflow_sha }}"))
        self.assertEqual(2, source.count("repository: $" + "{{ github.repository }}"))
        self.assertIn("ref: $" + "{{ needs.start_check.outputs.head-sha }}", source)
        self.assertIn("ref: $" + "{{ needs.prepare.outputs.head-sha }}", source)
        self.assertIn("group: sfstack-quality-publication-$" + "{{ github.repository }}", source)
        self.assertIn("github.event.repository.default_branch", source)

if __name__ == "__main__":
    unittest.main()
