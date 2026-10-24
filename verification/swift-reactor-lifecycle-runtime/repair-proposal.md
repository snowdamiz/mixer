# Proposed isolated test repair; not selected or implemented

The unchanged sealed candidate ran once in Swift Debug. Its 23 selected test
identities produced 21 passes and two failures. Other feature/profile contexts
and broader regressions were stopped. Engine correctness is not inferred from
the passing subset. This proposal changes only a future isolated test candidate;
the original candidate and failed binaries remain unchanged.

## SL09: lifetime work budget and exact diagnostic boundaries

`owner_with` passes the original budget into `RuntimeControl::adopt` before the
actual constructor, then unconditionally unwraps construction. Execution work
is cumulative over this same owner. The first constructor charge precedes memory
zeroing: 584 × 65,536 memory bytes + 46,713 table slots + 4 globals = 38,319,741.
Four global initializers add 4 × 16; the one data-range check adds 1; its payload
adds 17. Scalar-reader checks do not debit additional execution work. Successful
construction therefore requires exactly **38,319,823** work credits for this
fixture. There is no element segment when the supplied table initializer is empty.

The zero work lifetime budget correctly rejects construction. The observed
failure is `WorkExhausted / swift_run_work / ExecutionWork`, attempted
38,319,741, limit 0, stage Invocation/function 34/offset 211 inherited from the
fixture's explicit construction cursor. The fixture's unwrap causes the test
failure before Initialize runs. Do not relabel it an initializer failure.

Retain zero-lifetime work as an explicit constructor rejection subcase. Match
the actual `ConstructionFailure::Cleanup(tail)` and inspect its original failure,
then consume `ConstructionCleanupTail::complete` with every original possible
return/pair/owner storage, collecting final usage and checking zero outstanding
reservations/tickets/live debt. Never drop the retained tail or fabricate an
owner. The current failed unwrap did not execute that explicit completion path;
its OS process ended and the captured target was cleaned.

For an initializer-specific work edge, set the **original** pre-adoption budget
to the independently derived 38,319,823. Assert construction usage equals that
sum. Initialize then reaches `FrameOperationPhase::enter_inner`'s first `work(1)`
after the frame-depth check, before signature/pin/guest execution. Require exact
Initialization/function 35/offset None, WorkExhausted, `swift_run_work`,
ExecutionWork, attempted 38,319,824, limit 38,319,823. Usage must preserve
execution_work=38,319,823 and instructions/fuel/host=0, terminalize the actual
lifecycle, restore its original bound and allow accounted cleanup. No budget
reset, replacement authority or new test-control seam is needed.

Replace the current broad kind-family assertion with independent exact cases:

| Original limit | Actual intended checkpoint | Required kind / code / resource | Attempt / limit | Cursor |
| --- | --- | --- | --- | --- |
| instruction_fuel=0 | First initializer constant instruction prefix | FuelExhausted / swift_run_fuel / InstructionFuel | 1 / 0 | Initialization, function 35, first initializer opcode offset |
| execution_work=38,319,823 | First actual initializer frame-entry work charge | WorkExhausted / swift_run_work / ExecutionWork | 38,319,824 / 38,319,823 | Initialization, function 35, None |
| frames=0 | Entry frame-depth check before entry work/pin | FrameLimit / swift_frame_depth / Frames | 1 / 0 | Initialization, function 35, None |
| values=0 | First initializer constant push into actual zero-capacity values arena | ValueLimit / swift_execution_value_capacity / Values | 1 / 0 | Initialization, function 35, first initializer opcode offset |
| controls=0 | Entry function-control capacity check with actual acquired pin | ControlLimit / swift_frame_control_capacity / Controls | 1 / 0 | Initialization, function 35, None |
| host_calls=0 | Actual initializer fd_write call before host service effect | HostCallLimit / swift_run_host_calls / HostCalls | 1 / 0 | Initialization, function 35, actual call opcode offset |

The first opcode offset comes from the existing module helper's independent
`starts[1]` byte-position construction; the fd_write call is `starts[1]+8` after
four two-byte constant arguments. Cursor values must not be read back from the
failure to construct expected values. Assert every exact counter and real cleanup
boundary relevant to its case, including no stdout effect for host rejection.
These predictions are unrun. Exact/one-below pairs for every other resource,
State/Combined overlap, and the rest of the full original SL09 matrix remain open.

