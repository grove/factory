"""No-model tests for labeled authorization, isolated advisory plans and claims."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from integrations.github import issue_labels, plan_advice

BASE = "a" * 40
BODY = """## Exact permitted scope
1. Implementation: \x60examples/answer.py\x60.
2. New regression: \x60tests/test_answer.py\x60.

## Observable acceptance criteria
1. Existing behavior must fail the new assertion in a real RED run.
2. Repaired behavior passes the identical regression and full suite.
"""


class LabelAPI:
    def __init__(self):
        self.repository = {"full_name": "fixture/software", "default_branch": "main"}
        self.workflow = {"id": 801, "path": ".github/workflows/sfstack-issue-label.yml"}
        self.run = {"id": 1234, "run_attempt": 1, "workflow_id": 801,
                    "path": self.workflow["path"], "event": "issues",
                    "repository": self.repository, "head_repository": self.repository,
                    "head_branch": "main", "head_sha": BASE,
                    "actor": {"login": "maintainer"}, "triggering_actor": {"login": "maintainer"}}
        self.issue = {"number": 7, "state": "open", "title": "defect: child remains alive",
                      "body": BODY, "updated_at": "2026-11-23T10:00:00Z",
                      "labels": [{"name": "factory:plan"}]}
        self.branch = BASE
        self.permission = "write"
        self.comments = []
        self.posts = []

    def get(self, path):
        prefix = "repos/fixture/software/"
        if path == "repos/fixture/software":
            return deepcopy(self.repository)
        assert path.startswith(prefix), path
        suffix = path[len(prefix):]
        if suffix == "":
            return deepcopy(self.repository)
        if suffix.startswith("actions/runs/"):
            return {**deepcopy(self.run), "id": int(suffix.rsplit("/", 1)[-1])}
        if suffix == "actions/workflows/sfstack-issue-label.yml":
            return deepcopy(self.workflow)
        if suffix == "git/ref/heads/main":
            return {"object": {"sha": self.branch}}
        if suffix == "collaborators/maintainer/permission":
            return {"permission": self.permission}
        if suffix == "issues/7":
            return deepcopy(self.issue)
        if suffix.startswith("issues/7/comments?per_page=100&page="):
            page = int(suffix.rsplit("=", 1)[-1])
            return deepcopy(self.comments[(page - 1) * 100:page * 100])
        raise AssertionError("Unexpected GET: " + suffix)

    def post(self, path, body):
        self.posts.append((path, body))
        assert path == "repos/fixture/software/issues/7/comments", path
        comment = {"user": {"login": "github-actions[bot]", "type": "Bot"},
                   "body": body["body"], "id": len(self.comments) + 500}
        self.comments.append(comment)
        return deepcopy(comment)


class IssueLabelTests(unittest.TestCase):
    def setUp(self):
        self.api = LabelAPI()
        self.context = {"repository": "fixture/software", "run_id": "1234",
                        "run_attempt": "1", "workflow_sha": BASE,
                        "ref": "refs/heads/main", "event_name": "issues"}
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.event = Path(self.tmp.name) / "event.json"
        self.payload = {"action": "labeled", "label": {"name": "factory:plan"},
                        "issue": {"number": 7}, "repository": self.api.repository,
                        "sender": {"login": "maintainer"}}
        self.env = patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(self.event)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.write_event()

    def write_event(self):
        self.event.write_text(json.dumps(self.payload), encoding="utf-8")

    def mark_run(self):
        self.payload["label"]["name"] = "factory:run"
        self.api.issue["labels"].append({"name": "factory:run"})
        self.write_event()

    def mark_direct_run(self):
        self.mark_run()
        # No factory:plan label or prior bot snapshot for the direct route.
        self.api.issue["labels"] = [{"name": "factory:run"}]

    def fake_ai(self):
        proposal = {
            "version": 1,
            "steps": [
                {"file": "examples/answer.py",
                 "action": "Inspect the answer computation and repair the specific incorrect return value."},
                {"file": "tests/test_answer.py",
                 "action": "Introduce a new unittest assertion that detects the original wrong answer."},
            ],
            "verification": [
                {"criterion": 1, "method": "Run tests/test_answer.py against the unchanged base for real RED, then repaired GREEN."},
                {"criterion": 2, "method": "Run the exact tests/test_answer.py GREEN regression and full unittest discovery."},
            ],
            "risks": ["The test may accidentally assert the implementation rather than observable behavior."],
            "questions": [],
        }
        issue_labels.publish_ai_plan(self.api, self.context, json.dumps(proposal))
        return proposal

    def test_plan_only_previews_then_one_exact_paid_run_claim(self):
        preview = issue_labels.approve_label(self.api, self.context)
        self.assertFalse(preview["run"])
        self.assertEqual(["examples/answer.py", "tests/test_answer.py"], preview["plan"]["allowed_paths"])
        self.assertEqual("defect", preview["plan"]["repair_mode"])
        self.assertEqual("tests/test_answer.py", preview["plan"]["regression_file"])
        self.assertEqual(1, len(self.api.posts))
        self.fake_ai()
        self.assertEqual(2, len(self.api.posts))
        self.mark_run()
        approved = issue_labels.approve_label(self.api, self.context)
        self.assertTrue(approved["run"])
        self.assertEqual(preview["plan"], approved["plan"])
        self.assertEqual(3, len(self.api.posts))
        verified = issue_labels.verify_claim(self.api, self.context, "maintainer")
        self.assertEqual(approved["plan"], {k: v for k, v in verified.items()
                           if k not in {"advisory_plan", "ai_plan_sha256"}})
        self.assertEqual(self.fake_proposal_digest(), verified["ai_plan_sha256"])
        with self.assertRaisesRegex(ValueError, "already has a durable Factory run claim"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(3, len(self.api.posts))

    def fake_proposal_digest(self):
        record = issue_labels.current_ai_plan(self.api, self.context["repository"],
                                              issue_labels.parse_plan(self.api.issue, self.context["repository"], BASE))
        return record["digest"]

    def test_software_host_requires_and_preserves_the_exact_label_claim(self):
        from integrations.github import software
        issue_labels.approve_label(self.api, self.context)
        self.fake_ai()
        self.mark_run()
        with self.assertRaisesRegex(ValueError, "unique, unchanged trusted Factory authorization"):
            software.SoftwareHost(self.api, self.context).admitted()
        claimed = issue_labels.approve_label(self.api, self.context)
        host = software.SoftwareHost(self.api, self.context)
        repository, source, actor = host.admitted()
        self.assertEqual("maintainer", actor)
        self.assertEqual(claimed["plan"], {k: v for k, v in host.label_plan.items()
                         if k not in {"advisory_plan", "ai_plan_sha256"}})
        self.assertEqual(self.fake_proposal_digest(), host.label_plan["ai_plan_sha256"])
        self.assertEqual("main", repository["default_branch"])
        with self.assertRaisesRegex(ValueError, "Label run parameters differ"):
            host.prepare(Path(self.tmp.name), 7, ["README.md"],
                         claimed["plan"]["acceptance_criteria"], Path(self.tmp.name) / "out",
                         mode="defect", regression_file="tests/test_answer.py")

    def test_direct_run_claims_exact_scope_without_separate_paid_planning(self):
        from integrations.github import software
        self.mark_direct_run()
        with patch.object(issue_labels, "current_ai_plan",
                          side_effect=AssertionError("Direct mode must not require a paid AI plan")):
            authorized = issue_labels.approve_label(self.api, self.context)
            verified = issue_labels.verify_claim(self.api, self.context, "maintainer")
            host = software.SoftwareHost(self.api, self.context)
            repository, _, actor = host.admitted()
        self.assertTrue(authorized["run"])
        self.assertNotIn("plan_requested", authorized)
        self.assertEqual(1, len(self.api.posts))
        claim = issue_labels.parse_marker(self.api.comments[0], issue_labels.CLAIM_MARKER)
        self.assertEqual("direct", claim["planning_mode"])
        self.assertNotIn("ai_plan_sha256", claim)
        self.assertNotIn("ai_plan_run_id", claim)
        self.assertIn("Direct build (no separate AI plan)", self.api.comments[0]["body"])
        self.assertEqual({**authorized["plan"], "advisory_plan": None,
                          "ai_plan_sha256": None}, verified)
        self.assertEqual(verified, host.label_plan)
        self.assertEqual("maintainer", actor)
        self.assertEqual("main", repository["default_branch"])
        with self.assertRaisesRegex(ValueError, "already has a durable Factory run claim"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(1, len(self.api.posts))

    def test_direct_host_rejects_injected_ai_advice_or_digest(self):
        from integrations.github import software
        self.mark_direct_run()
        authorized = issue_labels.approve_label(self.api, self.context)
        plan = authorized["plan"]
        target = {
            "issue": software.issue_snapshot(self.api.issue, self.context["repository"]),
            "allowed_files": {path: {} for path in plan["allowed_paths"]},
            "criteria": software.criteria(plan["acceptance_criteria"]),
            "mode": plan["repair_mode"], "regression_file": plan["regression_file"],
            "actor": "maintainer", "repository": self.context["repository"],
            "run_id": self.context["run_id"], "run_attempt": self.context["run_attempt"],
            "base_sha": BASE, "base_branch": "main",
        }
        host = software.SoftwareHost(self.api, self.context)
        host.current(target)
        target["advisory_plan"] = {"invented": "AI approval"}
        with self.assertRaisesRegex(ValueError, "outside the claimed label plan"):
            host.current(target)
        target.pop("advisory_plan")
        target["ai_plan_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "outside the claimed label plan"):
            host.current(target)

    def test_direct_run_refuses_existing_plan_label_without_publication(self):
        # An in-flight or failed factory:plan label is not permission to
        # silently skip paid planning and start implementation.
        self.mark_run()
        with self.assertRaisesRegex(ValueError, "factory:plan is present"):
            issue_labels.approve_label(self.api, self.context)
        self.assertFalse(self.api.posts)

    def test_direct_run_rechecks_issue_base_identity_and_label(self):
        self.mark_direct_run()
        issue_labels.approve_label(self.api, self.context)
        original_body = self.api.issue["body"]
        self.api.issue["body"] += "\nExtra unreviewed requirement.\n"
        with self.assertRaises(ValueError):
            issue_labels.verify_claim(self.api, self.context, "maintainer")
        self.api.issue["body"] = original_body
        self.api.branch = "f" * 40
        with self.assertRaisesRegex(ValueError, "Default branch advanced"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")
        self.api.branch = BASE
        self.context["run_id"] = "1235"
        with self.assertRaisesRegex(ValueError, "unique, unchanged trusted Factory authorization"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")
        self.context["run_id"] = "1234"
        self.api.issue["labels"].append({"name": "factory:plan"})
        with self.assertRaisesRegex(ValueError, "earlier AI planning request"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")

    def test_direct_run_rejects_forged_or_duplicate_bot_claim(self):
        self.mark_direct_run()
        issue_labels.approve_label(self.api, self.context)
        valid = deepcopy(self.api.comments[0])
        self.api.comments[0]["user"] = {"login": "forger", "type": "User"}
        with self.assertRaisesRegex(ValueError, "unique, unchanged trusted Factory authorization"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")
        self.api.comments[0] = valid
        self.api.comments.append(deepcopy(valid))
        with self.assertRaisesRegex(ValueError, "unique, unchanged trusted Factory authorization"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")

    def test_direct_run_does_not_downgrade_failed_or_orphaned_ai_planning(self):
        issue_labels.approve_label(self.api, self.context)
        self.mark_run()
        self.api.issue["labels"] = [{"name": "factory:run"}]
        with self.assertRaisesRegex(ValueError, "Missing or ambiguous validated AI plan"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(1, len(self.api.posts))
        # Even if the original snapshot is absent, an orphaned authenticated
        # AI-plan comment is not evidence that the direct route was chosen.
        self.api.issue["labels"] = [{"name": "factory:plan"}]
        self.payload["label"]["name"] = "factory:plan"
        self.write_event()
        self.fake_ai()
        self.api.comments = [c for c in self.api.comments if not c["body"].startswith(
            issue_labels.PLAN_MARKER)]
        self.mark_direct_run()
        with self.assertRaisesRegex(ValueError, "AI planning history"):
            issue_labels.approve_label(self.api, self.context)

    def test_direct_run_still_requires_writer_and_first_attempt(self):
        self.mark_direct_run()
        self.api.permission = "read"
        with self.assertRaisesRegex(ValueError, "repository writer"):
            issue_labels.approve_label(self.api, self.context)
        self.api.permission = "write"
        self.context["run_attempt"] = "2"
        with self.assertRaisesRegex(ValueError, "current run attempt"):
            issue_labels.approve_label(self.api, self.context)
        self.assertFalse(self.api.posts)

    def test_changed_issue_invalidates_approved_plan(self):
        issue_labels.approve_label(self.api, self.context)
        self.mark_run()
        self.api.issue["body"] += "\nAn added requirement cannot silently inherit authorization.\n"
        with self.assertRaisesRegex(ValueError, "No current reviewed Factory plan"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(1, len(self.api.posts))

    def test_advanced_main_invalidates_plan_without_a_paid_run(self):
        issue_labels.approve_label(self.api, self.context)
        self.mark_run()
        self.api.branch = "f" * 40
        with self.assertRaisesRegex(ValueError, "Default branch advanced"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(1, len(self.api.posts))

    def test_nonwriters_and_bots_cannot_authorize(self):
        for permission in ("triage", "read"):
            self.api.permission = permission
            with self.subTest(permission=permission), self.assertRaisesRegex(ValueError, "repository writer"):
                issue_labels.approve_label(self.api, self.context)
        self.api.permission = "write"
        self.api.run["triggering_actor"] = {"login": "github-actions[bot]"}
        with self.assertRaisesRegex(ValueError, "human label author"):
            issue_labels.approve_label(self.api, self.context)
        self.assertFalse(self.api.posts)

    def test_untrusted_event_or_non_first_attempt_never_claims(self):
        for action, label in (("unlabeled", "factory:plan"), ("labeled", "other")):
            self.payload["action"] = action
            self.payload["label"]["name"] = label
            self.write_event()
            with self.subTest(action=action, label=label), self.assertRaisesRegex(ValueError, "authenticated issue-label"):
                issue_labels.approve_label(self.api, self.context)
        self.payload["action"] = "labeled"
        self.payload["label"]["name"] = "factory:plan"
        self.write_event()
        self.context["run_attempt"] = "2"
        with self.assertRaises(ValueError):
            issue_labels.approve_label(self.api, self.context)
        self.assertFalse(self.api.posts)

    def test_claim_must_be_from_github_bot(self):
        issue_labels.approve_label(self.api, self.context)
        self.fake_ai()
        self.mark_run()
        issue_labels.approve_label(self.api, self.context)
        self.api.comments[-1]["user"] = {"login": "untrusted-user", "type": "User"}
        with self.assertRaisesRegex(ValueError, "no unique, unchanged trusted Factory authorization"):
            issue_labels.verify_claim(self.api, self.context, "maintainer")

    def test_claim_cannot_be_reused_by_another_run_or_actor(self):
        issue_labels.approve_label(self.api, self.context)
        self.fake_ai()
        self.mark_run()
        issue_labels.approve_label(self.api, self.context)
        with self.assertRaisesRegex(ValueError, "Only the approved factory:run label"):
            issue_labels.verify_claim(self.api, self.context, "other")
        self.context["run_id"] = "1235"
        with self.assertRaises(ValueError):
            issue_labels.verify_claim(self.api, self.context, "maintainer")

    def test_plan_requires_fresh_model_output_and_is_not_free(self):
        preview = issue_labels.approve_label(self.api, self.context)
        self.assertTrue(preview["plan_requested"])
        with self.assertRaisesRegex(ValueError, "already planned"):
            issue_labels.approve_label(self.api, self.context)
        self.mark_run()
        with self.assertRaisesRegex(ValueError, "Missing or ambiguous validated AI plan"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(1, len(self.api.posts))

    def test_bad_ai_scope_and_missing_verification_do_not_publish(self):
        issue_labels.approve_label(self.api, self.context)
        original = self.fake_ai()
        self.assertEqual(2, len(self.api.posts))
        for failure in (
            {**original, "steps": [{**original["steps"][0], "file": "integrations/github/automation.py"},
                                   original["steps"][1]]},
            {**original, "verification": original["verification"][:1]},
            {**original, "risks": []},
            {**original, "verification": [
                {"criterion": 1, "method": self.api.issue["body"].splitlines()[4]},
                original["verification"][1]]},
        ):
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                plan_advice.validate(json.dumps(failure), issue_labels.parse_plan(
                    self.api.issue, self.context["repository"], BASE))
        with self.assertRaisesRegex(ValueError, "already published"):
            issue_labels.publish_ai_plan(self.api, self.context, json.dumps(original))
        self.assertEqual(2, len(self.api.posts))

    def test_ai_plan_human_visible_tampering_or_changed_issue_blocks_run(self):
        issue_labels.approve_label(self.api, self.context)
        self.fake_ai()
        self.mark_run()
        self.api.comments[-1]["body"] += "\nMalicious new instruction."
        with self.assertRaisesRegex(ValueError, "Human-visible planning comment"):
            issue_labels.approve_label(self.api, self.context)
        self.assertEqual(2, len(self.api.posts))

    def test_path_scope_and_criteria_are_fail_closed(self):
        for body in (
            "## Files to change\n- \x60integrations/github/admin.py\x60\n## Acceptance criteria\n- Do a thing.\n",
            "## Files to change\n- \x60examples/answer.py\x60\n## Acceptance criteria\n",
            "## Files to change\n- \x60examples/answer.py\x60\n## Acceptance criteria\n- A.\n" "- A.\n",
            "## Files to change\n- \x60examples/answer.py\x60\n- \x60examples/answer.py\x60\n## Acceptance criteria\n- A.\n",
        ):
            with self.subTest(body=body):
                self.api.issue["body"] = body
                with self.assertRaises(ValueError):
                    issue_labels.parse_plan(self.api.issue, "fixture/software", BASE)

    def test_change_mode_without_regression(self):
        self.api.issue.update({"title": "docs: explain CLI", "body":
                              "## Allowed files\n- \x60docs/how-to/run-local.md\x60\n\n"
                              "## Acceptance criteria\n- Show one runnable example.\n"})
        plan = issue_labels.parse_plan(self.api.issue, "fixture/software", BASE)
        self.assertEqual("change", plan["repair_mode"])
        self.assertEqual("", plan["regression_file"])


if __name__ == "__main__":
    unittest.main()
