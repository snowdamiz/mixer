# Isolated operation ledger and registry integration

This candidate implements the selected operation side of the durable pending
registry contract. It changes no live Worker entry, public wire format,
scheduled handler, deployment, provider, clock, business capacity or root
tracker. Root selects integration after independent source/runtime review.
The binding scope remains `mixer-product-plan.md`.

The implementation is in
`verification/hosted-worker-pending-registry-engine/candidate/src/`. Its baseline
is the live accepted V2 engine, ledger and schema copied into `inputs/live/`;
root supplied baseline revision `8b9b4950`. Exact source bytes, including the
fixed registry dependency and excluded test entry, are bound by each run's
source manifest. No Patch/Skip source, fixture or dependency is used. Existing
pinned TypeScript, Miniflare, workers types and workerd are reused.

## Private API selected with root

`Engine` retains its V2 clock/provider/verifier/hooks arguments and accepts an
optional final `RegistryContext { identity, registry }`. The identity is fixed
by the trusted operation binding, independent of the caller's requested
command. A missing context has an unavailable registry and cannot create a row,
launch, inspect, grant a claim or accept a result. An already durable stop can
still execute owned cleanup.

`commandRegistered(request, resourceIdentity, pendingIdentity, receipt)` is the
private command entry for later ingress integration. The caller must first
fully authenticate and validate the unchanged wire request and canonical
identity, then preregister before obtaining or initializing a new operation
DO. The engine independently validates the complete fixed identity tuple,
operation-key hash, identity digest, receipt fields, shard and request/resource
binding. Before its first operation-row mutation it validates the exact receipt
through the trusted registry port, awaits that result, then performs the normal
qualified clock, immutable binding and guard checks in the current transaction.
Registration cannot refresh an expired guard. A lost registration ACK leaves
only a permanent version-zero registry orphan.

Once retained locally, the same immutable registration serves later commands.
Those commands do not require a fresh registration RPC, including during a
registry registration outage. `command` cannot initialize a missing row and
remains an internal retained-registration path. No public HTTP or runner route
is added by this packet.

`recoverKnown(identity, receipt, ticket)` accepts identity and audit metadata
only. It does not accept a request, guard, source, provider URL or credential;
it never invokes command/claim, constructs a missing operation or clears
quarantine. A version-zero orphan returns `empty_orphan` without any row,
effect, lease or terminal evidence. Positive missing or regressed state, or a
full binding/receipt disagreement, persists a separate permanent bounded
quarantine fence. An older valid registry snapshot may reconcile the newer
current local row. Terminal digest work rechecks exact version, bytes, binding,
retained identity/receipt, quarantine and the independently stored fence after
its final await.

`enrollExisting(identity)` is trusted explicit maintenance for one known matching
existing row. It validates the binding, registers, retains the receipt and
writes a latest outbox. Missing returns `missing`. It does not enumerate a
namespace, reconstruct a row, clear migration/restore/clock quarantine, or
provide restore authority.

## Schema and delivery order

Schema 3 adds retained identity/registration JSON, an acknowledged version,
per-effect and per-claim barrier versions, and one coalesced exact latest track
outbox. A separate singleton quarantine table can fence a missing operation
without fabricating execution state. Missing or partial schema metadata over
surviving operation/audit/quarantine safety state fails closed, as does a
schema-3 database missing an expected safety table.

Schema-1/2 migration is synchronous and atomic. It preserves every existing
identity, authority, request, terminal/result byte, stop, consumed claim,
provider identity, dispatch marker, version and audit entry; it sets quarantine
without rewriting phase. Schema 2 preserves its exact clock floor. Schema 1
initializes its previously absent floor from the retained lower bound, then
quarantines. Explicit enrollment does not clear quarantine. Existing durable
stop cleanup remains available.

Every `Ledger.save` transition atomically replaces the sole outbox with its new
version and exact projection source. Terminal bytes stay local, bounded to
32 KiB, and are hashed with Web Crypto outside SQL. The engine rechecks exact
outbox version/bytes, receipt and terminal bytes immediately before `track`.
No SQL transaction spans a hash, RPC, hook, clock wait or provider await.

