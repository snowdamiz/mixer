# Isolated SQLite pending-registry and audit components

This packet implements the first component slice selected in
[the root receipt](../verification/hosted-worker-pending-registry-root-selection/selection.json)
against contract SHA-256 `5d7ede675cdc83f1a7c000a8bfebf05418e8afe8f99e2c131f22ce52d1f4413a`
and public interface SHA-256 `7bcabae139b5405cfe3856761febb2db69793a9a7cbebba7923a463bfaec2c88`.
The candidate is isolated under
[`verification/hosted-worker-pending-registry-components/candidate/`](../verification/hosted-worker-pending-registry-components/candidate/).
No live controller, root tracker, dependency, deployment, schedule or credential
was changed. Root owns integration and Git.

## Implemented behavior

`src/pending-registry.ts` exports `MixerPendingRegistryShard` and `RegistryPort`.
The shard extends the pinned runtime's actual SQLite Durable Object class.
Static parameterized SQL allocates permanent slots, preserves complete canonical
identity bytes, compares canonical int64 TEXT through `BigInt`, stores exact
canonical projection bytes, fences stale/equal-conflicting tracks and prevents
terminal reactivation. `scan_due` uses two bounded indexed iterators and never
mutates delivery state. Only `reserve_wake` decrements visit backoff; monotonic
run IDs suppress repeated/old visits. Exact ticket/version/receipt CAS protects
completion. Successful recovery updates delivery metadata only: terminal tracking
is the sole transition that makes a record quiescent.

`src/pending-audit.ts` exports `MixerPendingAuditCoordinator`. Its SQLite meta
row retains the run token, next shard, sixteen allocation cursors and one current
receipt. Thirty-two summary slots bound historical detail. A live unresolved
run/recovery slot rejects concurrent invocations. Before each remote wait the
coordinator commits the appropriate cursor/checkpoint; interrupted receipts
survive actual process death. Eight wake starts, sixteen pages, 512 examinations,
32 records/page, 65,536 encoded bytes/page and the shared 24,000 ms elapsed budget
are enforced before starting additional work. Page/reserve/finish calls wait at
most 250 ms; recovery waits at most 2,500 ms while reserving finish allowance.
Timeout means unknown outcome. A noncooperative recovery retains the live slot
until its real settlement is observed; no late reply bypasses ticket CAS.

The additive [completion-retention contract](hosted-worker-pending-registry-completion-contract.md)
was selected in amendment SHA-256
`67db5a40f4433699203475d046528600d5939785b0b803b68151febff182e576`.
The coordinator retains sixteen nullable completion slots, each at most 2,048
encoded bytes and permanently assigned to one shard. Actual late settlement first
retains the exact ticket/disposition in bounded memory, then makes one synchronous
SQLite CAS write; rejection is retained as `unavailable`. There is no callback
RPC, timer, retry or await. A failed write retains the memory value; the next
invocation persists it and establishes durability before remote completion.
Process death before durable retention leaves the original reservation unknown.

During circular traversal the coordinator checkpoints shard rotation before
attempting an occupied slot's exact `finish_wake` once, within the existing
250 ms/shared 24-second budget. Accepted/stale completion permits exact CAS clear.
Unknown/unavailable completion retains its slot and blocks new wakes only for
that shard; healthy shards keep progressing. Known ordinary dispositions use
the same slot when their finish acknowledgement is unknown. Local coordinator
write/clear failure stops that invocation; storage progress is required before
new recovery. Old tickets cannot clear newer completion slots or replace newer
track/terminal state.

`src/pending-types.ts` contains private closed validators, fixed namespace naming,
standard Web Crypto hashes/random 128-bit IDs and caller wait bounds.
`src/public-contract.ts` is an exact type-only copy of the selected sealed file.
The private config is explicit:

```json
{"generation":"<lowercase hex64>","operationsNamespace":"<ASCII identity>","registryNamespace":"<ASCII identity>"}
```

It is supplied as `MIXER_PENDING_CONFIG` with bindings `PENDING_REGISTRY`,
`PENDING_AUDIT` and `OPERATIONS`. Exactly sixteen versioned registry names and
one versioned audit name can initialize valid storage. The full normalized
configuration is retained in each SQLite schema row. Missing/conflicting config,
unknown schema or an object outside its fixed name is unavailable. Configuration
is an identity fence; agreement does not prove storage has never rolled back.

The production candidate imports neither the excluded fixture nor the existing
engine/provider/clock. It adds no dependency. Its SQL asset is
`src/registry-schema.sql`; the coordinator uses static internal schema SQL.
On integration the existing build must additionally copy `registry-schema.sql`
alongside `schema.sql`. `candidate/build.mjs` demonstrates the asset-copy wiring
without modifying the live build.

