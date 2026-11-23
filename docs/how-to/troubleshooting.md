# Troubleshoot and recover safely

Start with the issue's bot comments, the exact Actions run/attempt and the associated PR. The [read-only summary](inspect-factory-run.md) can gather this evidence without calling Copilot. Inspect existing writes before authorizing more work.

| Symptom | Safe response |
| --- | --- |
| Label did not start work | Confirm exact label, trusted default-branch caller, open issue, valid scope and a human writer. Inspect the authorization job. Do not bypass permissions. |
| Planning snapshot exists but AI plan is missing/rejected | Inspect plan and publisher jobs; do not add `factory:run` or downgrade to direct. An unchanged failed plan cannot simply be replayed. |
| Issue text or default branch changed after planning | Review the new snapshot. Only if another paid plan is intended, remove/reapply `factory:plan` for the changed snapshot and review the validated plan. |
| Permanent build claim exists | Inspect original attempt and artifacts. Never delete claim comments, relabel or rerun the paid label event. Reconcile any partial publication before a separately authorized follow-up issue. |
| Build failed or draft is absent | Read measured verification and publisher logs; distinguish a failed check from a GitHub publication failure. Do not force a draft or start a manual build to bypass the claim. |
| GitHub asks to approve PR workflows | Review the candidate, then approve normal PR-triggered workflows if appropriate. This is not PR approval or merge. Require all checks. |
| Native Quality gate is pending | Follow the separate independent Quality run. It must finish with current authenticated evidence. Pending/superseded results never pass. |
| Native gate failed but exact independent Quality is now completed/success | Verify unchanged head/base/intent and current check ownership. Rerun **only the read-only native gate job**; do not rerun the paid independent Quality assessment. |
| Independent Quality failed | Inspect the actual gate and evidence. Fix genuine findings. A fresh full assessment is a new paid decision; don't rerun only failed controller jobs to borrow artifacts from another attempt. |
| Base advanced | Update the PR as needed; old Quality clearance is invalid. Request a current assessment for the selected PR, not every open PR. |
| Evidence missing or expired | Record the limitation. Absence is not a pass and does not justify a paid replay merely to recreate logs. |

## Manual entry points are different

The explicit manual [Software workflow](run-software-factory.md) and [Quality workflow](run-github.md) have their own attempt semantics. A whole-workflow retry may run Copilot and may create another draft or assessment. Inspect/reconcile existing effects first; only a maintainer can decide to authorize a fresh attempt. The manual entrypoint is not a fallback to circumvent a permanent label claim. No automatic paid retry or merge.

## Check credentials and configuration

Check repository secret names, token entitlement, reviewed SHA pins, Actions create-PR policy and required CI/Quality configuration. Never print credentials, paste them into issues or weaken branch protection to make a run green. See [configuration](../reference/configuration.md).

For interrupted publication and recovery experiments, consult the [historical evidence](../history.md). Those retired drills are not procedures to dispatch again.
