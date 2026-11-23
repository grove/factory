# Install and validate the Factory host

**Installing into a project?** Use the [onboarding walkthrough](getting-started-new-repository.md). It installs small pinned callers, not copies of the host. This page is for Factory maintainers.

## Local setup

Use Python 3.11+ in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python tools/bootstrap_contracts.py
sfstack-contract version
python -m unittest discover -s tests -v
```

Bootstrap verifies the bundled wheel against `sfstack.lock.json` and installs the hash-pinned dependencies. No sibling sfstack checkout or private-module import is needed.

Run the deterministic regressions with fresh output directories:

```sh
python evals/run_github_regression.py --output dist/github-regression
python evals/run_software_regression.py --output dist/software-regression
python evals/run_defect_regression.py --output dist/defect-regression
```

See [regression documentation](../evals/README.md). These are no-model fixtures and subprocess checks; they do not establish live agent effectiveness or human approval.

## Enable the GitHub host

The caller owns its repository events, credentials, verification results and published checks. Follow [configuration](reference/configuration.md) for the reviewed profile, required native Quality gate and repository settings. Review all pin and permission changes in normal PRs.

## Install in another target repository

Use [onboarding](getting-started-new-repository.md). Do not copy Factory's own CI or override the host's checks through issue text. An existing installation requires a reviewed upgrade diff rather than silently overwriting callers.

## Upgrade the portable contracts

Build the wheel from a reviewed immutable sfstack source revision. Update the bundled wheel, source provenance, SHA-256 in `sfstack.lock.json`, hash-locked requirements and accepted version together. Run the complete host suite and positive/negative regressions before accepting the new pin.

Never use unpinned packages or candidate-supplied CLI paths in trusted jobs.

For details of the old manual and reusable workflow integration pilots, see the [historical installation record](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md) and [evidence index](history.md). Follow current instructions rather than the historical deployment steps.

[Back to documentation](README.md).

## Archived sections

Historical sections from the previous guide remain available at the immutable revision below. They may describe obsolete workflows or settings.

<a id="reuse-quality-factory-in-sfstack-first-manual-pilot"></a>
- [Reuse Quality Factory in sfstack (first manual pilot)](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md#reuse-quality-factory-in-sfstack-first-manual-pilot)
<a id="self-contained-github-agentic-workflows-reviewer"></a>
- [Self-contained GitHub Agentic Workflows reviewer](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md#self-contained-github-agentic-workflows-reviewer)
<a id="automatic-quality-assessments-via-reusable-factory-event-coordinator"></a>
- [Automatic Quality assessments via reusable Factory event coordinator](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md#automatic-quality-assessments-via-reusable-factory-event-coordinator)
<a id="live-acceptance-after-target-merge"></a>
- [Live acceptance after target merge](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md#live-acceptance-after-target-merge)
<a id="reusable-software-factory-for-a-trusted-target-repository"></a>
- [Reusable Software Factory for a trusted target repository](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md#reusable-software-factory-for-a-trusted-target-repository)
