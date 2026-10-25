# Independent aggregate admission review

Review scope: the frozen fleet-total, fleet-platform, organization-total and
existing organization/platform admission contract in
`verification/hosted-build-aggregate-admission/handoff.json`, at repository HEAD
`aaa9d2d7eaf44e82dc12fefe2b41431d0fd44d11`. The review owns this document and
`verification/hosted-build-aggregate-admission-independent-review/` only.
Production code, producer tests, migrations, collector, global status and Git
were not modified by this review.

No blocking product defect was found. The frozen independently authored controls
passed **11/11 with zero skips** against real disposable PostgreSQL on the first
root-run attempt. The evidence checks below bind that result to the reviewed
Admission source and migration. This supports acceptance of this development
slice within its documented local scope; it does not accept an operational or
GA gate.

## Reviewed contract

The reviewed files are `hosted/lib/mixer_hosted/builds/admission.ex`, migration
`20261025000002_add_build_aggregate_limits.exs`, current admission, aggregate
admission, coordinator and storage tests, and the two admission contract documents.
The handoff hashes were recomputed before preparing executable controls; all
nine recorded inputs matched. Root separately corrected the foundation
integration fixture's expected migration list after its full-suite run found the
new fourth migration. That fixture correction does not change the reviewed
Admission implementation or migration.

The capacity decision uses retained `Reservation.held` rows at all four scopes.
There is no derived occupancy counter to leak on rollback. Configuration has
explicit first activation and revision CAS, including closed placeholders.
Missing aggregate policy rejects fresh reservations. The already-held path
still validates the retained reservation and lease before bypassing fresh
eligibility, so missing or reduced aggregate configuration cannot strand its
reconciliation.

All valid configuration, claim and token-guarded mutations reach
`lock_capacities/2`: it rejects unsupported isolation before taking the fixed
transaction advisory mutex `(1296648258, 1)`. Existing scoped rows follow in
fleet, platform, organization and organization/platform order; build,
reservation and lease rows follow. The global mutex also covers absent parents
and remains held across composed Multi fragments. The lease clock is sampled
after the locks. A caller that takes raw build/admission locks first violates
the published composition contract; this review does not authorize that pattern.

The migration creates closed aggregate policy tables and the held-platform
index. It backfills each distinct organization represented by existing pair
policy. It does not rewrite retained build journals, reservations, leases,
worker fences or jobs, and it adds no aggregate foreign key that could prevent
held reconciliation after aggregate policy disappears.

## Independent executable controls

The independently authored `aggregate_admission_review_test.exs` uses its own
worker module, real Ecto/Oban writes and the dedicated disposable
`mixer_aggregate_admission_review_test` PostgreSQL database. It contains eleven
controls:

| Control | Observable boundary |
| --- | --- |
| Mutex before row locks | Every valid Admission/configuration fragment is observed waiting on the exact two-int advisory key in `pg_locks`, with no granted relation lock on the seven admission/build tables. Later rollback preserves all rows. |
| Earlier READ COMMITTED snapshot | A contender first counts zero held reservations, waits behind an uncommitted claim, then rejects after that claim commits the last fleet slot. |
| Unsupported isolation | REPEATABLE READ, SERIALIZABLE and READ UNCOMMITTED renewal attempts reject while another transaction still owns the mutex, preserving existing ownership. |
| Rolled-back release | A waiting cross-platform claim cannot see a temporary release that rolls back; the original reservation, lease, journal and job rows remain identical. |
| Composed release and replacement | Definitive queued cancellation, release, a different organization's claim and fleet shrink commit in one Multi; occupancy remains one and the new owner can reconcile at zero fresh capacity. |
| First-activation rollback | Fleet, platform and previously missing organization activation each roll back while a mutex waiter subsequently activates exactly once at revision zero. |
| Closed configuration | Missing pair or any aggregate policy rejects without a reservation or lease; synthetic deletion/recreation of each aggregate parent never acts as unlimited capacity. |
| Eighteen contenders | Concurrent transactions across three organizations and both pools fill exactly seven fleet slots, four iOS and three Android, while respecting organization and pair ceilings; duplicate claims preserve occupancy. |
| Started uncertain worker | All-limit shrink, cancellation, yield and deletion of aggregate policy preserve the original WorkerRef; stale or nondefinitive release fails and an exact stopped event releases. |
| Upgrade/backfill | Down/up of only the additive migration preserves held and released records plus jobs, creates one closed row per distinct pair owner including an idle organization, and preserves a started worker through coordinator transfer. |
| Cross-scope CAS rollback | Stale organization or platform revisions roll back preceding changes at other quota levels exactly. |

