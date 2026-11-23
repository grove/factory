# Build a change with issue labels

**Already installed?** Start with an issue. If Factory is not installed in your repository, follow [Install Factory](../getting-started-new-repository.md).

## Once per repository

The default branch must contain the reviewed SHA-pinned issue-label and Quality callers. The exact labels, entitled Copilot secret, required CI/Quality, protected branch and draft-PR settings must be configured. See [Configuration](../reference/configuration.md).

Opening or editing an issue alone does not start work.

## Create a simple issue

Choose **Software Factory work item** when creating a GitHub issue, or use this format (replace the file and criteria with a real task):

```md
Title: docs: clarify the CLI version check

## Problem
New users cannot tell how to verify the installed CLI version.

## Files to change
- `docs/reference/public-cli.md`

## Acceptance criteria
1. Give the actual offline version command and expected output.
2. Explain that the command does not invoke an agent.
```

Use 1–8 exact backticked file paths, each on its own bullet, and 1–8 concrete criteria. The allowed paths are `docs/`, `examples/`, `tests/` or root `README.md`. No directories, globs, hidden files, workflows or dependency/configuration changes.

## Choose one of two human-authorized paths

| | Direct build | AI-planned build |
| --- | --- | --- |
| Use when | The issue is already clear and bounded | You want a separate strategy before spending on implementation |
| First action | Add `factory:run` once | Add `factory:plan` |
| Bot response | Permanent direct-mode claim with exact scope | Scope snapshot, then independently validated advisory AI plan |
| Next action | Inspect build | Review the second comment; add `factory:run` once only if satisfied |
| Model usage | Paid implementation + independent Quality | Paid planning + paid implementation + independent Quality |

Only a human writer may add the authorizing label. Direct mode is available only when no earlier trusted planning request/snapshot or orphaned AI plan exists and the planning label is not present. A failed plan is not a shortcut to direct mode.

A plan proposes file-level steps, verification, risks and questions. For example, “make empty input invalid” is merely a criterion; “change the parser to raise ValueError and test that exact behavior” is actionable advice. Proposed tests are not executed evidence.

## Follow the run and review the draft

1. Open the bot's one-shot claim and check the exact scope and acceptance criteria; follow its Actions run.
2. For direct mode, separate plan/publish-plan jobs should be skipped. A planned build uses previously validated advice and does not repeat planning. Check the actual implementation and independent verification jobs.
3. A successful build publishes a draft PR and requests separate exact-head Quality. Inspect the build evidence and actual diff. If GitHub asks to approve PR workflows, review the change and approve the ordinary workflows as appropriate.
4. Check current Quality and required CI; review the issue's acceptance criteria and decide whether to merge yourself. Check post-merge CI and close the issue when finished.

## Repair a defect

For a bounded behavior bug, start the issue title with `defect:` and list an existing `examples/` implementation file and one new `tests/test_*.py` regression file. You can specify `Mode: defect` and `Regression file: tests/test_example.py` explicitly. The host requires a healthy original baseline, genuine test-only RED, repaired GREEN and full verification. A proposed regression alone is not proof. See [manual Software reference](run-software-factory.md#repair-a-reproduced-defect-v02) for the verification semantics.

## Recover without duplicate spending

The run claim permanently binds the authorized issue, base, scope, actor and first attempt. If a plan fails or is stale, inspect its records; a changed issue/base needs a fresh explicitly authorized plan before building. An unchanged failed plan cannot simply be billed again.

After a build is claimed, do not delete the bot claim, remove/reapply the label, rerun the paid label event or dispatch a manual build to bypass the claim. Inspect the exact run and reconcile any partial publication. A further attempt needs a separately authorized follow-up issue.

[Full troubleshooting](troubleshooting.md) covers failed or pending jobs, missing drafts, native Quality recovery and stale evidence.

## What it does not do

Labels do not grant broader scope, substitute for checks, approve or merge PRs, or deploy code. Candidate execution and publication remain separate. Ordinary Actions isolation is not a hostile-code sandbox.

## Read-only run diagnostics

Use [Inspect a run](inspect-factory-run.md) to see jobs, evidence, independent Quality, reported usage and safe recovery hints without another paid AI call.

[Back to documentation](../README.md).
