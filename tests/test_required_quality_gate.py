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

    def test_positive_check_waits_for_exact_workflow_completion(self):
        for status in ("queued", "in_progress"):
            with self.subTest(status=status):
                self.api = GitHubReads()
                self.api.run.update(status=status, conclusion=None)
                self.assertEqual("pending", self.result()[0])
                self.assertFalse(any("/jobs?" in p or "/artifacts?" in p
                                     for p in self.api.requests))
                self.api.run.update(status="completed", conclusion="success")
                self.assertEqual("passed", self.result()[0])

    def test_wait_polls_until_authenticated_run_completes(self):
        self.api.run.update(status="in_progress", conclusion=None)
        times = iter([0, 1])
        sleeps = []

        def complete(seconds):
            sleeps.append(seconds)
            self.api.run.update(status="completed", conclusion="success")

        self.assertTrue(wait_for_quality(
            self.api, REPO, self.api.event, timeout_seconds=4,
            interval_seconds=1, monotonic=lambda: next(times), sleep=complete))
        self.assertEqual([1], sleeps)

    def test_pending_workflow_identity_must_be_authenticated_first(self):
        for change in (
            {"id": 4321}, {"workflow_id": 999}, {"path": ".github/workflows/other.yml"},
            {"event": "workflow_run"}, {"head_branch": "other"},
            {"head_sha": "f" * 40}, {"run_attempt": 2},
            {"display_title": "Unrelated assessment"},
            {"repository": {"full_name": "other/repo"}},
            {"head_repository": {"full_name": "other/repo"}},
        ):
            with self.subTest(change=change):
                self.api = GitHubReads()
                self.api.run.update(status="in_progress", conclusion=None)
                self.api.run.update(change)
                self.assertEqual("blocked", self.result()[0])

    def test_non_successful_or_inconsistent_run_states_block(self):
        for status, conclusion in (("completed", "failure"), ("completed", "cancelled"),
                                   ("completed", None), ("in_progress", "failure"),
                                   ("queued", "success"), ("unknown", None)):
            with self.subTest(status=status, conclusion=conclusion):
                self.api = GitHubReads()
                self.api.run.update(status=status, conclusion=conclusion)
                self.assertEqual("blocked", self.result()[0])

    def test_timeout_during_authenticated_completion_remains_nonpassing(self):
        self.api.run.update(status="in_progress", conclusion=None)
        times = iter([0, 5])
        sleeps = []
        self.assertFalse(wait_for_quality(
            self.api, REPO, self.api.event, timeout_seconds=4,
            monotonic=lambda: next(times), sleep=sleeps.append))
        self.assertEqual([], sleeps)

    def retire_check(self):
        self.api.check.update(conclusion="failure", output={
            "title": "Quality assessment superseded",
            "summary": ("A newer assessment requires fresh evidence. "
                        "This result no longer grants quality clearance."),
        })

    def test_supersession_gap_never_reuses_retired_clearance(self):
        successor = deepcopy(self.api.check)
        self.retire_check()
        self.assertEqual("pending", self.result()[0])
        successor.update(id=55, status="in_progress", conclusion=None)
        successor["external_id"] = owner_text(owner(
            8, BASE, "run", 1234, 1, "123-1", 3, intent=pr_intent_digest(self.api.pr)))
        self.api.checks.append(successor)
        self.assertEqual("pending", self.result()[0])
        successor.update(status="completed", conclusion="success")
        self.assertEqual("passed", self.result()[0])

    def test_negative_quality_cannot_masquerade_as_supersession(self):
        self.retire_check()
        self.api.check["output"]["summary"] = "A real negative assessment."
        self.assertEqual("blocked", self.result()[0])
        self.retire_check()
        self.api.check["app"]["id"] = 123
        self.assertEqual("blocked", self.result()[0])

    def test_generation_change_during_evidence_reads_never_passes(self):
        successor = deepcopy(self.api.check)
        successor.update(id=55, status="in_progress", conclusion=None)
        successor["external_id"] = owner_text(owner(
            8, BASE, "run", 1234, 1, "123-1", 3, intent=pr_intent_digest(self.api.pr)))
        original_get = self.api.get

        def get(path):
            result = original_get(path)
            if "/artifacts?" in path:
                self.retire_check()
                self.api.checks.append(successor)
            return result

        self.api.get = get
        self.assertEqual("pending", self.result()[0])

    def test_check_retired_or_failed_during_evidence_reads_never_passes(self):
        for retired in (True, False):
            with self.subTest(retired=retired):
                self.api = GitHubReads()
                original_get = self.api.get

                def get(path):
                    result = original_get(path)
                    if "/artifacts?" in path:
                        if retired:
                            self.retire_check()
                        else:
                            self.api.check["conclusion"] = "failure"
                    return result

                self.api.get = get
                self.assertEqual("pending" if retired else "blocked", self.result()[0])

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
        times = iter([0, 5])
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
        self.assertIn("ref: 3982085ba70d782ae51aad03e126001002161bc5", source)
        self.assertIn("repository: grove/factory", source)
        self.assertIn("working-directory: trusted", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("pull_request_target:", source)
        self.assertNotIn("checks: write", source)
        self.assertNotIn("actions: write", source)
        self.assertNotIn("COPILOT_GITHUB_TOKEN", source)
        self.assertNotIn("github.event.pull_request.title", source)
        self.assertIn("timeout-minutes: 35", source)


if __name__ == "__main__":
    unittest.main()
