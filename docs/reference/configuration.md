# Configuration and supported profile

This reference describes the current caller-scoped pilot. For setup, see [Install Factory](../getting-started-new-repository.md).

## Supported work

| Setting | Supported value |
| --- | --- |
| Verification | Python 3.13, `python -m unittest discover -s tests -v`, substantive passing tests without installing project-specific dependencies |
| File scope | 1–8 exact UTF-8 files in `docs/`, `examples/`, `tests/`, or root `README.md`; no globs, hidden paths, symlinks, submodules, executable files, deletion or rename |
| Size | At most 32 KiB per original or replacement file, 64 KiB total replacement contents |
| Acceptance | 1–8 concrete criteria, at most 2,000 characters each |
| Defect mode | Existing permitted implementation file in `examples/` and one new `tests/test_*.py` regression; genuine baseline/RED/GREEN/full-suite proof |
| PR eligibility | Open, same-repository PR targeting default branch; no fork PR or merge-queue candidate |
| Authorization | Human with repository write or higher permission; exact labels and one-shot claim |
| Merge | Current required CI, native Quality and independent human review; Factory never approves, merges or deploys |

The pinned host controls verification commands and file policy. To support another language, dependency installation or source layout, review and qualify a separate profile rather than overriding it through issue text.

## GitHub settings

- Repository Actions enabled. Set `COPILOT_GITHUB_TOKEN` in the caller repository's Actions secrets using the [Copilot engine setup](https://github.github.com/gh-aw/engines/copilot/). Standard `GITHUB_TOKEN` handles scoped GitHub API operations.
- Keep default Actions permissions read-only where permitted. GitHub's repository-wide **Allow GitHub Actions to create and approve pull requests** toggle is needed for draft creation; review the security impact. Factory's publisher never approves PRs.
- Keep the normal PR and default-branch CI. Require the exact **sfstack quality** check with GitHub Actions as expected source, up-to-date branches, and human review. The native read-only witness authenticates the independently dispatched result; it is not an alternative assessment.
- Create the exact case-sensitive labels `factory:plan` and `factory:run`.

## Installed files and source pins

The [installer](../../tools/onboard_repository.py) renders seven files. Each source checkout and reusable workflow stays pinned to an immutable 40-character reviewed SHA. Do not replace reviewed pins with tags, `@main` or an issue-supplied revision.

| Caller or template | Responsibility |
| --- | --- |
| `sfstack-issue-label.yml` | Human label authorization, optional plan, permanent build claim |
| `sfstack-software.yml` | Explicit manual build fallback |
| `sfstack-quality.yml` | Independent Quality assessment |
| `sfstack-pr-signal.yml` | Permissionless signal for eligible PR activity |
| `sfstack-quality-events.yml` | Dispatch/reconcile, invalidate old-base clearance without model calls |
| `sfstack-quality-required.yml` | Native read-only required check |
| `factory-work-item.md` | Issue template |

See [reviewed templates](../../tools/onboarding_templates) for the actual pins and workflow definitions. Quality and its event coordinator share a source pin; the label coordinator and its reusable Software workflow share the selected reviewed Factory revision. Separate manual Software and native Quality pins are intentional. Review upgrades as normal PRs.

## Cost and retention

Planning, implementation and independent review consume Copilot usage when they run. Eligible PR events can request Quality automatically; base-push invalidation and the native witness do not call AI. The installer preview and [run summary](../how-to/inspect-factory-run.md) are read-only/no AI. GitHub Actions compute and account billing are separate. Artifact names include attempts where applicable; core evidence is typically retained for 14 days, other artifacts may differ. Check the actual expiry and preserve required audit records.

[Architecture and authority](../explanation/trust-boundaries.md) explains why these restrictions exist.
