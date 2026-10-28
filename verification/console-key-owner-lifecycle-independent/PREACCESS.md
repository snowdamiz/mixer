# Independent KeyOwner lifecycle expectations before producer access

Prepared from the accepted source contract and its preserved original inputs.
No modified canonical Admission/KeyOwner, new lifecycle suite, or implementation
packet was read before this document and its companion files were frozen.

The acceptance boundary is the ordinary atom-registered KeyOwner under the
actual KeyOwnerSupervisor, with serial publication and restart. The correction
is graceful cleanup of an observable dead pointer. The existing dead-table
acquire rescue already denies access; this is not evidence of stale successful
authentication. No CAS, arbitrary concurrent publisher, manual registration
transfer, cross-node, transferred ETS ownership, or alternative registry support
is expected.

## Required source behavior

1. Both ordinary and fixture initialization share the same trap_exit-before-
   Admission.new ordering. Invalid options stop with the existing configuration
   error and publish no table. A duplicate registered start never enters init.
2. Admission.close(owner, expected_table) returns true only when the exact current
   pointer equals expected_table, the table is alive, and its ETS owner equals
   the caller. All absent, mismatched, dead, and foreign-owned cases return false
   without changing the current pointer. It must not delete ETS tables, scan
   global persistent terms, retain an unfenced close/1, or schedule cleanup after
   process exit. It must tolerate arbitrary invalid expected-table values by
   returning false when no matching owned live table exists.
3. KeyOwner.terminate passes its stored name and table. Admission closes before
   waiter replies and synchronous flight draining. Existing child order,
   one_for_all strategy, infinity shutdown, and cleanup waits remain unchanged.
   Adding trap_exit must preserve OTP parent shutdown despite handle_info's
   ordinary catch-all. No blanket exception rescue or catch is justified.
4. Graceful stop and terminate_child remove the old pointer and ETS table.
   Forced kill may retain the dead old pointer until replacement; acquire and
   public authenticate must still return identity_unavailable. Replacement must
   use a new owner/table/epoch and empty caches. Old-PID messages must not create
   state. Old permit rejection must happen before dead ETS lookup.
5. Success already past its final fence is not retroactively revoked. A stale
   synthetic Lease is only a rejection oracle and carries no success claim.

## Required first-run test evidence

KOL01 must start the actual supervisor and stop its parent, without direct owner
stop or test erasure. It must retain old owner/worker/table identities and assert
both old processes and ETS are gone, exact pointer absence, and both public
denials. It should acquire/release a real Admission permit before stop.

KOL02 must use terminate_child/restart_child and prove workers stay alive during
owner-only stop, then new owner/table/epoch and empty state. A real old permit
must reject at checkout and finish, while stale release cannot delete a freshly
acquired replacement permit. Placeholder Lease fields must remain on the early
rejection path.

KOL03 must suspend only the owned supervisor with an unconditional resume in
after. After old owner DOWN, the test must observe the dead ETS and its preserved
pointer before resuming restart. Both public APIs must deny without exception.
Replacement must change both children/table/epoch, reject old state, and finish
with ordinary pointer cleanup.

KOL04 must separately cover same-creator mismatch, same-expected-table foreign
caller, absent pointer, dead expected table, malformed expected table where
applicable, exact creator success, and second-close false. Cases that publish a
current live table must assert it remains usable after rejected closes. A foreign
caller test cannot establish ownership merely by executing in the creator PID.

KOL05 must attempt ordinary same-name start and assert already_started with the
original PID, unchanged table/epoch, original ETS ownership, and final normal
cleanup. KOL06 must check invalid manifest, binding, and roots through ordinary
supervised startup, retaining failure output and proving exact owner/worker
registrations and pointer absent. Only exact failed-start owned processes may be
reaped.

KOL07 must kill only the actual owned DynamicSupervisor with no flights. It must
prove one_for_all replaces both old child PIDs, old ETS removal, empty new state,
new epoch/table, stale rejection, and final normal pointer removal. Any callback
exception is adverse evidence. This no-flight test cannot exercise the dead-
supervisor terminate_child call inside an iteration over tracked flights.

The suite must use valid original production-path configuration with the bound
profile disabled and actual Admission. A valid permit for a disabled profile
should yield unauthenticated while live; after stop it must yield
identity_unavailable. This distinction catches a test that never reaches the
owner or accidentally enables fetching. No success verifier, transport double,
fixture constructor, prefilled snapshot, provider, socket, DB, browser/session,
app endpoint, or network fixture belongs in this first boundary.

## Runner and acceptance conditions

Before execution, review all staged sources, dependency pins, compiler ordering,
source hashes, runner, exact commands, limits, output handling, terminal result
counts, failure classification, and cleanup. Any original-before-image experiment
must run in its own fresh isolated VM, fail a relevant lifecycle assertion, and
retain its failure details; unrelated compile/startup failure is not a regression
demonstration. A corrected run must be separate and succeed without suppressed
warnings or callback faults. The intended host bound is at most 55 seconds and
no unreleased compilation/runtime may be invoked while another lane holds it.

Cleanup must cover both success and failed assertions: resume any suspended owned
supervisor, retire only exact owned children/components, assert registrations
absent and exact ETS removal, and retain exact relevant admission-key state.
Do not erase the very key whose absence is under test before observing it. A
test cleanup erase can only follow a retained failure and must not turn cleanup
or terminal assertions green. No broad process inventory or process kill is
needed or authorized.

KOL08 real TLS drain, KOL09 active-flight worker-supervisor death, actual app and
HTTP/browser/session integration, production provider, custody, operations,
physical phones, native/UI/capture, and every GA gate remain pending. Python
oracle checks below validate only an independently stated expected-state matrix,
not BEAM/ETS/OTP behavior, product correctness, or test execution readiness.
