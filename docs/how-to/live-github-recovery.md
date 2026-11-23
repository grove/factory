# Historical live GitHub post-ACK response-loss acceptance (no AI)

The one-time acceptance drill was completed on 23 November 2026 and is now
**retired**. Its two manually dispatched workflows,
`sfstack-live-recovery.yml` and `sfstack-recovery-noai.yml`, have been removed
from the normal `grove/factory` workflow set. **Do not attempt to dispatch them
again.**

See the permanent [evidence record](../evidence/live-recovery-2026-11-23.md),
the archived [proof JSON](../evidence/live-recovery-2026-11-23-proof.json),
and the [archive manifest](../evidence/live-recovery-2026-11-23-manifest.json).
The historic test implementation remains in
[`evals/live_recovery_probe.py`](../../evals/live_recovery_probe.py)
for code review and deterministic regression tests, but has no active GitHub
Actions entry point.

## What the live exercise established

The authenticated maintainer-triggered [run #45144342739](https://github.com/grove/factory/actions/runs/45144342739)
completed successfully on the protected base
`32b58d7af36b03f9a735e5f86586a68f6f920e0f`.
The production migrated publisher operated on independently verified synthetic
data. The client discarded four responses **after real GitHub accepted the
writes** (branch, draft PR, nonpassing check, and one inert Actions dispatch).
An authenticated replay recovered the original branch, PR, check and dispatch
without duplicate mutable POSTs.

The resulting [draft PR #11](https://github.com/grove/factory/pull/11)
was closed without merging. The synthetic Quality check finished with failure,
not an invented success. The separate inert run
[#45144866988](https://github.com/grove/factory/actions/runs/45144866988)
was observed in flight and completed with no Copilot usage.

The [earlier run #45139424060](https://github.com/grove/factory/actions/runs/45139424060)
remains an authentic failure: GitHub Actions was not allowed to create a PR.
It was not retroactively marked successful.

## Evidence boundary and security

This is **not a physical network partition**, a runner crash or a real paid
Quality-controller execution under lost dispatch. These claims are excluded
from acceptance. The full GitHub artifacts had 14-day retention; an audit
snapshot and SHA-256 manifest were preserved before expiry.

For future migrations, prefer the existing deterministic
`evals/run_recovery_fault_injection.py` and `tests/test_github_software.py`
regressions. Any new live test requires a new separately approved work item,
read-only preparation, scoped write authority, and human-controlled cleanup.
No operational need remains for the retired manual workflow.

The one-off repository-wide GitHub Actions
`can_approve_pull_request_reviews` setting should be restored to the
maintainer's intended baseline (`false`, with default workflow permissions
`read`) if that has not already happened. That administration setting is
outside this cleanup PR; no branch-protection change is proposed.
