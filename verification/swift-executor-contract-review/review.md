# Independent executor-contract review

Decision: **changes required for R1 before contract freeze**. The proposal's
authority and algorithm design is otherwise suitable for bounded continuation
only after accepted cache implementation, root helper/layout freeze and a
separate implementation assignment. It grants no executor or target acceptance.

The reviewed producer receipt is exactly
`62f825ab418b207c057f384b2c0afdbfabb3fee50e0db75e945f0d3448f092de`.
`receipt.json` independently binds 56 artifact/log/committed-source entries,
audits the nine producer commands and preserves their bytes. Both artifact-only
checker commands were replayed from copied inputs: 15 invalid mutations were
rejected, with 20 named functions and all 75 assertions still pending.
`review-inputs.tar` retains that snapshot. The producer collector was not run.

## R1: the final observation tail needs three optional shapes

The frozen foundation reserves `2*size_of::<WasiUsage>()`. Independent executable
Debug/Release probes of committed `3a1bb5a` establish WasiUsage=104/align8 and
Option<WasiUsage>=112/align8 on this aarch64 Apple host. Thus the current
208-byte allowance cannot cover even two 112-byte optional values. More
conservatively, the actual accounted-WASI final refund retains three such
values, so changing only the two shapes is insufficient.

The root-owned bounded correction is **3 Option<WasiUsage>**, 336 bytes on this
target, replacing 208; the foundation becomes 16,168 rather than 16,040 bytes
(+128). This changes the upfront named reservation only, with the same ticket,
categories and cleanup behavior. It must be tested/source-reviewed by root;
this review makes no shared source or contract change. Other targets need their
own measurements. Old receipts remain historical evidence and must not be
rewritten to claim this correction was present.

The named live-set map below counts a caller's retained Copy binding and nested
by-value arguments conservatively. It relies on no last-use/compiler-elision
proof. A nested observation inside a whole charged failure/usage is not a free
standalone slot and is not reused to conceal a missing optional observation.

| Path/window | Independently live standalone Option<WasiUsage> | Coverage |
| --- | --- | --- |
| Cache `complete` -> `drop_reserved_with_wasi` -> successful `refund_with_wasi` | drop argument; refund argument = 2 | amended foundation 3-option allowance |
| Cache later `record_cleanup` -> `usage` | record argument; usage argument = 2 | amended foundation; previous refund call has returned |
| Cache failed refund -> `cleanup_fault_with_wasi` -> `fail` -> `usage` | drop; refund; cleanup-fault; fail; usage arguments = 5 | rejected header is **not refunded**, so its existing six-option permanent cleanup envelope remains charged |
| AccountedWasi final successful header refund | `cleanup` local `wasi`; drop argument; refund argument = **3** | amended foundation; actual AccountedWasi storage was dropped before refund |
| AccountedWasi failed header refund | same outer local plus drop/refund/cleanup-fault/fail/usage arguments = **6** | rejected header retains its existing six-option cleanup envelope |
| Earlier WASI buffer refunds / cache entry or proof refunds | header and its permanent cleanup envelope are still charged | never double-spend that envelope after a successful header refund |

The deeper fault branch checks owner/underflow before any successful header
debit. Therefore the larger rejected-path envelope is still retained; the
successful-refund path never calls cleanup-fault/fail/usage. `record_cleanup`
occurs after the cache refund call and its Result end, rather than while their
observation parameters remain live.

`AccountedWasi::cleanup` additionally retains `result` and `released` failure
Results, then uses by-value `Result::and`. The foundation's four failure-sized
shapes can name accumulator, released result and the two and-operand/return
transfers across this interval; the and parameters end before its result is
assigned/returned. Cache completion names caller outcome, observed refund Result
and failure/return-output transfers within four shapes. `record_cleanup` names
usage return/local and after-cleanup assignment transfers within the four usage
shapes. The control's own stored first failure is separately charged in the
control header, rather than counted as spare failure scratch. Six ticket shapes
cover the actual optional-header extraction/owned ticket/drop/refund transfers;
no ticket count or registry is added.

Measured Option<SwiftRunFailure> and Result<(),SwiftRunFailure> are each 1,096,
identical in size/alignment to SwiftRunFailure; Option<SwiftRunUsage> is 504,
identical to SwiftRunUsage; Option<ReservationTicket> is 24, identical to the
ticket. These whole outer shapes fit the corresponding existing named classes
on this target. This is a named Rust-object model, not a claim about LLVM copies,
stack slots, RSS or allocator overhead. Scalar/borrow handles remain named by
their containing foundation/component/tail model; they cannot be charged by
reusing payload bytes inside failure/usage fields.

