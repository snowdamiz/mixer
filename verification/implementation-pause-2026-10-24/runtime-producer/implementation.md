# Private Swift active frames

The private original-owner entry, return and terminal cleanup slice is implemented. The final product source is frozen as tree `4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4` in [the versioned source freeze](../verification/swift-active-frames-implementation/source-freeze/20261024T045840237261Z/freeze.json). The producer host matrix, exact-source typed MIR replay, eight compiled field layouts and offline evidence verifier pass. [Independent implementation review completed without a remaining blocking finding](../verification/swift-active-frames-implementation-review/decision.json). Root acceptance remains pending at the user's pause; this document advances no GA gate.

The [final receipt](../verification/swift-active-frames-implementation/final-receipt.json) joins the actual command origins, exact archived inputs, retained executables, layout results and scope. The [host receipt](../verification/swift-active-frames-implementation/results/20261024T050444826239Z/receipt.json) and [compiler metadata receipt](../verification/swift-active-frames-implementation/metadata/20261024T050606606361Z/receipt.json) remain immutable underlying observations. The [offline verifier](../verification/swift-active-frames-implementation/verify.py) needs no disposable Cargo target directories.

## Ownership and behavior

`vm/src/experimental_swift_reactor/frame_operations.rs` owns the private phase, real pin acquisition, entry rollback, normal finish, terminal drain, completion and positive accounting declarations. Its sibling test module constructs actual `SwiftReactorInstance`, cache, control, State and accounted WASI owners from independently authored Wasm bytes. It does not construct fake pins or frames. Successful entry creates every tested frame and every frame contains a pin returned by the actual cache.

The execution State contains an inline `FrameCleanupState` with the saved outer bound, nested restore obligation, unvisited prefix, sticky live mismatch, guard-attempt flag and unpublished `EntryGuard`. State grows from 312 to 424 bytes on this host. State construction uses an inline const initializer: the final production/unit MIR contains no runtime `FrameCleanupState::empty` helper call before execution-header admission. The whole-State construction growth propagates through the existing construction inventories.

`FrameOperationPhase` seals its inherited value phase and its owner references behind private fields. A sibling or parent cannot reach the nested push/pop/numeric methods through a returned cleanup-only phase. Its private entry/finish methods reject when inactive; only drain and completion remain usable after cleanup reacquisition. No public invocation, instruction dispatcher, initialization or Ready transition is introduced.

Entry first checks that this call can start a new attempt. An inactive/occupied rejection never rolls back an earlier guard. A new Active agreement failure becomes terminal. Entry captures the actual values and controls lengths in positive synchronous local positions; only a guard acquired by that call can use those lengths in rollback before returning. Neither ledger counts nor old retained-frame offsets are used as snapshots.

Pin acquisition uses the actual cache operation and consumes its returned Option slots through its original completion method. A successful actual pin and a nested completion failure can coexist. The unpublished pin moves into State immediately; entry stores nested restoration debt and preserves the original first failure. Parameter checks, copied local types, work charges, live predebits and fixed-capacity checks precede matching publications. Each locals borrow ends before checking or mutating. The function entry control comes from one private common `Control::function_entry` constructor. The actual guard pin moves into the published frame once the entry is complete.

Synchronous rollback truncates only this attempt's actual appended suffix. It removes at most the corresponding acquired guard debit after that effect; an unexpected larger actual suffix cannot consume caller live debits. Failed reductions latch `live_unreconciled`, including when the live ledger already reads zero. The retained guard contains unresolved acquired obligations, never reusable arena offsets.

Finish uses the original result pop and push operations and their work/failure order. It removes actual callee arena suffixes, attempts the actual pin release and only then publishes a caller result. A rejected release reconstructs the same frame with the returned original pin in the just-vacated indexed position. That frame is a processed suffix entry for the current pass. Drain cannot retry it in that pass or interpret its stale operands/control offsets.

Drain is terminal cleanup. It performs no ordinary cancellation, deadline, fuel or work admission. It attempts the retained entry pin at most once per pass, clears the actual global values/controls, and visits the deepest unvisited frame prefix exactly once. Successful original releases reduce actual frames; failed releases keep the original frame and pin in order. Multiple frame failures and an independent unpublished guard pin survive simultaneously. A later explicit cleanup-only reacquisition starts another pass, retaining the exact saved bound and all unresolved obligations.

Completion consumes fixed four-slot caller storage, ends named large wrappers before shrinking the construction bound, and restores the exact previous bound only after all frame/pin/live/nested obligations have resolved. `Retained` and `RestoreRejected` outcomes leave the State record and charges intact. A completed empty phase returns State to Idle; failures keep lifecycle Terminal. It never creates an initialized lifecycle.

