# Ordinary KeyOwner supervised lifecycle contract

A small code correction is warranted for graceful supervised shutdown. The dead
ETS pointer is already fail closed; it is not stale authentication authority.
It is an observable cleanup defect when a normal supervisor shutdown bypasses
KeyOwner.terminate/2. Candidate 4 retained exactly this defect and failed its
terminal suite. Candidate 6 qualifies explicit normal fixture stop only.

## Current source and evidence

KeyOwner.initialize/2 publishes an ETS table created by its own PID into
persistent_term but never enables trap_exit. Its child shutdown is infinity.
Its terminate/2 erases the name-only pointer, replies identity_unavailable to
waiters, then synchronously terminates each owned FetchFlight. Admission.acquire/2
rescues dead-table ArgumentError into identity_unavailable; release/1 treats a
dead table as already released. The ETS table has no heir and dies with its owner.
The four identity module bytes match both retained candidates 4 and 6.

KeyOwnerSupervisor starts the DynamicSupervisor first and KeyOwner second under
one_for_all. Graceful component shutdown therefore stops the owner while the
worker supervisor is still alive. Replacement starts after old siblings stop.
Each owner starts with a new table, epoch, and empty caches. Old permits fail the
new table-identity check before ETS lookup; old leases cannot finish against the
new epoch. FetchFlight already traps exits and waits for owned raw-port,
connection, and worker DOWN before normal termination completes.

These are source conclusions and retained historical observations. This packet
runs no new Elixir or native checks. Existing startup lifecycle assertions test
public denial and empty restart; they do not assert persistent_term absence.

## Existing test contracts to reuse

- KeyOwnerTest K07g (834-864) explicitly calls
  GenServer.stop(pid, :normal, :infinity), then proves suspended TLS-controller
  cleanup ordering. It exercises the callback path that already works; it does
  not exercise a parent-supervisor exit.
- K07h (866-943) kills the fixture owner under ComponentFixture one_for_all and
  proves replacement waits for old controllers/workers/raw ports. It exercises
  forced owner death with real transport and a fixture constructor, rather than
  ordinary KeyOwnerSupervisor graceful shutdown.
- StartupLifecycleTest IS05 (158-194) starts the actual application, kills the
  owner, checks empty replacement, then stops/restarts the application. It
  asserts registrations and public denial but neither pointer absence nor an
  active-flight resource-drain matrix.

Reuse these exact assertions/support for KOL08; add the missing ordinary parent
shutdown assertion and Admission pointer checks instead of duplicating a broad
identity or dispatcher suite. KOL09 isolates worker-supervisor death with active
flights, which is a different ordering hazard.

## Exact prospective behavior

1. For the ordinary locally registered atom owner managed by
   KeyOwnerSupervisor, successful initialization enables trap_exit before
   publishing Admission state. The shared initializer covers ordinary and
   existing test-fixture construction. Invalid configuration publishes no table.
2. A graceful parent shutdown or Supervisor.terminate_child for KeyOwner invokes
   its existing terminate path. Once that path closes admission, new acquire and
   authenticate calls return {:error, :identity_unavailable}. Queued callers also
   return that existing error. Calls that completed their final fence before
   shutdown may already have succeeded; shutdown is not retroactive revocation.
3. Admission.close(owner_name, expected_table) returns a boolean. It erases the
   persistent term only when its current value equals expected_table and that
   table's ETS owner is self(). Absent, mismatched, foreign-owned, or dead-table
   inputs return false without modifying the current pointer. KeyOwner passes
   s.name and s.table. Remove the unfenced close/1 internal entry point after its
   sole call site is migrated. Do not delete a foreign table or scan global terms.
4. Close admission before replying to waiters and draining owned flights. Keep
   the current synchronous cleanup and child ordering. A normal component stop
   completes with old owner/worker supervisor/flight PIDs gone, their owned raw
   sockets/controllers gone, the old ETS table gone, and its pointer absent.
5. Automatic one_for_all restart uses a new owner PID, worker supervisor PID,
   table and epoch with empty trust state. Old permits/leases remain rejected;
   late old-PID results cannot publish into the replacement. No fallback trusts
   an old snapshot during unavailability.
6. Untrappable kill/VM termination cannot promise terminate/2 or immediate
   persistent_term absence. With the VM still alive, a dead pointer may remain
   until same-name initialization replaces it. That interval must deny access.
   Keeping this bounded dead reference is acceptable crash-path behavior for this
   slice; no background eraser or crash-monitor publication system is selected.

## Ownership and restart limits

The close/2 check is defensive ownership validation, not an atomic compare-and-
erase primitive. persistent_term offers no compare-value erase. Its safety here
also depends on the existing ordinary lifecycle: one locally registered owner,
publication only in its initializer, cleanup only in that same PID before exit,
and supervisor restart after old PID death. There is no asynchronous name-only
cleanup that can run after replacement. Never add such a cleanup callback.

Do not claim support for concurrent arbitrary Admission.new calls, manual name
unregistration/reassignment, ETS ownership transfer, alternative registries, or
cross-node owners. Supporting those would need serialized publication/cleanup or
a different registry design and separate qualification. A mismatched-pointer
regression proves a no-op for an already installed replacement, not a general
concurrent CAS guarantee. Same-VM arbitrary code mutation is outside this API's
trust boundary.

Enabling trap_exit also changes handling of nonparent linked exits; KeyOwner
currently links only to its starter and monitors flights. Preserve parent OTP
shutdown behavior; do not add a catch-all EXIT clause that swallows parent exits.
A dead/unavailable worker supervisor can make terminate_child exit; test this
fault for public denial and safe restart before deciding whether any additional
cleanup handling is needed. Do not introduce broad exception swallowing.

The existing infinity shutdown and FetchFlight DOWN waits can stall when a TLS
controller is suspended or broken. Do not weaken resource-drain ordering or
invent a latency guarantee. The minimum correction and first socket-free tests qualify only Admission
cleanup, public denial, and restart fencing. They do not prove waiter completion
with active flights or real TLS/resource teardown. Those remain separate pending
runtime gates, including worker-supervisor death while flights are active. Direct production provider, application/HTTP integration,
Neon/Cloudflare operation, custody, browser/session authority, and GA remain
outside this contract.

## Selected next implementation boundary

Coordinate ownership of only hosted/lib/mixer_hosted/identity/key_owner.ex and
admission.ex plus a dedicated identity lifecycle regression test file. Add the
shared trap_exit flag, migrate name-only close to guarded close/2, and author
KOL01-KOL07 from prospective-tests.json. No supervisor strategy, authentication,
transport, configuration schema, browser/session, database, workflow, or provider
change is selected. Review callback cleanup separately only if KOL07 exposes a
concrete defect. Keep KOL08-KOL09 resource/fault tests pending until root grants a
bounded exact host execution slot; this packet grants none.

First acceptance is a fresh exact isolated socket-free lifecycle test run with
terminal counts, warnings, revision/hashes and owned-process cleanup. It is not
met by source inspection or a rerun of the dispatcher packet. Root then decides
whether to schedule the existing real TLS cleanup cases and application startup
matrix. No product file was changed and no behavioral test was run here.
