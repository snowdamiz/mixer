# Private concrete-attempt owner

Owner scoped tests pass; independent review and final coordinator composition are
separately owned. Production is limited to the two new private source files
`CapabilityConcreteAttempt.swift` and `CapabilityConcreteRetirement.swift`; the
new `ConcreteAttemptTests.swift` obtains inputs through real signed v3 bytes and
the real recovery store. No old store, selection, signals, policy, SDK, bridge,
contract, schema or public API was edited by this lane.

The I/O-free initializer checks generation and immediately reserves one adapter
obligation before constructing its private setup actor. The coordinator must
store the attempt before awaiting its one-shot `construct()`. The actor opens
only the derived concrete HTTP/KV adapters off UI. Before a group exists, a failure
awaits opened KV close inline. After the group is expected/created, the existing
bridge owns its one host/KV close Task and separate native-close job. This code
creates no Task, dispatch job, terminal consumer, polling loop, service callback
or accepting validator. HTTP initialization has no exchange/session before a
request in the pinned SDK; that fact is not generalized to arbitrary adapters.

`stop(cause:)` synchronously records local stop before bridge cancellation, moves
and clears every stored input/group/construction/session alias under its lock,
then cancels/closes outside the lock in an inner helper. That helper returns
before unused setup retirement. `startup`, owned enable with the exact original
uptime cutoff, and the internal no-arguments export invocation each allow one
method at a time; inner session-owning frames return before their tail is joined.
Duplicate construction does not cancel a valid first construction. The private
caller must use the same installed material and signals issued by its store.

The fixed retirement sink owns only flags, one continuation and the adapter
obligation. It never retains an attempt, group, construction, session, actor or
Task. `reservation.adapterOwner` remains nil. Its transitive reservation/store/
signals/stream graph requires the separately owned consumer to retain no strong
coordinator/attempt/group/session across `next()`. Its exact join is
`setupReturned && methods == 0 && (!groupExpected || bridgeRetired)`. The obligation
moves once under the sink lock; actual `obligation.retire()` runs outside that
lock, and a true waiter result is published only after it returns and clears the
reservation's retiring state. A canceled or duplicate wait returns false without
retiring. Cancellation is latched before registration, and the final return
checks cancellation again. No deinit fabricates adapter exit. A missing bridge
retirement, failed native close or quarantine therefore keeps the outer slot
unavailable; the inherited bridge behavior is qualified in the earlier lifecycle
lane, not replaced with a task-return shortcut here.

Six unmodified tests pass in Debug, Release and TSan. They cover actual signed
selection/validation, concrete native startup/enable/Wasm storage and persisted
KV bytes, outer sixteen-slot coexistence, I/O-free init/stop, one-shot waiting,
real constructor rejection after KV opened, cancellation during setup, original
expired cutoff before adapter init, generation mismatch and real KV initializer
failure. The setup cancellation may win before group creation or after create is
queued; exact delayed schedules are covered by the derived probes below. A test
key is explicitly public TESTONLY material, not a production signing key.

Three fixed derived cases pass in each Debug/Release/TSan mode, nine isolated
executions. They hold a setup frame after real native create, or a startup method
frame after real VM return; stop and actual bridge retirement occur while each
frame is held, yet the adapter obligation/outer sixteenth slot remain counted.
Only logical return frees it. A registered canceled wait and duplicate wait do
not claim retirement. A third case throws just after returned KV initialization
and before group creation, proving actual inline KV close and zero bridge
retirement callbacks. The five source edits are counters/barriers/fixed faults in
derived copies only. No native result, exit or acknowledgement is fabricated.

Qualification reused immutable transition candidate2 manifest
`eca159ee0c07066a5f6bccb3ef8e02396a6489cb6f392c9bf2f8d4cb8c04ff62`,
its retained dependency products and the one `b25e3b7` native archive
`a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72`.
The combined 127-input candidate4 manifest is
`1841b66af21862254655cd11255d4208ee48f463bb84ef7bd2789a14b9615fa1`.
Direct compilation rebuilt only the activation module/test bundle. No package,
dependency or Rust graph was built. Debug/Release symbol outputs show one native
enable definition in each runtime dylib and no native VM definitions in the test
bundle; all three derived modes repeat that single-registry check. Two ordinary
external-import failures keep the new types private, while the old public
material-capture type remains importable.

Historical evidence is preserved. Candidate1 stopped before compilation because
live shared-lane files had advanced; root authorized explicit immutable dependency
qualification instead. Candidate2 production compiled, but the new test fixture
missed four associated-value labels and the direct driver omitted the XCTest
Swift overlay. Candidate3 still had an incorrect overlay path. Both were fixed
only in tests/tools. Candidate4 Debug/Release six-test runs passed. Its TSan bundle
compiled, but `xcrun` stripped the loader environment and the runtime aborted
before tests; `replay-tsan.py` ran the exact unchanged bundle with the resolved
XCTest executable and all six tests passed. `run.py` now uses that same resolved
launch for future runs. No production byte changed across these compiler/launcher
corrections. The final audit distinguishes the old failed receipt from its exact
successful TSan replay instead of relabelling it green.

`final-receipt.json` binds production/tests, immutable dependency/export,
unmodified and derived results, the launcher repair, opacity checks, and source/
evidence manifests. Cache components are excluded. Live Store/Signals/coordinator
changes after the dependency freeze are deliberately not asserted equal; root's
final combined integration must qualify those exact newer inputs. Local TSan
reuses retained TSan dependency products; Rust/platform code is not Swift TSan
instrumented. Cooperative clock checks do not give atomic hard real-time, rollback,
Task/allocator destruction or global resource-cap guarantees. No physical-device,
production, trust/credential, signed execution façade, real health, publication or
GA qualification is claimed. No commit/push is performed by this lane.
