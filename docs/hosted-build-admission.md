# Durable internal build admission and coordinator leases

`MixerHosted.Builds.Admission` supplies a shared PostgreSQL capacity boundary
requiring fleet-total, fleet-platform, organization-total and organization/platform
limits for each fresh reservation. Projects and applications share the applicable
limits. Fleet iOS and Android pool rows are distinct, and both also consume the
fleet-total limit. See [the aggregate admission contract](hosted-build-aggregate-admission.md)
for configuration, migration/upgrade, transaction isolation and current evidence.

Capacity must be explicitly configured internally with a limit from 0 through
10,000. Zero pauses new admission. Configuration creates revision 0 using `:new`;
subsequent changes require an exact revision. Lowering the limit below current
occupancy succeeds without eviction. Existing reservations can still reconcile;
new attempts wait until held occupancy is below the new limit.

The original admission migration adds three retained tables:

| Table | Identity and retained data |
| --- | --- |
| `mixer_build_capacities` | Organization/platform primary key, limit, revision |
| `mixer_build_reservations` | Build record primary key, organization/platform, admitted attempt and worker fence, held flag, release evidence event ID |
| `mixer_build_coordinator_leases` | Build record primary key, coordinator owner ID, monotonic lease epoch, database-derived expiry |

Composite foreign keys bind each reservation to its exact build and capacity
scope. Reservation and lease rows survive release. A lease epoch never resets
when a build retries, and exhaustion fails closed. The coordinator epoch is
independent of the lifecycle worker fence: transferring coordination neither
changes the worker reference nor proves the external worker has stopped.
The additive aggregate migration adds three closed policy tables and a platform
held-reservation index without changing those existing worker/reservation rows.

The internal Multi builders are:

- `configure_multi(multi, name, %{organization_id: id, platform: :ios | :android},
  :new | expected_revision, limit)` returns the capacity struct.
- `configure_fleet_multi(multi, name, :new | expected_revision, limit)` configures
  the shared fleet total.
- `configure_fleet_platform_multi(multi, name, %{platform: :ios | :android},
  :new | expected_revision, limit)` configures a fleet pool.
- `configure_organization_multi(multi, name, %{organization_id: id},
  :new | expected_revision, limit)` configures the organization total.
- `claim_multi(multi, name, full_scope, owner_id, ttl_ms)` reserves a queued
  attempt and claims coordination. TTL is explicitly bounded to 1–300,000 ms;
  owner IDs are bounded printable text.
- `renew_multi(multi, name, token, ttl_ms)` renews an exactly matching live lease.
- `transition_multi(multi, name, token, revision, event_id, event, job_factory)`
  guards start, cancel, expire, completed and stopped events, then composes
  `Storage.transition_multi` and its atomic Oban job insertion.
- `release_multi(multi, name, token, terminal_event_id)` releases only after the
  exact replayed current attempt has sufficient terminal evidence.

Claim/renew/release return `%{record: record, build: build, reservation: row,
lease: row, now_ms: database_time, outcome: outcome, token: token}` at `name`.
Release returns a nil token. A live token is an `Admission.Token` containing
exact full scope, record UUID, attempt, owner ID and epoch. These fields are
internal reconciliation data, never tenant authorization, worker identity,
source access, dispatch permission or a secret bearer credential. Transition
returns the existing Storage result at `name`, its Oban row at `{name, :job}` and
the admission guard context at `{name, :admission}`.

Every operation/configuration fragment requires `READ COMMITTED`, takes the fixed
PostgreSQL transaction advisory mutex `(1296648258, 1)`, and locks applicable
fleet-total, fleet-platform, organization-total and organization/platform rows
before the exact full-scope build, reservation and coordinator lease. Fresh held
reservations are counted at all four levels under that shared transaction, so
multiple replicas cannot admit the final slot simultaneously. Missing aggregate
rows fail closed for fresh claims; held reconciliation and release skip fresh
capacity eligibility. No in-process counter, node ownership assumption or Oban
per-node concurrency substitutes for that transaction. Callers must take the
mutex before raw locks or Storage fragments that lock existing builds. Multiple
Admission/configuration fragments may compose under the retained mutex. A claim
can compose a later guarded transition using `Multi.merge` and its returned token.
CAS failure, job factory rejection, insertion failure or a later Multi failure
rolls back all configuration, reservation, lease, lifecycle and job changes.

PostgreSQL `clock_timestamp()` is sampled after the complete lock sequence.
Transaction-start `now()` and caller clocks are not accepted. Leases are live
only while database time is strictly before expiry. A same-owner live claim is
idempotent and does not extend the lease; renewal is explicit. Expired reclaim
always increments the epoch, even for the same owner. Other live owners and all
stale tokens fail. A held reservation may be reclaimed for reconciliation while
running, cancelling, reconciling or terminal; its occupancy is retained throughout.

A capacity claim alone cannot dispatch work. A trusted future coordinator must
persist a guarded lifecycle start before external dispatch. This permits release
of a conclusively never-started queued cancellation: the exact current attempt's
replayed history has no worker reference, start time or deadline, and its matching
cancel event caused the terminal state. Once started, cancellation and expiry
retain occupancy until replayed `completed` or `stopped` evidence matches the
admitted attempt and original worker fence. Lease expiry, cancellation requests,
terminal status snapshots and historical completion events are insufficient.
Indexed/journal disagreement and malformed or inconsistent reservation state
fail closed.

Guarded retry is rejected while a reservation is held. After definitive release,
`retry_multi` rechecks the current revision, released evidence and cleared owner
under the admission lock order, then composes Storage's bounded retry transition
with current database time. The retained release event is checked against replayed
history before readmission. Historical tokens and terminal events cannot release
the new attempt. `yield_multi` expires only the coordination lease, retaining
worker occupancy and its fence. The internal Coordinator uses these contracts;
Storage remains independently callable and no external dispatch adapter is configured.

The original producer database tests use the dedicated disposable `mixer_admission_test` database,
real row-lock contention and direct-SQL fixture expiry. They cover last-slot
races, scope isolation, capacity shrink, expiry and ownership transfer, guarded
mutations with atomic rollback, cancellation/timeout uncertainty, terminal
reconciliation, release/retry, epoch exhaustion and corrupted state. Root's
collector owns database creation, execution receipts and cleanup. Source compile
checks are not database or external-worker receipts.

Public build authorization, membership-aware RLS, authenticated workers, provider
execution, production dispatch, queue estimates, billing attribution, provider
capacity measurement, operational failure qualification and GA remain pending. No
router, credential, customer message, release authority or frozen catalog code is
changed. No Patch/Skip implementation or new dependency is introduced.
