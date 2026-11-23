# Architecture and trust boundaries

Factory is a caller-scoped GitHub Actions integration, not a central service. [sfstack](https://github.com/grove/sfstack) provides the portable skills, contracts, workflow recipes and validation policy. Factory invokes the installed public CLI from a hash-pinned wheel. Repository state, credentials and evidence belong to the caller.

## Who does what?

| Boundary | Responsibility |
| --- | --- |
| Human maintainer | Select scope and criteria; explicitly authorize paid planning/build; configure repository rules; review and merge |
| Label authorizer | Authenticate human actor and original event; pin issue and base; create permanent exact-scope claim |
| Read-only planner | Propose a strategy, never edit the candidate or publish comments |
| Builder | Produce a bounded candidate proposal; no PR/check/merge write credential |
| Independent host verifier | Reconstruct exact candidate, execute trusted checks, verify evidence in a separate runner |
| Trusted publisher | Publish only verified draft PRs; request Quality for exact head/base; reconcile prior writes |
| Quality controller | Independently pin PR intent/head/base, verify, review and publish owned check generation |
| Native required gate | Read-only authentication of the current completed Quality workflow and evidence; wait through legitimate pending states |

A successful build means independently verified draft publication, not a successful Quality verdict. A successful Quality assessment does not grant merge authority. The ordinary CI and human review remain mandatory.

## How changes stay bounded

Issue text cannot choose a credential, workflow source, verification command or expanded file policy. Direct mode records the deterministic scope before paid implementation. Planned mode adds validated advisory AI output; only a separate human label authorizes implementation. An earlier planning snapshot cannot be bypassed by direct mode. The claim, issue, base, actor and attempt are checked again before work and publication.

Workflow code comes from reviewed immutable sources. Candidate execution and publication have separate job boundaries. The publisher validates artifacts and reconciles existing refs/checks before mutable writes. The event coordinator fences stale assessments by generation and invalidates outdated clearance without spending Copilot.

The runner is ordinary GitHub Actions isolation, not a hardened sandbox against malicious candidate code or cryptographic attestation. Treat candidate execution as normal CI risk. Forks, arbitrary source changes, production deployment and merge queues are outside the current qualified profile.

See [configuration](../reference/configuration.md), [safe recovery](../how-to/troubleshooting.md), and [historical evidence](../history.md).
