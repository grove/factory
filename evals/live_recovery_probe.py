#!/usr/bin/env python3
"""Controlled live GitHub post-ACK reply-loss test of migrated SoftwareHost.

No model is invoked; Quality dispatch uses a separate inert workflow.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from integrations.github import automation, software
from integrations.github.host_io import load_json

REPO, ISSUE = "grove/factory", 9
CANARY = "docs/live-recovery-probe.md"
WORKFLOW = "sfstack-live-recovery.yml"
NO_AI = "sfstack-recovery-noai.yml"
MUTATIONS = ("/git/refs", "/pulls", "/check-runs",
             "/actions/workflows/" + NO_AI + "/dispatches")


def configure():
    # Production SoftwareHost methods remain unchanged. Only synthetic
    # workflow provenance and the intentionally inert Actions target differ.
    software.WORKFLOW = WORKFLOW
    automation.QUALITY = NO_AI


def write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def trusted():
    c = software.context()
    if (c["repository"] != REPO or c["ref"] != "refs/heads/main"
            or c["event_name"] != "workflow_dispatch"
            or c["run_attempt"] != "1" or os.environ.get("GITHUB_ACTOR") != "grove"
            or not automation.SHA.fullmatch(c["workflow_sha"])):
        raise ValueError("Only maintainer's first Factory/main dispatch is admitted.")
    return c


class DropAfterRealPost:
    """Inject one lost client reply after each selected REAL POST succeeded."""

    def __init__(self, token):
        self.api = automation.GitHubAPI(token)
        self.counts = Counter()
        self.dropped = set()

    def get(self, path):
        return self.api.get(path)

    def patch(self, path, body):
        return self.api.patch(path, body)

    def post(self, path, body):
        kind = next((m for m in MUTATIONS if path.endswith(m)), None)
        if kind:
            self.counts[kind] += 1
            if self.counts[kind] != 1:
                raise ValueError("Duplicate mutable POST forbidden: " + kind)
        result = self.api.post(path, body)
        if kind and kind not in self.dropped:
            self.dropped.add(kind)
            raise OSError("Injected post-ACK response loss: " + kind)
        return result


def prepare(args):
    configure()
    c = trusted()
    if args.issue_number != ISSUE:
        raise ValueError("Only the dedicated Factory issue #9 is permitted.")
    repo = Path(args.repo).resolve()
    if software.git(repo, "rev-parse", "HEAD").decode().strip() != c["workflow_sha"]:
        raise ValueError("Candidate checkout differs from authenticated base.")
    inputs, ctx, result = map(lambda s: Path(s).resolve(),
                              (args.inputs, args.context_dir, args.result))
    if any(p.exists() for p in (inputs, ctx, result)):
        raise ValueError("Each evidence directory must be new.")
    host = software.SoftwareHost(automation.GitHubAPI(os.environ["GH_TOKEN"]), c)
    host.prepare(repo, ISSUE, [CANARY], [
        "Add only a non-secret synthetic recovery canary document.",
        "Exercise lost GitHub publication responses without a model.",
        "Do not merge, approve, or grant passing Quality based on this fixture.",
    ], inputs)
    software.render(inputs, repo, ctx)
    response = load_json(ctx / "change-template.json")
    target = load_json(inputs / "target.json")
    doc = ("# Synthetic live-recovery canary\n\n"
           f"Workflow run: {c['run_id']}/{c['run_attempt']}\n"
           f"Pinned base: {c['workflow_sha']}\n"
           "Never merge this document into main. No model generated it.\n")
    response.update({
        "status": "passed", "summary": "Known-safe synthetic fixture; no agent ran.",
        "criteria_addressed": [item["id"] for item in target["criteria"]],
        "behavior_changes": ["One transient, non-secret test document."],
        "checks_run": [{"command": "independent host check", "observed": "Builder claim only."}],
        "remaining_work": [], "edits": [{"path": CANARY, "content": doc}],
        "limitations": ["Known input fixture, not a paid agent implementation."],
    })
    raw = json.dumps(response).encode("utf-8")
    (ctx / "proposal.json").write_bytes(raw)
    write(ctx / "submission.json", {"items": [{"type": "submit_change",
        "change_sha256": hashlib.sha256(raw).hexdigest()}]})
    verdict = software.verify(repo, inputs, ctx / "submission.json", "success", result)
    if verdict.get("passed") is not True or verdict.get("status") != "passed":
        raise ValueError("Actual independent host verification did not pass.")
    candidate = load_json(result / "candidate.json")
    write(args.report, {"phase": "independently_verified", "run_id": c["run_id"],
        "base_sha": c["workflow_sha"], "candidate_sha": candidate["head_sha"],
        "scope": [CANARY], "model_invoked": False, "passed": True})


def quality_run(host, request_id, pr, target, deadline=120):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        run = host.quality_run(request_id, pr, target)
        if run:
            return run
        time.sleep(3)
    raise ValueError("No authenticated no-AI dispatch became visible; do not POST again.")


def completed_run(api, number, deadline=150):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        run = api.get(f"repos/{REPO}/actions/runs/{number}")
        if run.get("status") == "completed":
            return run
        time.sleep(3)
    raise ValueError("No-AI run did not finish within bounded polling window.")


def publish(args):
    configure()
    c = trusted()
    repo = Path(args.repo).resolve()
    if software.git(repo, "rev-parse", "HEAD").decode().strip() != c["workflow_sha"]:
        raise ValueError("Trusted candidate base changed.")
    api = DropAfterRealPost(os.environ["GH_TOKEN"])
    host = software.SoftwareHost(api, c)
    bundle, result = Path(args.inputs), Path(args.result)
    target = load_json(bundle / "target.json")
    candidate = load_json(result / "candidate.json")["head_sha"]
    proof = {"passed": False, "source": REPO, "issue": ISSUE,
             "run_id": c["run_id"], "attempt": c["run_attempt"],
             "base_sha": target["base_sha"], "candidate_sha": candidate,
             "evidence_digests": load_json(result / "gate.json")["digests"],
             "model_invoked": False, "merge_authorized": False,
             "physical_network_partition": False,
             "fault": "Discard client response only after REAL GitHub ACK."}
    branch = f"sfstack/issue-{ISSUE}-{c['run_id']}-{c['run_attempt']}"
    proof["branch"] = branch
    try:
        first = None
        try:
            first = host.publish(bundle, result, repo)
        except ValueError as exc:
            if not any(s in str(exc) for s in ("Quality dispatch response uncertain",
                                               "Reserved quality dispatch is uncertain")):
                raise
            proof["first_attempt"] = "fail-closed on uncertain dispatch"
        if first:
            proof["first_attempt"] = "inline authenticated dispatch recovery"
        if set(api.dropped) != set(MUTATIONS):
            raise ValueError("Not all four live POST replies were dropped after ACK.")
        pulls = host.pages("pulls?state=all&head=grove:" + branch)
        if len(pulls) != 1 or pulls[0].get("draft") is not True:
            raise ValueError("Expected exactly one owned draft PR on GitHub.")
        pr = pulls[0]
        number = pr["number"]
        proof["pull_request"] = number
        if pr.get("state") != "open" or pr["head"]["sha"] != candidate:
            raise ValueError("Recovered PR has wrong candidate head/state.")
        check = host.find_check(pr)
        owner = automation.check_owner(check) if check else None
        request_id = f"{c['run_id']}-{c['run_attempt']}"
        if not owner or owner.get("q") != request_id or owner.get("k") != "request":
            raise ValueError("No uniquely owned pending Quality reservation.")
        if check.get("conclusion") == "success":
            raise ValueError("Synthetic no-AI Quality may not pass.")
        proof["reserved_check"] = check["id"]
        run = quality_run(host, request_id, pr, target)
        proof["no_ai_run"] = run["id"]
        proof["observed_inflight"] = run["status"] in {"queued", "in_progress"}
        if not proof["observed_inflight"]:
            raise ValueError("An authenticated in-flight Actions run was not observed.")
        done = completed_run(api, run["id"])
        if done.get("conclusion") != "success":
            raise ValueError("The inert Actions probe did not finish successfully.")
        final = host.quality_run(request_id, pr, target, run["id"], run["run_attempt"])
        if final.get("status") != "completed":
            raise ValueError("Completed Actions identity could not be reauthenticated.")
        replay = software.SoftwareHost(api, c).publish(bundle, result, repo)
        proof["replay"] = {k: replay.get(k) for k in (
            "published", "draft", "quality_requested", "quality_reconciled", "merge_authorized")}
        proof["post_counts"] = dict(api.counts)
        if (not replay["published"] or not replay["draft"]
                or not replay["quality_requested"] or not replay["quality_reconciled"]
                or replay["merge_authorized"] is not False
                or any(api.counts[key] != 1 for key in MUTATIONS)):
            raise ValueError("Replay did not prove single mutable writes.")
        current = host.find_check(pr)
        if current["id"] != check["id"] or current.get("conclusion") == "success":
            raise ValueError("False Quality approval or owner change.")
        host.update_check(pr, current, automation.check_owner(current), "completed",
                          "No-AI recovery probe only", "No model review or Quality approval.",
                          conclusion="failure")
        if host.find_check(pr).get("conclusion") != "failure":
            raise ValueError("Synthetic check did not fail closed.")
        current_pr = api.get(host.path(f"pulls/{number}"))
        if (current_pr.get("state") != "open" or current_pr.get("draft") is not True
                or current_pr["head"]["sha"] != candidate
                or current_pr["head"]["ref"] != branch
                or current_pr["base"]["ref"] != "main"):
            raise ValueError("Dummy PR changed; preserve the human-owned state.")
        closed = api.patch(host.path(f"pulls/{number}"), {"state": "closed"})
        if closed.get("state") != "closed" or closed.get("merged_at"):
            raise ValueError("Unable to prove dummy PR was closed unmerged.")
        proof.update({"draft_closed_unmerged": True, "no_ai_run_conclusion": done["conclusion"],
                      "synthetic_quality_check": "failure", "passed": True})
    finally:
        # On errors retain concrete refs, never blind-retry or delete unknown state.
        write(args.report, proof)
    print(json.dumps(proof, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("prepare", "publish"), required=True)
    p.add_argument("--issue-number", type=int, default=ISSUE)
    p.add_argument("--repo", required=True)
    p.add_argument("--inputs", default="inputs")
    p.add_argument("--context-dir", default="context")
    p.add_argument("--result", default="result")
    p.add_argument("--report", required=True)
    args = p.parse_args()
    try:
        if args.phase == "prepare":
            prepare(args)
        else:
            publish(args)
        return 0
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        print("live-recovery: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
