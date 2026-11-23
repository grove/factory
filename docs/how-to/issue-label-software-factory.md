# Launch Software Factory from GitHub issue labels

**New target repository?** Install the SHA-pinned issue/Quality callers first using the [guided onboarding walkthrough](../getting-started-new-repository.md). This guide describes operating the feature *after* deployment.

The ordinary GitHub Software Factory can also accept a **reviewed issue plan**
and one explicit **human-applied label**. This avoids retyping the old
multi-parameter `workflow_dispatch` form, while retaining exact path scope,
independent verification, draft-only publication and human-controlled merging.

The label coordinator is only activated in a repository after its trusted,
SHA-pinned caller has been reviewed and merged. Do not install the caller
without its matching Factory revision. The original manual dispatch remains
available as an operator fallback.

## Once per repository

1. Create two issue labels in **Settings → Issues → Labels**:
   `factory:plan` (no-AI preview) and `factory:run` (paid implementation).
   Their names are exact and case-sensitive.
2. Ensure `sfstack-issue-label.yml` exists on the repository's **default
   branch** and references the exact reviewed Factory SHA for both the
   authorization checkout and the existing reusable Software Factory.
3. Retain the existing `COPILOT_GITHUB_TOKEN` secret for the reusable build
   and permit Actions to create **draft pull requests** in the caller
   repository. Keep strict independent CI/Quality, protected `main` and
   human-only merge. This coordinator changes no branch or repository settings.

## Create a simple issue

A normal Markdown issue is sufficient. For example:

    Title: docs: clarify the portable CLI version check

    ## Problem
    A new adopter cannot tell how to verify the portable CLI version.

    ## Files to change
    - `docs/reference/public-cli.md`

    ## Acceptance criteria
    1. Give an exact offline version command and expected JSON keys.
    2. Clarify that the command does not invoke the agent.

Each allowed path must be exactly **one backticked file** on its own bullet,
within the existing restricted `docs/`, `examples/`, `tests/` or root
`README.md` scope. There may be one to eight files and one to eight concrete
acceptance criteria. No glob, hidden file, workflow or controller change can
be authorized by an issue. The ordinary underlying host enforces the same
exact-file policy again before a build and before publication.

For a defect repair, start the title with `defect:`, include one existing
`examples/` implementation path and one **new**
`tests/test_*.py` regression path. The new regression is required to run
genuine test-only RED and repaired GREEN. You may state `Mode: defect`
explicitly and `Regression file: tests/test_example.py`; otherwise the only
`tests/test_*.py` path is selected for a `defect:` title. Any ambiguity or
missing scope fails closed.

## Two intentional clicks

1. A repository **writer** adds `factory:plan` to an open issue.
   A trusted, default-branch job parses the issue with no model or candidate
   code execution. The only mutation is a bot-authored comment containing a
   human-readable exact plan and machine-readable provenance. Review it.
2. When satisfied, a writer adds `factory:run` once. The label handler
   verifies the actual GitHub event, author permission, same issue title/body,
   original plan, immutable base SHA and one-run history; it writes a durable
   one-shot claim. **Only then** can the pinned reusable Software Factory
   receive its Copilot credential, implement and independently verify the
   change, publish a draft PR, and request exact-head Quality.

If the issue was edited, the plan no longer matches, or `main` advanced,
remove and reapply `factory:plan` to receive a new reviewable preview.
If a run has **already been claimed**, relabeling or rerunning will not
automatically purchase a second build. Inspect its GitHub run and retained
artifacts, reconcile any draft/check/dispatch before a new **separately
authorized** issue and attempt. Do not erase claim comments to bypass recovery.

The coordinator authenticates the original human labeler through the GitHub
Actions run, the original `issues:labeled` event payload, and live repository
writer permission. A bot, triage user, reader, edited issue or stale plan
cannot authorize model work. The GitHub Actions bot's plan and claim comments
are independently re-read; an issue-body instruction is never a credential,
workflow path, command or policy override. Neither the authorizer nor builder
gets GitHub publication rights; only the trusted publisher receives scoped
PR/check/Actions write permissions.

## What it does not do

- `factory:plan` performs **no AI planning**. It is a deterministic, readable
  preview of the exact source/criteria you wrote into the issue. A future
  AI-assisted suggestion tool would need separate cost/authority approval.
- Labels do not authorize a successful Quality result, approval, merge or
  deployment. GitHub may require the maintainer to approve normal PR-triggered
  workflows after an Actions-created draft appears.
- A one-shot claim is intentionally fail-closed; a crash after the claim and
  before model activation is **not** silently retried.
- This is GitHub Actions isolation, not a hostile-code sandbox, cryptographic
  host attestation or a network-outage guarantee.
