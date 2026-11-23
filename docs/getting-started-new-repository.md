# Getting started: install Software and Quality Factory in another GitHub repository

**Start here if you maintain a repository that does not yet have sfstack Factory.**
This guide installs small, version-pinned GitHub Actions *callers* in your own
repository. The implementation stays in [`grove/factory`](https://github.com/grove/factory);
your issues, pull requests, credentials, logs, verification runs, and checks stay
in **your** repository. There is no server, cross-repository credential, or
automatic merge service to provision.

**What you will have:** write an issue using an issue template, apply
`factory:plan` to request a paid, read-only Copilot implementation plan, and (after reviewing it) apply
`factory:run` once to authorize a paid Copilot build. Independently verified
output becomes a *draft PR*, then receives separate Quality and ordinary CI.
**You** review and decide whether to merge.

**Important limitation:** this first installer supports only the reviewed
**Python-unittest pilot profile**. Its pinned Factory host runs
`python -m unittest discover -s tests -v` inside ordinary GitHub Actions with
Python 3.13. The repository must already have substantive discoverable tests
that run without installing project-specific dependencies. Existing Software
Factory edit policy permits **only exact** `docs/`, `examples/`, `tests/` files
or root `README.md`; it cannot change your `src/` or `lib/` tree. The installer
does *not* make a Node, Go, Rust, pytest-only, dependency-heavy, or arbitrary
source-layout project compatible. [Other projects](#other-languages-and-custom-checks)
need a separate reviewed host policy/verification change **before** a paid run.

## Quick start: preview first, then make an installation PR

Requirements: Git, Python 3.11+, the [GitHub CLI](https://cli.github.com/)
(`gh`) authenticated to your own repository, and a **clean checkout** of your
project's current default branch. Have the factory source available in a
separate directory; use a reviewed, immutable Factory revision, not an
unreviewed PR or a branch supplied by issue text.

```sh
# 1. Obtain and review the Factory source in a separate directory.
git clone https://github.com/grove/factory.git ~/factory
# Only after reviewing the current Factory release:
FACTORY_REVISION="$(git -C ~/factory rev-parse HEAD)"
# Pin the full immutable revision; never choose a mutable branch in the caller.

# 2. Clone YOUR GitHub repo and update its default branch.
gh repo clone YOURORG/YOURREPO ~/yourrepo
git -C ~/yourrepo switch main
git -C ~/yourrepo pull --ff-only origin main

# 3. Preview the files and SHA-256 hashes: this does NOT write anything.
python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION"

# 4. Explicitly request a reviewable installation PR in YOUR repo.
# This checks a clean checkout, target identity, test inventory and current base;
# it creates a NEW local branch, commits only the generated files, pushes that
# branch without force and opens a PR. It never merges or configures settings.
python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION" \
  --checkout ~/yourrepo \
  --create-pr
```

Replace `YOURORG/YOURREPO` and `main` with **your** exact repository and default
branch. Before step 4, review the pinned Factory source and ensure that your
project satisfies the [prerequisites](#before-you-begin). If you use a branch
other than `main`, supply its exact name (for example, `release/v2`). The
installer binds the label guard to your repository and the Quality event filter
to your branch. It requires a reviewed exact `--factory-revision`, because the
new label workflow must use the same immutable Factory commit for its coordinator
and paid AI planning path. Never use `@main` or an unreviewed commit. The Quality
event workflows retain their separately reviewed matching SHA pins.

The tool does not automatically clone Factory dependencies, run target code,
call Copilot, or contact GitHub during a preview. **Only** `--create-pr` uses
your Git and `gh` credentials to fetch the current base, push a new branch and
open a PR. You can avoid all target-repository writes by using the [offline
bundle](#offline-review-or-no-github-cli) mode.

## Before you begin

1. **Confirm the project is eligible.** Your repository has a `tests/` tree with
   discoverable `test_*.py` tests, and the complete Python 3.13 standard-library
   `unittest` suite works *without installing extra project dependencies*.
   The installer checks for test files but **does not execute tests**. Run the
   command below yourself or, preferably, through your existing unprivileged
   CI. Test discovery must execute genuine tests with no skips or expected
   failures to qualify as positive Factory verification:

   ```sh
   python -B -m unittest discover -s tests -v
   ```

2. **Check your target file scope.** Only `docs/`, `examples/`, `tests/`, and
   root `README.md` are supported by this reviewed pilot. If you need changes
   to `.github/workflows/`, `src/`, `lib/`, lockfiles, dependencies, or other
   source trees, stop: the bounded host policy must be changed and reviewed
   separately. Do not attempt to bypass it through an issue label.
3. **Keep your current CI.** The generated seven files do **not** copy
   `grove/sfstack`'s `validate.yml`, because that workflow tests sfstack's own
   modules and is not usable in your repository. Maintain real independent
   project CI triggered on `pull_request` and on your default-branch push.
   The installer does not authenticate or configure your CI policy.
4. **Check repository access.** You need write access to create the installation
   PR and maintainer/admin access for setting secrets and protected-branch
   requirements. The new reusable workflows refer to a **public, immutable**
   Factory revision; an issue cannot select a different revision.
5. **Protect your main branch.** Keep required PR review/CI, strict up-to-date
   required status checks and no administrator bypass or force pushes. For a
   solo maintainer, GitHub can require **zero** external approvals while still
   requiring a PR and successful checks; teams can require reviews as their
   policy demands. The installer does **not** update branch protection.

## Review the installation PR

Your PR will propose exactly **seven** files:

| File | Purpose |
| --- | --- |
| `.github/workflows/sfstack-issue-label.yml` | Receive `issues:labeled`, authenticate a human writer, prepare immutable scope, run isolated billable AI planning, post a verified plan and accept a separate one-shot implementation claim |
| `.github/workflows/sfstack-software.yml` | Preserve the manual issue-to-draft fallback |
| `.github/workflows/sfstack-quality.yml` | Receive trusted manual/automatic Quality dispatch and call pinned Quality Factory |
| `.github/workflows/sfstack-pr-signal.yml` | Emit a zero-token PR event signal |
| `.github/workflows/sfstack-quality-events.yml` | Reconcile and invalidate stale checks, dispatch new exact-head Quality, **not** launch AI on default-branch pushes |
| `.github/workflows/sfstack-quality-required.yml` | Native read-only `sfstack quality` PR check that authenticates separate Quality evidence |
| `.github/ISSUE_TEMPLATE/factory-work-item.md` | Friendly issue template with exact paths and observable criteria |

**Review carefully:** the new label workflow's `github.repository` must exactly
match your target; the event coordinator's `push.branches` must use your
current default branch. Factory source and reusable-workflow refs must be **40-
character immutable SHAs**, never `@main`, tags or issue-supplied refs. The
Quality caller and Quality event coordinator must use the *same* Factory pin.
Different existing reviewed pins for the native Quality gate, manual Software
caller, and label Software caller are intentional; don't replace them with a
mutable latest version to make them look uniform.

If any of these seven paths already exists, the installer **refuses to
overwrite** it. Integrating into a repository with an existing partial Factory
installation is an upgrade/migration requiring separate review, not a safe
first install. The generated manifest contains per-file SHA-256 hashes for a
read-only audit and has no secret values.

Normal PR checks may require a maintainer to approve a workflow before they run.
Read the diff and CI evidence, then **merge the installation PR yourself**
through ordinary protected-branch review. The tool never approves or merges.

## Configure GitHub once, *after review and merge*

1. In your target repo **Settings → Secrets and variables → Actions**, set
   `COPILOT_GITHUB_TOKEN` to a token compatible with the [GitHub Copilot
   engine](https://github.github.com/gh-aw/engines/copilot/) and its entitlement.
   From a trusted terminal, you can run `gh secret set COPILOT_GITHUB_TOKEN
   -R YOURORG/YOURREPO` to enter it without putting the token on a command
   line. Never include its value in an issue, PR comment or workflow file.
2. In **Settings → Actions → General → Workflow permissions**, keep the default
   workflow permissions at **Read repository contents and packages** where
   permitted, and allow **GitHub Actions to create and approve pull requests**
   so the *scoped trusted publisher* can create **drafts**. This is a repository-
   wide toggle that also permits eligible workflow approvals; consider its
   security impact. The Factory never calls a PR approval or merge operation.
3. Create exactly two issue labels in **Issues → Labels**:
   `factory:plan` and `factory:run` (spelling/case matters). The PR intentionally
   does not create them or pre-apply either label to any issue.
4. Configure your existing branch protection or ruleset to require an up-to-date
   GitHub Actions **`sfstack quality`** check, alongside your own required CI
   checks; use the **GitHub Actions** check source rather than a name-only
   context that another app could spoof. The native required-Quality workflow
   is included because dispatch-only custom checks are not always eligible
   as a required PR check. Preserve human-controlled merges.
5. Confirm all workflows appear on the target's default branch and ordinary
   CI passes there. Never manually launch a production build merely to see
   whether the workflow is visible.

## First exercise: deliberate paid planning, then separately authorized paid build

Create an open issue using **Software Factory work item**, for example:

```md
Title: docs: clarify the getting-started instructions

## Problem
First-time readers need a short, accurate setup explanation.

## Files to change
- `docs/getting-started.md`

## Acceptance criteria
1. Add a short setup overview with the real prerequisites.
2. Explain how to confirm the project tests pass.
```

1. Apply `factory:plan` **as a human with write permission**. This explicitly
   authorizes a **paid Copilot planning call** but no implementation. In the
   `sfstack issue-label Software Factory` Actions run, expect **two** bot
   comments: first an exact deterministic authorization snapshot; second
   a proposed implementation plan with concrete file-level work, independent
   verification, risks and questions. The planning job cannot execute or
   publish source code. It does not
   create a PR. Confirm exact files, criteria, mode and pinned base.
2. Only if you want to spend Copilot usage, add `factory:run` **once**, as a
   writer. The trusted handler makes a durable one-shot claim and starts the
   existing Software Factory. It independently runs the configured tests,
   creates only a **draft PR**, and requests exact-head Quality.
3. Review the draft, its retained gate evidence and the independent
   `sfstack quality` result. If GitHub blocks PR-triggered CI in an
   `action_required` state, approve those normal workflows in the UI. Never
   treat a successful build alone as permission to merge.
4. Merge **manually** only when all current-head CI/Quality checks are green
   and the change satisfies your issue. Check post-merge CI and close the issue.

**No automatic reruns:** editing the issue or advancing the default branch
invalidates the plan. Remove/reapply `factory:plan` only if you explicitly
authorize another paid planning call for the changed scope/base, then review
the new AI proposal; do **not** simply relabel `factory:run`. Once a run is claimed, its
claim is permanent and relabeling cannot buy another build. Inspect existing
PR, check and Actions identities, then open a separately authorized follow-up
issue if needed. See [label troubleshooting](how-to/issue-label-software-factory.md)
for the exact safety boundary.

## Offline review or no GitHub CLI

To render a **fresh offline bundle** without GitHub, target Git writes, or
model calls:

```sh
python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION" \
  --output /tmp/factory-install-review-001
```

The new directory contains the seven `.github` files plus
`install-plan.json` with SHA-256 hashes. Read the manifest and workflows.
Then create a branch in your own clean target clone, copy **only** the
`.github` files into that branch, and open a PR using GitHub's web UI or a
normal authenticated Git client. The manifest is for reviewing the generated
bundle, not a required target workflow or secret. Never copy the sample
`grove/sfstack` CI workflow into an unrelated project.

## Common problems and recovery

| Symptom | Meaning and safe action |
| --- | --- |
| Installer says `Output directory already exists` | It will not overwrite an earlier bundle. Use a fresh output path. |
| Installer refuses an existing caller file | It found a partial/current Factory installation. Treat it as an upgrade requiring a new human-reviewed diff; don't overwrite silently. |
| Installer says the target is stale or dirty | Commit/remove your own local work, update the exact default branch and retry **only after inspecting the current checkout**. |
| Installer created a branch but the push or `gh pr create` failed | Do not blindly rerun. Inspect the local branch, GitHub's remote branch and any existing installation PR; continue the interrupted PR operation manually without force-pushing. No paid build is dispatched by the installer. |
| No AI plan comment | Confirm the label and human writer, inspect the issue-label Actions jobs and Copilot access. The first scope snapshot is not approval. Do not apply `factory:run` until validated model advice is published. |
| `factory:run` rejected as stale | Issue text or base changed after planning; reapply `factory:plan` and review the new preview before any new authorization. |
| A durable claim exists | Never delete the bot claim comment or reapply `factory:run` to restart; reconcile its original run/PR/check instead. |
| PR is blocked in `action_required` | A maintainer may need to approve normal PR-triggered workflows, including CI and native Quality. Don't bypass required checks. |
| Candidate verification fails | Inspect the host logs. The pinned host executes Python unittest; a dependency-heavy or different-language project is not supported by this installer. Don't swap in an agent-supplied verification command. |

## Other languages and custom checks

The current Factory verifier selects its trusted checks from the **reviewed
Factory-host policy** (`integrations/github/checks.json` at the pinned Factory
revision). The thin target caller cannot override those commands through an
issue, label or workflow input. This is deliberate: otherwise untrusted issue
text could remove tests or change what "verified" means. The present host also
has an exact-file scope limit.

To support another language, test runner, dependencies or source tree, make a
**separate reviewable Factory change** that introduces a trusted
project-specific verification profile and file policy. Qualify its real
positive/negative tests, update the target's immutable Factory pins through a
normal installation upgrade PR, then run a small authorized pilot. Never
pretend that copying the workflows alone validates an arbitrary project.

## What the installer never does

It never edits GitHub secrets, repository Actions permissions, required checks
or branch-protection rules. It never auto-labels an issue, invokes Copilot,
executes target code, bypasses CI, approves or merges a PR, or sends credentials
to an issue or untrusted PR. Only the explicit `--create-pr` flag performs
ordinary Git and GitHub CLI writes to create a **reviewable installation PR**.
Normal CI/Quality may run when that PR is opened if your repository already
has such workflows; review their cost policy. The default preview is offline.

For deeper architecture and migration details, see
[Factory installation](installation.md),
[Software Factory operations](how-to/run-software-factory.md), and
[label-based authorization](how-to/issue-label-software-factory.md).
