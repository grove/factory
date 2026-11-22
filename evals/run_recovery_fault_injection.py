#!/usr/bin/env python3
"""Execute the real migrated hosts against deterministic fault-injected fake GitHub.

This deliberately calls production SoftwareHost/Host methods through their
existing GitHub boundary fixtures. It sends NO GitHub API requests, contains
NO live credentials, creates NO remote branches/PRs/checks, and starts NO AI.
A pass is controlled fault-injection evidence, not live GitHub transport proof.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

CASES = {
    "lost-branch-response": "test_github_software.GitHubSoftwarePublicationTests.test_lost_branch_response_adopts_exact_reference_without_overwrite",
    "lost-pr-response": "test_github_software.GitHubSoftwarePublicationTests.test_lost_pr_creation_response_is_reconciled_in_same_attempt",
    "lost-pr-human-ready": "test_github_software.GitHubSoftwarePublicationTests.test_lost_pr_reply_cannot_overwrite_human_ready_state",
    "lost-pr-human-title": "test_github_software.GitHubSoftwarePublicationTests.test_lost_pr_reply_cannot_overwrite_human_title",
    "lost-pr-human-intent": "test_github_software.GitHubSoftwarePublicationTests.test_lost_pr_reply_cannot_overwrite_human_acceptance_body",
    "lost-pr-human-head": "test_github_software.GitHubSoftwarePublicationTests.test_lost_pr_reply_cannot_overwrite_human_head",
    "lost-quality-reservation": "test_github_software.GitHubSoftwarePublicationTests.test_lost_check_reservation_response_adopts_exact_owner",
    "lost-quality-dispatch-visible": "test_github_software.GitHubSoftwarePublicationTests.test_lost_quality_dispatch_response_reconciles_matching_workflow_run",
    "lost-dispatch-queued": "test_github_software.GitHubSoftwarePublicationTests.test_lost_dispatch_reconciles_queued_run",
    "lost-dispatch-inprogress": "test_github_software.GitHubSoftwarePublicationTests.test_lost_dispatch_reconciles_inprogress_run",
    "lost-dispatch-completed-success-no-approval": "test_github_software.GitHubSoftwarePublicationTests.test_lost_dispatch_reconciles_completed_success_without_claiming_approval",
    "lost-dispatch-completed-failure": "test_github_software.GitHubSoftwarePublicationTests.test_lost_dispatch_reconciles_completed_failure_without_repost",
    "late-visibility-inprogress": "test_github_software.GitHubSoftwarePublicationTests.test_late_quality_visibility_reconciles_inprogress_run",
    "late-visibility-completed-failure": "test_github_software.GitHubSoftwarePublicationTests.test_late_quality_visibility_reconciles_completed_negative_run",
    "quality-dispatch-not-visible": "test_github_software.GitHubSoftwarePublicationTests.test_failed_quality_dispatch_stays_reserved_until_reconciled_without_duplicate",
    "quality-dispatch-wrong-provenance": "test_github_software.GitHubSoftwarePublicationTests.test_duplicate_or_wrong_quality_provenance_cannot_clear_reserved_request",
    "publisher-replay-no-duplicates": "test_github_software.GitHubSoftwarePublicationTests.test_retry_reconciles_existing_exact_branch_draft_and_quality_run",
    "publisher-human-state": "test_github_software.GitHubSoftwarePublicationTests.test_changed_factory_branch_or_reviewed_pr_is_never_overwritten",
    "quality-run-generation-handoff": "test_github_software.GitHubSoftwarePublicationTests.test_quality_controller_handoff_preserves_reserved_check_generation",
    "coordinator-lost-dispatch-inflight": "test_github_automation.GitHubAutomationTests.test_lost_dispatch_reply_recovers_exact_inflight_run_without_repeat_post",
    "coordinator-lost-dispatch-completed": "test_github_automation.GitHubAutomationTests.test_lost_dispatch_reply_reconciles_completed_run_as_failure_not_approval",
    "coordinator-duplicate-or-invalid": "test_github_automation.GitHubAutomationTests.test_lost_dispatch_reply_with_ambiguous_or_wrong_run_fails_closed",
    "coordinator-dispatch-not-visible": "test_github_automation.GitHubAutomationTests.test_dispatch_failure_leaves_a_failed_check",
    "cancelled-quality-controller": "test_github_automation.GitHubAutomationTests.test_cancelled_controller_reconciliation_only_fails_its_owned_check",
    "late-cancellation-fenced": "test_github_automation.GitHubAutomationTests.test_late_cancellation_cannot_close_newer_owner",
    "stale-base-fenced": "test_github_automation.GitHubAutomationTests.test_inflight_old_base_review_is_invalidated_and_cannot_publish",
    "older-completion-fenced": "test_github_automation.GitHubAutomationTests.test_old_completion_event_cannot_close_a_new_run_attempt",
}


def run_cases(output: Path) -> bool:
    output.mkdir(parents=True, exist_ok=False)
    entries = []
    stream = io.StringIO()
    successful = True
    for label, dotted in CASES.items():
        suite = unittest.defaultTestLoader.loadTestsFromName(dotted)
        stream.seek(0)
        stream.truncate(0)
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        passed = (result.wasSuccessful() and result.testsRun == 1
                  and not result.skipped and not result.expectedFailures)
        entries.append({
            "scenario": label, "test": dotted, "status": "passed" if passed else "failed",
            "tests_run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "output": stream.getvalue()[-12000:],
        })
        print(f"{label}: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            successful = False
    report = {
        "schema_version": "1.0",
        "kind": "controlled-github-host-fault-injection",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": __import__("os").environ.get("GITHUB_SHA", ""),
        "boundary": "Production SoftwareHost and Quality Host; in-memory API injected post-write response loss",
        "limitations": [
            "No real GitHub API mutation, network partition or live paid Copilot run is exercised.",
            "The test does not establish that real GitHub will deliver all lifecycle events promptly.",
            "Every scenario must fail if it posts duplicate mutable refs/PRs/dispatches or invents a quality pass.",
        ],
        "passed": successful,
        "scenarios": entries,
    }
    (output / "fault-injection-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "fault-injection.log").write_text(
        "\n\n".join(e["scenario"] + "\n" + e["output"] for e in entries), encoding="utf-8")
    print(f"{len(entries)} controlled scenarios; all passed: {successful}")
    return successful


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    return 0 if run_cases(Path(args.output).resolve()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