A successful accepted/duplicate ACK acknowledges only its exact sent version.
It cannot lower the watermark or erase a newer coalesced outbox. Delivery
metadata writes do not increment the operation version or enqueue themselves.
A registry watermark ahead of current local state or a conflicting track
quarantines; no registry response reconstructs authority.

Reconciliation flushes committed intent before preparing new run work, persists
the dispatch marker plus its exact barrier version, waits for that projection's
ACK and only then performs the V2 final identity/guard/qualified-clock check.
A failed dispatch track never resets `launch_dispatched`; recovery inspects the
same identity rather than launching again. Claim consumption similarly commits
its own barrier, waits for delivery and rechecks exact consumed authority and
identity with a final qualified clock sample. No await follows a granted claim's
final transaction. That final clock-only save may create a newer outbox than the
already satisfied barrier; it cannot change which effect/claim the ACK covers.
A newer command, stop, changed effect/claim identity, fence or quarantine wins.

A committed stop attempts delivery but may run owned cleanup when the registry
or qualified clock is unavailable. Terminal admission follows root's
[stop/terminal clarification](hosted-worker-pending-registry-stop-terminal-contract.md):
exact current resource/effect and desired stop, definitive absence with all
descendants gone and launches settled, retained matching registration, ACK
covering the exact stop effect barrier, and a valid monotonic qualified sample.
Quarantine/fences remain closed. A live run guard is not required, so expired
run authority cannot prevent cleanup completion after services recover. Without
these conditions the row remains stop-pending and obtains fresh proof on a
later bounded reconcile; cleanup alone does not declare drained or release
capacity.

Terminal commands flush their new terminal outbox within the command. An
outstanding terminal outbox keeps an operation alarm even when `next_due_us` is
null and the registry has already become quiescent. Thus a lost terminal ACK
can recover through an actual operation alarm or constructor restart without a
customer command or an audit record that has already quiesced. Each reconcile
still has at most one provider action; there is no retry loop. Platform time is
only a wake hint.

The selected corrected registry permits higher versions of the exact same
permanent terminal projection, updating only its watermark. This is required
when a terminal replay accepts newer guard/clock history. A pending projection
or changed terminal phase/digest cannot reopen or rewrite the terminal. The
before/after dependency hashes are in the packet's `dependency-selection.json`;
public interfaces and identity helpers are unchanged.

## Verification and boundaries

Run `node verification/hosted-worker-pending-registry-engine/candidate/check.mjs`.
The runner builds the candidate, snapshots/hashes all source, captures complete
stdout/stderr and exit/EOF state, and writes exact tool versions and test reports.
Each test uses actual workerd SQLite operation storage plus the fixed registry
DO binding. The provider, qualified clock, fault controls and resource identities
are explicitly finite excluded fixtures; there is no in-memory registry.

The suite covers preregistration and expiry, lost/out-of-order ACKs, a newer
command/stop during dispatch or claim delivery waits, final clock-only outboxes,
terminal byte hashing and post-await fence checks, actual alarm and restart ACK
recovery, missing/regressed/orphan identities, schema-1/2 migration and partial
schema rejection, and owned SIGKILL recovery of intent/consumed claims. Test
runtimes and storage are disposed after every test. SIGKILL targets use the
existing exact executable/direct-parent ownership verifier; other projects'
processes are preserved. Cleanup receipts include process absence and owned
storage removal. The initial failed fixture assertions and the reproduced
terminal-registry defect remain archived in `runs/`; they are not rewritten
as passes.

Public ingress, scheduled entry wiring, the independently reviewed audit
coordinator, production qualified time/provider/signing, deployed schedules,
capacity/restore operations, native/device qualification and GA acceptance are
outside this candidate. The existing 71 controller groups and 20 owned-process
controls remain prior V2 evidence, not claimed reruns of this changed engine.
No source publication or production action is implied by this packet.

The frozen producer run passed **32/32 groups**: `runs/20261025T044817457Z`
(source digest `1481d1484c319e282fea6c9e61e3f21a149b323d6a7d3681bd3da0c5814db3c1`).
It records five exact-owned SIGKILL controls, 32 disposed storage environments,
all observed owned PIDs absent, and complete build/test output EOF. The top-level
packet receipt binds the final review artifacts. Independent review is pending.
