# Durable pending-operation registry and independent audit contract

Status: public implementation contract selected by root after source review.
Root selected the finite profile, identity-only recovery direction and automatic
fair revisits described below. This packet contains no live controller change,
dependency, schedule, deployment or provider enablement. Root selects the public
interfaces here before assigning dependent implementation. The binding scope remains
`mixer-product-plan.md`, especially its hosted execution and operational gates.

This extends the [controller contract](hosted-worker-controller-contract.md),
lines 319–365, and preserves the earlier
[track/outbox selection](hosted-worker-controller-implementation.md#pending-independent-audit-integration-contract).
The accepted starting code is the [V2 integration](hosted-worker-controller-v2-integration.md).
The repaired controller at `7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8` has
[terminal Linux CI evidence](hosted-worker-controller-linux-ci-checkpoint.md).
That evidence uses a synthetic provider and clock; it does not implement or
qualify this registry. Frozen catalog-inspector/authority-driver and interrupted
outbound-worker-transport lanes are outside this contract and were not reopened.

## Invariants and selected placement

Keep the current operation DO as the sole authority for its immutable binding,
guard, clock history, desired stop, launch dispatch, consumed claim and result.
A registry record confers permission to address that known identity for recovery
only. It cannot create a build, supply a command/guard/source specification,
renew authority, grant a runner claim, release Phoenix/Neon capacity, replace a
provider identity, authorize signing, or clear quarantine. Phoenix policy and
business authority remain separate.

Use SQLite DO storage through the controller's existing pinned runtime. Add 16
fixed registry-shard DOs and one fixed audit-coordinator DO in a separately named
binding from `OPERATIONS`. These are logical class/binding additions to this
controller, not a new service or dependency. An independently invoked Worker
`scheduled` handler calls the fixed audit coordinator; operation alarms,
customer requests, monitoring promises and operation `waitUntil` tasks are not
the audit trigger. The same Worker may contain the handler: its independence is
from per-operation wake delivery, not from the entire provider failure domain.
Actual schedule installation and delivery remain unqualified.

Configuration pins one lowercase hex64 `namespace_generation`, the operation
namespace identity and registry namespace identity. There is no generated
default, caller-selected namespace or fallback generation. Generation equality
is an identity fence, not proof that storage has never been restored. Missing or
conflicting configuration disables registration, audit and new effects. No
namespace is recreated, restored or automatically replaced by this slice.

## Finite development profile

| Resource | Selected limit |
| --- | --- |
| Registry allocation | Exactly 16 possible shard names, 4,096 lifetime identity slots per shard; 65,536 total permanent identities. One additional fixed audit-coordinator DO. |
| Identity and stored record | 2,048 UTF-8 bytes per canonical identity; 4,096 bytes per registry record, excluding bounded SQLite/index overhead. No source, guard, credential, result body or provider log. |
| Local outbox | One coalesced latest track outbox per operation, with at most 32 KiB of exact local terminal bytes when a digest must be computed outside the transaction. |
| Scan | At most 32 records and 65,536 encoded bytes per page; at most 16 pages and 512 examined records per invocation. Never materialize the registry to paginate it. |
| Scheduled invocation | At most eight recovery RPC starts, one unresolved recovery RPC per live audit coordinator, 24,000 ms elapsed handler budget. No inline readiness wait. |
| Registry/storage RPC | 250 ms caller wait per call; no retry loop within a command or page. Timeout means unknown outcome. |
| Recovery RPC | 2,500 ms caller wait, within the invocation's remaining budget; at most one existing provider action with its unchanged 2,000 ms provider limit. |
| Delivery counters | Consecutive failures saturate at 32; `needs_attention` becomes true at eight. `skip_visits` stays in 0–7. Counters never wrap. |
| Audit records | One current run receipt plus 32 bounded summary slots per audit coordinator, one latest wake reservation/disposition per registry identity. Permanent identity/safety records are not ring-buffer detail. |

Limits count attempts before starting them. Stop before starting another page or
wake when its maximum wait cannot fit the remaining elapsed budget. A timeout
does not establish RPC/provider cancellation. Keep the current unresolved task
slot until settlement is observed; do not start another wake in that invocation
after its timeout. A later process may duplicate a recovery wake; the operation's
durable intent and claim rules still prevent a duplicate launch/grant. This does
not claim exactly-once audit delivery or a global remote-task count across crash.
Page, `reserve_wake` and `finish_wake` waits all consume that same 24-second
invocation budget, each with the 250 ms registry-call cap. Reserve the remaining
finish allowance before starting a wake; there is no separate unbudgeted retry
or finalization loop. A reserve/finish timeout leaves its reservation outcome
pending/unknown for later CAS recovery; it cannot fabricate cancellation or a
successful disposition. Independently settled later replies may be applied only
through the unchanged ticket/version CAS.

Root selected these bounds for development. Per-shard imbalance can exhaust one
shard before the global total; no overflow shard is allowed. The 4,097th identity
in a shard fails closed before operation allocation/mutation. Terminal and orphan
records count forever. Capacity exhaustion cannot justify deleting tombstones,
changing generations or recycling slots. Existing registrations, terminal replay,
audit scans and committed-stop enforcement must continue at capacity. Physical
storage overhead, fleet CPU/FD/memory/log limits and actual usable capacity still
need deployed measurements and accounting.

## Canonical identity and public private-binding API

The type-only interface is sealed in
[`verification/hosted-worker-pending-registry-contract/public-contract.ts`](../verification/hosted-worker-pending-registry-contract/public-contract.ts).
It uses strings for protocol int64 values, compared with `BigInt`. Only bounded
internal indices, counters and limits use JavaScript/SQLite INTEGER values.

Preserve current `operationKey(r)` bytes:

```text
SHA256(UTF8(JSON.stringify([
  "mixer-worker-controller-do-v1", environment_id, pool_id,
  controller_id, operation_id
])))
```

The identity tuple, without Unicode normalization or reordered fields, is:

```text
["mixer-worker-pending-identity-v1", namespace_generation,
 environment_id, pool_id, controller_id, platform,
 operation_key, operation_id, immutable_sha256]
```

Its SHA-256 is `identity_digest`. The shard is the numeric value of the first
lowercase hex character of `operation_key`, 0–15. Registry names are the
versioned configured tuple plus that index; clients never send a shard index.
Recompute both hashes before entering SQLite transactions and verify complete
identity bytes as well as digests on conflicts. The immutable digest remains
the existing transport digest; it is not redefined by this contract.

The selected operations are:

* `register(identity) -> RegistrationReceipt`: atomically allocate or return the
  existing identical record, initially pending with tracked version `"0"`.
  Await durable storage before acknowledging. A lost acknowledgement retries
  idempotently, returning the same record UUID and allocation index. Same key
  with different identity/generation/digest conflicts without another allocation.
* `track(receipt, state_version, projection) -> TrackAck`: store the latest
  operation-derived projection and next-due hint. A greater version replaces the
  old projection; an equal version is accepted only for exact identical bytes;
  an older version is stale with no mutation. Equal-version conflict and a
  reported registry watermark greater than the current local ledger require
  quarantine/attention, not overwrite. No nonterminal update can reopen a
  quiescent terminal record, regardless of higher version.
* `scan_due(cursor, limit) -> Page`: select bounded pending records in stable
  allocation-index order, with wrap, including attention/orphan records.
  `next_due_us` is retained as an exact hint; it never authorizes or filters out
  a pending identity indefinitely. This call is read-only for every record's
  delivery/backoff metadata; it does not decrement `skip_visits`, reserve a wake,
  or advance a cursor. Cursor advancement belongs to the audit coordinator.
* `reserve_wake(record_id, expected_track_version, run_id) -> WakeTicket | skip`:
  compare-and-swap the scanned snapshot, decrement bounded visit backoff or
  durably reserve exactly one attempt before calling the operation. A newer
  track/terminal disposition makes the reservation stale. A duplicate run and
  record returns the same reservation without starting a second RPC.
  This is the only transaction that decrements `skip_visits`; duplicate
  `(run_id, record_id)` visits cannot decrement it twice.
* `finish_wake(ticket, disposition)`: only an exact reservation ID may update
  delivery metadata. An old/lost reply cannot overwrite a newer reservation,
  newer track projection or permanent terminal disposition.
* `recoverKnown(identity, receipt, ticket) -> RecoveryDisposition`: a private
  operation binding call containing identity and audit metadata only. It has no
  `WireRequest`, command, guard, source/spec, provider URL or credential. It
  reads the current existing operation ledger, validates the full identity and
  generation, then replays its outbox/arm/reconcile path. It never calls
  `Engine.command` or `Engine.claim`, binds a missing operation, renews expiry,
  invents an effect, changes provider identity or clears quarantine.
* `runScheduled() -> AuditSummary`: only the fixed configured scheduled handler
  invokes the audit coordinator; it takes no tenant-selected identity or time.

The public HTTP route, eight application headers, wire-v1 bytes, nonce echo,
four-second controller handler budget and five-second client deadline remain
unchanged. No registry or recovery route is added to public HTTP. Private RPC
registration receipts and tickets are not new client headers or bearer tokens.
All private-binding payloads are closed, length-bounded records validated at
both ends. A digest or a record UUID alone is never authorization.

## Durable rows and ordering that closes the discovery gap

Each registry shard has a schema/version/config row, an allocation counter
bounded to 4,096 and the permanent records. A record retains its full canonical
identity, allocation index, stable hex128 record UUID, latest exact tracked
version/projection, pending/quiescent disposition, optional terminal evidence
digest, and bounded delivery metadata. SQLite writes are parameterized static
SQL. `state_version`, wake/run sequences and `next_due_us` are canonical decimal
TEXT with int64 overflow rejected; no textual numeric sorting. A schema mismatch
or unsafe migration is unavailable. No deletion, TTL or counter reuse exists.

The audit coordinator stores its generation, monotonic run sequence, next shard,
16 per-shard allocation cursors and current run/CAS state. A schema/configuration
conflict stops traversal; it never discovers another namespace by enumeration.

An operation schema-3 migration adds an immutable registration receipt and one
track outbox/ack watermark. Save the outbox projection atomically with every
effect/stop/claim/terminal intent and next-due transition. Keep a single newest
outbox rather than append a new unbounded queue. Local outbox acknowledgement
uses exact version/projection CAS and does not increment the operation's state
version or create another outbox. Receipt/ack/delivery metadata cannot change
the authority watermark or clock history.

The command/effect order is:

1. Authenticate and bound/decode the complete request; recompute and validate its
   identity/digests. Reject auth/shape/scope/conflicting identity before registry
   allocation. The top-level entry registers before obtaining/initializing a
   new operation DO. Only the already registered private command entry may
   initialize an operation row; constructor metadata initialization cannot
   synthesize a row, guard or effect.
2. Durably `register` the identity and obtain its stable receipt **before any
   initial operation-row mutation**. The operation validates that receipt through
   its trusted registry port. Registration contains no requested command or
   authority. An outage/lost acknowledgement prevents a new row/effect; a later
   retry obtains the same receipt.
3. In the current synchronous operation transaction, perform the unchanged
   immutable/guard/qualified-clock checks and commit the intended transition plus
   latest track outbox. Registration alone never makes an expired guard valid.
   Await local durability. The registry already retains this pending identity,
   even if the process dies now and never sets an alarm.
4. Flush the outbox to `track` and await its durability before dispatching a new
   launch/inspect effect or issuing a claim grant. Recheck the outbox/version after
   each await; an older acknowledgement cannot clear a newer pending projection.
   Mark effect dispatch durably as today and flush the projection covering that
   dispatch intent before the provider call. A failed flush retains uncertainty
   and the original identity; it never clears `launch_dispatched` to retry launch.
5. Preserve V2's final post-await authority/identity/qualified-time check. Its
   accepted clock-history write may produce a newer outbox than the already
   acknowledged effect/claim intent. That is safe because the pending subscription
   is permanent; the effect/claim barrier covers its exact persisted intent,
   not an impossible requirement to acknowledge every final clock-only write
   before another final time sample. Track that newer clock projection later.
   For a grant there is no await after its final V2 transaction/output gate.

Persist the exact barrier state version with each effect and consumed-claim
intent. Compare `registry_ack_version >= barrier_version` with `BigInt` before
its final recheck. The ack is a delivery barrier, not authority. A higher local
clock-only version does not change which effect/claim the barrier covers. A
newer command, different effect/claim identity, stop or quarantine still wins.

Terminal commit writes a terminal outbox atomically. When a SHA-256 needs an
async Web Crypto call, retain the exact bounded terminal bytes locally in that
outbox; compute its digest outside the transaction and recheck its exact
version/bytes before `track`. Only `track` of matching permanent terminal state
can make the registry quiescent. Lost terminal acknowledgement repeats the same
track; it does not erase the terminal row or rerun scripts. Registry terminal
digests are copies of local evidence, not substitutes for provider drain proof.

This order strengthens the earlier outbox-only sketch. With outbox alone, a
crash after local intent and before registry registration leaves no discoverable
identity when the alarm also fails. Pre-registration makes that crash produce a
known pending identity. A crash earlier produces an orphan registration that
can only cause a harmless read/recovery attempt.

## Stop, missing-ledger and migration behavior

An already registered operation uses its retained receipt; it does not require
a successful fresh `register` round trip for every request. A committed explicit
stop remains enforceable while registry/clock delivery is unavailable. Its
reconcile path attempts the track outbox but proceeds with owned stop/cleanup if
that delivery fails. The stop permission comes only from the current durable
`desired=stop`, never from registry metadata or a new expired request. This
exception cannot grant a launch/claim, accept a result, declare drained, or drop
capacity. New identities still require pre-registration, including first stop.

For registered version `"0"` with no operation row, return `empty_orphan`: do not
create a row, effect, lease or terminal evidence. Keep it pending, eligible for
fair later visits and attention after repeated failures. Do not retire on
absence: the originally registered command may still be delayed. A subsequent
valid authenticated command may use the retained registration and independently
pass the normal qualified-authority checks.

If the registry has tracked a positive version but the operation is missing,
or the operation version is below the retained registry watermark, persist a
separate bounded quarantine fence without fabricating an operation row. Return
`quarantined`, retain registry pending/attention and perform no new work. Full
identity, generation, receipt or immutable-binding disagreement also quarantines.
An older scan against a newer local row may reconcile that current row; it may
not replay its old snapshot over the ledger. No scan reconciles arbitrary keys.

Existing schema-1/2 rows lack a proven pre-registration barrier. Migrate
non-destructively to schema 3, preserve every identity, terminal result, stop,
consumed claim, dispatch marker and V2 clock floor, and quarantine new effects.
Enforcement of an existing durable stop remains possible. A trusted bounded
`enrollExisting(identity)` maintenance call may register only an explicitly known
existing matching row and persist its outbox; it cannot reconstruct a missing
row or clear any quarantine. There is no automatic namespace enumeration or
claim that this discovers all legacy operations. Deployment must provide a
source-bound inventory/enrollment receipt or keep the affected old population
quarantined. No new restore authority is introduced by enrollment.

## Fair traversal, concurrency and no-customer-traffic recovery

The coordinator starts a run in a synchronous transaction with an incremented
run/CAS token. One in-memory unresolved-run slot prevents concurrent scheduled
calls in that live DO; duplicate callers return bounded `busy`. Never hold a SQL
transaction across a page fetch, registration, recovery RPC, hash or provider
call. On a later process start an unfinished run remains an interrupted receipt;
continue from its durable cursors under a new token. Do not infer that its old
RPC was cancelled or erase an operation's dispatch/claim marker.

Visit shards in fixed circular order. Each selected page has at most 32 pending
allocation indices, ordered tail-then-head with at most one wrap and no duplicate
index. Persist the next-shard cursor before leaving that shard. Within its page,
advance the per-shard cursor only through examined records; stop after the eighth
selected wake or elapsed/call cap, leaving later entries for the next visit.
Checkpoint/reserve before each RPC; a crash can duplicate or delay a visit, not
make a record unreachable. Never reset the cursor to zero on every trigger or
drain one busy shard before considering its successors. Terminal records remain
stored but are excluded by the bounded indexed pending scan.

Every visit to a pending record either selects an attempt or decrements
`skip_visits`. After consecutive failed/empty/quarantined/unavailable attempts,
set `skip_visits = min(7, 2^min(failures,3)-1)` and saturate failures at 32.
Success resets delivery failures/backoff. `needs_attention` is true from failure
eight; attention records remain in the same traversal with skip at most seven.
No individual record exhausts automatic retries forever, and no customer request
is needed to resume them. Registry `next_due_us` and platform timer samples are
scheduling hints; this visit-count backoff makes no wall-time freshness claim.

Within a progressing scan of a fixed finite pending population, the circular
shard/record cursors visit every pending record; visit-count backoff permits an
attempt at least every eighth visit. This is logical fairness, conditional on
successful storage/schedule progress and no blocking outage. It is not a measured
latency, recovery-time objective or provider guarantee. A failed shard page must
produce an error/attention summary and leave that shard's row cursor intact;
the durable next-shard cursor still advances so other shards can progress.

Successful recovery means the private operation read/validated existing state,
replayed eligible outbox and performed bounded arm/reconcile; it does not mean
the build completed. Reconciliation may dispatch a **previously persisted**
prepared intent only after all current registration, immutable, guard, clock and
final V2 checks. Audit does not create an intent. A prepared launch that is no
longer authorized remains uncertain or becomes a persisted deadline stop under
the existing definite-time rule. Audit never calls the runner claim interface.

The development recovery surface is the same trusted `runScheduled()` binding,
invoked from a test scheduled event with public fetch disabled and all operation
alarms faulted/exhausted. Optional trusted inspection returns at most one bounded
page/summary and accepts no commands or row edits. No reset/retry-grant API is
needed because attention records remain automatically eligible. An operator
invocation may request another identical bounded audit run; it cannot bypass
page/call caps, reset safety state, change generations or clear quarantine.

## Failure-order acceptance cases

[`acceptance-cases.json`](../verification/hosted-worker-pending-registry-contract/acceptance-cases.json)
defines fault boundaries and required observations for the future source-bound
runtime tests. The cases are requirements, not claimed product passes.

| Boundary | Required outcome |
| --- | --- |
| Before registry commit / after commit before ACK | No operation/effect before an acknowledged registration; retry allocates once and returns identical receipt. |
| Registration ACK / local intent / failed alarm before track | Orphan or pending registered identity survives real process restart; independent scheduled event finds it with no public HTTP. |
| Track commit before ACK / out-of-order tracks / concurrent command | Exact replay is idempotent; older ACK cannot clear newer local outbox; equal-version conflict fails closed. |
| Dispatch marking / provider effect / lost response | Retain launch-dispatched and original resource/claim; inspect/stop only when the original launch may have happened; no replacement launch. |
| Terminal local commit / terminal track / lost terminal ACK | Pending until exact terminal evidence is durably tracked; terminal record retained forever and never reactivated. |
| Audit checkpoint/reservation / RPC / stale completion / restart | CAS protects newer state; duplicate wake harmless; eight-start/page/time caps and owned-task cleanup observed. |
| Missing ledger / wrong generation / older restored version | Orphan version zero stays pending; positive-version missing/regressed/conflicting identity quarantines with no reconstructed authority. |
| Registry/shard/operation outage / full shard | No new unregistered effect; pending state retained; other shards visited; existing durable stop still enforced. |
| Stale/unqualified/backward clock | Audit and registry cannot renew a guard or override V2 quarantine; no new launch/claim. |

Implementation acceptance requires actual cross-DO SQLite storage, source-bound
fault injection, process restart/SIGKILL, independently observed provider-call
history and all three classes' state. Include 4,096/4,097 slot boundaries in a
selected shard, all 16 hash buckets, nontrivial cursor wrap, equal/older/newer
versions above JavaScript's exact-number range, eight-attempt versus ninth,
32-record versus 33rd, concurrent runs, a slow noncooperative wake, permanent
attention revisits, query-only registrations and existing terminal replay.
Use smaller explicitly test-only capacities for exhaustive interleavings as
additional evidence; they do not replace fixed-profile boundary tests.

Keep the existing 20 process-identity controls and 71 controller groups passing.
Extend the excluded workerd/SQLite test Worker and recurring Linux runner;
synthetic credentials, clock/provider, fault injection and maintenance controls
stay outside production imports. Dispose owned DO storage, processes, sockets,
timers and scratch after every successful or failed run; preserve unrelated
processes/data. Record source/tree hashes, versions, exact commands/output,
timeouts, EOF and cleanup. A TypeScript/packet check alone does not pass this
runtime acceptance matrix.

## Minimum implementation coupling and remaining qualification

| File | Coordinated change after root selection |
| --- | --- |
| New `src/pending-registry.ts`, `src/registry-schema.sql` | Private typed port, static identity/shard logic, 16 SQLite registry shards, compare-and-swap track/reservation transitions, finite schema/profile. |
| New `src/pending-audit.ts` | Fixed audit-coordinator DO, durable fair traversal/run CAS, bounded scheduling/recovery and summaries. |
| `src/schema.sql`, `src/ledger.ts` | Non-destructive schema-3 fields/table, registration/barrier/outbox/ack and missing-ledger quarantine metadata. Preserve all V2 safety/clock fields. |
| `src/engine.ts`, `src/provider.ts` | Inject registry port, atomically project intents, persist exact barrier versions on internal effects/claims, flush/recheck before effect/grant, terminal projection and durable-stop outage path. No enabled provider. |
| `src/operation.ts`, `src/index.ts` | Authenticated pre-registration before new operation lookup, trusted registered command entry, identity-only recovery/enrollment bindings, fixed scheduled entry and exports. No public recovery routes. |
| `build.mjs`, `test/worker.ts`, test driver/runner and closure expectations | Copy second SQL asset; actual three-class SQLite/restart/cap tests; preserve excluded test entry and existing runner evidence. |
| Root-owned docs/trackers/inventory | Update observed implementation/limitations. No new package is needed. Future deployment config selects explicit bindings/migrations/schedule under separate authorization. |

Root owns these production files, trackers, dependency selection and Git. This
lane owns only this contract and its verification packet. Implementing public
interfaces follows root's selection of this frozen contract; storage/audit and
engine integration are separate bounded implementation assignments.

The current production `UnavailableClock`, `UnavailableProvider` and object
verifier remain unavailable. No qualified clock, clock freshness source, provider
adapter, ingress framing/EOF guarantee or nonrollbackable restore authority is
invented by this design. A restore of either registry or operation namespace can
erase history; their mutual agreement cannot prove history never rolled back.
Keep affected identities quarantined until an independently retained authority
watermark/tombstone/consumed-claim record and external-effect reconciliation are
qualified. There is no automatic restore, namespace replacement or two-active-
namespace mode.

After a local implementation passes, keep these exact deployed gates open:
actual configured Cron-to-Worker-to-audit-to-shard-to-operation delivery with no
customer HTTP; measured missed-alarm/retry-exhaustion recovery latency and outage
behavior; actual whole-domain allocation/task/storage/resource ceilings and
retention accounting; namespace/deployment/PITR/rollback fences; production
bounded-error clock and ingress; authenticated runner/source/private-R2/result
authority; real Linux/macOS provider provisioning, image pins, sandbox isolation,
one-shot runner and descendant/ticket disposal. Independent Phoenix/Oban
zero-traffic wake, Neon recovery, signing, OTA distribution, stores, FieldLog
immutable-package dogfood, final physical-phone acceptance, accountable review
and every relevant GA gate remain separate and pending.
