# Internal durable build execution coordinator

`MixerHosted.Builds.Coordinator` is an actual production Oban worker for the
`builds` queue. It coordinates existing replayed journals, retained admission
reservations and coordinator leases. It does not run customer scripts. Dispatch
requires a trusted, explicitly configured adapter; the application config and
runtime currently install none. No public route or worker authentication surface
is added, and no external worker or provider is executed by this slice.

## Intent and transaction boundary

`Coordinator.new(intent)` is the Storage job factory. The worker accepts exactly
the existing ten-key Storage intent, with bounded identifiers, revision, attempt,
worker fence, platform and event kind. It reads the full scoped journal and
compares record identity, revision, attempt, fence and the actual latest journal
event kind. Superseded intents return successfully without dispatch. An older
creation job is therefore not a capability to start the current attempt. A
forged kind with otherwise current numeric fields is also ineffective.

Queued reconciliation takes Admission's transaction advisory mutex, then fleet →
platform → organization → organization/platform → build → reservation → lease
locks. Only READ COMMITTED transactions are admitted; a prior repeatable-read
snapshot could miss reservations committed during a mutex wait. Fresh claims
require configured limits at all four levels, while held work remains eligible
for reconciliation after a limit is reduced or disabled. The coordinator samples
PostgreSQL time after those locks, reserves capacity, persists the
guarded lifecycle start, and inserts its successor Coordinator job atomically.
Only that committed start intent can reach the adapter. Failure in its Oban
insert, admission guard, revision CAS or later Multi step rolls back the entire
transaction. External callbacks occur after commit and outside SQL transactions.

`Admission.yield_multi(multi, name, token)` applies the same live-token guard and
sets lease expiry to the sampled database time, retaining owner, epoch and held
reservation. It returns a nil token. Start and expiry transitions include yield
atomically so the successor job can immediately reclaim at a larger epoch.
Finished local callback paths also yield before snoozing. An interrupted
coordinator which cannot yield retains the ordinary lease expiry boundary.
Yield is never capacity release or evidence of worker termination.

## External operation contract

`MixerHosted.Builds.Dispatch` defines `query(request)`,
`ensure_started(request)` and `stop(request)`. Each receives a `Dispatch.Request`
with these fields:

| Field | Meaning |
| --- | --- |
| `operation_id` | SHA-256 of a versioned JSON array containing record UUID and the exact original WorkerRef |
| `ref` | Original full-scope WorkerRef, including attempt and worker fence |
| `spec` | Immutable source/build/toolchain inputs reconstructed from the journal |
| `deadline_ms` | Persisted deadline of that attempt |
| `guard` | Record ID, current journal revision, coordinator owner, lease epoch and expiry |

The stable operation ID and original worker fence survive every coordinator
transfer. The coordinator epoch is separate and increases when coordination is
reclaimed. Scope, operation IDs and lease fields are internal data, not tenant
authorization, worker authentication or secret bearer credentials.

An adapter returns `{:ok, %Dispatch.Observation{operation_id: id, ref: ref,
status: status}}`, where status is `:absent`, `:running`, `{:completed, result}`
or `{:stopped, diagnostic_sha256}`. The coordinator validates exact operation/ref
binding, then the existing Lifecycle/Journal validates terminal result shape,
classification and artifacts. Errors are `{:error, :unavailable | :uncertain |
:stale}`. Other values, wrong binding, raised callbacks, process exits and local
timeouts retain capacity and cause reconciliation to snooze.

The provider implementation must durably enforce all of the following:

- Bind an operation to its immutable original ref, spec and deadline.
- Idempotent ensure/query/stop for the complete operation retention period;
  replaying ensure can never create a second execution or a second charge.
- Reject expired requests and stale lexicographic `{epoch, revision}` ordering.
  A SQL check alone cannot prevent an already in-flight external request.
- A definitive stop installs a terminal tombstone, including for an operation
  not yet observed. A delayed ensure can never reopen a terminal identity.
- Authenticate and authorize worker communication independently, retain terminal
  evidence, and isolate customer code outside the control-plane BEAM process.

These are explicit requirements for a future adapter. The test registry models
them and is excluded from production compilation; its behavior does not qualify
a real provider, isolation system, source authorization or worker authentication.
No exactly-once property is assumed from Oban.

## Cancellation, expiry and retry

Each invocation makes at most one query and one ensure/stop callback, each in a
monitored child with a bounded timeout. A running query snoozes without another
ensure. Cancellation and deadline expiry preserve the active original WorkerRef.
Expiry is persisted with another atomic intent before a stop request. The worker
rechecks its lease, current intent and database deadline between callbacks.
An `:absent` query proves no terminal state and cannot release capacity; a stop
tombstone or definitive completion is still required. Callback uncertainty may
retain occupancy indefinitely until definitive evidence or operational repair;
there is no unsafe age-based release.

Definitive observations pass through Admission's live-token guard and the
Lifecycle CAS transition, insert the new Coordinator intent, and release the
exact attempt using that exact terminal event ID in one transaction. A response
which arrives after ownership transfer cannot mutate or release the new owner.
A conclusively never-started queued cancellation can use Admission's existing
special terminal evidence rule.

`Admission.retry_multi(multi, name, full_scope, revision, event_id, factory)`
replays under the same lock order and requires the exact current terminal attempt,
held=false, retained replayed release evidence and cleared lease ownership. It
then composes Storage's retry transition at fresh database time. Backoff,
infrastructure classification and finite attempt limits remain Lifecycle
decisions. Compiler/test/policy failures are not automatically retried. Retry
domain state and job insertion roll back together; an old attempt's job or
release event cannot dispatch or release its replacement.

## Configuration and qualification boundary

An internal deployment must explicitly set this exact application config:

```elixir
config :mixer_hosted, :build_dispatch,
  adapter: AQualifiedTrustedAdapter,
  lease_ttl_ms: 30_000,
  call_timeout_ms: 1_000,
  poll_ms: 1_000
```

This example names no existing adapter. The callback module must export the three
contract functions; config accepts no additional or duplicate fields. Callback
timeout is 1–10,000 ms, lease TTL 1–300,000 ms and at least three callback
timeouts, and polling 1–60,000 ms. Oban snooze rounds up to whole seconds. The
default returns `:dispatch_unavailable` before admission. Explicit config remains
trusted internal deployment data, with no HTTP input or environment string to
module conversion.

Producer integration tests use the dedicated `mixer_coordinator_test` database
and `MixerHosted.Test.BuildDispatchFixture` under `test/support`. Root's collector
owns PostgreSQL creation, execution and cleanup receipts. Tests cover committed
start visibility, crash/timeout after modeled effect, epoch transfer, stale jobs
and provider requests, permanent stop tombstones, held uncertain reservations,
deadline/cancellation, classified bounded retry, backoff, release evidence and
atomic insertion/later-Multi rollback. Independent tests use their own adapter.

This is local loopback PostgreSQL and modeled external-effect evidence. Neon,
Cloudflare wake/liveness, production provider execution, authenticated worker
results, hostile-code isolation, signing, billing attribution, queue estimates,
operational restore/failover, public API authorization and GA remain pending.
No frozen catalog/authority code or new dependency is used.
