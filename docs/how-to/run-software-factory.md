# Run Software Factory manually

For normal installed-repository work, [use issue labels](issue-label-software-factory.md). This page is the explicit manual entrypoint reference. It is not a method to bypass a permanent label-event claim.

## Enable the integration

Install the reviewed default-branch callers, configure GitHub and retain required CI and Quality using the [onboarding guide](../getting-started-new-repository.md). The manual caller is named `sfstack-software.yml`; only an authorized maintainer chooses its inputs.

## Select a small issue and run it

Select an open issue, exact file paths and observable criteria. In **Actions → sfstack GitHub software → Run workflow**, select the current default branch.

| Input | Meaning |
| --- | --- |
| `issue-number` | Open issue in the caller repository |
| `allowed-paths` | JSON array of 1–8 exact permitted file paths |
| `acceptance-criteria` | JSON array of 1–8 observable outcomes |
| `repair-mode` | `change` (default) or `defect` |
| `regression-file` | Defect mode: one exact new Python unittest path |

Example command template (replace the repo, branch, issue, paths and criteria):

```sh
gh workflow run sfstack-software.yml --repo YOURORG/YOURREPO --ref main \
  -f issue-number=123 \
  -f 'allowed-paths=["docs/getting-started.md"]' \
  -f 'acceptance-criteria=["Explain how to run the existing tests."]'
```

This explicitly authorizes paid Copilot implementation. See [configuration](../reference/configuration.md) for exact file and size limits.

## Repair a reproduced defect (v0.2)

Choose `repair-mode=defect`. Include an existing implementation file under `examples/` and one new `tests/test_*.py` file; specify the regression file input. The new test must not exist on the pinned base.

The host independently requires:

1. Passing original full-suite baseline.
2. Genuine test-only RED with an executed failing assertion, not a skip, import error or timeout.
3. Reconstructed exact scoped candidate and repaired GREEN.
4. Passing full candidate suite, retained evidence and independent Quality.

Copilot's diagnosis and suggested tests are claims, not measured proof. A broader repair needs a separate reviewed file policy.

## What executes

Admission pins the issue, base, exact paths, criteria, actor and attempt. The agent produces a bounded change proposal; a separate fresh host verifier reconstructs and tests it. Only the trusted publisher receives scoped write permission and opens a draft PR after verification. It explicitly requests Quality for the exact candidate. See [Architecture and trust boundaries](../explanation/trust-boundaries.md).

## Why the draft explicitly starts Quality Factory

An Actions-created PR may need human approval before ordinary PR-triggered workflows run. The publisher separately requests Quality rather than relying on the PR event. Review the diff and approve the ordinary workflows where appropriate; do not bypass required checks.

## Inspect the result and evidence

| Attempt-specific artifact | Contains |
| --- | --- |
| `sfstack-software-inputs-<attempt>` | Pinned inputs and work item |
| `sfstack-agent-change-<attempt>` | Raw proposal, when available |
| `sfstack-software-result-<attempt>` | Verified candidate, logs and evidence; defect mode includes baseline, RED/GREEN and diagnosis |
| `sfstack-software-publication-<attempt>` | Publication result, when attempted |

A successful Software run is not a successful Quality assessment. Review the current [Quality result](run-github.md), ordinary required CI and actual diff before human merge.

## Runtime, cost, and operator responsibilities

Implementation and independent review use Copilot. GitHub Actions compute is separate. Inspect reported usage or retained evidence where available; no inferred invoice. The [run summary](inspect-factory-run.md) is for label-event runs, not arbitrary manual dispatches.

## Retry or recover

First inspect existing branches, drafts, check ownership and publication evidence. A manual all-jobs retry can start a new paid attempt and create another draft. If a manual attempt genuinely needs repeating, the maintainer must explicitly authorize it against the intended current issue/base. Do not borrow artifacts from an earlier attempt or rerun only failed controller jobs. A claimed label run is different: never replay it via this manual entrypoint.

See [Troubleshooting](troubleshooting.md) for safe recovery. Historical pilot and transport incident details are in the [original guide](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md) and [evidence index](../history.md).

[Back to documentation](../README.md).

## Archived sections

Historical sections from the previous guide remain available at the immutable revision below. They may describe obsolete workflows or settings.

<a id="compiler-redacted-agent-file-transport-issue-20"></a>
- [Compiler-redacted agent-file transport (issue #20)](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#compiler-redacted-agent-file-transport-issue-20)
<a id="crash-safe-publication-and-quality-factory-request-recovery-29"></a>
- [Crash-safe publication and Quality Factory request recovery (#29)](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#crash-safe-publication-and-quality-factory-request-recovery-29)
<a id="troubleshoot-the-first-live-run"></a>
- [Troubleshoot the first live run](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#troubleshoot-the-first-live-run)
<a id="completed-v02-live-defect-pilot--credential-inheritance-15"></a>
- [Completed v0.2 live defect pilot — credential inheritance (#15)](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#completed-v02-live-defect-pilot--credential-inheritance-15)
<a id="five-live-copilot-attempts-and-measured-workflow-time"></a>
- [Five live Copilot attempts and measured workflow time](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#five-live-copilot-attempts-and-measured-workflow-time)
<a id="recovered-change-independent-gates-and-final-merge"></a>
- [Recovered change, independent gates and final merge](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#recovered-change-independent-gates-and-final-merge)
<a id="what-was-and-was-not-demonstrated"></a>
- [What was and was not demonstrated](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#what-was-and-was-not-demonstrated)
<a id="safe-recovery-when-verification-passes-but-draft-publication-fails"></a>
- [Safe recovery when verification passes but draft publication fails](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#safe-recovery-when-verification-passes-but-draft-publication-fails)
<a id="repeat-a-controlled-live-acceptance-test-on-a-different-defect"></a>
- [Repeat a controlled live acceptance test on a different defect](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#repeat-a-controlled-live-acceptance-test-on-a-different-defect)
<a id="controlled-loss-of-response-and-interrupted-run-acceptance"></a>
- [Controlled loss-of-response and interrupted-run acceptance](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#controlled-loss-of-response-and-interrupted-run-acceptance)
<a id="reusable-caller-scoped-software-factory-deployment"></a>
- [Reusable caller-scoped Software Factory deployment](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#reusable-caller-scoped-software-factory-deployment)
<a id="nested-reusable-workflow-syntax-evidence"></a>
- [Nested reusable workflow syntax evidence](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md#nested-reusable-workflow-syntax-evidence)
