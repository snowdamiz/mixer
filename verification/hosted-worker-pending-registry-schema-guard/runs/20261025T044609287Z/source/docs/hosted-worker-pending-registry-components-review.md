# Independent pending-registry component review

Review outcome: **changes required for the frozen component packet**. One
reproducible schema fail-closed defect remains. The earlier loss of known late
recovery failures is repaired in this source, including rejection normalization,
memory fallback, exact completion retention and healthy-shard progress.

The reviewed producer receipt SHA-256 is
`d25bc98f405bb25ea1c93ee583c92fe370f58dd777c8d28376830d8d2c648a18`;
the runtime source digest is
`4b5df151a39ac703ef76705cf7d6d7a6c10ac69f4a2c5e6f2a33f2f1e6dd0078`;
the proposed integration patch SHA-256 is
`a242e56d745de292b353d4b74bee90acee7b84089a8292485d4030deb71442f6`.
This review uses the root-selected base and completion contracts. It changes no
producer, engine, live entry, root tracker, dependency, deployment or Git state.

## Required correction

**[P2] Reject surviving audit safety tables when schema metadata is missing.**
In the frozen
[`pending-audit.ts`, lines 14–16](../verification/hosted-worker-pending-registry-components/candidate/src/pending-audit.ts),
the constructor only validates `pending_audit_meta` when that table exists. If
the table is absent while `pending_audit_completion` or `pending_audit_summary`
survives, it executes `CREATE TABLE IF NOT EXISTS` and inserts a new configuration,
run sequence `"0"`, zero cursors and no current receipt. That replaces missing
schema/configuration/CAS history with valid-looking new state. It violates the
selected requirement that an unknown schema or unsafe migration is unavailable;
the registry constructor already rejects its analogous record-without-meta state.

An original actual workerd/SQLite control first retained an exact late
`unavailable` completion, deliberately removed only the audit metadata table in
its owned test store, then performed an identity-checked SIGKILL/restart. The
constructor recreated the metadata and the next run returned `finished` with
run ID `"1"`, applying the old completion. Expected: `unavailable`, preserving
the surviving tables without creating replacement metadata. This is an explicit
partial-schema fault injection; the review does not claim an ordinary SQLite
crash produces a missing table. Reject this state before schema initialization
and add the restart regression control. The same check should cover either
surviving audit safety table.

The preserved failing assertion and observations are in
[`focused-report.json`](../verification/hosted-worker-pending-registry-components-review/focused-report.json).
The review fixture's table-removal method is excluded test code, with no public
or production route. Root received the finding before completion of this report.

## Source and evidence assessment

| Requirement | Observed evidence and boundary |
| --- | --- |
| Canonical identity, sixteen buckets and closed validation | The component recomputes the preserved operation key and canonical identity SHA-256 before registry transactions; conflicts compare full identity bytes as well as digest. ASCII principals, exact keys, lowercase digests/UUIDs, generation, platform and bounded canonical decimal fields fail closed. Fixed versioned object names bind configuration. All 17 independent contract vectors and all 16 buckets have source-bound actual SQLite evidence. |
| Permanent bounded identity records | Static parameterized SQL retains permanent allocation indices and terminal rows, caps each shard at 4,096 lifetime identities, and checks encoded records against 4,096 bytes. The producer boundary control observed 4,096 accepted, a rejected 4,097th, terminal replay and post-SIGKILL retention. No deletion, TTL or overflow namespace exists. |
| TEXT int64 and exact CAS | Version/run/attempt values remain canonical decimal TEXT and use `BigInt` ordering. Exact projection bytes govern equal-version replay. Full receipt, tracked version and exact ticket bytes fence completion. Newer tracking clears old tickets; a terminal track is permanent. Success dispositions update delivery only and cannot make a record terminal. |
| Read-only scan and fair revisits | Two bounded indexed tail/head iterators provide allocation ordering and one wrap without materializing all rows. `scan_due` does not mutate delivery state. Only a distinct increasing run's reservation decrements 0–7 visit backoff. Failures saturate at 32 and attention starts at eight. Actual evidence includes nontrivial wrap, repeated pure scans, 35 failures, maximum eight-visit gap and 528 identities visited across sixteen shards by 80 excluded scheduled events. |
| Invocation, page and wait bounds | Source counts before starts: eight recovery starts, sixteen pages, 512 examinations, 32 records/page and 65,536 encoded bytes/page. Pages/reserve/finish have 250 ms caller waits; recovery has at most 2,500 ms with finish allowance inside one 24,000 ms elapsed budget. Durable shard rotation occurs before waits. Producer evidence includes the ninth untouched wake, sixteen pages/512 examinations, and 95 examinations over 21,116.872 ms with 220 ms registry waits. The maximum legal closed-principal page was 44,211 bytes; a legal page cannot reach the byte-truncation branch before the 32-row cap. |
| One unresolved recovery and late settlement | A live unresolved slot blocks concurrent/new runs after timeout until actual settlement. Timeout halts further wakes in that invocation and does not claim cancellation. Callback validation converts rejection/invalid replies to `unavailable`, stores the exact result in memory before one synchronous local SQLite CAS write, and performs no RPC, retry, timer or await. |
| Bounded completion durability and shard progress | Sixteen permanent shard slots each enforce at most 2,048 encoded bytes. A retained memory value is persisted and synced before any next-run remote work. Each occupied shard is rotated/checkpointed before one bounded exact `finish_wake`; accepted/stale allows exact clear, unknown/unavailable retains that shard's slot. Local write/clear failure stops the invocation; unavailable remote completion blocks that shard's new wakes while healthy shards progress. Producer controls cover stale completion against newer terminal tracking, real SQLite write/clear aborts, restart, failure attention and healthy-shard progress. |

