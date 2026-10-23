# Common presentation lifetime/setup seams

Stage 2 implementation, ready for root review. This changes no supported mode or
native C/JNI source. Android signed UI remains unsupported.

## Source and ownership

`CapabilityGuestUIPresentationLifetime.swift` defines checked never-reused scalar
lifetime IDs, private-constructor scalar receipts, and one-shot permit and
installation move cells. Issuing an installation twice rejects. Moving a cell
empties its old owner. Only the admitted permit awaits actual `Task.value`; a
concurrent finish returns pending data and creates no second waiter or Task.
The exact result remains in the lifetime object after the binding changes its
current lifetime. Apple receipts have no endpoint or native facade cleanup and
cover MainActor view retirement, never destruction of its publicly retainable
model.

`CapabilityPreparedPresentation.swift` owns the initial installation until the
core accepts it. Transfer holds the guard, control and binding gates and moves
that same installation into the binding's core slot. Binding takes the exact
pre-bind permit under its gate; it creates a fresh lifetime only after observing
the prior exact retired receipt. Failed bind keeps its local permit and awaits
its cleanup before throwing. Abandoning an armed guard synchronously quarantines
the reservation. Cleanup of a disarmed guard only reads status.

`CapabilityGuestUIRuntime.openOwned` protects async prepare, core construction,
transfer, and opening admission with one catch. Before transfer the same open
frame awaits the setup guard. After transfer the existing core cleanup job owns
cleanup. Capability-only open also puts construction and opening admission inside
its catch. An unclaimed store admission is now a one-shot worker input and is
cleared during cleanup when opening never began.

The observation owns one installation and one finish admission. Its first finish
stops the exact exchange, joins timer cancellation and the coordinator consumer,
then consumes the presentation permit. Reentry returns pending data or its
retained immutable result. Control installation checks the exact ordinary
operation, signals object, exchange binding and open state before moving the
cell. Detach and ending-observation still have one move owner. Worker fallback
and core final cleanup quarantine non-retired status. Core latches data close,
finishes its moved observation, waits the ordinary tail, then takes any remaining
pre-bind permit before final retirement and outer reservation close. No setup
cleanup Task was added.

Apple keeps its MainActor model, public accessor and native display-probe
behavior. Its sole existing bound consumer Task is wrapped by the lifetime.
Empty pre-bind cleanup creates no presentation Task and has an explicit
`noTaskCreated` receipt. The portable `prepare` branch issues and explicitly
retires an unused obligation before throwing; it allocates no model, facade,
endpoint, resource owner or presentation Task.

The native Android join/fence and facade-cleanup implementation is still a
separate stage. Its endpoint receipt must be added inside the trusted lifetime
implementation under root coordination; no internal receipt-forging factory was
exposed as a shortcut. The current receipt constructor creates Apple receipts
only.

## Executed verification

`final-1/receipt.json` binds 25 commands, exact source inputs, tool versions,
retained dependency receipts/artifacts and outputs. Source revision was
`d6505acac44ca8de456abb7748a149bf8990b72a`; source tree digest is
`8d540e60a53c40267e68de822cee181e22f92b69e61fe023d03e05ad6f247f47`.
The final receipt digest is
`b1170406d20390a383d1fede09e43aaddd2cf343f164ad068664c00885f59450`.

Command: `python3 verification/common-presentation-lifetime/run.py --name final-1`.
Each Debug/Release/TSan mode compiled and linked the complete actual activation
module, executed 14 XCTest cases and the Apple presentation model/hidden-window
regressions, and rejected a non-testable public client naming the internal guard,
permit, receipt and binding. XCTest contains eight existing cold-start cases,
five lifetime/observation/core cases and one permanent-quarantine case. Swift
Testing reports 14 cases: 13 executed and one explicit visible-window skip.
TSan emitted no warnings. The current activation/test files were instrumented;
the exact retained dependency objects and native archive were not rebuilt or
instrumented.

The tests exercise real Task tails, duplicate moves, wrong permit, concurrent
join, observation/coordinator ordering, empty setup cleanup, cancellation during
prepare, transfer, close before bind/start, reader-admission failure, exact receipt
before fallback, constructor rejection, opening-admission rejection, local failed
installation, matching-signal install, ending-observation detach, and permanent
quarantine on abandonment/missing final authority. Source mocks and replacement
product implementations are not used.

Command: `python3 verification/common-presentation-lifetime/portable.py`.
`portable-1/receipt.json` compiles the same complete source with the real
MixerApple module deliberately unavailable. Debug/Release/TSan each execute the
unchanged portable `#else` branch for 32 prepare/reject/retire cycles, preserving
the one-shot issue rule and returning capacity without quarantine. This is a
host portable-branch receipt, not an Android compiler/runtime receipt.

Earlier candidates remain as failed/intermediate evidence: candidate 1 had test
autoclosure concurrency compile errors; candidate 2 needed the official Testing
macro library path; candidate 3 passed Debug before the final observation and
quarantine cases were added. Final-1 is the complete host matrix.

## Limits

No physical-device discovery, connection request or run occurred. No Android
transport/JNI integration, real Java main Looper, native return fence, positive
visible display qualification, immutable separately published FieldLog package,
signing/store/release or GA reviewer gate is claimed. The existing visible-window
opt-in remains skipped and both physical platforms remain pending. This lane
does not edit STATUS, PLAN, work graph, GA gates or CI and does not commit/push.
