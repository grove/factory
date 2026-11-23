# Launch Software Factory from GitHub issue labels

**New target repository?** Install the SHA-pinned issue/Quality callers first using the [guided onboarding walkthrough](../getting-started-new-repository.md). This guide describes operating the feature *after* deployment.

The ordinary GitHub Software Factory accepts an explicit **human-applied**
`factory:run` label against a bounded issue. An optional `factory:plan` label
first purchases a Copilot-generated strategy for human review. Both routes
retain exact path scope, independent verification, draft-only publication and
human-controlled merging instead of the old multi-parameter
`workflow_dispatch` form.

The label coordinator is only activated in a repository after its trusted,
SHA-pinned caller has been reviewed and merged. Do not install the caller
without its matching Factory revision. The original manual dispatch remains
available as an operator fallback.

## Once per repository

1. Create two issue labels in **Settings → Issues → Labels**:
   `factory:plan` (**paid** Copilot-assisted strategy) and `factory:run` (**paid** implementation).
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

## Choose one of two human-authorized paths

- **Direct (one paid build):** On a bounded open issue that has **not**
  requested `factory:plan`, a repository writer adds `factory:run` once.
  The trusted controller authenticates the label event and writer, parses the
  issue into an exact file/criteria/base snapshot, and publishes a permanent
  bot-authored **direct-mode run claim** before any paid builder starts.
  This claim is the deterministic scope record; there is **no separate
  Copilot planning job or AI-plan approval**. The human must have already
  decided that the issue's own instructions justify implementation.
- **AI-planned (two paid decisions):** First add `factory:plan`
  as a writer to purchase one read-only Copilot implementation proposal.
  The controller posts a deterministic scope snapshot, and a separate paid
  model job proposes per-file actions, verification, risks and questions.
  The independent trusted publisher validates the JSON and posts the
  **second AI-assisted plan comment**. Review that bot-authenticated advice;
  only then add `factory:run` once, which purchases a separate
  implementation attempt bound to the validated plan digest.

Both paths retain a durable one-shot claim, the same restricted file allowlist
and original acceptance criteria, actual host verification, draft-only PR
publication, independent Quality and human-only merge. The reusable Software
host reauthenticates the claim and rejects altered scope, issue text, base SHA,
actor or run attempt. Direct mode carries **no** fabricated AI plan or digest;
planned mode **must** include the original validated advice.

If `factory:plan` has ever produced a trusted scope snapshot for
the issue, even if its paid model or publisher failed, `factory:run`
cannot fall back to direct mode. A still-present `factory:plan` label
also blocks direct mode until the planning state is reconciled. If the
issue or default branch changes after planning, request and review a fresh
paid plan for the new snapshot; an unchanged failed attempt cannot simply
be billed again. If a build has already been claimed, relabeling or rerunning
will not purchase another one: inspect its run and retained artifacts and
reconcile any pending writes before a separately authorized follow-up issue.
Do not erase bot claim comments to bypass recovery.

The coordinator authenticates the original human labeler through the GitHub
Actions run, the original `issues:labeled` event payload, and live repository
writer permission. A bot, triage user, reader, edited issue or stale plan
cannot authorize model work. The GitHub Actions bot's claim and, when requested, plan comments
are independently re-read; an issue-body instruction is never a credential,
workflow path, command or policy override. Neither the authorizer nor builder
gets GitHub publication rights; only the trusted publisher receives scoped
PR/check/Actions write permissions.

## What it does not do

- `factory:plan` is **optional AI-assisted planning** and consumes
  Copilot usage. Its first comment is only the deterministic scope snapshot;
  its second comment must contain validated advisory implementation steps.
  A model failure never authorizes a build or direct-mode fallback.
- `factory:run` separately consumes Copilot usage for implementation.
  The trusted Software host verifies the exact direct-mode one-shot claim
  **or** the existing planned-mode digest and approved advice. Neither mode
  widens allowed files or acceptance criteria, and both retain independent
  verification and human review.
- Labels do not authorize a successful Quality result, approval, merge or
  deployment. GitHub may require the maintainer to approve normal PR-triggered
  workflows after an Actions-created draft appears.
- A one-shot claim is intentionally fail-closed; a crash after the claim and
  before model activation is **not** silently retried.
- This is GitHub Actions isolation, not a hostile-code sandbox, cryptographic
  host attestation or a network-outage guarantee.