## Original authority and the two barriers

Both zero-frame value preparation and consuming `cleanup_owned` reject a nonempty frame cleanup record or live frame/pin/value/control mismatch before taking an owner. The same cleanup-independent original-owner preflight runs for frame prepare, cleanup-only resume, value prepare and consuming cleanup. It checks the real WASI pair, cache pair, actual State header and all six actual buffer tickets, then exact ticket category/byte layout and actual arena capacities. Read-only `ReservationTicket::matches_layout` is used after the original owner validation and grants no refund, reservation or ticket authority.

Root approved one additive implementation-contract supplement after the frozen declaration contract: `RuntimeControl::check_construction_owner(cursor, wasi)`. The shared preflight now also checks the actual retained construction ticket before any arena or State transition. The helper requires presence, a nonzero matching owner, original live-ticket/category/combined sufficiency, and exact Construction/current-usage layout. It borrows the actual ticket, computes original predicates, ends the borrow and records rejection through the existing diagnostic path. It takes or clones no ticket and performs no checkpoint, work, allocation, refund, restoration or ledger repair. The frozen contract packet remains unchanged; the added helper and all four caller edges have fresh permanent positive source/MIR positions.

The resulting construction diagnostics are `swift_run_missing_construction`, `swift_run_construction_owner`, `swift_run_construction_underflow` and `swift_run_construction_layout`. Fresh missing, foreign and wrong-layout construction-ticket cases cover all four barriers. Each fixture retains and restores actual displaced authority. Wrong-layout cases cross-substitute genuine same-owner State/construction tickets; generic owner sufficiency can pass, so exact layout must originate the rejection. Earlier sticky first failures cannot make those cases pass accidentally.

Approved test seams are cfg(test) only: replace/restore actual cache or construction tickets while returning the displaced originals; temporarily narrow a real budget ceiling while returning its exact old scalar; alter an actual nested/outer restoration target at its original boundary; publish common Controls from actual decoded kind/end/height/result provenance; and reject a single observed-room comparison in the existing primitive push. No seam repairs live usage or manufactures a token/frame. Fault cleanup preserves the original cleanup invariant rather than clearing it to satisfy a generic fixture assertion.

## Positive actual-source accounting

The accepted frozen 1,061-field contract remains fully occupied: permanent 175,144 production / 175,336 unit bytes and active 240,776 bytes. The existing full value-operation term stays exactly 119,576 bytes. The Frozen reservation stays 2,912 bytes.

The implementation adds **16,804 distinct positive fields**: 1,064 explicit source roles, 7,220 exact production MIR positions and 8,520 unit-only positions (8,228 selected unit MIR positions plus explicit unit hook roles). Compiler-elided source aliases stay separately positive. Arguments, locals, return places, Try/ControlFlow/residual types and anonymous closure payloads have distinct source/argument/returned/caller fields; the map records exact function/local/type/capture identities. No old field, padding, receiver alias, old scratch reserve or narrower nested value term is credited.

The [supplement schema](../verification/swift-active-frames-implementation/implementation-inventory-schema.json), [generator](../verification/swift-active-frames-implementation/inventory.py), final actual-source MIR and saved fresh typed-role files provide the literal map. The old heuristic attempt is retained under `rejected-accounting/`; it is not qualifying evidence. The final typed replay compares exact function names, local IDs, source names, types, captures and field keys. Only global emitted-MIR stream line numbers are excluded from equality because unrelated preceding CTFE bodies shift them; full fresh line locations remain preserved for lookup.

All new original-owner and construction-validation caller edges are permanent, including value/cleanup paths before frame admission. The full primitive-push hook/capacity transfer inventory is also permanently unit charged, since ordinary zero-frame value callers can traverse it. The production primitive-push capacity leaf retains its literal original `values.capacity()` comparison and adds no capacity local. The unit hook therefore cannot consume frame scratch that a zero-frame caller has not admitted.

The common constructor's actual end/height/result and whole-Control source/argument/return/caller positions are included. Its private `Kind` field-initializer compiler spill remains within the agreed opaque constructor boundary; no Kind visibility was widened. Unrelated test fixture Defaults and TLS-generated machinery are outside the product-phase map; directly authored hook leaves, receivers, borrows and anonymous captures are selected and positively unit accounted.

Fresh Swift/all-feature Debug/Release production and unit compiles produce the following identical bounds across their four configurations per mode:

