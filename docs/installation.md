# Install and validate factory

The supported initial deployment is a **same-repository GitHub Actions host**.
The workflow run, issue or pull request, credentials, controller revision, and
published check all belong to the repository containing the integration. Moving
the source into `grove/factory` does not turn its existing API calls into a
cross-repository controller.

## Local setup

Clone this repository and activate a Python 3.11+ virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python tools/bootstrap_contracts.py
sfstack-contract version
python -m unittest discover -s tests -v
```

The bootstrap verifies the bundled wheel against `sfstack.lock.json` and installs
the hash-pinned dependency set. The installed CLI version must match the lock.
No sibling sfstack checkout or `PYTHONPATH` setting is needed.

## Enable the GitHub host

Merge the reviewed integration into the default branch. Configure
`COPILOT_GITHUB_TOKEN` through repository secret settings, using a credential with
the Copilot entitlement described in the [quality guide](how-to/run-github.md).
For Software Factory, enable the repository setting allowing Actions to create
pull requests. The host creates drafts and never approves or merges them.

The [quality guide](how-to/run-github.md) describes automatic PR signals, manual
dispatch, branch freshness, check ownership, and operator recovery. The
[software guide](how-to/run-software-factory.md) describes explicit issue scope,
defect reproduction, independent verification, and durable publication.

Configure the destination's normal CI, the `sfstack quality` check from the
GitHub Actions app, an up-to-date branch requirement, and independent human
review before relying on those checks as merge gates. A visible check alone
does not enforce a merge rule. The migration does not change repository settings.

## Install in another target repository

Use a reviewed, immutable factory revision as the installation source. Install
the host as one coherent snapshot:

- `integrations/github/` and its host-owned workflow, policy, check definitions,
  and submission schemas.
- The `sfstack-*.yml` workflows and authored/compiled Agentic Workflows in
  `.github/workflows/`, together with `.github/aw/` compiler and action pins.
- `tools/bootstrap_contracts.py`, `sfstack.lock.json`, the pinned requirements
  files, and the wheel in `vendor/`.

Keep the destination's ordinary CI. Select that project's trusted verification
commands in `integrations/github/checks.json`; the bundled defaults run factory's
own regression suite. Review the bounded file policy in `software.py` before
using it for a different project. Its initial scope allows exact files under
`docs/`, `examples/`, `tests/`, or `README.md`; installing the host does not widen
that scope.

If the default branch is not `main`, update the workflow push filters. Record the
installed factory revision and validate the complete integration in that target.
Repository names in command examples refer to `grove/factory`; substitute the
actual target. Do not redirect dispatch to a different repository without a
separately designed and reviewed identity and credential boundary.

## Upgrade the portable contracts

Build a wheel from a reviewed immutable sfstack source revision. Update the
wheel, its source provenance and SHA-256 in `sfstack.lock.json`, the hash-locked
requirements, and the client's accepted version together. Run the complete
host tests and positive/negative regressions before accepting the new pin.

Never accept an unpinned package, a mutable source branch, or a candidate-supplied
CLI path as a substitute for the trusted controller dependency.

## Reuse Quality Factory in sfstack (manual-only pilot)

A thin workflow in `grove/sfstack` named
`.github/workflows/sfstack-quality.yml` can invoke this reusable workflow by
an **immutable full commit SHA**. The first pilot is deliberately
`workflow_dispatch` only: it does not install the automatic PR signal,
coordinator, or Software Factory.

The caller must use the exact workflow filename `sfstack-quality.yml` and
`run-name: sfstack quality / PR #<number> / request manual`. The publisher
checks the caller's Actions run ID, attempt, filename, display title, default
branch, and head SHA before writing a check. The reused jobs check out the
**factory** controller from `job.workflow_repository` at
`job.workflow_sha`, while the candidate, API reads, artifacts and
`sfstack quality` check belong to the **caller** repository. The Agentic
Workflows nested review is loaded from the same factory revision using the
GitHub.com self-reference `$/` syntax, not the caller's checkout.

The caller grants `contents: read`, `pull-requests: read`,
`actions: read`, and `checks: write`, and passes only
`COPILOT_GITHUB_TOKEN` from its own Actions secrets. Do not call from
`pull_request` events or expose its credential to candidate code.
The default `checks.json` executes `python -m unittest discover -s tests -v`
on the pinned candidate, which also works for the initial sfstack pilot;
other repositories need a separately reviewed project-specific check policy.

**Not part of this phase:** automatic PR triggers, base-push invalidation
coordination, unattended check reconciliation, cross-repository publication
tokens, Software Factory, or an enforced GitHub merge rule. A green check is
not itself permission to merge. The manual workflow is only a bounded
integration pilot; later automation must add caller-local event coordination
without weakening run ownership, tests, or human review.