The independent combined control used a different identity population and an
interleaving of late **rejection**, real completion-write `RAISE(ABORT)`, the next
run failing before healthy remote work, repair of that local fault, a held
finish acknowledgement after registry commit, healthy-shard recovery, SIGKILL,
exact completion replay and stale-ACK clear. It passed: failure was counted once,
the original recovery was not repeated, and the healthy shard progressed. This
directly checks the earlier late-failure loss rather than inferring repair from
the producer's test count.

## Reproduction and custody

From the repository root:

```sh
node verification/hosted-worker-pending-registry-components-review/run-review.mjs
```

The command intentionally exits 1 for the preserved missing-schema assertion.
It imports the frozen compiled production candidate and its excluded synthetic
recovery/inspection adapter through an independent excluded review wrapper.
There is no in-memory registry substitute and no whole-suite rerun.

[`integrity.json`](../verification/hosted-worker-pending-registry-components-review/integrity.json)
verifies 23 producer artifact bindings, 23 current source bindings, all 23 archived
source copies, all eleven compiled files, selected contract/interface/amendment
hashes and all producer command stdout/stderr hashes. The producer's preserved
run has seventeen passed actual workerd/SQLite groups, twenty passed owned-process
identity controls, fourteen identity-checked SIGKILL boundaries and seventeen
disposed owned storage directories. These are verified existing receipts, not
newly executed review passes.

The independent review ran two focused controls: one passed and one failed.
[`command.json`](../verification/hosted-worker-pending-registry-components-review/command.json)
records exact argv/cwd, exit 1, no timeout, both stream EOFs, direct-child closure,
absent detached process group and removed scratch.
[`runtime-receipt.json`](../verification/hosted-worker-pending-registry-components-review/runtime-receipt.json)
binds source revision, all reviewed source/compiled files and tool versions.
The independent report records two disposed stores, two identity-checked
SIGKILL/restart boundaries and four observed owned process identities, all absent
after cleanup. It makes no remote-task cancellation claim. The review used
Darwin arm64, Node v22.23.3, workerd 2026-07-30 and Miniflare 4.20260730.0.

Real engine pre-registration, schema-3 outbox/ACK/barriers, identity-only actual
ledger recovery, migration, live three-class scheduled/export wiring, all thirty
full acceptance cases and regression qualification of the 71 existing controller
groups remain separate work. Deployed Cron, actual providers/clock/ingress/restore
authority, whole-domain resources, signing/stores/FieldLog, physical phones,
accountable GA review and every deployed gate remain pending. No device or UI
test, cloud action or excluded frozen hosted lane was used by this review.
