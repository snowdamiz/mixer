# Worker controller V2 integration

The controller now rejects a claim whose authority or worker identity changed
while durability was awaited. It also retains every accepted qualified clock
interval and a nondecreasing historical lower bound, so a later rollback cannot
authorize new work. Permanent consumption and stop records survive restart.
Existing schema-1 operations retain their identities and results but enter
quarantine because their lost clock history cannot be reconstructed safely.

The exact reviewed `engine.ts`, `ledger.ts`, `schema.sql` and excluded test Worker
are integrated. The three production files and all 17 compiled production files
(including declarations) match the frozen V2 candidate byte for byte. Production
clock, provider and object-verification support remain unavailable; this change
does not deploy a controller or enable a live build worker.

The independent review passes all 72 frozen producer groups plus 17 new groups
through actual local workerd/SQLite. The three original V1 failures are preserved.
Root verifies 119 review artifacts, 356 archived inputs, 64 archived fixtures and
12 command/output pairs before integrating. See the
[independent review](hosted-worker-controller-v2-independent-review.md) and
[root decision](../verification/hosted-worker-controller-v2-root-review/independent-decision.json).

`npm test` now rebuilds the controller, runs the original 28 groups, seven
unchanged review regressions and 36 focused repair groups, then checks the nine
runtime production imports. The test command creates fresh evidence containing
the exact source and fixture inputs, tool versions, output bytes, exit status,
pipe EOF and owned process-group/scratch results. A new Linux CI job uses the
same command and installs locked development packages with scripts disabled.
No new dependency is added.

The CI-runner review found missing input bindings and a lost receipt on EOF
timeout. These were corrected and the original runner snapshots retained.
Separate finite negative checks also exposed a macOS process-inspection EPERM
case. The runner records such errors, fails, and preserves scratch while cleanup
is unconfirmed. It does not reinterpret a permission error as an empty process
group. If the direct child remains unconfirmed after the finite observation
window, the failed receipt records that fact before the reporting process exits.
All prior successful and incomplete review attempts remain separately scoped.

Root host checks and compiled-output bindings are in
[`verification/hosted-worker-controller-v2-integration/`](../verification/hosted-worker-controller-v2-integration/).
Root accepts the final local integration after verifying 85 independent review
artifacts, 16 current reviewed inputs, all 71 runtime groups and all 17 compiled
production files. The [root acceptance](../verification/hosted-worker-controller-v2-integration/acceptance.json)
binds the final run and [runner review](hosted-worker-controller-ci-review.md).
Linux CI remains pending until the pushed workflow reaches a terminal result.

Pending product work includes the registry and missed-wake recovery, independent
restore authority, qualified live time, authenticated runner ingress, real
provider resource and isolation controls, source/result authorization, signing,
distribution and operational qualification. The interrupted outbound-client
review stays frozen and its installation stays rejected. Local controller
checks do not qualify those items, physical phones, FieldLog dogfood or GA.
