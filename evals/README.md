# Executable host regressions

Install the pinned contract CLI with `python tools/bootstrap_contracts.py`.
Run each command with a new output directory:

```sh
python evals/run_github_regression.py --output dist/github-regression
python evals/run_software_regression.py --output dist/software-regression
python evals/run_defect_regression.py --output dist/defect-regression
```

## Execute the GitHub bridge failure and repair path

The GitHub regression creates a disposable repository with a known inventory
boundary defect, executes six real checks, then assesses a separately committed
repair. A deliberately positive fixture review cannot override failing
verification. The repaired candidate passes the automated quality policy;
neither result authorizes mutation or represents human approval.

## Execute the bounded Software Factory handoff

The Software regression exercises issue preparation, canonical build-skill
rendering, bounded reconstruction, Git identity, and independent verification.
An unfixed proposal fails; a separately fixed proposal passes the same checks.
The issue and agent responses are declared fixtures. Git commits, subprocess
results, digests, and host decisions are real.

## Execute the defect RED/GREEN path

The defect regression requires a healthy baseline, a new regression that fails
with a real assertion against the original code, and a repair that passes both
the regression and the full declared suite. Negative cases remain blocked.

The corresponding unittest suite also covers stale identity, tampering,
artifact transport, failed or empty checks, lost publication responses,
at-most-once dispatch, and conflicting human state. Run it with:

```sh
python -m unittest discover -s tests -v
```

These regressions use the installed public CLI in a checkout with no sfstack
source tree. They require no GitHub API or model calls. They establish
deterministic host behavior, not live credential setup, Copilot effectiveness,
production isolation, or completion of the remaining
[destination live acceptance](../docs/migration.md).

The shared [inventory fixture](cases/inventory-boundary/task.md) is copied from
the extraction baseline so these host regressions remain independent of the
portable library's checkout.
