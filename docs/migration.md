# Migration from sfstack

## Repository boundary

| Stays in `grove/sfstack` | Moves to `grove/factory` |
| --- | --- |
| Canonical skills, schemas, protocol, recipes, portable adapters, and local reference tools | GitHub Software and Quality controllers, event routing, Actions and Agentic Workflows |
| Versioned public contract CLI and distribution build | Strict client for the installed public CLI and the exact dependency lock |
| Portable policy, artifact/evidence validation, planning, and quality consolidation | GitHub admission, credentials, candidate isolation, verification, draft publication, check ownership, and recovery |
| Core tests and local quality regression | GitHub, software, defect, transport, and publication regressions and operational guides |

The extraction starts from
[`7a4b56b4d1e34db124743d39fd694f2cd88463ea`](https://github.com/grove/sfstack/commit/7a4b56b4d1e34db124743d39fd694f2cd88463ea).
The host consumes CLI interface 1.1 through a hash-pinned 1.1.0 wheel. The build
provenance in `sfstack.lock.json` identifies its exact source revision. This
bundled distribution is not a claim of a PyPI or GitHub release publication.

The existing GitHub workflow, artifact, and check names are preserved. Those
names participate in authenticated run matching and durable replay; renaming
them is unnecessary for repository separation.

## Acceptance carried into the destination

The owner authorized extraction before the remaining live recovery exercise.
This explicitly supersedes the old sequencing restriction in
[sfstack #29](https://github.com/grove/sfstack/issues/29) and
[sfstack #34](https://github.com/grove/sfstack/issues/34). It does not mark an
unexecuted test as passing.

The following destination acceptance remains open until its actual evidence is
recorded in [factory #1](https://github.com/grove/factory/issues/1):

- Exercise the migrated controller with one bounded ordinary change and one
  genuine defect RED/GREEN path through an automatic draft and exact-head
  Quality assessment. Reuse earlier evidence for unchanged primitives; do not
  repeat paid agent work merely to test a publisher response loss.
- Inject a lost or ambiguous Quality dispatch response and reconcile both
  in-flight and completed authenticated identities. Retain evidence that no
  duplicate assessment owner, invented success, or automatic retry occurred.
- Exercise a deliberately interrupted publication against the actual migrated
  publisher with dummy data, proving exact run/attempt/base/digest/candidate
  reconciliation. A manually created Git branch is not this test.
- Verify **or document** the destination's required `sfstack quality` source,
  strict up-to-date checks, ordinary CI, and human review requirements. Enforcing
  rules on the temporary sfstack pilot is not a prerequisite for extraction.

## Historical evidence and its limits

The ordinary-change run
[`44632044871`](https://github.com/grove/sfstack/actions/runs/44632044871)
and defect run
[`44771993268`](https://github.com/grove/sfstack/actions/runs/44771993268)
remain evidence of the original pilot's successful paths. Run
[`44746100752`](https://github.com/grove/sfstack/actions/runs/44746100752)
verified the repair but failed during publication; its later recovery does not
make that original invocation successful.

Natural superseded Quality runs show stale-input rejection. The original
synthetic lost-branch-response probe shows Git object/ref readback only. Neither
establishes a live fault-injected dispatch recovery by this migrated controller.
The detailed retained history remains in the
[software guide](how-to/run-software-factory.md) and the source issues.

## Cutover and rollback

Review the destination import and source extraction together. Land the factory
import before removing the old sfstack host so the implementation and operator
guides remain available throughout cutover. The portable CLI addition can be
reviewed independently; the bundled host dependency is already tied to its
immutable source commit.

Existing sfstack runs, checks, drafts, and recovery refs remain in sfstack.
There is no attempt to transplant authenticated run IDs across repositories.
Any operator recovery for an old run uses its original repository and evidence.

If cutover must be reversed, revert the source extraction using normal review.
Do not replay destination run identities against the old repository or overwrite
human changes. Neither migration PR merges itself, changes branch rules,
copies secrets, or starts a paid model run.
