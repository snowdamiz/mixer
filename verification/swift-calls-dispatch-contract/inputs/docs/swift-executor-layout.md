# Private Swift executor type, lifetime and layout prerequisite

This is a bounded compiling prerequisite under the frozen revision 2 executor
contract, after root accepted cache candidate 3. It supplies chosen private
owner/borrow/transfer types and executable host layout measurements. It supplies
no interpreter algorithm, runnable constructor, initialize/invoke entry point,
new public route, target execution, or executor implementation acceptance.

The code was compiled in the exact derived tree described by
`verification/swift-executor-layout/measurement-overlay.patch`, not wired into
the working VM. Root owns application of the smaller
`verification/swift-executor-layout/root-wiring.patch`. Historical contract and
acceptance artifacts remain sealed. `mixer-product-plan.md` remains binding;
root owns tracker and gate changes.

## Chosen private ownership and lifetime shapes

`ExecutionMode` is crate-private and sealed. Its associated cache, owned pin,
frame, operation GAT and failure types select only Frozen/Swift associations.
`ExecutionParts<'a, M>` borrows the actual cache and six actual vector handles.
`FrozenOperation<'a>` borrows the unchanged legacy budget, cancellation, usage,
failure and function/offset fields. Neither adapter changes stored legacy fields
or runs legacy algorithms.

`SwiftExecutionOperation<'a>` holds the mutable original control and mutable
actual AccountedWasi plus the current Cursor. The Cursor is ephemeral call
location, not stored policy, identity, deadline or ledger state. The
`with_cache_operation` HRTB callback permits shorter control/parts/WASI reborrows;
its result cannot retain those borrows. Its compile witness prepares and closes
an actual cache phase. A retained immutable WASI borrow excludes a concurrent
mutable borrow, and a retained FunctionView excludes cache mutation. Selected
instruction/branch target storage contains copied scalars, with no cache borrow.

`SwiftFrame` has the legacy scalar meanings and exactly one non-Clone
SwiftFunctionPin. `SwiftExecutionState` has six Vec handles, six optional buffer
tickets and **one `execution_header` ticket**. This ticket is the sole permanent
execution header covering State, the exclusive composed-owner residual, and
cleanup storage. There is no second State-header reservation.

The composed owner has private Option control/cache/WASI/State fields and a
one-byte Uninitialized/Ready/Terminal lifecycle enum. These are chosen state
representations only; no method implements those transitions here. Construction
and operation phases retain the previous construction bound; their future
one-shot methods and exact admission order remain implementation work.

`ExecutionCleanupTail` owns the original control, same execution header, one
copied final WASI observation and first-failure copy. Its helper consumes all
caller return storage and the tail failure before returning the original
control/ticket/observation. The HeaderCompletionParts return temporary is
destructured in a complete statement before refund. No cache/WASI/State owner,
large tail/result wrapper, or replacement control is accepted at that boundary.

## Measured Apple arm64 layouts

`layout-map.json` contains Debug/Release size/alignment/field-offset output,
feature/target/toolchain, 53 named simultaneous transfer terms and all eight
required phase entries. Source/argument/return positions are explicitly charged;
these are chosen finite prerequisite budgets, not measured interpreter call
chains. The eventual implementation must bind its actual locals, helpers and
loop/return storage within reviewed maps before acceptance.

The non-test derived executable is separate from unit tests because
AccountedWasi includes test instrumentation. Debug and Release layouts agree
within each configuration.

| Shape or additional envelope | Production bytes | Unit-test bytes |
| --- | ---: | ---: |
| Value / legacy Control / SwiftFrame | 16 / 32 / 64 | 16 / 32 / 64 |
| SwiftExecutionState | 312 | 312 |
| SwiftReactorInstance | 4,480 | 4,528 |
| AccountedWasi | 1,448 | 1,496 |
| Exclusive composed-owner residual | 8 | 8 |
| ExecutionParts / Swift operation / operation phase | 56 / 48 / 112 | 56 / 48 / 112 |
| Construction / operation / growth additional terms | 52,088 / 16,328 / 9,752 | 52,688 / 16,328 / 9,752 |
| Cleanup additional terms | 50,272 | 50,512 |
| Proposed same execution-header envelope | 50,592 | 50,832 |

