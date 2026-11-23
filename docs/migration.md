# Migration from sfstack

The GitHub host is now maintained in Factory. This is a completed repository migration, not an installation checklist. See [current documentation](README.md) for everyday operation.

## Repository boundary

| sfstack | Factory |
| --- | --- |
| Portable skills, schemas, protocol, recipes, adapters and local tools | GitHub events, admission, credentials, candidate execution, draft publication and check ownership |
| Versioned public contract CLI and distribution | Installed hash-pinned CLI client and dependency lock |
| Portable policy and evidence validation | GitHub-specific enforcement, operational regressions and recovery |

The extraction began at [sfstack commit 7a4b56b](https://github.com/grove/sfstack/commit/7a4b56b4d1e34db124743d39fd694f2cd88463ea). Existing GitHub workflow, artifact and check names were preserved because they participate in authenticated identity and recovery. The host consumes the locked distribution described by `sfstack.lock.json`.

## Acceptance carried into the destination

[Factory issue #1](https://github.com/grove/factory/issues/1) is closed with the scoped live recovery evidence. Planned and direct label-based builds, the native Quality race repair and operational summary subsequently reached reviewed acceptance. See the [milestone and evidence index](history.md) for exact records and limitations, including deferred live CLI smoke testing.

## Historical evidence and its limits

The original migration record, prior negative runs and incident evidence remain at [the immutable pre-refactor revision](https://github.com/grove/factory/blob/e7045bc934f504bebf1a6d06b0871fbcce1165b5/docs/migration.md). The [retired recovery drill](how-to/live-github-recovery.md) documents the provider-backed post-acknowledgement response-loss experiment. It does not establish physical-outage or arbitrary live paid-agent recovery.

## Cutover and rollback

Historical issues, runs, checks, drafts and credentials stay in their original repository. Do not transplant run identities or replay paid work. Any rollback or pin change requires reviewed PRs, current checks and human approval.

[Back to documentation](README.md).
