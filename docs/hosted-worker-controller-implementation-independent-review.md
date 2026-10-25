# Independent review of the per-operation Worker/SQLite controller

Decision: **reject this frozen source for development-slice acceptance until two
correctness findings are repaired and independently replayed**. The unchanged
producer suite passes all 28 groups, but three added workerd/SQLite regression
cases fail. Production enablement and every operational/GA gate remain pending.

Reviewed on 2026-10-25 UTC (2026-10-24 America/New_York). This lane owns only this
report and `verification/hosted-worker-controller-implementation-independent-review/`.
It changed no producer source/evidence, shared status, Git, cloud/provider,
credentials, native runtime, phones, customer data or deployed service. It neither
read/imported/executed the separate catalog-inspector/authority-driver lane nor
resumed the interrupted outbound transport independent review. The original
transport vectors were used only as data by the frozen controller suite.

## Findings

**[P1] Final claim grant ignores a superseding authority watermark.** In
`hosted-worker-controller/src/engine.ts:219–223`, consumption commits and durability
is awaited, then the method checks current desired state, quarantine and time.
It never compares the consumed epoch/revision/owner/expiry with the current guard.
The frozen contract requires an older callback not to grant a claim after newer
authority commits, and requires the final authority recheck.

Both independent cases use the real DO runtime, actual SQLite and the existing
verification-only `after_claim_commit` barrier. An ensure reaches inert; a claim
consumes under `(1,0,owner-a)` and pauses. A valid query commits either
`(2,0,successor)` or `(1,1,owner-a)`. Releasing the paused callback returns
`{granted:true,claimId:...}` in both cases. A query has therefore advanced
authority while an older claim callback still issues its grant. The matching
stop-at-this-boundary control denies the grant and preserves the consumed claim
across runtime restart, so this is specifically a missing watermark fence rather
than failure to observe concurrent DO writes.

Bind the prospective grant to the exact authority captured when consumption
commits, then compare it atomically with the current row immediately before
returning a grant. Also retain the exact claim/resource/instance/boot identity and
the final qualified-time check. A denied or lost grant must leave consumption
permanent; do not repair this by resetting the claim or transferring a previous
grant to a successor. Re-run both failing cases and the stop control against a
newly sealed producer tree. The race and assertion evidence are retained in
`regression-report.json`; the first two-failure run and its exact fixture source
are separately retained as `regression-attempt-1-report.json` and
`regressions-attempt-1.mjs`.

**[P1] Qualified effect/claim samples do not advance durable clock history.**
`engine.ts:14–18` compares a sample only with `row.clock_lower`; successful
samples do not update the stored interval. Those fields are updated only by
`command()`. Consequently, later qualified samples used during effect
reconciliation, claims and report acceptance can be forgotten before rollback
detection. The frozen contract requires a persisted last accepted interval and
quarantine on excessive backward movement.

The independent test creates the operation at `1900000000000000` microseconds,
then runs actual reconciliation at `1950000000000000`. The row still stores
`clock_lower=1899999999999999`. The synthetic clock subsequently moves backward
to `1920000000000000`, far outside the one-microsecond synthetic error interval.
A fresh claim is granted and `quarantined` remains zero. The rollback is hidden
because it remains above the obsolete request-time watermark.

Persist accepted qualified intervals for every authority-sensitive sample under
the same SQLite transaction, preserving rollback evidence across process death.
Define the comparison for overlapping error intervals without clamping time to a
previous sample. Preserve stale-request zero-write behavior and the ability to
enforce a previously committed stop without a qualified clock. Replay the added
clock case plus the original expiry, rollback, final-check and stop cases.

## Verified scope

Before executing candidate tests, the independent verifier matched the supplied
producer receipt SHA-256
`fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a`,
source-tree digest
`6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95`
and archive SHA-256
`d6894fdae991b51485e7bec04a86027f87d84261ddc527e292e072c8b8dd55b7`.
It independently hashed all 60 source/compiled/contract input records, 1,180
installed dependency file records, 29 Jason file records, 54 producer artifacts
and four runtime inputs. Archive member names and bytes match the source manifest.
All 58 locked dependency entries have exact matching versions, licenses,
integrities, resolved package URLs and nonempty purposes in the owned inventory;
all are development-only. No dependency was installed or globally changed and no
dependency install script ran. The already sealed dependency bytes were copied
into an owned scratch tree and verified again before disposal.

