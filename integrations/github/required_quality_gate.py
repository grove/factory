#!/usr/bin/env python3
"""Read-only merge-eligible bridge to the trusted, independently published Quality result.

The pull_request workflow runs this code from a reviewed immutable Factory SHA.
It never checks out the PR candidate, publishes check runs, dispatches AI, or
has write permission. Only complete pinned Quality evidence can pass.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit

from integrations.github.automation import (
    CHECK_NAME, GitHubAPI, Host, REPOSITORY, SHA, check_owner, pr_intent_digest,
    read_json,
)

ACTIONS_APP_ID = 15368
QUALITY_WORKFLOW = "sfstack-quality.yml"
REQUIRED_JOBS = (
    "Execute pinned verification",
    "Review through Agentic Workflows / agent",
    "sfstack quality gate",
    "Publish the PR quality check",
)
PR_ACTIONS = frozenset({"opened", "reopened", "synchronize", "edited", "ready_for_review"})


def fail(reason):
    return "blocked", reason


def pending(reason):
    return "pending", reason


def superseded(check):
    """Recognize only the coordinator's explicit, nonpassing retirement state."""
    output = check.get("output") or {}
    return (check.get("status") == "completed"
            and check.get("conclusion") == "failure"
            and output.get("title") == "Quality assessment superseded"
            and isinstance(output.get("summary"), str)
            and output["summary"].startswith(
                "A newer assessment requires fresh evidence. This result no longer grants quality clearance."))


