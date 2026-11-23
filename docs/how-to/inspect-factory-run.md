# Inspect a Software Factory run without spending more Copilot usage

This operator command is a **read-only diagnostic**, not a new workflow,
approval, Quality gate, or authorization to retry. It reports the selected
historical attempt and the current observed Quality generation; it does not
execute candidate code or alter GitHub state.

## Run it from a reviewed Factory checkout

Use a GitHub token with only the repository metadata, Actions, issues,
pull requests, checks and contents **read** permissions needed for the
selected repository. Set GH_TOKEN in your environment through your normal
credential mechanism. Do not put a token on the command line or paste it
into an issue. The tool uses repository-relative GitHub GETs only; it
does not need the Copilot credential.

    python -m integrations.github.run_summary \
      --repository grove/sfstack --run 45253589667

If you already have a suitably scoped authenticated GitHub CLI credential, use a one-command environment assignment from the Factory checkout (do not print the token):

```sh
GH_TOKEN="$(gh auth token)" python -m integrations.github.run_summary \
  --repository grove/sfstack --run 45253589667
```

The credential must also allow reads of workflow definitions. A connector that exposes only run metadata may not support the command's identity checks. Do not weaken those checks to accommodate a restricted connector.

The command emits one JSON object. It recognizes the label workflow and
its actual run ID, attempt, repository and caller base SHA. It uses
GitHub-owned job metadata, bot-authored claim/plan records, and the exact
factory branch naming convention to identify the linked PR. It reports:

- Planning-only, planned or direct mode (unknown if the claim is missing,
  conflicting or not authenticated). A planned build links the separate
  planning run and its measured jobs.
- All jobs, explicit stage outcomes, failure stages, and artifact links.
  Pending, skipped, failed, successful, unknown and superseded states are
  distinct; a skipped planner is expected in direct mode.
- The linked PR's current head/base, draft/merge status, and retained
  build evidence. Artifact presence or a PR body alone is not test success.
- The selected independent Quality generation, its exact workflow and
  attempt, measured job states and retained evidence. A stale/superseded
  check is not reported as success; expired or mismatched evidence cannot
  establish a positive Quality assessment.
- A safe recovery hint. A successful historical assessment is not
  permission to merge a current PR. Check ordinary CI and the real native
  required gate separately. Always review the original issue and PR.

A rejected identity, unsupported workflow or ambiguous PR exits nonzero
rather than inventing a report. A valid diagnostic with negative or
pending stages can exit zero: the exit code is **not** a Quality verdict.
This command handles the first attempt of issue-label workflows. It
deliberately refuses retries of the paid label event; reconcile the original
claim and its effects instead.

## Inspect published usage

GitHub's Actions metadata identifies the retained gh-aw usage artifact.
To inspect its reported agent totals, download the intact usage ZIP from
the artifact link shown by the command, then provide the local archive:

    python -m integrations.github.run_summary \
      --repository grove/sfstack --run 45253589667 \
      --usage-zip direct-run-usage.zip \
      --quality-usage-zip quality-usage.zip

Both archives are optional. Download the original ZIP via GitHub; an
extracted or repacked archive will not have the same digest. The tool
checks its bytes against GitHub's artifact SHA-256 and checks the embedded
repository, run, attempt, base and immutable agent workflow identity
before reading the published agent totals. It never extracts or executes
archive contents.

Input/output/cache token counts are in tokens. Reported AI credits are
in AI credits. These are **agent totals only**, not an aggregate of
planning, threat detection, Quality and all billable activity. The separate
Quality archive can provide its own agent totals. Neither is an invoice or
a price estimate. The simple read-only planner does not currently publish
this gh-aw usage archive, so its usage remains unknown.

Missing, expired, ambiguous, malformed or unverified usage remains
unknown, not zero. The summary never invents a price. Actual account
billing should be checked separately with the billing provider.

## Existing live evidence

Use the previously completed pilot runs without triggering new work:

- [Planning-only #45233284312](https://github.com/grove/sfstack/actions/runs/45233284312).
- [Planned build #45233942585](https://github.com/grove/sfstack/actions/runs/45233942585)
  and [PR #56](https://github.com/grove/sfstack/pull/56).
- [Direct build #45253589667](https://github.com/grove/sfstack/actions/runs/45253589667),
  [PR #59](https://github.com/grove/sfstack/pull/59),
  [usage ZIP](https://github.com/grove/sfstack/actions/runs/45253589667/artifacts/14857545938),
  and [independent Quality #45254935613](https://github.com/grove/sfstack/actions/runs/45254935613).

Artifact retention is finite. Preserve any necessary audit records through
your normal evidence policy rather than retrying a paid run to regenerate
them. The tool does not alter a claim, label, check, PR or workflow.
