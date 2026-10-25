# Isolated pending-registry entry composition

This packet composes the accepted cumulative schema-3 Engine/Ledger with the
original controller entry and corrected live registry/audit components. The
candidate is confined to `verification/hosted-worker-pending-entry-integration/`;
no live controller source, root tracker, Git state, schedule, provider,
credential, customer message or deployment was changed. Root's supplied source
revision is `4a28261b333c28b4fce386f370a19b93e735c8d2`.

The binding entry contract is
[`hosted-worker-pending-entry-integration-contract.md`](hosted-worker-pending-entry-integration-contract.md).
Root accepted the producer/review packet through
[`acceptance.json`](../verification/hosted-worker-pending-migration-outbox-root-review/acceptance.json).
Its accepted Engine production source digest is
`b997c592def14da3eb47b8e23ef3058510610545c420ee44568a86d1718f7c3e`;
its old compiled digest is
`43e4cdefddf998a56d7ae8c0ec982eec02ec2c937329e042c141fa512dacc846`.
Neither digest describes the newly rewired entry closure. The new source,
compiled inventory, reachable runtime closure and exact hashes are in this
packet's `source-manifest.json`, `compiled-manifest.json`,
`production-closure.json`, and `receipt.json`.

The entry authenticates and decodes the unchanged wire request, computes the
canonical full identity with the pinned configuration, and durably registers
through its one fixed shard before obtaining any operation DO ID or stub. The
250 ms registration wait shares the four-second outer elapsed/abort budget.
Every entry await is followed by an elapsed/abort check. Capacity, conflict,
invalid receipts, missing configuration and late acknowledgements cannot allocate
an operation object. There is no new public route, receipt header or credential.

The operation derives that identity independently and verifies the exact DO ID
against its configured operation binding. `OperationState` owns one Ledger and a
serialized, permanent initialization slot for at most one Engine/context. A
retained registration must validate completely, including canonical identity and
receipt bytes, request/binding digest and operation ID. Invalid retained rows stay
unavailable with a separate permanent fence; their original row bytes remain
unchanged. Public commands cannot select context for an unenrolled migrated row.
Only explicit private enrollment can attach a registration, preserving quarantine.

The production DO contains a JavaScript-private `#state`; its method surface is
exactly `fetch`, `recoverKnown`, `enrollExisting`, and `alarm`. It always composes
`UnavailableClock`, `UnavailableProvider`, and `UnavailableObjectVerifier`.
Synthetic effects are supplied only by an excluded fixture that directly creates
the non-DO state class. No production environment switch enables them.

The scheduled handler addresses only the fixed configured audit coordinator and
awaits its bounded `runScheduled()` RPC. The unchanged coordinator retains its
16-shard, 16-page, 512-record, eight-wake, 24-second limits and one unresolved
recovery slot. Tests invoke the actual workerd scheduled handler without customer
HTTP or operation alarms. This is local scheduled-handler delivery, not evidence
that a provider Cron schedule is installed or delivers in a deployment.

The final executable results are:

| Suite | Passing groups |
| --- | ---: |
| Entry composition through actual workerd and SQLite | 45 |
| Original controller / independent / focused compatibility | 28 + 7 + 36 = 71 |
| Accepted cumulative Engine regressions, rewired imports | 688 + 69 + 12 = 769 |
| Accepted registry/audit component regressions | 17 |
| Exact owned-process identity controls | 20 |
| Total, without counting nested original vectors again | 922 |

The entry controls cover preallocation ordering; all eight forwarded application
headers, exact wire bytes and nonce echo; ingress rejection; unavailable and
malformed registration; configuration/generation/namespace/exact-ID fences;
250 ms timeout, abort and a late acknowledgement across the four-second bound;
32 concurrent first calls and one in-flight Engine; retained restart validation;
malformed, missing and migrated rows; identity-only private recovery; independent
scheduled recovery; stale/duplicate wake completion; permanent terminal, MAX and
history fences; claim/report rejection; and positive cleanup behavior. Production
unavailable behavior is exercised separately from synthetic fixture effects.

The original compatibility fixtures required explicit registered admission. Their
first validated request now selects one exact immutable fixture identity, retained
across later calls and restart; there is no empty-ledger direct-command bypass or
per-request Engine reset. The first unchanged focused run and its failures are
preserved under `original-compat/focused/first-unchanged-report.json`. Root
explicitly selected the exact adaptations recorded in
`original-compat/focused/root-approved-assertion.diff`: schema 2 becomes 3;
migration preserves the original state version; clock-unavailable and quarantined
cleanup keeps terminal null; restored monotonic qualified time admits the accepted
pending result. Cleanup, identity, consumed-claim and no-regrant assertions remain.
The original focused source remains byte-preserved beside the adapted fixture.

One actual composition correction was required: a public request to an unenrolled
migrated row initially reached `commandRegistered`, which could permanently fence
it before explicit enrollment. The corrected entry returns unavailable before
context/command dispatch, preserving both the row and its enrollment path. All
failed attempts and their output remain in `attempts/`. Early exploratory entry
attempts predate per-attempt source-manifest capture; they retain commands, EOF
logs and reports but do not claim contemporaneous source snapshots. Final
acceptance runs are source-bound. Historical intermediate production closures
are not claimed to match the final candidate.

Reproduce with the pinned local tools:

```sh
python3 verification/hosted-worker-pending-entry-integration/run.py build
python3 verification/hosted-worker-pending-entry-integration/run.py entry
python3 verification/hosted-worker-pending-entry-integration/run.py original71
python3 verification/hosted-worker-pending-entry-integration/original-extra.py regressions focused
python3 verification/hosted-worker-pending-entry-integration/regressions.py
python3 verification/hosted-worker-pending-entry-integration/run.py identity20
python3 verification/hosted-worker-pending-entry-integration/run.py closure
```

Each run records command, Node/tool versions, output/EOF, source bindings and its
actual scope. Workerd ownership is checked by exact direct-parent/executable
identity before hard kills; every owned SQLite directory is removed and recorded
PIDs are absent after final acceptance. No native simulator, emulator, physical
phone, provider or external effect was used. Phones remain disconnected and
pending for final acceptance. Production clock/ingress, provider provisioning,
namespace/PITR rollback fences, actual schedule installation, resource limits,
runner/source/result authority, signing, stores, immutable-package FieldLog
qualification, accountable review and all applicable GA gates remain pending.

A bounded documentation search for the original eight-header contract returned
snippets from original transport amendment/V2 documentation. No frozen
catalog-inspector, authority-driver, or rejected outbound-worker V2 packet,
implementation or test was imported or executed. The original controller fixtures
and transport wire-vector data remain the only transport test inputs used here.