Synchronization checks server lock state rather than inferring a database wait
from a task launch delay. These controls are local correctness probes; the
number of contenders is not a throughput, fairness, failover or load result.

## Evidence and limitations

`preparation-receipt.json` records exact formatting/syntax argv, Elixir output,
HEAD, live input hashes and the prepared test hash. Root executed the frozen
review file using the existing collector's explicit `--additional-test` and
`--only-additional-tests` options. This review did not start a collector or
another database. The observed test command, from the hosted directory, was:

```text
mix test --warnings-as-errors --seed 0 --trace /Users/andreyyurlov/Documents/dev/mixer/verification/hosted-build-aggregate-admission-independent-review/aggregate_admission_review_test.exs
```

The root collection is
`verification/hosted-build-aggregate-admission-root-review/independent-attempt-1/`.
Its receipt records Elixir 1.20.4 with Erlang/OTP 29 and PostgreSQL 17.11
(Homebrew), UTC, loopback-only with no TLS. `tests.log` reports `Result: 11 passed`;
there are no skipped independent controls. The `tests` command exited zero.
The independent source remained unchanged from preparation through execution.

| Binding | SHA-256 |
| --- | --- |
| Admission implementation | `87bd56955fa99c2978a407c74cfcc87819ac6059a0bc4a86a36df763424ab0eb` |
| Aggregate migration | `443ede59186c0fca9454bcec319965217007c328719dbb152bdf6552901e009b` |
| Independent test | `21e953d415436778280e7e22aac38039e74a6deebf57113bd2ad7a24e319684e` |
| Collected source tree | `d670c9376af2d5f384b294e736fbd9a1f760daec89396deba433a87b020e8f52` |
| Source archive | `85cc4570374b21fdd1be2a2fa546d1bae6878158d59af3c1b7a766417847c92c` |
| Independent tests output | `65eb03d1fd7badd45faa57d73c1a44690a2d08a42e5f5921b9cae7f8ba2e0d3e` |
| Collection receipt | `42528941d8a7ee4cdf75241a48f405613a6dbe96b39a78ae489fba6310942151` |

`verify_evidence.py` is a read-only binding verifier.
`evidence-binding-review.json` independently recomputes the canonical source
manifest digest and archive hash, rehashes all nine live handoff inputs, verifies
the six reviewed hosted handoff members plus the independent test against their
archived and live bytes, and verifies all 23 command-output hashes and expected
exit codes. It confirms the recorded scratch path is absent. The collection
receipt records the owned PostgreSQL stopped and scratch removed. Root's
`independent-binding-review.json` separately verifies all 92 current/archive
inputs; this review's narrower seven-member archive comparison does not claim
review of unrelated hosted source.

The independent run retains two diagnostics: the manual test Oban PostgreSQL
notifier logged missing database options, and migration down/up emitted module
redefinition warnings. The direct persisted Oban-row, transaction, journal and
admission assertions passed. Notification transport startup and delivery are
not qualified by these tests. No warning or logged error is hidden or counted
as notification readiness.

The root full-suite `attempt-2` result is separate: 255 passed and two Linux
network isolation controls skipped. Its source-tree digest is
`256d02916db75025b0d087c45ebff979a5108f588d1a3b5b8b7334cce2464bdc`;
the independent-only tree adds this review test. The skipped full-suite controls
receive no acceptance credit. The preserved predecessor `attempt-1` had four
invalid foundation integration cases due to the three-migration expectation;
root corrected that fixture before the passing full-suite run.

No production migration, writer rollout, capacity tuning, provider execution,
cloud/Neon operation, native/device verification, signing, authentication,
source authority, catalog inspection, customer message or GA acceptance is
performed or established here. All old admission writers must be replaced or
stopped before aggregate enforcement can be relied upon. The fleet-wide mutex
serializes compliant writers in one database; its operational throughput and
fairness remain unmeasured. Physical phones remain deferred under the current
project instruction.
