# Install and validate factory

The supported deployment is a **caller-scoped GitHub Actions host**, installed locally or invoked through SHA-pinned reusable Factory workflows.
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

## Reuse Quality Factory in sfstack (first manual pilot)

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

## Self-contained GitHub Agentic Workflows reviewer

The first real cross-repository Quality assessment
[run #44918424600](https://github.com/grove/sfstack/actions/runs/44918424600)
confirmed authenticated admission, exact-head candidate verification and access
to the Copilot credential. The compiled Agentic Workflows reviewer then failed
in **activation before an agent ran** with:

```
ERR_CONFIG: ERR_SYSTEM: Failed to resolve runtime import path
.github/workflows/sfstack-review.md: ENOENT
```

The source Markdown belongs to `grove/factory`, while GitHub supplies the
caller repository workspace during `workflow_call`. It must not be copied to
each caller or retrieved from a mutable branch. The authored review now sets
`inlined-imports: true`, which causes the **pinned gh-aw compiler** to embed
the author-reviewed prompt directly in the lock file. This removes the
runtime dependence on the caller's `.github` directory. See
[gh-aw self-contained lock files](https://github.github.com/gh-aw/reference/imports/#self-contained-lock-files-inlined-imports-true).

The review's host-owned `steps` also check out the Factory controller from
`job.workflow_repository` at `job.workflow_sha` instead of
`github.workflow_sha`, which is the **caller** default-branch commit during a
reusable call. The candidate remains checked out from the caller repository
at the authenticated PR head. The strict compiler output and negative
boundary tests are required evidence before this change can be installed.

The failed run correctly published a `sfstack quality` **failure** on the
original candidate head. This change does not retroactively pass it, replace
a missing human review, or permit automatic merging. After reviewing this
factory PR, update the pin in the caller repository through a second reviewed
PR and repeat the manual test; do not force push or replace the old run.

## Automatic Quality assessments via reusable Factory event coordinator

The **same-repository** GitHub Actions host can now be reused without copying
the Python controller into a target. Install three thin workflows in that
repository: the credential-free `sfstack-pr-signal.yml` triggered by
`pull_request`, the `sfstack-quality-events.yml` caller triggered by
`workflow_run` / default-branch `push`, and the existing manual-and-automatic
`sfstack-quality.yml` caller. Pin **both** called Factory workflows to the
**same immutable reviewed Factory commit**; do not use a mutable branch.

The signal only acknowledges same-repository PR events that target the default
branch: opened, reopened, synchronize, edited, and ready_for_review. Its token
has **zero permissions**. The default-branch event workflow uses the fully
authenticated `workflow_run` object to re-read the PR and dispatch a
`workflow_dispatch` of `sfstack-quality.yml` with the exact expected head,
current base and coordinator request ID. The controller itself always checks
the run's authenticated workflow ID, default-branch SHA and run title.

On every default-branch push, the **invalidation** job revokes old-base
`sfstack quality` clearance without starting another paid Copilot review.
After the Quality run completes, the **reconciliation** job can close
interrupted, orphaned or superseded check ownership as a failure and must never
invent success. The coordinator uses the same serialized check-writer lock as
the Quality publisher; only its `dispatch` job has `actions: write`.
The other two jobs cannot start AI reviews.

The caller grants the upper bound `contents: read`, `pull-requests: read`,
`actions: write`, `checks: write`; the **called** workflow narrows permissions
per job. It passes no model secret. The Quality caller passes
`COPILOT_GITHUB_TOKEN` only to the trusted Quality path. Never run the
coordinator from `pull_request_target`, download PR artifacts into its
privileged jobs, or trust event payload data without the authenticated API
re-read. The event jobs check out Factory from the immutable
`job.workflow_repository`/`job.workflow_sha`; GitHub runs, PRs and checks
belong to the target.

**Important:** Fork PRs do not trigger this automatic route, and a base push
only **invalidates** stale clearance (it does not automatically reassess every
open PR). An operator can run Quality manually against the new base, or wait
for a new eligible PR signal. GitHub branch protection / rulesets must still
require an up-to-date GitHub Actions `sfstack quality` check, the ordinary CI
and human approval. A visible passing check without those rules is **not a
merge gate**. The host executes candidate tests on ordinary Actions runners,
not an isolation boundary suitable for hostile PR code.

### Live acceptance after target merge

1. Keep a bounded same-repository draft PR as the subject (sfstack uses
   [draft PR #37](https://github.com/grove/sfstack/pull/37)).
2. After reviewing and merging the coordinated Factory + target PRs, update
   the subject PR's branch with one harmless new commit. Confirm `sfstack PR
   signal`, `sfstack quality events` dispatch, and the automated Quality run
   all have verified caller identities; inspect the exact-head check.
3. Push a new default-branch commit and confirm the existing success is
   invalidated or remains nonpassing for the advanced base **without** a new
   AI review. Advance the PR branch or run manually to get fresh clearance.
4. Inject fault cases separately, including ambiguous dispatch and publisher
   response loss; preserve any negative artifacts instead of claiming a
   successful result. Track in [Factory acceptance #1](https://github.com/grove/factory/issues/1).

The same-repository Factory self-hosted path continues to operate independently.
This is a reusable **event-processing workflow**, not a central GitHub App or
server with cross-repository credentials.

## Reusable Software Factory for a trusted target repository

The bounded Software Factory workflow can be called by a **thin**
`.github/workflows/sfstack-software.yml` in the target repository, with a
**full, reviewed Factory commit SHA** (never a mutable branch), just as for
Quality. The operator dispatches the caller from its **default branch** and
selects an open issue, 1–8 exact allowed paths, explicit acceptance criteria,
and `change` or `defect` mode. There are **no automatic issue triggers**;
issue text cannot choose additional files or widen repository permissions.

Factory's `sfstack-software.yml` provides both `workflow_dispatch` for
same-repository use and `workflow_call` for reuse. The controller checkouts
use `job.workflow_repository` and `job.workflow_sha` (the reviewed
Factory source), while the *candidate* is checked out from
`github.repository` at the authenticated caller default-branch
`github.workflow_sha`. The nested gh-aw builder uses the Factory-bound
`$/` self-reference and its reviewed Markdown prompt is **inlined** in the
compiled lock file.
GitHub [documents the `$/` self-repository syntax](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows) for nested reusable calls; it resolves to the called Factory workflow's own repository and commit, not the outer caller's workspace. The same mechanism passed the [live cross-repository Quality assessment](https://github.com/grove/sfstack/actions/runs/44925384278). The Software path itself still needs its own non-agent graph probe and later live acceptance. The verifier executes the candidate in a fresh job with
no write privileges. Only the final publisher has scoped
`contents/pull-requests/actions/checks: write`, and it reconstructs Git
objects from a separate **read-only caller candidate checkout**, never
from Factory's unrelated source tree. It may create a **draft PR** and
request a fresh exact-head Quality assessment but may not approve or merge.

Before a first live invocation, the target repository owner must configure
`COPILOT_GITHUB_TOKEN`, allow GitHub Actions to create pull requests,
and review project-specific verification/test commands and allowed file scope.
Keep the target's existing protected `main`, required CI and Quality checks,
and its **solo-maintainer** merge rule (zero external approvals). The owner
must still inspect the draft and evidence before voluntarily merging. Do not dispatch against a hostile codebase on an
ordinary runner or treat a schema-valid builder response as a completed
publication.

**Acceptance remains separate:** A strict compiler pass and host fixture tests
do not prove actual cross-repository issue admission, agent proposal, draft
publication, or Quality dispatch. Run a bounded, harmless issue on the
caller after the Factory SHA and target caller have been reviewed and merged.
Retain the build and verification artifacts, exact candidate SHA, created
draft, Quality check and human inspection in Factory acceptance issue #1.
