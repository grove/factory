# Assess a pull request with Quality Factory

Quality Factory independently checks an eligible PR, including human-authored changes. It does not need Software Factory to run first. It verifies the pinned candidate, obtains a bounded Copilot review and publishes an authenticated result. Ordinary CI and human review are still required.

## Install and enable

Follow [Install Factory](../getting-started-new-repository.md) and [Configuration](../reference/configuration.md). Quality needs a reviewed immutable caller and entitled Copilot credential. Eligible PRs are open, same-repository PRs targeting the default branch. Fork PRs and merge-queue candidates are outside this profile.

## Normal PR flow

1. Open or update an eligible PR. The permissionless PR signal tells the trusted coordinator to assess its current head, base and title/body.
2. The independent Quality workflow executes pinned verification, a bounded Copilot review, consolidation and evidence publication.
3. The native read-only `sfstack quality` required job authenticates the current independent result, including its completed backing workflow, required jobs and evidence. It waits through legitimate pending or superseding states without starting another model run.
4. Inspect the actual PR and both Quality and ordinary CI. Only a human decides whether to merge.

A passing assessment can be reused for unchanged head/base/title/body. A draft-to-ready change alone does not require fresh review of an identical passing result. A changed head or acceptance intent needs fresh evidence. A default-branch push invalidates stale clearance **without automatically starting AI review of every open PR**.

Pending, failed, missing, inconclusive or stale evidence is not a pass. A superseded old check can appear red even though a newer assessment is running; inspect the latest trusted generation.

## Run or retry manually

In **Actions → sfstack GitHub quality → Run workflow**, select the current default branch and enter an open PR number. Leave optional expected-head, expected-base and request-id fields empty for a manual assessment. Or:

```sh
gh workflow run sfstack-quality.yml --repo YOURORG/YOURREPO --ref main -f pr-number=123
```

This explicitly requests a **new paid assessment**, even when a previous one passed. Use it when fresh review is needed; never dispatch blindly after a native gate failure.

If the exact current independent Quality workflow already completed successfully but only the native read-only witness failed, inspect the identities and rerun **only that native job**. Do not restart Copilot. For a genuinely failed independent assessment, investigate the evidence first; a whole-controller retry is a fresh paid decision and requires its own attempt evidence. See [Troubleshooting](troubleshooting.md).

## Make the check required

Configure branch protection/rulesets for the exact **sfstack quality** check from the GitHub Actions source, ordinary required CI, up-to-date branches and human review. Use the native PR workflow included by the installer, not the independent workflow's internal job named `sfstack quality gate`. The native witness is read-only and cannot invent a successful result.

## Cost control and further decoupling

Eligible PR events can consume Copilot usage automatically. The base-push invalidation and native gate do not run AI. Avoid unnecessary manual dispatches. The current assessment remains bound to the current base; do not reuse stale clearance to reduce cost.

## What runs and where authority lives

The token-free PR signal, trusted default-branch coordinator, pinned independent Quality controller, separate verification/review/publication jobs and native read-only gate have different responsibilities. See [Architecture and trust boundaries](../explanation/trust-boundaries.md).

## Inspect evidence and authorization

Follow the published check to its exact workflow, attempt, candidate and base. Inspect verification and review outcomes, the trusted gate, and retained `sfstack-quality-<attempt>` artifact. A green check is not human approval. Missing or expired evidence cannot establish a new success.

## Validate after merging

Review default-branch CI; existing stale assessments on other open PRs may be invalidated without new model calls. Refresh a selected PR only when current review is needed.

## Maintain and test the integration

[Host validation](../installation.md) describes offline regression tests. The [original technical guide](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-github.md) preserves implementation details and earlier rollout history.

## Scope and limits

This is ordinary GitHub Actions isolation, not a hardened sandbox. Never broaden permissions or bypass policy to assess an unsupported candidate.

[Back to documentation](../README.md).
