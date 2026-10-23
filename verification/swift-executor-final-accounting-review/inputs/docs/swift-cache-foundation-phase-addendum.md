# Cache foundation phase alternatives

This additive contract accepts the selected whole-slot phase map for the private
Swift cache candidate2. It does not change `swift-cache-stage-contract.md`, the
runtime-control implementation, the existing foundation counts or their measured
16,504-byte Apple arm64 total. It does not accept the complete cache candidate,
authorize an executor implementation, or qualify target execution.

The exact implementation source is `vm/src/experimental_swift_reactor/cache.rs`,
SHA256 `3a247fdfe0a09e39b6185a303168f48f0e30274d836207bcf5c616d287c3b36d`.
The exhaustive branch/field specification is
`verification/swift-function-cache/candidate-2/preflight-and-root-tail-map.md`,
SHA256 `4e7b7e65e4634c82c7718721f63ab45a730a79fc27243a01b406d6973fd25327`;
its compiler-measured JSON is `preflight-root-tail-map.json`, SHA256
`1089fa9afdc3bf493380da6a3ff73acd6962831456d0d33cb60d2305e00eb695`.
These exact files, including their complete source-to-field map, are incorporated
by reference. A changed branch or ownership graph requires reassessment.

Before ordinary phase enlargement succeeds, the actual proof/control/adopted
owners remain intact in their first whole slots. No ownership move, Partial
construction or final proof/control consumption overlaps prepare. Complete groups
may use only the following whole local transfer slots:

| Slot | Whole bytes | Complete phase group | Measured bytes |
| --- | ---: | --- | ---: |
| Control2 | 1720 | PreflightGroupA | 1352 |
| Control3 | 1720 | PreflightGroupB | 1664 |
| Proof2 | 664 | PreflightSetupInventory | 440 |
| Proof3 | 664 | PreflightOwnerInventory | 352 |
| Adopted2 | 712 | PreflightPrimitiveInventory | 368 |
| Adopted3 | 712 | PreflightEnlargeInventory | 632 |

Pure layout sums use explicit const evaluation. Actual runtime getter/results,
closures, retained caller values and the entire failing enlargement chain remain
counted. The newly requested enlargement cannot fund its own preflight. Each
complete helper group ends before a later owner transfer uses that slot. This is
an accounting phase alternative, not aliasing or placement inside Rust objects.
No padding, remainder, foreign owner or inferred last-use savings are available.

During ordinary cache boundaries and same-header final completion, whole Control2
instead covers CompletionBorrowInventory192, including the actual40-byte returned
tuple and caller outcome reference. Whole Control3 covers RootLeafInventory1632.
Its mutually exclusive complete members are admission1136, owner720,
work_live1632, remove_live560 and refund1104. A member cannot change while its
caller frame survives. In particular the remove-live underflow member includes
the simultaneously active caller and cleanup-fault chain; it cannot switch to
another member to hide those values.

The final completion helper consumes all large cache/tail/Result/Option transfer
storage before returning the small tuple. WASI sampling's owner member ends
before the refund member starts; a second sampling statement ends before
record_cleanup. Root failure/usage/ticket/optional-WASI classes retain their
original separately mapped counts. The caller-held observation and copied outcome
are explicitly accounted; no value borrows the released cache header or a foreign
WASI header. All these borrowed phase groups end before actual control consumption.
The exclusive tail borrow and consuming helper boundary enforce that ordering.

The accepted measured component sums are cleanup62096, header62424,
construction57128 and operation80566 for this exact source/toolchain. Other targets
must measure their own actual size/alignment and satisfy the same complete-group
fit assertions. These are authored named Rust value footprints; they do not claim
compiler stack placement, opaque library internals, allocator overhead or RSS.
Caller/executor objects outside this selected graph require separate upfront
envelopes and cannot reuse these slots without their own proven phase map.

Independent review matched all138 layout rows and582 fields across24 inventory
groups in both Debug and Release, recalculated literal component sums, and
reviewed the ownership/statement boundaries. Root acceptance is recorded in
`verification/swift-cache-foundation-phase-review/acceptance.json`. Complete
candidate2 behavioral, legacy, privacy and coverage qualification remains separate;
owner-identity exhaustion and every-terminal sticky behavior are not inferred
from PinLimit/nonce cases. No full Swift target, device, release or GA gate passes.
