# Independent review of root's final-boundary correction

**Accepted for this exact bounded accounting correction.** Root integration and
executor implementation acceptance remain separate. The final source is bound in
`decision.json`: control SHA256
`424a544b29bc506f3d064620b339e11753aab5dd76c0285da1dbdd4d1e8db31c`,
control tests `ff2e38b0f365890ce3f63bbc76776c6d1c5d4b501386a5e25a23ca4cbe5ec68b`,
cache tests `c39b1ebb527c6cf4921bce31f9e811bfd1e485f76f09400d41546ca06426be09`.
The original executor layout files remain unchanged, including executor source
`33f4ae0f00f20c24656a3456e5203a980e456acbb22a72214b74e82eb423f81e`.

`rebound/input-manifest.json` freezes all final relevant VM inputs before reads;
its source-tree digest is
`37fcd76f824dfc2eb8e25006433fa2377dc571e37c24fac43405577ae0857f5a`.
Pure frozen source lives under `rebound/inputs/frozen-vm/`. The separate derived
`tree/` adds metadata hooks and one independent test only. No production file,
tracker, contract, earlier review or earlier seal was edited by this reviewer.
The initial private-const correction's snapshot and successful checks remain in
the parent `inputs/`, `tree/`, `logs/` and `commands.json`; `rebound/rebinding.patch`
records the final visibility/cache-expectation delta.

## Production mapping and phase proof

All **seven production inventory types and 84 fields** match the previously
reviewed source roles, concrete types, sizes, alignments and offsets. This is a
field-level comparison, not a total-byte fit. The resulting complete groups are:

| Actual production type | Size / alignment |
| --- | ---: |
| FinalOutputBorrows | 16 / 8 |
| FinalClockInventory | 224 / 16 |
| FinalFaultInventory | 264 / 8 |
| FinalCategoryInventory | 40 / 8 |
| FinalRefundInventory | 688 / 16 |
| FinalRecordInventory | 272 / 16 |
| FinalFinishInventory | 864 / 16 |

Production and cfg(test), Debug and Release, produce the same seven group
layouts and every field offset. RuntimeControl remains 1720 bytes / alignment8.
The original engine and owner definitions are byte-identical outside the single
additive inventory/formula block. `rebound/source-review.json` records the exact
field/type matching and `root-control.patch` shows that block against the old
frozen control source.

The missing output references, actual receiver/return borrows, checked Options,
tuple/pattern bindings, Cursor/Fault source/transfer roles, clock/micros scalars,
conversion Result, and complete ticket array/IntoIter/Flatten/next wrappers are
now named explicitly. Whole wrappers are reserved separately; their fields are
not also claimed from the plain-ticket classes. These are never-instantiated
metadata inventories, not new stored runtime owners or a runtime registry.

The existing helper boundaries still enforce the partition. Supplied generic
storage, tail failure and the large returned parts end before header refund.
The refund call and its Result end before record_cleanup; record and the outcome
assignment end before finish consumes the original control. Both output
references persist and appear in all complete groups. The underflow refund
branch retains its checked Options/tuple while fault/fail/usage/micros runs; the
complete Refund group includes both. Finish's checked arithmetic and clock
roles remain in its entire parent group. There is no switch inside a surviving
parent frame or last-use/padding credit.

The original **3 proof / 3 control / 3 adopted / 4 failure / 4 usage / 6 ticket /
6 optional-WASI** class counts and shapes remain literal and separate. Output
failure/usage objects use their diagnostic classes; their reference values use
the new output-borrow fields. Embedded control first-failure/ticket storage is
still charged in the actual owner. Observations remain three for successful
refund, six for nested rejected refund, three for record and three for initial
finish usage. No smaller borrow is relabeled as a failure/usage/ticket object.
The old cache Control2/Control3 phase alternatives are not reused for final
control consumption. No new reservation ticket or widened default budget exists.

## Const formula and admission

Both the complete-group maximum and eight-term checked sum are explicit const
initializers. The runtime foundation function's entire body is
`FOUNDATION_CONSTRUCTION_BYTES`. Its former runtime formula array, IntoIter and
try_fold no longer exist. The seven old terms are unchanged; the eighth is the
new named whole-group maximum **864 bytes**. The target's foundation is therefore
**17,368 bytes**, up from 16,504. Different targets must compile their own layouts;
this is a conservative authored-object allowance, not minimum-byte or physical
stack evidence.

The final visibility change only makes the metadata constant `pub(super)` so
private sibling tests can name the disjoint allowance. The final cache-test
change appends exactly that term and prints it. It changes no owner layout,
algorithm, limit, reservation ownership, failure order or public execution route.
The root appendix, frozen under `rebound/inputs/docs/`, accurately describes this
new upfront admission amount. It preserves the old cache extra envelopes and
historical C3/C2 exact-source receipts, rather than silently reaccepting them as
new foundation evidence.

## Executed evidence

`rebound/commands.json` records 13 successful commands including tool versions
and exact outputs; Rust1.99.0 (b940084d7), aarch64-apple-darwin. For **each** Debug
and Release profile this reviewer executed:

- One unit metadata test and one actual non-cfg(test) production metadata probe.
- Both root correction tests: three exact adoption boundaries (old floor, new
  floor minus one, exact new floor), and seven real AccountedWasi cleanup cases.
  The old/short budgets fail before runtime instruction/host work; exact new
  admission succeeds and drains. Cleanup tests preserve actual ArgsSizesGet
  observation, immutable first cause and independent cleanup invariants; valid
  cleanup reaches zero, rejected charges/tickets stay retained, with no new
  allocations or reallocations.
- One independent supplemental test covering **two further** finish branches:
  damaged Combined current and damaged live-ticket count. Every refund rejects,
  intact category charges remain, cleanup reports ReservationUnderflow, and no
  allocations occur. Damaged counters are not fabricated into an innocent pass.
- The actual corrected cache
  `frozen_layout_allocation_work_error_snapshots` test. The named old classes plus
  `final_boundary=864` produce `total=17368` in both profiles.

The initial corrected-source checks also passed before the final visibility and
cache-expectation rebind. All files listed in the previous review's 143-file
seal still match their original hashes; this review leaves those receipts intact.

This verdict covers only the exact new final-boundary accounting. Root's full
feature/legacy/privacy matrices and final integration decision remain separately
attributed. The model covers authored named Rust objects and requested payloads;
it excludes compiler stack placement, opaque standard-library internals,
allocator overhead and RSS. No executor constructor/interpreter algorithm,
full-target validation/instantiation/initialize/invoke, physical device,
published FieldLog, signing, release, store, operational, performance or GA gate
is accepted here.