## SL13: independently derived cache work

A cache hit still charges lookup and both searches. The fixture starts with 29
defined slots, 64 pin records and 512 patch entries, so constructor cache work is
29+64+512=605. The three first misses publish in first-empty order: initializer
35 at slot 0, corpus 62 at slot 1, callee 36 at slot 2. No eviction is needed.
`independent-source-traces.json` binds every exact source charge site and literal
fixture to the following arithmetic.

For each cold function, work comprises lookup (1), pin-record search (P),
resident miss search (29), two signature lookups (2), two 512-entry resets
(1,024), two parameter/descriptor checks (2), both encoded-body reads (2B),
scan/build instruction accounting (2I), build instruction pushes (I), planning
slot scan (29) and 64 eviction bits. Total = **1,151 + P + 2B + 3I**.
There are no local expansions, control patches or branch targets in these bodies.

| Operation | B including local-group byte | I | P | Work | Cumulative |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cache construction | — | — | — | 605 | 605 |
| First initializer 35 | 14 | 6 | 1 | 1,198 | 1,803 |
| First corpus outer 62 | 7 | 3 | 1 | 1,175 | 2,978 |
| First corpus indirect callee 36 | 19 | 9 | 2 | 1,218 | 4,196 |
| Second corpus outer 62, hit | — | — | 1 | lookup 1 + pin search 1 + slot search 2 = 4 | 4,200 |
| Second corpus callee 36, hit | — | — | 2 | lookup 1 + pin search 2 + slot search 3 = 6 | 4,206 |

The second call retains its outer pin in pin record 0 while acquiring the callee,
so the callee examines pin records 0 and 1. Both warm slot scans include earlier
residents. This independently predicts the observed 4,196→4,206 difference.
The original equality assertion incorrectly treats cache hits as free.

Proposed repair asserts the constructed/initialized/first/second cumulative
trace above and warm +10, with cache hits +2 and no new misses, decodes, evictions,
resident bytes or tickets. Keep the independently counted six initializer and
twelve-per-corpus instruction assertions and the unchanged deadline. Add source
comments for the per-operation arithmetic; do not change an expected value merely
to mirror an observation. These strengthened assertions remain unrun.

## Accounting impact and acceptance boundary

The complete proposed source delta is **one test-only file**:
`src/experimental_swift_reactor/lifecycle_tests.rs`. Within that file:

- Change only `swift_lifecycle_sl09_initializer_exact_resource_failures` to add
  the explicit zero-lifetime constructor rejection/actual consuming completion,
  independently derived original work budget and precise per-dimension cases.
- Change only `swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage`
  to add the independent cold/warm cache trace and hit/miss/decode assertions.
- Preserve all 23 exact test identities. Keep `owner_with`, module/Function
  fixture helpers, every test hook and all other test bodies byte-identical.
  Use existing APIs and fully qualified paths rather than changing shared imports
  or introducing an engine/control seam.

Every other candidate file must remain byte-identical, including production
`lifecycle.rs`, `memory_growth_operations.rs`, their accounting declarations and
formulas, `execution.rs`, frame/cache/control source and every Frozen source and
expanded method. The existing sealed accounting/compiler packets remain
immutable. No engine, owner/control field, public API, ABI, limit, ticket or
unrelated fixture change is requested.

Fresh unit compiler/runtime evidence must bind the repaired file. Verify the
fresh actual full bodies, exact types/layouts and carriers of all accounted
runtime positions in the selected contexts, explicitly accounting for any source
location changes. Production source/formulas and all Frozen methods must prove
byte identity. Any actual changed accounted body, new position or type/layout
change must be presented to root for exact accounting scope/selection before
numeric adoption; do not silently award changed positions prior-row credit.
Root must select new ownership and this accounting-impact proof before any
implementation. No numeric or runtime acceptance is requested by this proposal.

The entire original planned matrix and authored/remaining ledger remain
byte-preserved in this failure packet. SL12 passing unchanged-table indirect
reads do not implement guest table mutation. Full library, Frozen, default/span,
other three focused configurations, physical devices, full reactor and GA
qualification remain unrun/unaccepted here.