| Envelope, bytes | Production | Unit |
| --- | ---: | ---: |
| Frozen permanent | 175,144 | 175,336 |
| New permanent supplement | 911,504 | 1,770,320 |
| Total permanent | 1,086,648 | 1,945,656 |
| Frozen active | 240,776 | 240,776 |
| New active supplement | 689,096 | 1,264,520 |
| Total active | 929,872 | 1,505,296 |
| Fresh full original value term | 119,576 | 119,576 |
| Admitted frame envelope | 1,049,448 | 1,624,872 |
| Execution header | 1,378,536 | 2,238,504 |
| Construction envelope | 1,069,144 | 1,071,904 |
| Actual State | 424 | 424 |

The previously accepted value-only header was 289,536 production / 290,496 unit bytes, with construction 1,062,312 / 1,065,072, as recorded in the [prior compiler evidence](../verification/swift-executor-operations/results/20261024T013344529137Z/verified-summary.json). The resulting header increases are 1,089,000 / 1,948,008 bytes: the fresh frame permanent positions plus 2,352 bytes of propagated State/owner growth. Construction grows 6,832 bytes; its existing type-based whole-owner roles propagate that growth. Relative to the accepted 360,352-byte frame declaration preflight, the actual production/unit frame envelope grows by 689,096 / 1,264,520 bytes.

Compiled offsets, sizes and alignments cover 9,345 production and 17,865 unit fields, including all 1,061 frozen fields. Each field is unique, aligned, within its concrete containing object, and disjoint from every other nonzero field in that object. These observations establish layout, not actual-source completeness by themselves. The separate independent source/closure/lifetime review records its completed decision and evidence.

No installed/default byte ceiling was widened. On final-source AF01 under the unchanged default unit budget, state current/peak is 41,282,544 bytes; construction current/peak is 1,894,104 / 2,413,040; combined current/peak is 43,268,940 / 43,787,792. Default State and combined ceilings are 134,217,728 and 268,435,456 bytes. These are actual original-owner host observations. Production compiler envelopes are reported separately above; no public execution route exists to claim a production application run.

The AF22 narrower combined ceiling of 43,268,845 rejects the actual constructor peak at attempted 43,414,078 bytes, before any frame admission. The real construction cleanup tail completes to zero actual combined reservations. This is an explicit limitation: callers with narrower valid budgets may reject at construction after the positive supplement. Tests do not widen those budgets or label that rejection a frame-entry result.

## Executed host scope

All authoritative AF01–AF22 identities run on final source in Swift minimal/all features, Debug/Release. The candidate counts are 194/194/258/258 passed across selected unit and integration targets (904 total), compared with 172/172/236/236 on the archived baseline. Each configuration adds exactly 22 frame tests and removes none. Six existing ignored development oracle tests per configuration remain ignored; ignored tests are not passes.

| Case | Original-owner observation |
| --- | --- |
| AF01 | Nested and recursive entry, original parameter ownership, actual frames/pins/debits and exact local zero values. |
| AF02 | Zero/single results, nested and outer return, original pop/release/push order. |
| AF03 | Real frame and active-pin limits with retained prior pins. |
| AF04 | Actual 255/256 combined locals entry; independently authored 257 rejected by validation before constructing an owner. |
| AF05 | Actual decoded nested Controls, 512 inclusive depth and aggregate 4,096 boundary; budget-only control setup. |
| AF06 | Every bounded entry execution-work prefix with caller data preserved. |
| AF07 | Exact live predebit rejections and narrowed fixed capacity admission. |
| AF08 | Cancellation at every actual local check and synchronous suffix rollback. |
| AF09 | Actual acquired pin plus nested cache completion failure. |
| AF10 | Unpublished actual guard pin retained after rejected original release. |
| AF11 | Mixed indexed release successes/rejections with actual pin identity and order. |
| AF12 | Every actual frame release rejected while original frames/header authority remain. |
| AF13 | Independent guard pin and multiple failed frame pins retained together. |
| AF14 | Finish rejection is processed suffix; drain never reinterprets it. |
| AF15 | Caller result failures after actual callee retirement and release. |
| AF16 | Real live undercounts, including zero, latch and block consuming cleanup. |
| AF17 | Prior real accounted WASI effect, exact first failure and cleanup observations. |
| AF18 | Dropped phase, cleanup-only resume, no admission/work/value access. |
| AF19 | Fixed completion storage, outer restore rejection and cleanup-only retry. |
| AF20 | Fresh original provenance/layout cases at every barrier, including construction authority. |
| AF21 | Warm entry/finish/drain/completion refuse first allocation with zero requests; cold decode is separately observed and faults both actual allocation ordinals. |
| AF22 | Frozen/value regressions, full positive reservation, actual narrow construction rejection. |

