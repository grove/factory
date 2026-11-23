# Live GitHub post-write response-loss acceptance (no AI)

Related: Factory issue #9 and Factory acceptance issue #1.

This is deliberately lost client response after an accepted real GitHub HTTP POST,
not a physical network outage. The production migrated SoftwareHost publisher
runs against genuine GitHub objects with a known synthetic submission and actual
independent host tests. The candidate is a harmless one-file documentation
canary, not a paid agent implementation.

The Quality dispatcher is temporarily directed at the separate inert workflow
sfstack-recovery-noai.yml. It tests the real Actions transport/readback without
spending Copilot. The quality check remains nonpassing. The dummy draft is
closed without merging; its immutable candidate branch is retained for audit.

## Execute, after review and merge of this probe workflow

Use a maintainer-authenticated GitHub CLI account:

    gh workflow run sfstack-live-recovery.yml -R grove/factory --ref main -f issue-number=9
    gh run list -R grove/factory --workflow sfstack-live-recovery.yml --limit 3

Inspect artifacts recovery-fixture-1, sfstack-software-result-1,
and live-recovery-proof-1 before updating Factory #1. The test must prove
exactly one branch, draft PR, Quality check reservation, and no-AI Actions
dispatch POST; for each the HTTP reply is discarded after real GitHub accepts
the write. A replay using the actual migrated publisher must reconcile
the immutable evidence and current remote identities without a second POST.
The no-AI run must be observed queued/in flight and then completed.
No synthetic check may pass. All conflicting or altered human state must
fail closed. Failure is evidence to investigate, not permission to retry blindly.

No branch protection, secrets, permissions configuration or merge rules change.
Only the explicit maintainer-triggered, default-branch trusted job has
the narrowly necessary GitHub write scopes, serialized with the existing
Quality publisher lock. The verifier job has read-only permissions.

LIMITATION: A successful test proves live GitHub post-ACK client-response
suppression and provider readback, not an actual network partition, an
agent review, or successful production Quality dispatch under packet loss.
Do not close remaining acceptance criteria without inspecting exact evidence.
