#!/usr/bin/env python3
"""Read-only operator diagnostics for a label-triggered Factory attempt.

This is historical evidence, not an authorization or a merge gate.
No candidate code is executed, and the tool never writes to GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
import zipfile

from integrations.github import automation, issue_labels
from integrations.github.required_quality_gate import ACTIONS_APP_ID, REQUIRED_JOBS, superseded

LABEL_PATH = ".github/workflows/sfstack-issue-label.yml"
QUALITY_PATH = ".github/workflows/sfstack-quality.yml"
MAX_USAGE_ZIP = 16 * 1024 * 1024
MAX_USAGE_MEMBER = 2 * 1024 * 1024
COUNTS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


def url(repo, run_id):
    return f"https://github.com/{repo}/actions/runs/{run_id}"


def state(item):
    status, result = item.get("status"), item.get("conclusion")
    if status in {"queued", "in_progress", "waiting", "requested", "pending"} and result is None:
        return "pending"
    if status != "completed":
        return "unknown"
    if result == "success":
        return "successful"
    if result == "skipped":
        return "skipped"
    if result in {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}:
        return "failed"
    return "unknown"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same_repo(obj, repo):
    return isinstance(obj, dict) and obj.get("full_name", "").lower() == repo.lower()


class Reads:
    """Only a GET interface is exposed to the existing pagination helpers."""
    def __init__(self, api, repo):
        self.api, self.repo = api, repo
        require(automation.REPOSITORY.fullmatch(repo), "Invalid repository.")
        self.host = automation.Host(self, {"repository": repo, "run_id": "1", "run_attempt": "1"})

    def get(self, path):
        return self.api.get(path)

    def one(self, path):
        return self.get(self.host.path(path))

    def pages(self, path, key=None):
        return self.host.pages(path, key)

    def run(self, run_id, path, event, branch):
        require(automation.positive(run_id), "Invalid run ID.")
        run = self.one(f"actions/runs/{run_id}")
        workflow = self.one("actions/workflows/" + path.rsplit("/", 1)[-1])
        require(run.get("id") == run_id and automation.positive(run.get("run_attempt"))
                and run.get("path") == workflow.get("path") == path
                and run.get("workflow_id") == workflow.get("id")
                and automation.positive(workflow.get("id"))
                and run.get("event") == event and run.get("head_branch") == branch
                and same_repo(run.get("repository"), self.repo)
                and same_repo(run.get("head_repository"), self.repo)
                and automation.SHA.fullmatch(run.get("head_sha", "")),
                "Run identity does not match the trusted repository/workflow.")
        return run

    def jobs(self, run):
        path = f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs"
        jobs = self.pages(path, "jobs")
        require(all(automation.positive(j.get("id")) and isinstance(j.get("name"), str)
                    and j.get("run_id") == run["id"] and j.get("run_attempt") == run["run_attempt"]
                    for j in jobs) and len({j["id"] for j in jobs}) == len(jobs),
                "Job identity does not match the exact attempt.")
        return [{"id": j["id"], "name": j["name"], "state": state(j),
                 "conclusion": j.get("conclusion"),
                 "url": url(self.repo, run["id"]) + f"/job/{j['id']}"} for j in jobs]

    def artifacts(self, run):
        items = self.pages(f"actions/runs/{run['id']}/artifacts", "artifacts")
        require(len({a.get("id") for a in items}) == len(items), "Duplicate artifact IDs.")
        result = []
        for a in items:
            owner = a.get("workflow_run") or {}
            if not automation.positive(a.get("id")) or not isinstance(a.get("name"), str):
                continue
            trusted = owner.get("id") == run["id"] and owner.get("head_sha") == run["head_sha"]
            status = ("unverified" if not trusted else "expired" if a.get("expired") is True
                      else "retained" if a.get("expired") is False else "unknown")
            result.append({"id": a["id"], "name": a["name"], "state": status,
                           "digest": a.get("digest"), "url": url(self.repo, run["id"]) + f"/artifacts/{a['id']}"})
        return sorted(result, key=lambda a: a["id"])


def matching_job(jobs, suffix):
    selected = [j for j in jobs if j["name"] == suffix or j["name"].endswith(" / " + suffix)]
    return selected[0]["state"] if len(selected) == 1 else "unknown"


def evidence(artifacts, name):
    selected = [a for a in artifacts if a["name"] == name]
    if len(selected) != 1:
        return {"name": name, "state": "unknown" if selected else "missing"}
    return selected[0]


def refs(run):
    return sorted({r["path"] for r in run.get("referenced_workflows") or []
                   if isinstance(r.get("path"), str) and automation.SHA.fullmatch(r.get("sha", ""))
                   and r["path"].endswith("@" + r["sha"])})


def usage(repo, run, artifacts, archive=None):
    """A local GitHub ZIP is optional; verify bytes and embedded run provenance.

    Report published agent totals only, never an inferred charge or whole-run total.
    """
    candidates = [a for a in artifacts if re.fullmatch(r"[0-9a-f]{8}-usage", a["name"])]
    answer = {"state": "unknown", "reason": "No unique, retained usage artifact.",
              "artifacts": candidates, "invoice": None}
    if len(candidates) != 1 or candidates[0]["state"] != "retained":
        return answer
    item = candidates[0]
    if archive is None:
        answer["reason"] = "Download the linked usage ZIP and supply it with --usage-zip."
        return answer
    try:
        with Path(archive).open("rb") as stream:
            raw = stream.read(MAX_USAGE_ZIP + 1)
        require(len(raw) <= MAX_USAGE_ZIP, "Usage ZIP exceeds size limit.")
        require(item["digest"] == "sha256:" + hashlib.sha256(raw).hexdigest(),
                "Usage ZIP digest does not match GitHub artifact metadata.")
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            def read(name):
                matches = [f for f in bundle.infolist() if f.filename == name]
                require(len(matches) == 1 and matches[0].file_size <= MAX_USAGE_MEMBER,
                        "Missing, duplicate, or oversized usage member.")
                return automation.strict_json(bundle.read(matches[0]))
            info, metrics = read("aw_info.json"), read("agent_usage.json")
        require(info.get("repository") == repo and info.get("run_id") == run["id"]
                and str(info.get("run_attempt")) == str(run["run_attempt"])
                and info.get("sha") == run["head_sha"]
                and info.get("workflow_id") in refs(run)
                and info.get("engine_id") == "copilot", "Usage archive provenance mismatch.")
        values = {}
        for key in COUNTS:
            value = metrics.get(key)
            if type(value) is int and value >= 0:
                values[key] = {"value": value, "unit": "tokens"}
        value = metrics.get("ai_credits")
        if type(value) in (int, float) and math.isfinite(value) and value >= 0:
            values["ai_credits"] = {"value": value, "unit": "AI credits"}
        require(values, "No recognized published usage metrics.")
        return {"state": "reported", "source": item["url"] + " (agent_usage.json)",
                "scope": "agent totals only; excludes separately reported detection, Quality and planning",
                "metrics": values, "invoice": None}
    except (OSError, ValueError, TypeError, KeyError, OverflowError, zipfile.BadZipFile, RuntimeError):
        answer["reason"] = "Usage ZIP could not be authenticated or parsed."
        return answer


def scope_matches(record, repo, number, base):
    return (record.get("repository") == repo and record.get("issue") == number
            and record.get("base_sha") == base and record.get("version") == 1)


def mode_for(reads, run, number, label, issue):
    comments = issue_labels.comments(reads, reads.repo, number)
    claims = [r for c in comments if (r := issue_labels.comment_type(c, issue_labels.CLAIM_MARKER))]
    plans = [r for c in comments if (r := issue_labels.comment_type(c, issue_labels.PLAN_MARKER))]
    if label == "factory:plan":
        records = issue_labels.ai_plan_records(reads, reads.repo, number)
        matched = [p for p in records if p["plan_run_id"] == run["id"]
                   and scope_matches(p["scope"], reads.repo, number, run["head_sha"])
                   and p["scope"] in plans]
        return {"mode": "planning-only", "claim": "not-applicable",
                "ai_plan": "validated" if len(matched) == 1 else "missing-or-unverified"}
    exact = [c for c in claims if c.get("run_id") == run["id"]
             and c.get("run_attempt") == run["run_attempt"] == 1
             and c.get("actor") == (run.get("actor") or {}).get("login")
             and scope_matches(c, reads.repo, number, run["head_sha"])]
    if len(claims) != 1 or len(exact) != 1:
        return {"mode": "unknown", "claim": "missing-or-unverified"}
    claim = exact[0]
    current = claim.get("issue_digest") == issue_labels.issue_digest(issue)
    records = issue_labels.ai_plan_records(reads, reads.repo, number)
    if claim.get("planning_mode") == "direct" and not plans and not records and not {
            "ai_plan_sha256", "ai_plan_run_id"} & claim.keys():
        return {"mode": "direct", "claim": "recorded", "issue_text_matches_claim": current}
    if "planning_mode" not in claim:
        for plan in plans:
            if not scope_matches(plan, reads.repo, number, run["head_sha"]):
                continue
            expected = {**plan, "ai_plan_sha256": claim.get("ai_plan_sha256"),
                        "ai_plan_run_id": claim.get("ai_plan_run_id"), "run_id": run["id"],
                        "run_attempt": run["run_attempt"], "actor": claim["actor"]}
            matching = [p for p in records if p["scope"] == plan and p["digest"] == claim.get("ai_plan_sha256")
                        and p["plan_run_id"] == claim.get("ai_plan_run_id")]
            if claim == expected and len(matching) == 1:
                return {"mode": "planned", "claim": "recorded", "issue_text_matches_claim": current,
                        "planning_run": url(reads.repo, claim["ai_plan_run_id"])}
    return {"mode": "unknown", "claim": "conflicting-planning-history"}


def quality(reads, pr, branch, current_base, archive):
    """Summarize the selected generation, not historical duplicate successes."""
    check = reads.host.find_check(pr)
    if check is None:
        return {"state": "unknown", "reason": "No owned Quality check."}
    owner = automation.check_owner(check)
    if (check.get("app", {}).get("id") != ACTIONS_APP_ID or not owner or owner.get("v") != 3):
        return {"state": "unknown", "reason": "Unverified check provenance."}
    if (superseded(check) or owner["k"] == "stale" or owner.get("t") != automation.pr_intent_digest(pr)
            or (pr.get("state") == "open" and owner["b"] != current_base)):
        return {"state": "superseded", "generation": owner["g"], "reason": "Retired or stale assessment."}
    report = {"state": "pending", "generation": owner["g"], "check_id": check["id"],
              "base": owner["b"], "head": pr["head"]["sha"]}
    if owner["k"] != "run":
        return report
    run = reads.run(owner["i"], QUALITY_PATH, "workflow_dispatch", branch)
    require(run["head_sha"] == owner["b"] and run["run_attempt"] == owner["a"]
            and run.get("display_title") == f"sfstack quality / PR #{pr['number']} / request {owner['q']}",
            "Quality run does not match selected check generation.")
    jobs, artifacts = reads.jobs(run), reads.artifacts(run)
    retained = evidence(artifacts, f"sfstack-quality-{run['run_attempt']}")
    report.update(run_id=run["id"], attempt=run["run_attempt"], url=url(reads.repo, run["id"]),
                  workflow_state=state(run), jobs=jobs, evidence=retained,
                  usage=usage(reads.repo, run, artifacts, archive))
    if state(check) == "failed" or state(run) == "failed":
        report["state"] = "failed"
    elif state(check) == state(run) == "successful":
        output = check.get("output") or {}
        valid = (all(matching_job(jobs, name) == "successful" for name in REQUIRED_JOBS)
                 and retained["state"] == "retained"
                 and retained["url"] in (output.get("summary") or "")
                 and output.get("title") == "Quality passed"
                 and (output.get("summary") or "").startswith("**Passed**"))
        report["state"] = "successful" if valid else "unknown"
    elif state(check) == "unknown" or state(run) == "unknown":
        report["state"] = "unknown"
    # A changing generation never upgrades this diagnostic to success.
    latest = reads.host.find_check(pr)
    if latest != check:
        report["state"] = "superseded"
    return report


def summarize(api, repo, run_id, usage_zip=None, quality_usage_zip=None):
    reads = Reads(api, repo)
    metadata = reads.host.repo()
    branch = metadata.get("default_branch")
    require(isinstance(branch, str) and branch, "Missing default branch.")
    run = reads.run(run_id, LABEL_PATH, "issues", branch)
    require(run["run_attempt"] == 1, "Label-event retries are not authorized; reconcile the first attempt.")
    match = re.fullmatch(r"sfstack issue #([1-9][0-9]*) / (factory:plan|factory:run)", run.get("display_title", ""))
    require(match is not None, "Unknown label event title.")
    number, label = int(match[1]), match[2]
    issue = reads.one(f"issues/{number}")
    require(issue.get("number") == number and "pull_request" not in issue, "Issue identity mismatch.")
    mode = mode_for(reads, run, number, label, issue)
    jobs, artifacts = reads.jobs(run), reads.artifacts(run)
    report = {"schema": "sfstack-run-summary/v1", "repository": repo, "issue": number,
              "issue_url": f"https://github.com/{repo}/issues/{number}", "issue_state": issue.get("state"),
              "run_id": run_id, "attempt": run["run_attempt"], "url": url(repo, run_id),
              "label": label, **mode, "base": run["head_sha"], "source_refs": refs(run),
              "workflow_state": state(run), "jobs": jobs, "artifacts": artifacts,
              "usage": usage(repo, run, artifacts, usage_zip), "pr": None,
              "quality": {"state": "not-applicable" if label == "factory:plan" else "unknown"},
              "merge_authorized": False}
    report["failure_stages"] = [j["name"] for j in jobs if j["state"] == "failed"]
    if label == "factory:run":
        ref = f"sfstack/issue-{number}-{run_id}-{run['run_attempt']}"
        query = urlencode({"state": "all", "head": repo.split("/")[0] + ":" + ref})
        prs = reads.pages("pulls?" + query)
        require(len(prs) <= 1, "Multiple pull requests match this attempt.")
        if prs:
            pr = reads.one(f"pulls/{prs[0]['number']}")
            require(pr.get("number") == prs[0]["number"] and pr["head"]["ref"] == ref
                    and same_repo(pr["head"].get("repo"), repo) and same_repo(pr["base"].get("repo"), repo)
                    and pr["base"]["ref"] == branch and automation.SHA.fullmatch(pr["head"].get("sha", "")),
                    "Published PR identity mismatch.")
            retained = evidence(artifacts, f"sfstack-software-result-{run['run_attempt']}")
            linked = (retained["state"] == "retained" and retained["url"] in (pr.get("body") or "")
                      and f"Verified candidate: " + chr(96) + pr["head"]["sha"] + chr(96) in (pr.get("body") or ""))
            report["pr"] = {"number": pr["number"], "url": f"https://github.com/{repo}/pull/{pr['number']}",
                            "head": pr["head"]["sha"], "base": pr["base"]["sha"], "draft": pr.get("draft"),
                            "state": "merged" if pr.get("merged") is True else pr.get("state"),
                            "build_evidence": retained, "evidence_link_matches": linked}
            tip = reads.host.default_sha(branch)
            report["quality"] = quality(reads, pr, branch, tip, quality_usage_zip)
    if report["failure_stages"] or report["workflow_state"] == "failed":
        recovery = "Inspect failed jobs and retained evidence; reconcile any prior writes. Never replay a claimed paid attempt."
    elif report["workflow_state"] == "pending":
        recovery = "Inspect the current run; do not dispatch or relabel while it is pending."
    elif label == "factory:plan":
        recovery = ("Review the authenticated plan before a separate human build decision."
                    if mode.get("ai_plan") == "validated" else "No validated plan; inspect publication, do not authorize a build.")
    elif report["pr"] is None or mode["claim"] != "recorded":
        recovery = "Inspect the durable claim and publication evidence; do not relabel or assume a successful build."
    elif report["pr"]["state"] == "merged":
        recovery = "Historical merged PR; retain evidence and inspect post-merge CI. No retry."
    elif report["quality"]["state"] == "successful":
        recovery = "Review the current PR and ordinary required checks; only a human may merge."
    else:
        recovery = "Inspect the independent Quality result and required CI; no merge or automatic retry."
    report["recovery"] = recovery
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run", required=True, type=int)
    parser.add_argument("--usage-zip", type=Path)
    parser.add_argument("--quality-usage-zip", type=Path)
    args = parser.parse_args(argv)
    try:
        report = summarize(automation.GitHubAPI(os.environ.get("GH_TOKEN")),
                           args.repository, args.run, args.usage_zip, args.quality_usage_zip)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print("Unable to authenticate run summary: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
