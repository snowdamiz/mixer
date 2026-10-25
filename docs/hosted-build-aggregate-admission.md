# Transactional aggregate build admission

`MixerHosted.Builds.Admission` requires four explicit limits before creating a
fresh held reservation: fleet total, fleet platform pool, organization total,
and the existing organization/platform limit. Fleet iOS and Android rows bound
their distinct pools, while the fleet total spans both. Organization total spans
all that organization's projects, applications and platforms. The database
counts retained `Reservation.held = true` rows, regardless of journal state,
lease age, owning coordinator or replica. Uncertain external work still counts.

These are production Ecto/PostgreSQL enforcement paths used by the existing
coordinator. A test scheduler, node-local Oban concurrency or mutable occupancy
counter does not supply the limit. Every admitted attempt adds one reservation
row (or reuses its definitively released predecessor); reclaim and renewal never
add occupancy. Definitive release changes the exact retained reservation to
`held = false`. Capacity enforcement does not qualify an external provider.

## Configuration contract

The trusted internal Multi builders are:

```elixir
Admission.configure_fleet_multi(multi, name, :new, limit)
Admission.configure_fleet_platform_multi(multi, name, %{platform: :ios}, :new, limit)
Admission.configure_organization_multi(multi, name, %{organization_id: "org"}, :new, limit)
Admission.configure_multi(multi, name, %{organization_id: "org", platform: :ios}, :new, limit)
```

Each `:new` can instead be an exact expected integer revision for an update.
Platform is exactly `:ios` or `:android`, and each scope map accepts exactly the
displayed keys. The limit is an integer from 0 through 10,000. Organization IDs
follow the existing bounded printable-text rule. A first configuration returns
revision 0; subsequent updates require the current revision and increment it
once. Revision overflow fails closed. Repeated `:new` fails with
`:capacity_exists`; an unknown/unconfigured row cannot be activated through an
integer CAS. Existing organization/platform configuration behavior and errors
are retained.

The additive migration creates three tables:

| Table | Identity | Initial state |
| --- | --- | --- |
| `mixer_build_fleet_capacity` | Singleton `id = 'fleet'` | One closed placeholder |
| `mixer_build_fleet_platform_capacities` | `platform = 'ios'` or `'android'` | Two closed placeholders |
| `mixer_build_organization_capacities` | Bounded `organization_id` | Closed placeholder for each existing organization/platform capacity's organization |

Each aggregate table has database defaults `limit = 0`, `revision = 0`, and
`configured = false`. Check constraints enforce the identity, bounded limit,
nonnegative bigint revision, and zero limit/revision for unconfigured rows.
`:new` activates an unconfigured placeholder exactly once, or creates a missing
row explicitly. No missing or unconfigured row becomes unlimited. An additive
partial index on held reservations by platform supports the fleet-pool count;
the existing organization/platform held index supports organization counts too.
There are no aggregate foreign keys whose absence could strand an old worker.

Claims report `:fleet_capacity_unconfigured`,
`:fleet_platform_capacity_unconfigured`, or
`:organization_capacity_unconfigured` for missing/unconfigured aggregate policy.
An exhausted explicit limit reports `:fleet_capacity_exhausted`,
`:fleet_platform_capacity_exhausted`, or `:organization_capacity_exhausted`.
Existing pair and full-scope errors remain unchanged. The coordinator treats
admission errors as bounded snoozes and requires no Dispatch contract change.

## Lock and composition contract

Every Admission/configuration fragment requires PostgreSQL `READ COMMITTED` and
first takes the fixed two-int transaction advisory mutex `(1296648258, 1)`.
That namespace is reserved for Mixer build admission in this database; unrelated
features must not reuse it. Other isolation settings fail closed with
`:unsupported_admission_isolation`. A repeatable-read snapshot taken before a
mutex wait could otherwise miss the previous holder's committed reservations.

While holding the mutex, each fragment locks existing rows in this order:

1. Fleet-total row.
2. Applicable fleet-platform row.
3. Applicable organization-total row.
4. Applicable organization/platform row.
5. Exact full-scope build, reservation and coordinator lease.