The header formula is checked `sizeof(State) + sizeof(Instance) - sizeof(State)
- sizeof(Cache) - sizeof(WASI) - sizeof(Control) + named cleanup terms`, with all
subtractions required nonnegative. The measured residual includes every Option
tag and containing alignment byte. No padding supplies another live object.
Vec payloads have their six separate tickets. Cache/proof, WASI, Shared and
temporary replacement memory remain separate categories.

At the reference target counts, the six checked payload requests are 262,144;
131,072; 4,096; 38,273,024; 373,704; and 84,368 bytes for values, controls, frames,
memory, table and globals. This is a formula evaluation, not target allocation
or initialization. The 767-to-768-page old/new payload overlap is 100,597,760
bytes. A small storage-only witness measured exactly six allocations totaling
66,264 requested bytes and capacities 16/8/2/65,536/3/4, with no reallocation.
It does not validate constructor admission, initialization, growth commit or
failure-ordinal behavior.

Cancellation handles measure 8 bytes each. Two cloned handles share one
24-byte, align-8 requested backing allocation; one allocation and one
deallocation were observed. The same backing remains attributed once to the
existing Shared ticket, with no per-handle/per-frame ticket.

## Final accounting dependency remains open

The selected final helper's **behavior** passed both valid and deliberately
foreign-ticket cases in Debug/Release with zero allocations. Both use a copied
observation from an actual AccountedWasi ArgsSizesGet dispatch, followed by real
WASI cleanup. Successful completion reports zero combined bytes/tickets after
actual drop. Rejection latches `swift_run_release_owner` and retains the entire
original execution-header charge and one ticket. These tests do not prove a
complete named accounting envelope.

`final-boundary-map.json` names the surviving output borrows, ticket/error
transfers and sequential refund/record/finish windows. Six optional observation
shapes cover one final observation plus the five nested rejected-refund
parameters. The successful refund uses three; record/finish use three. Large
caller wrappers end before these foundation-only windows.

The frozen foundation does **not** explicitly assign the two output references
or the remaining final call-chain receiver/scalar/iterator wrappers. Its
Failure/Usage/Ticket slots are not relabeled to cover smaller references.
The output references alone demonstrate an additional 16-byte requirement.
The measured 256-byte RefundSupplement and 288-byte FinishSupplement are
**incomplete starter probes**, not sufficient allowances or a claimed minimal
correction. Independent review must additionally cover match tuples, argument
and return borrows, get_or_insert, primitive usage/micros transfers, and the
runtime foundation formula's own iterator/try_fold chain. Root owns the exact
disjoint correction, its source/contract changes and new verification before
this final boundary or the prerequisite can be accepted.

## Frozen evidence and remaining scope

`receipt.json`, complete input/overlay manifests and source freeze bind commands,
tool versions, source revision, exact source bytes and output hashes. The
metadata-only production probe export/example exists solely in the documented
derived overlay. It is absent from product source and the root wiring patch.

The collection runs seven Swift layout tests and one frozen-layout child test
per Debug/Release; all six requested feature
combinations per profile (neither, span, Swift, Swift+cache, Swift+span, all);
existing legacy span execution/allocation/oracle integration tests per profile;
seven negative compile/privacy probes per profile; minimal/combined clippy with
warnings denied; and formatting of the four new source files. Original legacy
field offsets are printed by a child probe, and existing frozen layout tests
remain in the regression scope. All existing working VM inputs remained byte
identical throughout collection. A failed early negative-probe draft used a
diverging panic expression; its preserved log is not counted as rejection
evidence. The corrected probe uses an actual separately owned pin.

The full future 20 executor tests/75 assertions, actual constructor/algorithm/
cleanup composition, full feature integration matrix beyond the named scope,
natural executor-origin failures, full target instantiation/initialization/
invocation, compiler/signing/store/customer/operational, immutable published
separate-repository FieldLog, performance/delivery size, physical iOS/Android,
and all GA evidence remain pending. Phones remain disconnected; no discovery,
device run, publication, commit or push was attempted by this lane.
