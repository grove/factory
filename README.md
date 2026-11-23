# factory

**GitHub Software Factory and Quality Factory, powered by sfstack contracts.**

Software Factory turns one explicitly scoped issue into a verified draft pull
request. Quality Factory independently assesses an existing pull request and
publishes `sfstack quality` on its exact head. Both retain their evidence and
leave approval and merge to a human.

This repository owns GitHub events, Actions jobs, admission, credentials,
candidate execution, durable publication, and recovery. The portable skill
library, schemas, recipes, and policy engine remain in
[`grove/sfstack`](https://github.com/grove/sfstack). The host invokes the installed,
versioned `sfstack-contract` CLI; it does not import sfstack's private modules.

## Start here

- **[Getting started: install in another GitHub repository](docs/getting-started-new-repository.md)** — guided, SHA-pinned caller installation, offline no-AI installer preview, explicit target PR, setup checklist and safety limits.
- [Install and validate the host](docs/installation.md), including manual cross-repository Quality reuse.
- [Assess an existing pull request](docs/how-to/run-github.md).
- [Build a bounded change or reproduce and repair a defect](docs/how-to/run-software-factory.md).
- [Review the migration boundary and remaining live acceptance](docs/migration.md).
- [Run the deterministic host regressions](evals/README.md).

The host operates on the **calling** repository's own issues, pull requests,
checks and credentials. It can be installed locally or called through pinned
reusable workflows; it is not a central cross-repository service. Its existing limits on
editable paths, candidate identity, credentials, and human approval remain in
effect.

## Validate locally

Use Python 3.11 or newer in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python tools/bootstrap_contracts.py
python -m unittest discover -s tests -v
python evals/run_github_regression.py --output dist/github-regression
python evals/run_software_regression.py --output dist/software-regression
python evals/run_defect_regression.py --output dist/defect-regression
```

Each regression output directory must be new. These commands run deterministic
fixtures and real subprocess checks; they need neither GitHub credentials nor a
model subscription. Fixture reviews do not establish human approval or live
agent effectiveness.

`sfstack.lock.json` records the exact core distribution, SHA-256, and source
revision. The wheel in `vendor/` is an immutable build of that source; dependency
installation verifies the lock before use. Its bundled skills and schemas come
from sfstack's canonical package build.

## Execution boundaries

| Component | Responsibility |
| --- | --- |
| Software controller | Admit a selected issue, pin scope and base, reconstruct a bounded proposal, verify independently, and publish only a draft. |
| Quality controller | Pin PR intent and head, run declared checks, obtain a bounded review, consolidate evidence, and publish an exact-head check. |
| Event coordinator | Own assessment generations, reconcile interrupted runs, and invalidate stale clearance. |
| Installed sfstack CLI | Resolve canonical skills, validate records and evidence, plan workflows, consolidate quality, and evaluate policy. |
| Repository operator | Configure credentials and merge rules, review evidence, and decide whether to merge. |

The workflows use ordinary GitHub Actions runners. They do not claim a hardened
sandbox for hostile candidate code. Agents never receive the publisher's write
credential, and a successful check is not a merge authorization.

## Provenance

Extracted from `grove/sfstack` at
[`7a4b56b4d1e34db124743d39fd694f2cd88463ea`](https://github.com/grove/sfstack/commit/7a4b56b4d1e34db124743d39fd694f2cd88463ea).
The historical workflow names, artifact names, and `sfstack quality` check name
are retained so their ownership and recovery identities remain stable.
Historical run evidence remains linked to its original repository; it is not
represented as a new factory acceptance run.

## License

[Apache License 2.0](LICENSE).
