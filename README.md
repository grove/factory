# Factory

**Turn a scoped GitHub issue into a verified draft pull request. Independently assess any eligible pull request. You stay in control of what merges.**

Factory runs inside your repository's GitHub Actions. It uses Copilot for bounded implementation and review, and [sfstack](https://github.com/grove/sfstack) for portable skills, contracts and evidence validation.

## Start here

| I want to… | Go to |
| --- | --- |
| Install Factory in my repository | [Install Factory](docs/getting-started-new-repository.md) |
| Build a change from an issue | [Use issue labels](docs/how-to/issue-label-software-factory.md) |
| Review an existing pull request | [Run Quality Factory](docs/how-to/run-github.md) |
| Understand a failed run or usage | [Inspect a run](docs/how-to/inspect-factory-run.md) · [Troubleshooting](docs/how-to/troubleshooting.md) |
| Understand or maintain Factory | [Documentation index](docs/README.md) |

## How it works

1. Create an issue with exact files and observable acceptance criteria.
2. Choose **direct**: apply `factory:run` once; or **planned**: apply `factory:plan`, review the validated AI proposal, then apply `factory:run` once.
3. Factory implements the bounded change, independently verifies it, opens a draft PR and requests independent Quality.
4. Review the actual change and evidence. Require current Quality and ordinary CI, then merge yourself.

Opening or editing an issue alone never starts implementation. Both labels require an authorized human writer. A claimed build cannot be restarted by relabeling.

**Costs:** direct mode skips the separate paid planner, not the paid implementation or independent Quality assessment. Planned mode adds a paid planning call. Eligible PR events may also initiate paid Quality; ordinary Actions minutes and account billing are separate. [Inspect reported usage](docs/how-to/inspect-factory-run.md).

## Is my repository supported?

The current **pilot** is intentionally restricted:

- Python 3.13 with substantive standard-library `unittest` tests that run without project-specific dependency installation.
- One to eight exact files under `docs/`, `examples/`, `tests/`, or root `README.md`; no arbitrary application source trees, workflows, or dependency changes.
- Same-repository PRs targeting the default branch, reviewed SHA-pinned callers, GitHub Actions, Copilot entitlement and required CI/Quality with human review.

Other languages, test runners, dependency-heavy projects and broader edit scopes require a separately reviewed host profile. The runner is ordinary CI isolation, **not** a hostile-code sandbox.

## Where the pieces live

Factory owns GitHub events, authorization, credentials, independent candidate execution, durable publication and recovery. sfstack owns the portable skills, schemas, recipes and policy engine. Factory consumes sfstack through its installed, versioned public CLI, not private module imports. Your issues, PRs, checks, credentials and evidence remain in your repository.

For maintainer setup and deterministic regressions, see [Install and validate the host](docs/installation.md). For security and integration details, see [Architecture and trust boundaries](docs/explanation/trust-boundaries.md).

[Historical evidence and migration](docs/history.md) records the pilot results and their limitations. It is not a setup procedure.

[Apache License 2.0](LICENSE).