### Disjoint composed-caller obligations

An external copied final WASI observation held while cache/WASI components drain
belongs to the **still-live execution permanent header envelope**. It is distinct
from each component's foundation observation arguments. The same applies to
caller-held component outcomes, execution-tail/Result/Option storage and its
control/WASI borrows (measured 8 bytes each). Neither the WASI six-option envelope
nor the foundation three-option allowance may simultaneously stand in for that
external copied value.

Before the **execution** header itself is refunded, its tail must have consumed
the large caller owner/Result/Option storage and all component tails, retained
the original control, and frozen an explicit final active-value map. A tail's
one raw or optional final-WASI observation plus the drop/refund arguments can
fit the amended three-option class (a raw 104-byte value is bounded by one
112-byte shape). A `record_cleanup` or final `finish_owned_cleanup -> usage`
chain likewise has at most the retained observation plus two forwarded options
only if no additional copied observation survives. Extra retained copies or
wrappers require their own named upfront bound. No implementation exists here,
so this is an acceptance condition, not a proved map of a future executor.

Update the cache/executor contract text, `cleanup.foundation_counts`, checker
expectations and named assertions consistently, preserving v1/v2 receipts before
the root-owned refinement. The executor's eight measured-layout phases remain
pending; they must record actual field shapes, alignments/offsets, simultaneous
counts and the final disjoint caller map. Do not accept a total-byte estimate
without that mapping. Two optional values (+16) or unrelated spare padding are
not sufficient resolutions of R1.

## Remaining contract assessment

- Complete opaque proof consumption, private sealed Frozen/Swift modes and
  borrowed parts preserve authority; no arbitrary host/index/source route or
  production competitor dependency is introduced. The cache code snapshot in
  the review archive is **analysis only and unaccepted**.
- A single shared opcode algorithm with literal old owners/layouts is the
  required extraction. The proposed static associated frame/pin/operation types
  are feasible without a self-borrowing owner; compiling exact lifetime/helper
  signatures and full frozen-route work/allocation/error/privacy parity remain
  implementation acceptance requirements.
- Six fixed vectors, checked exact capacities, one pin per defined frame,
  owned partial-enter guard, copying only the selected instruction/target and
  ending code borrows before mutation address pin/eviction/return authority.
  Release rejection retains its pin for continued unwind.
- Initialization uses sealed descriptors and absolute cursors, source-order
  globals, all-data then all-element range preflight before effects, ordered
  overlaps and exactly-once initialize before Ready. The same memory/table ABI
  applies to small synthetic sources. Ready and later stateful calls do not
  reset lifetime limits.
- AccountedWasi dispatch is the single executor host-entry charge; adapter calls
  remain independently authoritative. Failure snapshots use checked actual
  paired observations. The independently reviewed observed instruction/fuel
  prerequisite is recorded separately in
  `verification/swift-instruction-observation-review/receipt.json`; this does not
  rewrite the proposal's then-pending status.
- Terminal/cancellation/earliest-deadline ordering, instruction fuel before work
  and dispatch, precise bulk fuel, actual movement/work and old/new growth
  overlap match the binding design. The pending exact trace must include the
  import's current fixed work, all extra branch/end/tee credits and each Swift
  descriptor/loop check rather than relying only on the schedule's summary.
- Option-owned composition and an owned original-control cleanup tail avoid
  borrowing a parent while moving it. Intact rejection, drop-before-refund,
  continued drain, immutable first cause and no admission/work/service/time
  checks during cleanup are explicit. R1 and the actual composed-tail map block
  acceptance until corrected and measured.

No other contract blocker was identified. All 20 implementation functions,
fault ordinals, measured maps, independent engine source review and combined
regressions remain pending. Accepted cache implementation is still required.
The separately approved exact bounded target runner, physical iOS/Android,
immutable published separate-repository FieldLog consumer, compiler/native/API/
signing, performance/size, stores, customers, operations and GA remain pending.

Review model: gpt-6.1-sol, xhigh, fresh bounded context. No commit/push, producer
reseal, device discovery/run, target instantiation/initialize/invoke or engine
implementation was performed. The only compiled addition was an isolated named
layout unit probe against frozen foundation source, recorded separately in
`layout-receipt.json`.