## Local verification and reproduction

Run from the repository root:

```sh
node verification/hosted-worker-pending-registry-components/candidate/check.mjs
```

The runner uses the existing pinned controller dependencies. It builds the
candidate, runs the current twenty owned-process identity controls, and runs
seventeen actual cross-DO workerd/SQLite component groups. Its unique run directory
contains exact argv/cwd, tool versions, source revision/digest and source copies,
stdout/stderr hashes, EOF/process-group evidence, compiled manifest, runtime
observations, and owned process/storage cleanup receipts. `latest-run.json`
identifies the current receipt. No physical devices, cloud service, enabled
provider, external credentials or customer messages are involved.

Observed component boundaries include all 17 independent canonical vectors/all 16
shards; permanent 4,096/4,097 capacity; version ordering above 2^53 and int64 overflow;
registration/track/terminal lost ACK and real SIGKILL; permanent terminal retention;
pure scans/reservation-only backoff and dedup; stale tickets; 528 pending records
across 16 shards using 80 actual excluded scheduled events; ninth wake retention;
512 examinations/sixteen pages; automatic attention revisits; noncooperative
recovery timeout/live busy/later observed settlement; storage-call ACK timeouts;
late unavailable/rejected outcomes through attention; actual completion-write/clear
SQLite aborts and exact retry; unavailable-completion shard backpressure with
healthy-shard progress and newer terminal fencing; shard outage progression;
and elapsed invocation bounds that include delayed
registry calls. Timeout is never counted as cancellation or successful delivery.

Maximum legal closed ASCII principals include escaped quotes/backslashes. Their
32-record encoded page is below65536 bytes, so byte-cap truncation before 32 rows
is unreachable under the selected interface. The implementation enforces the
byte check, and the runtime test asserts the legal maximum page size. This does
not widen identity fields or claim the unreachable truncation branch was tested.
The first attention test underestimated visits needed by exponential backoff;
its failed report is preserved under `failures/`, then corrected to cross the
eighth failure without weakening the retry/backoff rules. The original 14-group passing receipt
is historical: root review then found that known late failures were discarded.
The completion amendment and additional regression controls repair that gap;
the outdated no-late-completion assertion and all subsequent failed receipts
remain preserved with source/tool/output bindings.

## Explicit remaining work

The excluded `FixtureRecovery` is a bounded SQLite call-history adapter. It has
no `Engine`, command, claim, guard, provider action or real operation row. Its
`empty_orphan`/pending responses establish registry/audit delivery behavior only.
The complete thirty-case acceptance contract is not passed by this slice;
[`acceptance-coverage.json`](../verification/hosted-worker-pending-registry-components/acceptance-coverage.json)
records every case and its engine-dependent remainder.

The next slice must implement real authenticated pre-registration before initial
operation mutation; schema3 receipt/outbox/ACK and exact effect/claim barriers;
terminal local-byte digest handling; identity-only actual `recoverKnown` and
missing/regressed-ledger quarantine; durable-stop outage enforcement; legacy
migration/enrollment; and production scheduled/index entry/export wiring. It
must keep the existing 20 identity controls and 71 controller runtime groups green
and qualify the actual three-class integration through real SQLite/restart/fault
histories. No registry receipt, projection or ticket grants engine authority.

Deployed Cron delivery, real providers/clock/ingress/restore authority, whole-domain
resource ceilings and retention accounting, Linux/macOS workers, runner sandbox,
Phoenix/Oban/Neon, signing/stores/FieldLog, final physical-phone acceptance,
accountable review and GA remain pending. This packet neither changes nor
qualifies those gates.

The accepted fresh local component run is
[`runs/20261025T042823425Z/receipt.json`](../verification/hosted-worker-pending-registry-components/runs/20261025T042823425Z/receipt.json):
17 runtime groups, 20 process identity controls, 17 disposed owned storage
directories and 14 identity-checked SIGKILL boundaries. Its runtime source digest
is `4b5df151a39ac703ef76705cf7d6d7a6c10ac69f4a2c5e6f2a33f2f1e6dd0078`.
The maximum legal encoded page measured 44,211 bytes. The shared elapsed-budget
run examined 95 records across three pages in 21,116.872 ms with 220 ms registry
waits and zero recovery starts. Static TypeScript AST closure contains four
component modules/assets and only `cloudflare:workers` as an external import;
this is a build-closure check, never an OTA authorization gate.