def snapshot(api, repository, event):
    """Return (passed|pending|blocked, reason) using only authenticated API reads."""
    if not REPOSITORY.fullmatch(repository):
        return fail("Invalid repository identity.")
    if event.get("action") not in PR_ACTIONS:
        return fail("Not an authorized pull request event.")
    number = event.get("number")
    event_pr = event.get("pull_request")
    if (type(number) is not int or number < 1 or not isinstance(event_pr, dict)
            or event_pr.get("number") != number
            or not isinstance(event_pr.get("head"), dict)
            or not SHA.fullmatch(event_pr["head"].get("sha", ""))):
        return fail("The event does not pin a valid PR number and head.")
    prefix = "repos/" + repository
    repository_info = api.get(prefix)
    if repository_info.get("full_name", "").lower() != repository.lower():
        return fail("GitHub repository identity changed.")
    branch = repository_info.get("default_branch")
    if not isinstance(branch, str) or not branch:
        return fail("Missing default-branch identity.")
    pr = api.get(prefix + f"/pulls/{number}")
    if (pr.get("number") != number or pr.get("state") != "open"
            or pr.get("head", {}).get("repo", {}).get("full_name", "").lower() != repository.lower()
            or pr.get("base", {}).get("repo", {}).get("full_name", "").lower() != repository.lower()
            or pr.get("base", {}).get("ref") != branch):
        return fail("Only open same-repository PRs against the default branch qualify.")
    head = pr.get("head", {}).get("sha")
    if head != event_pr["head"]["sha"]:
        return fail("PR head changed since the eligible event; fresh checks are required.")
    tip = api.get(prefix + "/git/ref/heads/" + branch)["object"]["sha"]
    if not SHA.fullmatch(tip):
        return fail("Default-branch SHA is invalid.")
    intent = pr_intent_digest(pr)
    host = Host(api, {"repository": repository, "run_id": "1", "run_attempt": "1"})
    check = host.find_check(pr)
    if check is None:
        return pending("No trusted Quality check has been published for this PR head.")
    owner = check_owner(check)
    if check.get("app", {}).get("id") != ACTIONS_APP_ID:
        return fail("Quality check was not produced by the expected GitHub Actions app.")
    if not owner or owner.get("v") != 3 or owner.get("k") not in {"run", "request", "stale"}:
        return fail("Quality result lacks authenticated generation/intent provenance.")
    if owner["b"] != tip or owner.get("t") != intent or owner["k"] != "run":
        return pending("Quality has not completed on the current base and acceptance intent.")
    if check.get("status") != "completed":
        return pending("Trusted Quality assessment is still pending.")
    if check.get("conclusion") != "success":
        # replace_check retires the old check before POSTing its successor.
        # Poll for the successor, never reuse the retired result.
        if superseded(check):
            return pending("The trusted Quality assessment was superseded; awaiting its successor.")
        return fail("The current trusted Quality assessment did not pass.")
    output = check.get("output") or {}
    if (output.get("title") != "Quality passed"
            or not isinstance(output.get("summary"), str)
            or not output["summary"].startswith("**Passed**")):
        return fail("The success check lacks the trusted publisher's positive assessment.")
    run_id, attempt = owner["i"], owner["a"]
    workflow = api.get(prefix + "/actions/workflows/" + QUALITY_WORKFLOW)
    run = api.get(prefix + f"/actions/runs/{run_id}")
    expected_title = f"sfstack quality / PR #{number} / request {owner['q']}"
    if (run.get("id") != run_id
            or run.get("workflow_id") != workflow.get("id")
            or workflow.get("path") != ".github/workflows/" + QUALITY_WORKFLOW
            or run.get("path") != workflow["path"]
            or run.get("event") != "workflow_dispatch"
            or run.get("head_branch") != branch or run.get("head_sha") != tip
            or run.get("run_attempt") != attempt
            or run.get("display_title") != expected_title
            or run.get("repository", {}).get("full_name", "").lower() != repository.lower()
            or run.get("head_repository", {}).get("full_name", "").lower() != repository.lower()):
        return fail("The published check is not backed by the exact trusted Quality workflow.")
    # The publisher writes its check before GitHub marks the workflow completed.
    # Authenticate identity first; only then wait for a matching active run.
    if run.get("status") in {"queued", "in_progress"} and run.get("conclusion") is None:
        return pending("The authenticated Quality workflow is still completing.")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        return fail("The published check is not backed by a completed successful trusted Quality workflow.")
    jobs_response = api.get(prefix + f"/actions/runs/{run_id}/jobs?per_page=100")
    jobs = jobs_response.get("jobs", [])
    if (type(jobs_response.get("total_count")) is not int
            or jobs_response["total_count"] != len(jobs) or not jobs
            or any(not isinstance(job.get("name"), str) for job in jobs)):
        return fail("Quality controller jobs cannot be exhaustively authenticated.")
    for suffix in REQUIRED_JOBS:
        matched = [job for job in jobs
                   if job["name"] == suffix or job["name"].endswith(" / " + suffix)]
        if len(matched) != 1 or matched[0].get("status") != "completed" or matched[0].get("conclusion") != "success":
            return fail("Missing successful independently verified Quality job: " + suffix)
    artifacts = api.get(prefix + f"/actions/runs/{run_id}/artifacts?per_page=100")
    items = artifacts.get("artifacts", [])
    evidence = [item for item in items if item.get("name") == f"sfstack-quality-{attempt}"]
    if (type(artifacts.get("total_count")) is not int
            or artifacts["total_count"] != len(items)
            or len(evidence) != 1 or evidence[0].get("expired") is not False
            or evidence[0].get("workflow_run", {}).get("id") != run_id
            or evidence[0].get("workflow_run", {}).get("head_sha") != tip):
        return fail("Exact-run retained independent Quality evidence is unavailable.")
    link = (f"https://github.com/{repository}/actions/runs/{run_id}"
            f"/artifacts/{evidence[0]['id']}")
    if link not in output["summary"]:
        return fail("The published check does not identify its retained evidence.")
    # Last read prevents an accepted result becoming stale during verification.
    last_pr = api.get(prefix + f"/pulls/{number}")
    last_tip = api.get(prefix + "/git/ref/heads/" + branch)["object"]["sha"]
    if (last_pr.get("state") != "open" or last_pr.get("head", {}).get("sha") != head
            or last_pr.get("base", {}).get("ref") != branch
            or last_pr.get("head", {}).get("repo", {}).get("full_name", "").lower() != repository.lower()
            or pr_intent_digest(last_pr) != intent or last_tip != tip):
        return fail("The PR head, base, or reviewed intent changed while verifying the gate.")
    # Re-read ownership after reading jobs and artifacts. A newer assessment
    # can retire this result without changing the PR head, base or intent.
    latest = host.find_check(last_pr)
    if latest is None:
        return fail("The authenticated Quality check disappeared while verifying the gate.")
    latest_owner = check_owner(latest)
    if (latest.get("app", {}).get("id") != ACTIONS_APP_ID or not latest_owner
            or latest_owner.get("v") != 3):
        return fail("Quality check provenance changed while verifying the gate.")
    if latest_owner != owner:
        if latest_owner["g"] > owner["g"]:
            return pending("A newer Quality generation appeared while verifying the gate.")
        return fail("Quality generation identity changed while verifying the gate.")
    if superseded(latest):
        return pending("The trusted Quality assessment was superseded while verifying the gate.")
    if (latest.get("id") != check.get("id") or latest.get("status") != "completed"
            or latest.get("conclusion") != "success" or latest.get("output") != output):
        return fail("The authenticated Quality result changed while verifying the gate.")
    return "passed", f"Trusted independent Quality passed: run {run_id}, check {check['id']}, head {head}, base {tip}."


def wait_for_quality(api, repository, event, timeout_seconds=1800, interval_seconds=15,
                     monotonic=time.monotonic, sleep=time.sleep):
    deadline = monotonic() + timeout_seconds
    while True:
        status, reason = snapshot(api, repository, event)
        print(f"Quality gate: {status}: {reason}", flush=True)
        if status != "pending":
            return status == "passed"
        remaining = deadline - monotonic()
        if remaining <= 0:
            print("Quality gate timed out. Rerun only this read-only job after Quality publishes; do not restart Copilot.", file=sys.stderr)
            return False
        sleep(min(interval_seconds, remaining))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args(argv)
    if not 1 <= args.timeout_seconds <= 2100:
        parser.error("Timeout must be 1–2100 seconds.")
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        parser.error("An eligible pull_request event is required.")
    try:
        event, _ = read_json(args.event)
        api = GitHubAPI(os.environ.get("GH_TOKEN"))
        return 0 if wait_for_quality(api, os.environ["GITHUB_REPOSITORY"], event,
                                    timeout_seconds=args.timeout_seconds) else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Quality gate failed closed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
