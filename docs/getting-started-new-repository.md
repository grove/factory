# Install Factory in your GitHub repository

Install once, then use issue labels to build small verified changes. Factory adds reviewed, version-pinned GitHub Actions callers; it does not replace your CI or take control of merges.

## Before you begin

You need:

- A GitHub repository whose Python 3.13 standard-library `unittest` suite runs substantive tests without extra project dependencies. Verify it in ordinary CI with `python -B -m unittest discover -s tests -v`.
- Work that fits exact paths under `docs/`, `examples/`, `tests/` or root `README.md`.
- Git, Python 3.11+, GitHub CLI (`gh`), write access and a clean target checkout. A maintainer must configure secrets and required checks.
- A reviewed immutable Factory commit. Do not use an arbitrary tag, branch or PR source.

The current [supported profile](reference/configuration.md) does not include arbitrary application source trees, workflow edits or other test stacks.

## Quick start: preview first, then make an installation PR

Replace `YOURORG/YOURREPO`, `main` and the Factory revision with your actual target, default branch and reviewed full commit SHA.

```sh
git clone https://github.com/grove/factory.git ~/factory
# Select a reviewed full 40-character Factory commit.
FACTORY_REVISION=REVIEWED_FACTORY_COMMIT_SHA
git -C ~/factory checkout --detach "$FACTORY_REVISION"

gh repo clone YOURORG/YOURREPO ~/yourrepo
git -C ~/yourrepo switch main
git -C ~/yourrepo pull --ff-only origin main

python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION"
```

This preview is offline. It shows the files and their SHA-256 hashes without writing to GitHub, executing target code or invoking Copilot.

To create the installation PR explicitly:

```sh
python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION" \
  --checkout ~/yourrepo \
  --create-pr
```

The installer checks repository identity, a clean current checkout and test-file inventory. It creates a new branch, commits only the seven generated files, pushes without force and opens a reviewable PR. It refuses existing caller files: a partial or previous installation needs an upgrade review, not an overwrite.

## Review the installation PR

Review the [seven generated files](reference/configuration.md#installed-files-and-source-pins). Verify the exact target repository, default-branch filter, immutable Factory pins, permissions and intended verification profile. Keep the existing project CI. Do not copy sfstack's own CI into your project.

Approve any normal PR workflows GitHub requires after reviewing the proposed changes. Merge the installation PR yourself.

## Configure GitHub once, after review and merge

1. In **Settings → Secrets and variables → Actions**, set `COPILOT_GITHUB_TOKEN` using an entitled credential supported by the [Copilot engine](https://github.github.com/gh-aw/engines/copilot/). The CLI can prompt securely: `gh secret set COPILOT_GITHUB_TOKEN -R YOURORG/YOURREPO`.
2. In **Settings → Actions → General → Workflow permissions**, keep default permissions read-only where permitted. Allow GitHub Actions to create and approve pull requests so the scoped publisher can create drafts. This is a repository-wide permission with security implications; Factory never approves or merges.
3. Under **Issues → Labels**, create exactly `factory:plan` and `factory:run`.
4. Protect the default branch: require ordinary project CI, the exact **sfstack quality** check from GitHub Actions, up-to-date branches and human review. A visible check alone is not merge enforcement.
5. Confirm the callers are on the default branch and ordinary CI passes.

The installer never changes these settings, creates secrets, applies labels, starts paid work or merges.

## First work item

Choose an actual small documentation improvement. In **Issues → New issue → Software Factory work item**, describe the problem, list exact permitted files and state concrete acceptance criteria.

For a clear issue, a human writer can apply `factory:run` once. The bot records a permanent claim and starts one paid implementation; independent Quality also uses Copilot. For a more uncertain issue, apply optional paid `factory:plan` first, review the validated second bot comment, then decide whether to authorize the build separately.

Follow [Build with issue labels](how-to/issue-label-software-factory.md) for the complete example, claim checks and review steps. A successful build produces a draft PR, not merge authorization. A human reviews the candidate, current Quality and CI, then decides whether to merge.

Do not relabel a claimed issue to retry it or use direct mode to bypass failed planning.

## Offline review or no GitHub CLI

Use a new output directory:

```sh
python ~/factory/tools/onboard_repository.py \
  --repository YOURORG/YOURREPO \
  --default-branch main \
  --factory-revision "$FACTORY_REVISION" \
  --output /tmp/factory-install-review-001
```

Review the seven generated files and `install-plan.json`. Copy only the generated `.github` files to a new branch of your clean target checkout and open a normal PR. The manifest is for review, not a target workflow. No GitHub access or model call is needed for rendering.

## Common problems and recovery

If preview refuses an existing output directory, choose a fresh one. If the target is stale or dirty, inspect and resolve your local work and update the branch. If a branch was created but publication failed, inspect the existing local and remote branch and any PR before continuing; do not blindly retry or force-push.

For run failures, see [Troubleshooting](how-to/troubleshooting.md). For current permissions and verification limits, see [Configuration](reference/configuration.md).

## Other languages and custom checks

A separate reviewed Factory policy and verification profile is required for additional languages, test runners, dependencies or source paths. An issue cannot choose arbitrary check commands.

## What the installer never does

It never executes target code, calls Copilot, changes permissions/secrets/branch rules, applies issue labels, approves or merges. Only `--create-pr` writes to GitHub to propose the installation; ordinary PR checks may run under the target's existing cost policy.

[Back to documentation](README.md).

## Archived sections

Historical sections from the previous guide remain available at the immutable revision below. They may describe obsolete workflows or settings.

<a id="first-exercise-deliberate-paid-planning-then-separately-authorized-paid-build"></a>
- [First exercise: deliberate paid planning, then separately authorized paid build](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/getting-started-new-repository.md#first-exercise-deliberate-paid-planning-then-separately-authorized-paid-build)
