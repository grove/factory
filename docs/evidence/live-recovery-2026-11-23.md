# Audited post-ACK live recovery — 23 November 2026

This is a historical, **provider-backed** acceptance record from
[Factory issue #9](https://github.com/grove/factory/issues/9) and
[Factory acceptance #1](https://github.com/grove/factory/issues/1).
The one-time privileged workflows are retired in the accompanying cleanup PR.

## Verified run and outcomes

- Successful [workflow #45144342739](https://github.com/grove/factory/actions/runs/45144342739),
  attempt 1, completed success for both independent verification and publisher.
  It ran on protected `grove/factory/main` at
  `32b58d7af36b03f9a735e5f86586a68f6f920e0f`.
- Synthetic candidate `414dce97f93721d6f789adbf88dfc0ce121cb848`,
  exact branch `sfstack/issue-9-45144342739-1`, one new
  `docs/live-recovery-probe.md` file. No agent-generated candidate was used.
- All six retained SHA-256 gate evidence digests were independently recomputed
  and match both the genuine verification artifact and the recorded live proof.
- Four accepted GitHub POSTs had replies deliberately discarded **after ACK**,
  one each: `git/refs`, `pulls`, `check-runs`,
  `actions/workflows/sfstack-recovery-noai.yml/dispatches`.
  The production SoftwareHost publisher reconciled the exact
  branch / draft PR / check / dispatch and did not repeat mutable POSTs.
- [Draft PR #11](https://github.com/grove/factory/pull/11) was closed
  **unmerged**. Owned check `137591493355` was conclusively
  `completed/failure`. No synthetic passing Quality check or automatic
  merge was authorized.
- [Inert Actions run #45144866988](https://github.com/grove/factory/actions/runs/45144866988)
  was authenticated both queued/in-progress and completed, request
  `45144342739-1`, attempt 1, without a duplicate dispatch.
- Prior [run #45139424060](https://github.com/grove/factory/actions/runs/45139424060)
  **failed closed**, because the repository had disabled Actions-based
  pull-request creation. Its exact orphan canary branch
  `sfstack/issue-9-45139424060-1` was retained for audit and is
  not to be blindly re-published.

## Durable evidence and SHA-256 integrity

A snapshot of four original GitHub Actions ZIP artifacts was downloaded before
their 14-day retention expired. The original ZIPs are preserved
**byte-for-byte** in an offline bundle; the full original proof and its digest
index are also represented in this repository as
[proof JSON](live-recovery-2026-11-23-proof.json) and
[archive manifest](live-recovery-2026-11-23-manifest.json).

The combined offline ZIP `factory-live-recovery-evidence-2026-11-23.zip`
has SHA-256:

```
d3a66e308c3308e1fa1b52649ec5ef6b94b0957f5b5041f5053ecb8b5d45b618
```

| Original GitHub artifact | ID | Original ZIP SHA-256 |
|---|---:|---|
| [Failed proof #45139424060](https://github.com/grove/factory/actions/runs/45139424060/artifacts/14802465086) | 14802465086 | `6a32cf8a1f49778d09f8b7be72afd47b28851148545f2693abbee0fc1c4ba50c` |
| [Successful fixture](https://github.com/grove/factory/actions/runs/45144342739/artifacts/14803562582) | 14803562582 | `ba098de0dba3762231c1d3a8ec690add7af81c57df6a83d2cf1a6e33748ff12c` |
| [Successful host verification](https://github.com/grove/factory/actions/runs/45144342739/artifacts/14803677399) | 14803677399 | `16a1fe14832fe47cdaf6139f253ea942d53468aeb796eba3f98584b6d8126436` |
| [Successful live proof](https://github.com/grove/factory/actions/runs/45144342739/artifacts/14804205210) | 14804205210 | `a647714ed69adb5921643e4c7bed9743b675a9d37bcb2bdc0c0b011db9cb0212` |

This evidence proves **post-ACK client response suppression against real
GitHub writes**, not a physical network partition, runner crash or a real
paid Quality controller recovering under packet loss. The earlier 27
in-memory negative cases are separate evidence.

## Retirement and least privilege

Remove only the two acceptance-specific Actions workflows. Preserve production
Quality, Software Factory, check-name protection, pinned controller references
and human-only merging. Keep the deterministic no-AI regression tests and
historical test code for review. The disposable test branches may be deleted
by the maintainer after independently archiving their exact commit objects;
no branch deletion is performed by the cleanup PR.

The repository-wide Actions permission that also allows pull-request approvals
was temporarily enabled for the drill; **its restoration must be checked
separately** by an administrator. This commit does not modify that setting.
