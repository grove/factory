# Historical evidence and acceptance

This page is an index to historical records, not an instruction to repeat the experiments. Negative evidence stays negative even when a later attempt succeeded.

## Validated pilot milestones

| Milestone | Recorded evidence |
| --- | --- |
| Migration and scoped recovery acceptance | [Factory #1](https://github.com/grove/factory/issues/1), [retired live recovery drill](how-to/live-github-recovery.md), [retained evidence](evidence/live-recovery-2026-11-23.md) |
| AI-assisted planning | [Factory #17](https://github.com/grove/factory/issues/17), [sfstack #54](https://github.com/grove/sfstack/issues/54), [planning run](https://github.com/grove/sfstack/actions/runs/45233284312), [merged planned-build PR](https://github.com/grove/sfstack/pull/56) |
| Direct build without separate planning | [sfstack #58](https://github.com/grove/sfstack/issues/58), [build run](https://github.com/grove/sfstack/actions/runs/45253589667), [merged PR](https://github.com/grove/sfstack/pull/59) |
| Required Quality gate reliability | [Factory #16](https://github.com/grove/factory/issues/16), [repair PR](https://github.com/grove/factory/pull/22), [Factory deployment](https://github.com/grove/factory/pull/24), [sfstack deployment](https://github.com/grove/sfstack/pull/60) |
| Read-only run diagnostics | [Factory #23](https://github.com/grove/factory/issues/23), [merged PR](https://github.com/grove/factory/pull/25); full live CLI smoke deferred until normal operator use |

The pilot demonstrates bounded work in the supported Python-unittest profile. The recovery drill exercised real provider-backed response loss after acknowledgement with synthetic data, not a physical network outage or a live paid-agent recovery experiment. Regression tests cover the specific Quality race cases; the deployment runs demonstrated the repaired gate working, not that every race was reproduced live. A result is not a guarantee for arbitrary projects.

## Original technical records

These immutable snapshots preserve the full pre-refactor text, links, original sections and incident reports. Some contain outdated instructions, pins or acceptance status; use the current documentation for operations.

- [Original Software Factory guide (including defect and publication recovery history)](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-software-factory.md)
- [Original Quality Factory guide](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/how-to/run-github.md)
- [Original installation and integration pilots](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/installation.md)
- [Original onboarding guide](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/getting-started-new-repository.md)
- [Original migration record](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/migration.md)
- [Original sfstack GitHub Quality guide](https://github.com/grove/sfstack/blob/bf3c743dcb2b88ef1bafa39720fff0aab35ebb02/docs/how-to/run-github.md)
- [Original sfstack GitHub Software guide](https://github.com/grove/sfstack/blob/bf3c743dcb2b88ef1bafa39720fff0aab35ebb02/docs/how-to/run-software-factory.md)

GitHub artifacts have finite retention; a historical link may expire. Do not replay paid workflows to regenerate an expired artifact. Preserve necessary evidence through your normal retention policy.

[Back to current documentation](README.md).