Observed tools are Node 22.23.3, npm 10.9.9, TypeScript 5.9.3, Miniflare
4.20260730.0, workerd 1.20260730.1 and workers-types 5.20260730.1, with runtime
compatibility date 2026-07-30 on macOS 27.0.1 arm64. The copied source rebuilds
successfully; all production compiled/data outputs match the frozen bytes.
Original artifact bytes, including historical failed logs, were only read.

| Independent check | Observed result |
| --- | --- |
| Frozen build and full test replay | Build exit 0; 28 reported groups pass, including unchanged 20 scenarios plus five fixtures, 36 original vectors and 24 additional Jason/Unicode vectors. |
| Runtime and persistence | Actual workerd SQLite DO transactions, rollback, 32 concurrent ensures, 16 claims, automatic alarm without HTTP, four identified owned-process SIGKILL/restart boundaries and permanent stop/claim state replay pass. These are local runtime and modeled-provider results. |
| Added authority/clock regressions | Seven groups: four pass; higher-epoch/new-owner grant, higher-revision grant and forgotten later clock interval fail with assertions. Exit 1 is retained as the review result. |
| Added noncooperative cancellation fixture | Pass. After the two-second timeout, a provider promise deliberately ignores abort. New stop/reconcile calls retain one occupied provider slot and no terminal result until the owned promise settles. Then stop/drain reaches permanent stopped without another launch. |
| Independent production closure | TypeScript AST traversal reaches nine production compiled/data files, with only `cloudflare:workers` external; no test schema, fixture selectors, test-report environment selector, dynamic import, require or eval. This is static module-closure evidence, not OTA authorization. |
| Cleanup | All replay/regression Miniflare instances dispose and all recorded owned storage paths disappear. No process remains using the exact owned scratch workerd binary. Owned scratch is removed; other projects are untouched. |

The added noncooperative fixture changes only a copy of the excluded test provider:
its held launch ignores `AbortSignal` until an explicit local release. Product
`src/` and production output bytes remain identical. The exact one-line fixture
transformation, input/output hashes and complete fixture are retained separately.
The claim and clock failures were obtained before that fixture transformation,
using the unchanged producer test bundle.

Source inspection and executable evidence support exact canonical decimal TEXT
storage with BigInt arithmetic, original numeric-token fence hashing, Unicode
preservation, current nonce/guard echoes, authentication before body/DO routing,
immutable binding checks, separate issued-effect guards, stable launch identities,
permanent consumption/tombstones, bounded 32-slot audit, definitive drain facts,
and retained occupancy after ambiguous provider work. Report validation requires
the exact claim/resource/binding and a verifier result before pending completion;
terminal completion waits for descendants and launch tickets to drain. The
production clock/provider/object verifier remain explicitly unavailable and the
production entry has no runner or test-control ingress. These supported findings
do not override the two failed authority/clock boundaries above.

## Handoff and limits

Root should select a bounded repair of the two findings, preserve this rejected
packet, seal the replacement tree and repeat independent source/runtime review.
No repair was performed by this lane. `receipt.json` binds this report, all
commands, fixture sources, outputs, failures, archives and cleanup observations.
`README.md` gives the exact replay sequence. The final receipt status is
`rejected-two-correctness-findings`, not source accepted or complete controller.

Actual Cloudflare ingress/TLS/header/framing/EOF, measured production clock,
Linux/macOS provider images and resource/egress/isolation limits, authenticated
trusted one-shot runner and descendant disposal, source/private-R2/object/result
authorization, registry/scheduler integration, missed wake/exhausted alarm retry
recovery, independent nonrollbackable restore/namespace authority, whole-domain
limits, Neon/Oban zero-traffic operation, operational latency/SLOs, public
authorization, signing/key custody, stores, customer qualification and GA gates
remain pending. Physical phones remain disconnected and deferred; this lane
performs no native testing. Local fixture results do not qualify any provider,
immutable published FieldLog release, customer workload or production operation.
