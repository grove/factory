"""Require a real, current independent Quality result for a native PR check."""
from copy import deepcopy
import unittest
from urllib.parse import urlsplit

from integrations.github.automation import CHECK_NAME, owner, owner_text, pr_intent_digest
from integrations.github.required_quality_gate import snapshot, wait_for_quality

REPO = "fixture/inventory"
BASE, HEAD = "b" * 40, "a" * 40


class GitHubReads:
    def __init__(self):
        self.repo = {"full_name": REPO, "default_branch": "main"}
        self.base = BASE
        self.pr = {
            "number": 8, "state": "open", "title": "Quality bridge", "body": "Use pinned verification",
            "head": {"sha": HEAD, "repo": {"full_name": REPO}},
            "base": {"sha": BASE, "ref": "main", "repo": {"full_name": REPO}},
        }
        self.event = {"action": "synchronize", "number": 8,
                      "pull_request": {"number": 8, "head": {"sha": HEAD}}}
        ident = owner(8, BASE, "run", 1234, 1, "123-1", 2, intent=pr_intent_digest(self.pr))
        self.check = {
            "id": 54, "name": CHECK_NAME, "head_sha": HEAD,
            "app": {"slug": "github-actions", "id": 15368},
            "check_suite": {"id": 90}, "external_id": owner_text(ident),
            "status": "completed", "conclusion": "success",
            "output": {
                "title": "Quality passed",
                "summary": ("**Passed** independent review\n"
                            "[Download the complete evidence bundle]"
                            "(https://github.com/fixture/inventory/actions/runs/1234/artifacts/12)")
            },
        }
        self.checks = [self.check]
        self.workflow = {"id": 25, "path": ".github/workflows/sfstack-quality.yml"}
        self.run = {
            "id": 1234, "run_attempt": 1, "workflow_id": 25, "path": self.workflow["path"],
            "event": "workflow_dispatch", "head_branch": "main", "head_sha": BASE,
            "status": "completed", "conclusion": "success",
            "display_title": "sfstack quality / PR #8 / request 123-1",
            "repository": {"full_name": REPO}, "head_repository": {"full_name": REPO},
        }
        self.jobs = [{"name": name, "status": "completed", "conclusion": "success"}
                     for name in (
                         "Run pinned factory Quality / Execute pinned verification",
                         "Run pinned factory Quality / Review through Agentic Workflows / agent",
                         "Run pinned factory Quality / sfstack quality gate",
                         "Run pinned factory Quality / Publish the PR quality check",
                     )]
        self.artifact = {
            "id": 12, "name": "sfstack-quality-1", "expired": False,
            "workflow_run": {"id": 1234, "head_sha": BASE},
        }
        self.requests = []

    def get(self, path):
        self.requests.append(path)
        suffix = urlsplit(path).path
        prefix = "repos/" + REPO
        if not suffix.startswith(prefix):
            raise AssertionError("Unexpected repository.")
        route = suffix[len(prefix):]
        if route == "":
            result = self.repo
        elif route == "/pulls/8":
            result = self.pr
        elif route == "/git/ref/heads/main":
            result = {"object": {"sha": self.base}}
        elif route == "/commits/" + HEAD + "/check-runs":
            result = {"check_runs": self.checks}
        elif route == "/actions/workflows/sfstack-quality.yml":
            result = self.workflow
        elif route == "/actions/runs/1234":
            result = self.run
        elif route == "/actions/runs/1234/jobs":
            result = {"jobs": self.jobs, "total_count": len(self.jobs)}
        elif route == "/actions/runs/1234/artifacts":
            result = {"artifacts": [self.artifact], "total_count": 1}
        else:
            raise AssertionError("Unexpected API read: " + route)
        return deepcopy(result)


class RequiredQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.api = GitHubReads()

    def result(self):
        return snapshot(self.api, REPO, self.api.event)

    def test_pinned_quality_success_with_evidence_is_accepted_read_only(self):
        self.assertEqual("passed", self.result()[0])
        self.assertTrue(self.api.requests)
        self.assertTrue(all("repos/" + REPO in p for p in self.api.requests))

    def test_missing_or_incomplete_quality_waits_without_inventing_success(self):
        self.api.checks = []
        self.assertEqual("pending", self.result()[0])
        self.api.checks = [self.api.check]
        self.api.check["status"] = "in_progress"
        self.assertEqual("pending", self.result()[0])

    def test_fail_closed_on_negative_quality_and_wrong_app_or_provenance(self):
        for attr, val in (("conclusion", "failure"), ("status", "cancelled")):
            with self.subTest(attr=attr):
                self.api = GitHubReads()
                self.api.check[attr] = val
                self.assertNotEqual("passed", self.result()[0])
        for mutate in (
            lambda a: a.check["app"].update(id=123),
            lambda a: a.run.update(event="workflow_run"),
            lambda a: a.run.update(run_attempt=2),
            lambda a: a.run.update(conclusion="failure"),
            lambda a: a.run.update(head_sha="f" * 40),
            lambda a: a.workflow.update(id=999),
            lambda a: a.jobs[2].update(conclusion="failure"),
            lambda a: a.artifact.update(expired=True),
            lambda a: a.artifact["workflow_run"].update(id=3),
            lambda a: a.check["output"].update(summary="Passed, but no evidence"),
        ):
            self.api = GitHubReads()
            mutate(self.api)
            self.assertNotEqual("passed", self.result()[0])

    def test_changed_pr_head_base_intent_and_forks_never_pass(self):
        for mutate in (
            lambda a: a.pr["head"].update(sha="f" * 40),
            lambda a: setattr(a, "base", "f" * 40),
            lambda a: a.pr.update(body="New acceptance criterion"),
            lambda a: a.pr["head"]["repo"].update(full_name="outsider/fork"),
            lambda a: a.pr.update(state="closed"),
            lambda a: a.event.update(action="labeled"),
        ):
            self.api = GitHubReads()
            mutate(self.api)
            self.assertNotEqual("passed", self.result()[0])

    def test_duplicate_complete_copies_must_agree(self):
        self.api.checks.append({**deepcopy(self.api.check), "id": 55})
        self.assertEqual("passed", self.result()[0])
        self.api.checks[1]["conclusion"] = "failure"
        with self.assertRaisesRegex(ValueError, "Multiple owned checks"):
            self.result()

    def test_old_intent_or_pending_generation_cannot_reuse_clearance(self):
        self.api.pr["title"] = "Different issue intent"
        self.assertEqual("pending", self.result()[0])

    def test_timeout_does_not_launch_another_assessment(self):
        self.api.checks = []
        times = iter([0, 0, 5])
        sleeps = []
        result = wait_for_quality(self.api, REPO, self.api.event, timeout_seconds=4,
                                  monotonic=lambda: next(times), sleep=sleeps.append)
        self.assertFalse(result)
        self.assertEqual([], sleeps)

    def test_read_only_workflow_contract(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] /
                  ".github/workflows/sfstack-quality-required.yml").read_text()
        self.assertIn("  pull_request:\n", source)
        self.assertIn("name: sfstack quality\n", source)
        self.assertIn("checks: read\n", source)
        self.assertIn("pull-requests: read\n", source)
        self.assertIn("actions: read\n", source)
        self.assertIn("persist-credentials: false", source)
        self.assertNotIn("pull_request_target:", source)
        self.assertNotIn("checks: write", source)
        self.assertNotIn("actions: write", source)
        self.assertNotIn("COPILOT_GITHUB_TOKEN", source)
        self.assertNotIn("github.event.pull_request.title", source)
        self.assertIn("timeout-minutes: 35", source)


if __name__ == "__main__":
    unittest.main()