AF05 uses distinct actual decoded blocks and function controls. Eight real callers with 512 Controls reject the next aggregate entry, while 4,095 plus one accepts. A separate duplicate of one genuine decoded block exercises a defensive per-function 513 check; a true 513-inclusive source is rejected by validation. This does not qualify a block or instruction dispatcher.

AF15's capacity rejection is an explicitly derived defensive-boundary injection. A valid result pop and callee retirement naturally free caller room, so this post-return capacity rejection is not naturally reachable from a valid owner. The one-shot cfg(test) observed-room seam preserves the actual Vec/capacity and production expression. Work, operand and live-predebit failures are separately exercised at their actual boundaries. Relative predebit/work ceiling seams are likewise identified as derived fault injections rather than fixed-budget construction cases.

Existing affected constructor/cache/value, validation/WASI, floating-point, allocation and Frozen/span tests pass in the selected four-profile target matrix. All-feature library Clippy and format pass, plus default/span/Swift/all library checks in Debug/Release. Broad all-target/all-feature Clippy still rejects the same 26 prior diagnostic identities. Comparison uses code/message/path/column and the actual associated source line; absolute line-number shifts from the one fixture field are preserved in raw logs, not misreported as new diagnostics or suppressed. Compiler-expanded bodies of the six selected Frozen helpers are identical. All 1,232 public Frozen trace records in each all-feature profile match baseline. All four production C ABI feature/profile pairs have identical exported `_mixer_` symbols; all eight actual dylibs are retained.

## Reuse and immutable inputs

The baseline source tree is `4df46815f8a9b30db00dda35ed97603da229ac3be957d3f27df38ed2ac56a7c9` (117 archived files). It includes root's pre-existing test observer fix. The final candidate tree has 119 files. The freeze records observed revision `bb897e9eb706ed787d287e7ba6f848ee43eba423`; the manifest/tree digest, rather than the then-current HEAD alone, identifies every uncommitted product byte tested.

The successful host collector contains 204 copied command records and 25 newly executed commands. Copied commands are never claimed as newly run. Every baseline runtime command originates in `results/20261024T045149763486Z` on the unchanged baseline and is carried through `050048420640Z`. Every **final candidate** runtime command originates in `results/20261024T050048420640Z` on **4f16367b**, including the final unit-hook accounting. Those checks passed before that collector stopped at its incomplete broad-Clippy diagnostic comparison. The successful collector reran complete `--keep-going` Clippy, expansion and ABI observations and imported the already successful exact-source runtime commands. Its final receipt records each command's entire import chain, exact source, timestamps, stdout/stderr hashes and original execution receipt, plus each retained binary's build/list/run association.

The older `f10e1fef…` candidate passed earlier runtime checks but is historical only and cannot qualify the final candidate. Its original versioned freeze and raw unsuccessful collector receipt remain intact. The earlier first preflight tree, intermediate failures and rejected inventory attempt likewise remain historical evidence. Final-source metadata is fresh: two exact-source MIR compiles plus eight derived-source layout build/run pairs. The archived derived layout source only appends uncalled metadata helpers and one diagnostic example; product algorithms and fields remain literal.

The compact product artifact archive retains 92 actual test executables and eight ABI dylibs. The separate metadata archive retains eight actual layout executables. Member indexes bind each SHA to its original source/configuration and command. Verification checks archive members directly and does not require original ignored targets or their absolute paths. Tool versions and exact argv/environment/output remain in underlying receipts. Rust/Cargo 1.99.0 and Python 3.14.8 were observed; `RUSTC_BOOTSTRAP=1` is used only for compiler-expanded diagnostic output, never normal runtime builds.

## Limitations and delivery boundary

No computer use, screenshots, simulator/emulator/device discovery, boots, installs or native runtime tests were performed. Native iOS/Android, physical phone, published separate-repository FieldLog consumption and GA acceptance remain pending. No Patch/Skip implementation, generated implementation, fixtures or dependencies were introduced. Frozen helper bodies, public Limits, C ABI and existing 119,576-byte value scratch are unchanged. The initial contract was declaration preflight; final runtime/layout observations do not replace the separate independent actual-source/algorithm decision or root acceptance.

This lane makes no commit or push and changes no plan, tracker or gate. Root owns integration and delivery. The [independent review](swift-active-frames-implementation-review.md) is a separate evidence lane. At the user's pausing point, all owned host test/compiler commands had already exited; empty process-path and open-file checks preceded removal of only this lane's disposable `build/` tree. The [cleanup receipt](../verification/swift-active-frames-implementation/process-cleanup/receipt.json) records that no termination was needed and that source, raw observations, historical attempts and compact qualifying executables remain preserved. No new runtime tests started after the pause instruction.