Configuration takes the applicable scopes only; lifecycle operations take the
complete applicable sequence. The mutex exists even when every configuration
row is absent. A first configuration, deletion/recreation fixture, or concurrent
claim therefore cannot race through a missing parent. After all row locks,
PostgreSQL `clock_timestamp()` supplies the lease/lifecycle time. Fresh admission
checks all four limits and counts held rows inside that same transaction before
persisting any reservation. Caller time and transaction-start `now()` are never
lease authority.

Multiple Admission/configuration fragments may compose in one Multi, including
configuration after a claim or release and operations for different scopes.
The shared exclusive mutex is reentrant and retained through the entire
transaction, so another compliant transaction cannot hold lower locks first.
Neither raw locks on these tables nor Storage fragments that lock existing build
records may precede the first Admission fragment. Callers must keep the mutex
for the whole composition, and must not acquire it after locking a build through
another path. Public Storage APIs remain independently callable, but bypassing
Admission is not permission to dispatch a worker or consume fleet capacity.

This initial implementation serializes admission activity fleet-wide in one
PostgreSQL database. That is an explicit correctness/performance tradeoff, not a
measured throughput or fairness claim. No multi-database fleet, provider-region
partition, queue-position estimate, billing entitlement or production capacity
measurement is qualified here. Replacing the mutex with a more concurrent lock
protocol requires separate contention, missing-row and composition qualification.

## Upgrade, uncertainty and rollback

The migration never rewrites existing build, reservation, worker fence or lease
rows. Closed aggregate defaults pause new admission until operators explicitly
configure every applicable limit. Existing held attempts can still claim,
reclaim, renew, yield, transition and definitively release when any aggregate
policy is missing, unconfigured, zero, or lower than occupancy. Released retries
remain journal/evidence guarded; readmitting the retry requires capacity anew.
Reclaim keeps the original WorkerRef and increases only the coordinator epoch.

Lowering a limit does not evict or release a worker. Cancellation, deadline
expiry, absent provider observations, a coordinator crash and lease expiry do
not decrement occupancy. No age-out or force-release API is added. Definitive
termination still requires the existing replayed current-attempt evidence and
original worker fence; a never-started queued cancellation retains its existing
special proof. Stale coordinators cannot mutate or free a replacement's slot.

An upgrade must replace or stop every old admission writer before relying on
aggregate enforcement: older binaries do not take the new mutex or check these
limits. Applying this migration alone does not retrofit those binaries. This
slice does not run a production migration or perform that rollout. Local
down/up tests remove only the new tables/index, recreate closed policy, and
prove existing held journal/reservation/lease bytes remain unchanged; that is
disposable-database migration evidence, not an authorized production rollback.

Configuration, capacity checks, lease mutations, lifecycle CAS and Oban insertion
participate in the same caller transaction. A rejected configuration revision,
invalid job factory, failed insertion, or later Multi failure rolls all changes
back. Counts come from reservations, so no separate aggregate counter can leak
or double-decrement on rollback.

## Evidence boundary

`hosted/test/mixer_hosted/builds/aggregate_admission_test.exs` uses the dedicated
`mixer_aggregate_admission_test` PostgreSQL database. It exercises competing
last-slot transactions across organizations and platforms, explicit closed
policy, bounded CAS and database constraints, first configuration and missing
parents, opposite Multi fragment orders, clock advancement during lock waits,
all-limit rollback, uncertainty/reclaim/release, and migration down/up with an
existing worker. Current producer admission/coordinator fixtures explicitly
configure aggregate limits. Frozen earlier review sources remain immutable and
retain their original scope; they need separate requalification with new policy.

`verification/hosted-build-aggregate-admission/diagnose.py` records targeted
producer commands, pinned versions, exact hosted input hashes/source archive,
output and owned PostgreSQL cleanup. `diagnostic-3/receipt.json` records 71 passed
producer build tests (20 aggregate, 17 prior admission, 19 coordinator and 15
storage), with the owned PostgreSQL instance stopped and scratch removed.
Earlier diagnostics retain a corrected assertion failure and an unused optional
argument warning; they do not qualify the final source. Root's full collector
and independent review remain separate evidence. No Neon/cloud rollout, worker
authentication, provider execution, hostile-code isolation, signing, public
authorization, physical/native device run, operational failover or GA gate is
accepted by this local slice.
