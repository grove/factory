"""Offline read-only operational summaries using GitHub-shaped evidence fixtures."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
import base64
import hashlib
import json
import unittest
import zipfile

from integrations.github import automation, issue_labels, plan_advice, run_summary

REPO = "fixture/software"
BASE, HEAD, PIN = "a" * 40, "b" * 40, "c" * 40
REF = "grove/factory/.github/workflows/sfstack-build.lock.yml@" + PIN
QUALITY_REF = "grove/factory/.github/workflows/sfstack-review.lock.yml@" + PIN
PLANNER = "Generate actionable Copilot implementation proposal (paid, no writes)"
PUBLISH_PLAN = "Revalidate exact issue and publish bounded human-reviewable plan"
BUILD = "Execute pinned, already-authorized Software Factory / "
EVIDENCE = "https://github.com/" + REPO + "/actions/runs/42/artifacts/90"
QUALITY_EVIDENCE = "https://github.com/" + REPO + "/actions/runs/43/artifacts/91"


def marker(prefix, record, message=""):
    return {"user": {"login": "github-actions[bot]", "type": "Bot"},
            "body": prefix + base64.urlsafe_b64encode(
                issue_labels.canonical(record).encode()).decode() + " -->\n\n" + message}


def run(number, label=None):
    path = run_summary.LABEL_PATH if label else run_summary.QUALITY_PATH
    source = REF if label else QUALITY_REF
    return {"id": number, "run_attempt": 1, "workflow_id": 10 if label else 11,
            "path": path, "event": "issues" if label else "workflow_dispatch",
            "display_title": f"sfstack issue #7 / {label}" if label else "sfstack quality / PR #9 / request 42-1",
            "head_branch": "main", "head_sha": BASE, "actor": {"login": "maintainer"},
            "repository": {"full_name": REPO}, "head_repository": {"full_name": REPO},
            "status": "completed", "conclusion": "success",
            "referenced_workflows": [{"path": source, "sha": PIN}]}


def job(number, run_id, name, conclusion="success"):
    return {"id": number, "run_id": run_id, "run_attempt": 1, "name": name,
            "status": "completed", "conclusion": conclusion}


def artifact(number, run_id, name, expired=False):
    return {"id": number, "name": name, "expired": expired,
            "workflow_run": {"id": run_id, "head_sha": BASE}}


class ReadAPI:
    """Deliberately has no write API methods."""
    def __init__(self):
        self.issue = {"number": 7, "title": "Document the public command", "body": "Bounded documentation change.",
                      "state": "closed"}
        self.scope = {"version": 1, "repository": REPO, "issue": 7,
                      "issue_digest": issue_labels.issue_digest(self.issue), "base_sha": BASE,
                      "allowed_paths": ["docs/example.md"],
                      "acceptance_criteria": ["Explain the public command."],
                      "repair_mode": "change", "regression_file": ""}
        self.claim = {**self.scope, "planning_mode": "direct", "run_id": 42,
                      "run_attempt": 1, "actor": "maintainer"}
        self.comments = [marker(issue_labels.CLAIM_MARKER, self.claim)]
        self.runs = {42: run(42, "factory:run"), 43: run(43), 41: run(41, "factory:plan")}
        self.jobs = {
            42: [job(1, 42, "Authorize"), job(2, 42, PLANNER, "skipped"),
                 job(3, 42, PUBLISH_PLAN, "skipped"),
                 job(4, 42, BUILD + "Implement through Agentic Workflows / agent"),
                 job(5, 42, BUILD + "Apply and verify the bounded proposal"),
                 job(6, 42, BUILD + "Open a draft PR and request quality assessment")],
            43: [job(20+i, 43, "Run pinned factory Quality / " + name)
                 for i, name in enumerate(run_summary.REQUIRED_JOBS)],
            41: [job(30, 41, "Authorize"), job(31, 41, PLANNER),
                 job(32, 41, PUBLISH_PLAN), job(33, 41, BUILD, "skipped")],
        }
        self.artifacts = {42: [artifact(90, 42, "sfstack-software-result-1")],
                          43: [artifact(91, 43, "sfstack-quality-1")], 41: []}
        self.pr = {"number": 9, "state": "closed", "merged": True, "draft": False,
                   "title": "Document the public command",
                   "body": EVIDENCE + "\nVerified candidate: " + chr(96) + HEAD + chr(96),
                   "head": {"sha": HEAD, "ref": "sfstack/issue-7-42-1", "repo": {"full_name": REPO}},
                   "base": {"sha": BASE, "ref": "main", "repo": {"full_name": REPO}}}
        ident = automation.owner(9, BASE, "run", 43, 1, "42-1", 2, intent=automation.pr_intent_digest(self.pr))
        self.check = {"id": 100, "name": automation.CHECK_NAME, "head_sha": HEAD,
                      "app": {"id": 15368, "slug": "github-actions"},
                      "external_id": automation.owner_text(ident),
                      "status": "completed", "conclusion": "success",
                      "output": {"title": "Quality passed", "summary": "**Passed** " + QUALITY_EVIDENCE}}
        self.checks = [self.check]
        self.tip = BASE
        self.prs = [self.pr]
        self.requests = []

    def planned(self):
        proposal = {"version": 1, "steps": [
            {"file": "docs/example.md", "action": "Describe the command and add a concrete invocation."}],
            "verification": [{"criterion": 1, "method": "Compare the example with the public command reference."}],
            "risks": ["The documented invocation might be outdated."], "questions": []}
        record = {"version": 1, "scope": self.scope, "plan_run_id": 41,
                  "proposal": proposal, "digest": plan_advice.digest(proposal)}
        claim = {**self.scope, "ai_plan_sha256": record["digest"], "ai_plan_run_id": 41,
                 "run_id": 42, "run_attempt": 1, "actor": "maintainer"}
        self.comments = [marker(issue_labels.PLAN_MARKER, self.scope),
                         marker(issue_labels.AI_PLAN_MARKER, record, plan_advice.display(self.scope, proposal, 41)),
                         marker(issue_labels.CLAIM_MARKER, claim)]

    def get(self, path):
        self.requests.append(path)
        prefix = "repos/" + REPO
        assert path.startswith(prefix)
        route = urlsplit(path).path[len(prefix):]
        if route == "":
            result = {"full_name": REPO, "default_branch": "main"}
        elif route == "/issues/7":
            result = self.issue
        elif route == "/issues/7/comments":
            result = self.comments
        elif route == "/git/ref/heads/main":
            result = {"object": {"sha": self.tip}}
        elif route == "/actions/workflows/sfstack-issue-label.yml":
            result = {"id": 10, "path": run_summary.LABEL_PATH}
        elif route == "/actions/workflows/sfstack-quality.yml":
            result = {"id": 11, "path": run_summary.QUALITY_PATH}
        elif route.startswith("/actions/runs/"):
            pieces = route.split("/")
            run_id = int(pieces[3])
            if route.endswith("/jobs"):
                result = {"jobs": self.jobs[run_id]}
            elif route.endswith("/artifacts"):
                result = {"artifacts": self.artifacts[run_id]}
            else:
                result = self.runs[run_id]
        elif route == "/pulls":
            result = self.prs
        elif route == "/pulls/9":
            result = self.pr
        elif route == "/commits/" + HEAD + "/check-runs":
            result = {"check_runs": self.checks}
        else:
            raise AssertionError("Unexpected GET " + route)
        return deepcopy(result)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.api = ReadAPI()

    def result(self, run_id=42, **kwargs):
        return run_summary.summarize(self.api, REPO, run_id, **kwargs)

    def test_direct_complete_historical_merge(self):
        report = self.result()
        self.assertEqual("direct", report["mode"])
        self.assertEqual("recorded", report["claim"])
        self.assertEqual("skipped", report["stages"]["planning"])
        self.assertEqual("successful", report["stages"]["verification"])
        self.assertEqual("merged", report["pr"]["state"])
        self.assertEqual(HEAD, report["pr"]["head"])
        self.assertTrue(report["pr"]["evidence_link_matches"])
        self.assertEqual("successful", report["quality"]["state"])
        self.assertFalse(report["merge_authorized"])
        self.assertIsNone(report["usage"]["invoice"])

    def test_planned_and_planning_only(self):
        self.api.planned()
        result = self.result()
        self.assertEqual("planned", result["mode"])
        self.assertEqual("successful", result["planning"]["state"])
        self.assertEqual(41, result["planning"]["run_id"])
        result = self.result(41)
        self.assertEqual("planning-only", result["mode"])
        self.assertEqual("validated", result["ai_plan"])
        self.assertEqual("not-applicable", result["quality"]["state"])
        self.assertIsNone(result["pr"])

    def test_pending_and_failed_runs_never_treat_artifact_as_success(self):
        self.api.prs = []
        self.api.runs[42].update(status="in_progress", conclusion=None)
        self.api.jobs[42][-1].update(status="queued", conclusion=None)
        result = self.result()
        self.assertEqual("pending", result["workflow_state"])
        self.assertEqual("pending", result["stages"]["draft_publication"])
        self.assertIsNone(result["pr"])
        self.api.runs[42].update(status="completed", conclusion="failure")
        self.api.jobs[42][-1].update(status="completed", conclusion="failure")
        result = self.result()
        self.assertEqual("failed", result["workflow_state"])
        self.assertEqual(1, len(result["failure_stages"]))
        self.assertIn("Never replay", result["recovery"])

    def test_wrong_identity_and_forged_claim(self):
        self.api.runs[42]["head_repository"]["full_name"] = "outsider/fork"
        with self.assertRaisesRegex(ValueError, "Run identity"):
            self.result()
        self.api.runs[42]["head_repository"]["full_name"] = REPO
        self.api.comments[0]["user"]["type"] = "User"
        self.assertEqual("unknown", self.result()["mode"])
        self.api.jobs[42][0]["run_attempt"] = 2
        with self.assertRaisesRegex(ValueError, "Job identity"):
            self.result()

    def test_expired_missing_and_wrong_quality_evidence(self):
        self.api.artifacts[43][0]["expired"] = True
        result = self.result()
        self.assertEqual("expired", result["quality"]["evidence"]["state"])
        self.assertEqual("unknown", result["quality"]["state"])
        self.api.artifacts[43] = []
        self.assertEqual("missing", self.result()["quality"]["evidence"]["state"])
        self.api.artifacts[43] = [artifact(91, 99, "sfstack-quality-1")]
        self.assertEqual("unverified", self.result()["quality"]["evidence"]["state"])

    def test_quality_failed_and_superseded(self):
        self.api.runs[43]["conclusion"] = "failure"
        self.assertEqual("failed", self.result()["quality"]["state"])
        self.api.check.update(conclusion="failure", output={
            "title": "Quality assessment superseded",
            "summary": "A newer assessment requires fresh evidence. This result no longer grants quality clearance."})
        self.assertEqual("superseded", self.result()["quality"]["state"])
        self.api.check.update(conclusion="success", output={"title": "Quality passed",
                                                           "summary": "**Passed** " + QUALITY_EVIDENCE})
        self.api.pr.update(state="open", merged=False)
        self.api.tip = "d" * 40
        self.assertEqual("superseded", self.result()["quality"]["state"])

    def test_usage_archive_digest_and_run_identity(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage.zip"
            info = {"repository": REPO, "run_id": 42, "run_attempt": "1", "sha": BASE,
                    "workflow_id": REF, "engine_id": "copilot"}
            metrics = {"input_tokens": 5024, "output_tokens": 4245, "cache_read_tokens": 502625,
                       "cache_write_tokens": 43967, "ai_credits": 21.2678}
            item = artifact(92, 42, "980d0271-usage")
            self.api.artifacts[42].append(item)

            def write():
                with zipfile.ZipFile(path, "w") as z:
                    z.writestr("aw_info.json", json.dumps(info))
                    z.writestr("agent_usage.json", json.dumps(metrics))
                item["digest"] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

            write()
            self.assertEqual("unknown", self.result()["usage"]["state"])
            observed = self.result(usage_zip=path)["usage"]
            self.assertEqual("reported", observed["state"])
            self.assertEqual({"value": 21.2678, "unit": "AI credits"}, observed["metrics"]["ai_credits"])
            self.assertEqual({"value": 5024, "unit": "tokens"}, observed["metrics"]["input_tokens"])
            self.assertIsNone(observed["invoice"])
            item["digest"] = "sha256:" + "0" * 64
            self.assertEqual("unknown", self.result(usage_zip=path)["usage"]["state"])
            info["run_attempt"] = "2"
            write()
            self.assertEqual("unknown", self.result(usage_zip=path)["usage"]["state"])
            info["run_attempt"] = "1"
            write()
            item["expired"] = True
            self.assertEqual("unknown", self.result(usage_zip=path)["usage"]["state"])


if __name__ == "__main__":
    unittest.main()
