#!/usr/bin/env python3
"""Maintainer-approved, one-shot issue-label handoff to Software Factory.

The default-branch workflow authenticates immutable issue scope and records
only human-authorized claims. Optional Copilot planning produces *advice*;
the trusted host validates/publishes it, never the agent. A human factory:run
may instead claim an exact direct build without an AI plan. No agent merges.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from integrations.github import automation, plan_advice

LABEL_WORKFLOW = "sfstack-issue-label.yml"
PLAN_LABEL = "factory:plan"
RUN_LABEL = "factory:run"
PLAN_MARKER = "<!-- sfstack-label-plan-v1 "
CLAIM_MARKER = "<!-- sfstack-label-claim-v1 "
AI_PLAN_MARKER = "<!-- sfstack-ai-issue-plan-v1 "
BOT_LOGIN = "github-actions[bot]"
SCOPE_HEADINGS = frozenset({"allowed files", "files to change", "exact permitted scope", "factory scope"})
CRITERIA_HEADINGS = frozenset({"acceptance criteria", "observable acceptance criteria"})
LINE = re.compile(r"^\s*(?:[-*]|[1-9][0-9]*[.)])\s+(.+)$")
CODE = re.compile(r"\x60([^\x60\n]+)\x60")
HEADING = re.compile(r"^##\s+(.+?)\s*$")
PATH = re.compile(r"(?:README\.md|(?:docs|examples|tests)/[A-Za-z0-9_./-]+)\Z")
ACTOR = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}\Z")


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_digest(issue):
    return sha(canonical({"number": issue["number"], "title": issue["title"],
                          "body": issue.get("body") or ""}))


def section(body, names):
    seen = False
    lines = []
    for line in body.splitlines():
        heading = HEADING.fullmatch(line.strip())
        if heading:
            if seen:
                break
            seen = heading.group(1).strip().casefold() in names
        elif seen:
            lines.append(line)
    if not seen:
        raise ValueError("Issue needs a ## " + sorted(names)[0].title() + " section.")
    return lines


def selected_paths(body):
    values = []
    for line in section(body, SCOPE_HEADINGS):
        if LINE.match(line):
            quoted = CODE.findall(line)
            if len(quoted) != 1 or not PATH.fullmatch(quoted[0]):
                raise ValueError("Each scoped bullet must name exactly one permitted backticked file.")
            values.append(quoted[0])
    # Import the existing strict admission policy, rather than weakening it.
    from integrations.github import software
    return software.allowed_files(values)


def selected_criteria(body):
    values = []
    for line in section(body, CRITERIA_HEADINGS):
        match = LINE.match(line)
        if match:
            values.append(match.group(1).strip())
        elif values and line.strip():
            values[-1] += " " + line.strip()
    from integrations.github import software
    return [item["description"] for item in software.criteria(values)]


def parse_plan(issue, repository, base):
    from integrations.github import software
    software.issue_snapshot(issue, repository)
    paths = selected_paths(issue.get("body") or "")
    acceptance = selected_criteria(issue.get("body") or "")
    body = issue.get("body") or ""
    control_lines = [re.sub(r"[\*\x60]", "", line).strip() for line in body.splitlines()]
    explicit = []
    regression_matches = []
    for line in control_lines:
        match = re.fullmatch(r"(?:-\s*)?(?:repair mode|mode):\s*(change|defect)", line, re.I)
        if match:
            explicit.append(match.group(1).lower())
        match = re.fullmatch(r"(?:-\s*)?regression file:\s*(\S+)", line, re.I)
        if match:
            regression_matches.append(match.group(1))
    if len(explicit) > 1:
        raise ValueError("Ambiguous repair mode; supply exactly one mode.")
    mode = explicit[0] if explicit else ("defect" if issue["title"].lower().startswith("defect:") else "change")
    if len(regression_matches) > 1:
        raise ValueError("Ambiguous regression file.")
    regression = regression_matches[0] if regression_matches else ""
    if mode == "defect" and not regression:
        eligible = [p for p in paths if p.startswith("tests/test_") and p.endswith(".py")]
        if len(eligible) != 1:
            raise ValueError("Defect mode requires an explicit regression file when more than one test path is present.")
        regression = eligible[0]
    if mode != "defect" and regression:
        raise ValueError("Regression file can only be selected in defect mode.")
    # The actual host performs the separate base-tree existence and full
    # defect admission. Validate the deterministic shape here as well.
    if regression and (regression not in paths or not re.fullmatch(r"tests/test_[a-z0-9_]+\.py", regression)):
        raise ValueError("Regression must be a selected new tests/test_*.py file.")
    if mode not in ("change", "defect"):
        raise ValueError("Invalid repair mode.")
    return {"version": 1, "repository": repository, "issue": issue["number"],
            "issue_digest": issue_digest(issue), "base_sha": base,
            "allowed_paths": paths, "acceptance_criteria": acceptance,
            "repair_mode": mode, "regression_file": regression}


def parse_marker(comment, marker):
    body = comment.get("body") or ""
    if not body.startswith(marker):
        return None
    end = body.find(" -->")
    if end < 0 or end > 50_000:
        raise ValueError("Malformed Factory authorization marker.")
    try:
        encoded = body[len(marker):end].encode("ascii")
        decoded = base64.b64decode(encoded, altchars=b"-_", validate=True).decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed Factory authorization encoding.") from exc
    record = automation.strict_json(decoded)
    if not isinstance(record, dict) or record.get("version") != 1:
        raise ValueError("Invalid Factory authorization marker.")
    return record


def comment_type(comment, marker):
    owner = comment.get("user") or {}
    if owner.get("login") != BOT_LOGIN or owner.get("type") != "Bot":
        return None
    return parse_marker(comment, marker)


def comments(api, repository, issue_number):
    result = []
    for page in range(1, 101):
        page_items = api.get(f"repos/{repository}/issues/{issue_number}/comments?per_page=100&page={page}")
        if not isinstance(page_items, list):
            raise ValueError("Invalid issue comment pagination.")
        result.extend(page_items)
        if len(page_items) < 100:
            return result
    raise ValueError("Issue has too many comments; refuse partial authorization history.")


def checked_event(context, source, repository):
    if context["event_name"] != "issues" or context["run_attempt"] != "1":
        raise ValueError("Label-triggered work only admits the first issue event attempt.")
    path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not path:
        raise ValueError("Missing original GitHub issue event.")
    event, _ = automation.read_json(path)
    issue = event.get("issue") or {}
    sender = (event.get("sender") or {}).get("login")
    label = (event.get("label") or {}).get("name")
    if (event.get("action") != "labeled" or label not in {PLAN_LABEL, RUN_LABEL}
            or not automation.positive(issue.get("number")) or "pull_request" in issue
            or (event.get("repository") or {}).get("full_name") != repository
            or sender != (source.get("actor") or {}).get("login")):
        raise ValueError("Not an authenticated issue-label event in this repository.")
    return issue["number"], label, sender


def trusted_actor(api, context):
    host = automation.Host(api, context)
    repository, source = host.trusted_context(LABEL_WORKFLOW, {"issues"})
    actor = (source.get("actor") or {}).get("login", "")
    if (not ACTOR.fullmatch(actor) or actor != (source.get("triggering_actor") or {}).get("login", actor)):
        raise ValueError("Only a human label author can authorize Software Factory.")
    number, label, sender = checked_event(context, source, host.repository)
    if sender != actor:
        raise ValueError("Workflow actor differs from label author.")
    rights = api.get(host.path("collaborators/" + quote(actor, safe="") + "/permission"))
    if rights.get("permission") not in {"write", "maintain", "admin"}:
        raise ValueError("Authorizing label must be added by a repository writer.")
    if host.default_sha(repository["default_branch"]) != context["workflow_sha"]:
        raise ValueError("Default branch advanced after the label event; replan on current main.")
    issue = api.get(host.path(f"issues/{number}"))
    if issue.get("number") != number or issue.get("state") != "open" or "pull_request" in issue:
        raise ValueError("Issue is not an open, matching work item.")
    names = {x.get("name") for x in issue.get("labels", [])}
    if label not in names:
        raise ValueError("Authorizing label was removed or changed.")
    return issue, actor, label


def existing(api, repository, number):
    items = comments(api, repository, number)
    plans = [record for c in items if (record := comment_type(c, PLAN_MARKER)) is not None]
    claims = [record for c in items if (record := comment_type(c, CLAIM_MARKER)) is not None]
    return plans, claims


def publish_comment(api, repository, number, marker, data, message):
    encoded = base64.urlsafe_b64encode(canonical(data).encode("utf-8")).decode("ascii")
    body = marker + encoded + " -->\n\n" + message
    return api.post(f"repos/{repository}/issues/{number}/comments", {"body": body})


def ai_plan_records(api, repository, number):
    """Only authentic bot comments are considered; human text cannot authorize."""
    items = comments(api, repository, number)
    found = []
    for comment in items:
        value = comment_type(comment, AI_PLAN_MARKER)
        if value is None:
            continue
        if set(value) != {"version", "scope", "plan_run_id", "proposal", "digest"}:
            raise ValueError("AI planning authorization metadata is malformed.")
        scope = value["scope"]
        if (not isinstance(scope, dict) or scope.get("version") != 1
                or not automation.positive(value["plan_run_id"])
                or not isinstance(value["digest"], str)
                or len(value["digest"]) != 64):
            raise ValueError("AI planning provenance is invalid.")
        proposal = plan_advice.validate(plan_advice.canonical(value["proposal"]), scope)
        if value["digest"] != plan_advice.digest(proposal):
            raise ValueError("AI planning output digest changed.")
        expected = (AI_PLAN_MARKER + base64.urlsafe_b64encode(canonical(value).encode("utf-8")).decode("ascii")
                    + " -->\n\n" + plan_advice.display(scope, proposal, value["plan_run_id"]))
        if comment.get("body") != expected:
            raise ValueError("Human-visible planning comment differs from its approved JSON.")
        found.append(value)
    return found


def current_ai_plan(api, repository, scope):
    selected = [item for item in ai_plan_records(api, repository, scope["issue"])
                if item["scope"] == scope]
    if len(selected) != 1:
        raise ValueError("Missing or ambiguous validated AI plan; factory:run cannot begin.")
    return selected[0]


def publish_ai_plan(api, context, response):
    """Separate write-token host publishes ONLY fresh, strict model advice."""
    issue, _, label = trusted_actor(api, context)
    if label != PLAN_LABEL:
        raise ValueError("Only an authenticated factory:plan event can publish advice.")
    repo = context["repository"]
    scope = parse_plan(issue, repo, context["workflow_sha"])
    plans, claims = existing(api, repo, issue["number"])
    if claims or not plans or plans[-1] != scope:
        raise ValueError("The original issue scope snapshot is no longer current.")
    if any(item["scope"] == scope for item in ai_plan_records(api, repo, issue["number"])):
        raise ValueError("AI advice was already published; no duplicate paid-plan publication.")
    proposal = plan_advice.validate(response, scope)
    record = {"version": 1, "scope": scope, "plan_run_id": int(context["run_id"]),
              "proposal": proposal, "digest": plan_advice.digest(proposal)}
    publish_comment(api, repo, issue["number"], AI_PLAN_MARKER, record,
                    plan_advice.display(scope, proposal, record["plan_run_id"]))
    # No second POST after ambiguous responses. Independently re-read the record.
    if current_ai_plan(api, repo, scope) != record:
        raise ValueError("AI plan publication cannot be uniquely confirmed.")
    return record



def approve_label(api, context):
    issue, actor, label = trusted_actor(api, context)
    repo, number, base = context["repository"], issue["number"], context["workflow_sha"]
    plan = parse_plan(issue, repo, base)
    plans, claims = existing(api, repo, number)
    if claims:
        raise ValueError("Issue already has a durable Factory run claim; no automatic repeated paid work.")
    if label == PLAN_LABEL:
        if any(item == plan for item in plans):
            raise ValueError("This exact issue/base was already planned; never repeat paid AI planning.")
        summary = ("### Software Factory scope snapshot (Copilot plan requested)\n\n"
                   f"**Mode:** \x60{plan['repair_mode']}\x60\n\n"
                   "**Exact files:**\n" + "".join(f"- \x60{p}\x60\n" for p in plan["allowed_paths"]) +
                   "\n**Acceptance criteria:**\n" + "".join(f"{i}. {c}\n" for i, c in enumerate(plan["acceptance_criteria"], 1)) +
                   "\nThis is an immutable preflight snapshot, NOT the final implementation plan. "
                   "Adding factory:plan explicitly requests a billable Copilot planning "
                   "proposal; review the subsequent AI-assisted plan before factory:run. "
                   "If AI planning fails, do not authorize implementation. "
                   "Editing the issue or advancing the base invalidates this request.")
        publish_comment(api, repo, number, PLAN_MARKER, plan, summary)
        return {"run": False, "plan_requested": True, "issue_number": number, "plan": plan}
    if label != RUN_LABEL:
        raise ValueError("Only the explicit factory:run label may authorize implementation.")
    if plans:
        # A planning request, even one whose model or publisher failed, must
        # never silently fall back to a direct build.
        if plans[-1] != plan:
            raise ValueError("No current reviewed Factory plan for this exact issue and base. Reapply factory:plan.")
        approved_ai = current_ai_plan(api, repo, plan)
        claim = {**plan, "ai_plan_sha256": approved_ai["digest"],
                 "ai_plan_run_id": approved_ai["plan_run_id"],
                 "run_id": int(context["run_id"]), "run_attempt": 1, "actor": actor}
    else:
        # No planning was requested. The writer's factory:run label itself
        # authorizes this *one* paid build, not an additional paid AI plan.
        # Any orphaned AI advice/history is a conflict, not a bypass route.
        if ai_plan_records(api, repo, number):
            raise ValueError("AI planning history without a trusted scope snapshot; direct run is blocked.")
        claim = {**plan, "planning_mode": "direct",
                 "run_id": int(context["run_id"]), "run_attempt": 1, "actor": actor}
    message = (f"### Software Factory claimed (one-shot)\n\n"
               f"Authorized by **{actor}** via `factory:run` for exact issue #{number}, "
               f"run [{context['run_id']}](https://github.com/{repo}/actions/runs/{context['run_id']}). "
               "This claim is permanent; removing/reapplying the label or rerunning the job "
               "must not start another paid build. Any failed attempt needs human reconciliation.")
    if not plans:
        message += ("\n\n**Direct build (no separate AI plan):** The writer authorized "
                    "implementation against this deterministic scope without a paid "
                    "planning step. Independent verification, draft PR and human merge "
                    "are still required.\n\n**Exact files:**\n"
                    + "".join(f"- `{path}`\n" for path in plan["allowed_paths"])
                    + "\n**Acceptance criteria:**\n"
                    + "".join(f"{index}. {criterion}\n" for index, criterion in
                              enumerate(plan["acceptance_criteria"], 1)))
    publish_comment(api, repo, number, CLAIM_MARKER, claim, message)
    _, observed = existing(api, repo, number)
    if len(observed) != 1 or observed[0] != claim:
        raise ValueError("Issue claim is not uniquely read back after write; do not dispatch the model.")
    return {"run": True, "issue_number": number, "plan": plan}


def verify_claim(api, context, actor):
    issue, actual_actor, label = trusted_actor(api, context)
    if label != RUN_LABEL or actor != actual_actor:
        raise ValueError("Only the approved factory:run label may reach the Software host.")
    repo, number, base = context["repository"], issue["number"], context["workflow_sha"]
    plan = parse_plan(issue, repo, base)
    plans, claims = existing(api, repo, number)
    if len(claims) != 1:
        raise ValueError("The current run has no unique, unchanged trusted Factory authorization.")
    common = {"run_id": int(context["run_id"]), "run_attempt": 1, "actor": actor}
    if claims[0].get("planning_mode") == "direct":
        # Direct-mode claims cannot reclassify a failed, stale, or pending
        # factory:plan attempt as an approved unplanned build.
        if plans or ai_plan_records(api, repo, number):
            raise ValueError("Direct run cannot bypass an earlier AI planning request.")
        expected = {**plan, "planning_mode": "direct", **common}
        advisory, digest = None, None
    else:
        if not plans or plans[-1] != plan:
            raise ValueError("The current run has no unique, unchanged trusted Factory authorization.")
        approved_ai = current_ai_plan(api, repo, plan)
        expected = {**plan, "ai_plan_sha256": approved_ai["digest"],
                    "ai_plan_run_id": approved_ai["plan_run_id"], **common}
        advisory, digest = approved_ai["proposal"], approved_ai["digest"]
    if claims[0] != expected:
        raise ValueError("The current run has no unique, unchanged trusted Factory authorization.")
    # The existing Software host requires these keys and rechecks them against
    # the builder's pinned target. None means *absence*, not fake AI approval.
    return {**plan, "advisory_plan": advisory, "ai_plan_sha256": digest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--candidate", help="Read-only pinned candidate checkout for AI planning context")
    parser.add_argument("--publish-ai", action="store_true",
                        help="Validate a model response and publish a human-reviewable proposal")
    parser.add_argument("--proposal", help="Raw JSON response file, required for --publish-ai")
    args = parser.parse_args(argv)
    context = {name: os.environ[key] for name, key in {
        "repository":"GITHUB_REPOSITORY", "workflow_sha":"GITHUB_WORKFLOW_SHA",
        "ref":"GITHUB_REF", "event_name":"GITHUB_EVENT_NAME",
        "run_id":"GITHUB_RUN_ID", "run_attempt":"GITHUB_RUN_ATTEMPT"}.items()}
    try:
        api = automation.GitHubAPI(os.environ["GH_TOKEN"])
        if args.publish_ai:
            if not args.proposal:
                raise ValueError("--publish-ai requires --proposal")
            record = publish_ai_plan(api, context, plan_advice.read_file(args.proposal))
            with open(args.out, "w", encoding="utf-8") as stream:
                json.dump({"published": True, "digest": record["digest"]}, stream, sort_keys=True)
            print(json.dumps({"published": True}))
            return 0
        outcome = approve_label(api, context)
        if outcome.get("plan_requested"):
            if not args.candidate:
                raise ValueError("Planning needs the exact read-only candidate checkout.")
            issue = api.get("repos/" + context["repository"]
                            + "/issues/" + str(outcome["issue_number"]))
            if issue_digest(issue) != outcome["plan"]["issue_digest"]:
                raise ValueError("Issue changed between plan admission and prompt creation.")
            outcome["planning_prompt"] = plan_advice.prompt(issue, outcome["plan"], args.candidate)
        with open(args.out, "w", encoding="utf-8") as stream:
            json.dump(outcome, stream, sort_keys=True, indent=2)
            stream.write("\n")
        output = os.environ["GITHUB_OUTPUT"]
        with open(output, "a", encoding="utf-8") as stream:
            # Exact one-line JSON: untrusted issue content never becomes a shell command.
            plan = outcome["plan"]
            fields = {"plan_requested": "true" if outcome.get("plan_requested") else "false",
                      "authorized": "true" if outcome["run"] else "false",
                      "issue_number": str(outcome["issue_number"]),
                      "allowed_paths": canonical(plan["allowed_paths"]),
                      "acceptance_criteria": canonical(plan["acceptance_criteria"]),
                      "repair_mode": plan["repair_mode"],
                      "regression_file": plan["regression_file"]}
            for key, value in fields.items():
                if "\n" in value or "\r" in value:
                    raise ValueError("Unsafe multiline job output.")
                stream.write(key + "=" + value + "\n")
    except (KeyError, OSError, ValueError) as exc:
        parser.exit(1, f"issue-label: {exc}\n")
    print(json.dumps({"authorized": outcome["run"], "issue_number": outcome["issue_number"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
