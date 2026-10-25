# Provisional finite source-value inventory and lifetimes

This explains the executable inventory in `completion_tests.rs`; independent
review is required before accepting the proposed bound. All byte values come
from the explicit Rust1.99.0 release execution retained in
`commands/candidate-final-exact-swift/`. This is a named logical source-value
inventory for the **six selected completion fixture paths, their new serializer
and bounded readers only**, not a claim about optimizer copies, actual compiler stack, TLS runtime,
opaque formatting/hash/FileIO internals, kernel buffers, RSS or timing. Existing
VM fixture allocations keep their original product admission and are not funded
by observer storage. The inherited receipt helpers are regression-tested but
their full formatter memory remains unqualified. Rerunning inherited
`ordered_finite_tests` is regression evidence only. Their unchanged pre-End
`format!` helpers and Vec readers do not gain this new inventory qualification.

| Role | Bytes and simultaneous accounting |
| --- | --- |
| Complete TLS RefCell/Option storage | 4,416, even while None |
| Atomics/TLS owner/case counters | 52, including inherited/new fixture ID slots |
| Supported source literals | exactly502, unchanged 24-code table |
| Receipt templates | 1,024 charged; independent conservative no-dedup scan460 |
| Writer and whole Option return/move | 4,408 each, measured explicitly |
| CallbackValues | 584; three complete groups charged |
| BeginValues | 280; refs, checked Option returns, scalars and whole guard return |
| Original-result Outcome | 3,888; pin/release/failure outputs are also charged in their originating phases |
| ReceiptWriter | 544; three complete owners charged for create/local/return/finish transfers |
| FormatterValues | 656; three complete groups include argument array/descriptors, Formatter, every authored write Result/error/range/checked/slice/receiver role |
| Derived Debug values | 704; eight of each measured DebugStruct/List/Tuple/Map/Set helper family |
| EndReceipt | 128; two charged when copied across source roles |
| Metadata roles | 456; complete Metadata and Result owners plus borrow |
| PathBuf allocations | each enforced<=512 capacity, including every extension result |

The aggregate groups map to source values below. These are conservative capacity
groups, not substitutes for complete Result/owner fields in each phase formula.
Unused slots remain charged; no whole Result, writer or buffer is removed.

| Inventory fields | Source-to-role map |
| --- | --- |
| BeginValues.references[16] | `header`, `Writer::new`, `bounded_write`, `begin`: header/frame borrows, bindings iterator/output, File sink, bytes slice, attempts, atomic/TLS references, closure receiver and RefMut/borrow-result references; sixteen pointer words bound thin/fat references and iterator pairs |
| BeginValues.results[4] | original gate/NEXT/INIT compare-exchange Results, checked coordinate/attempt and header-write I/O Result/error roles; four complete16-byte checked-result slots conservatively bound these short-lived groups |
| BeginValues.scalars[8] | cap/mask/code count, coordinate, old gate, loop index, write offset and attempt/length scalars; eight complete u64 words |
| BeginValues.guard_return | complete Option<DispatchGuard>; writer and Option<Writer> charged separately |
| CallbackValues.payload/coordinates/record/body | actual hook payload, clock-free coordinates, constructed Record and immutable body view; three groups cover hook, observer and writer/encoding frames |
| CallbackValues gate/lifetime/operation/sticky and references | `enter`, `owner`, `observe`, TLS closure, `failure`: gate prior, lifetime, checked operation, sticky latch, gate/flag/cell/owner/phase/cache borrows |
| CallbackValues borrow_result/borrow/writer/file | complete try_borrow_mut Result and RefMut plus writer/sink borrows; original whole pin/release Results remain separate |
| CallbackValues write and encode fields | `push`, Record::encode, bounded_write: slices, offset/range/index/output, checked Option, actual io::Result/io::Error/error kind, current word and8-byte encoding temporary |
| FormatterValues.arguments/twenty_argument_roles | custody/usage_keys/failure_keys/persist: complete fmt::Arguments and twenty reference/function descriptor pairs at the largest call; three groups charge caller, forwarding and formatting roles including copies |
| FormatterValues scalars/borrows/formatter | streaming write_str/drain/bounded_write: counts, total/offset/range bounds, receiver/slice/attempt borrows and complete Formatter values |
| FormatterValues Result/error/range/text/bytes fields | complete authored I/O and formatting return/error roles, checked Option, borrowed text and buffer owner |
| DebugValues families | eight complete values per public helper family, covering the nested graph below |
| Outcome/tuple/outer binding | explicit run block, returned non-Copy Outcome+receipt, caller binding and persist borrow; construction/transfer charge two complete Outcomes and two EndReceipts |
| Rows and fixed readers | rows/decode/header_only/parity: four128-byte record/decode/copy roles, complete scalar Rows summary, two512-byte comparison blocks, descriptor/Metadata/Result and iterator roles; no heap Vec |

The separate named union explicitly lists original pin/release Results, cleanup
return Results/usages, displaced ticket, returned token and Rows as well as
Outcome. Distinct non-overlapping source roles are not aliased to Outcome bytes.
The union is not a simultaneous peak.

Eight Debug levels conservatively cover the finite derived-formatter graph:
original Option, SwiftRunFailure, optional after_cleanup, SwiftRunUsage, optional
WASI, WasiUsage, and WasiReservations/its scalar usage child. Selected fixtures
have WASI=None; the deeper family roles remain conservatively charged. Derives
format fields sequentially. Their maximum nested path is charged simultaneously;
it is not multiplied by the total number of sequential struct fields. This
counts the public helper values, not opaque formatting implementation stack.

`start` persists initial descriptor metadata inside a block before constructing
the header. Header construction owns no initialized operation-result output.
During Writer::new, the complete writer local and Option return are both charged
alongside complete TLS storage. During Begin transfer, the complete writer
argument and Option move are both charged. The lifetime guard is non-Copy and
non-Send; the writer is non-Copy. A moved source cannot be used afterward. The
inventory nevertheless charges both sides of each specified complete move.

Every actual new run builds `(Outcome, EndReceipt)` inside an explicit lexical
block. During construction, original Copy-output bindings and the entire new
Outcome are both charged. The non-Copy Outcome moves out as the block ends;
its original Copy bindings are then out of scope before `persist` is called.
For the return/move boundary, the two-complete-Outcome charge also covers the
return temporary and outer binding; these do not require a third simultaneously
valid Outcome after the source block ends. No optimizer or last-use inference is
used. The caller still owns the complete single Outcome through serialization,
record-prefix inspection and later path return.

All callback-capable operations are synchronous. Callback frames have returned
before End closes admission and observes zero callbacks. End's nested footer
frames return before `retire_after_quiescence`; retirement still conservatively
charges the caller's footer, complete original outputs, and complete taken
writer. Guard Drop closes admission first and removes a writer only at zero
admitted callbacks. An actual original Release after Drop is refused by static
hooks; two bounded512-byte file reads preserve the exact before/after bytes.

The receipt formatter owns a fixed512-byte buffer, enforcing an8,192-byte total
before accepting another string segment. It never first allocates an unbounded
format! String. Three complete buffer-owner roles, three complete argument and
write-helper groups, and eight Debug families are charged. Actual original
failure/usage objects remain retained through End, then formatted after quiescent
retirement and before any custody classification. The formatter boundary test
accepts exactly8,192 bytes and refuses one more without changing its total.

Post-retirement row readers use one128-byte block and a fixed scalar summary;
their complete decode/copy roles, reader results, Metadata, full Outcome, paths,
and TLS storage are charged. Parity uses two512-byte blocks and two descriptors,
with an8,192-byte input cap. It compares explicit semantic fields and all
allocation counters; full raw receipts preserve elapsed/deadline/validation
clock observations separately. No Vec/read_to_end/collect allocation is excluded
from the observer lifetime. These source-seam assertions are not full semantic
event replay or a qualified analyzer.

The executable eighteen-phase table and separate49,362-byte all-phase named union
are in `logical-inventory.json`. The proposed maximum is16,114/16,384, a270-byte margin.
Retirement is16,106; serialization15,466. This narrow margin and every complete
return/helper/source lifetime require review. The all-phase union deliberately
contains owners that never coexist and must not be called a simultaneous peak.

Python custody uses separate `_copy`, `_inspect`, bounded-receipt-read and
serialization scopes. Returning from `_copy` ends both closed FileIO owner
objects before `_inspect` owns its sole verification descriptor; there is no
fourth retained frame-reader owner. Copy/verify use one65,536-byte buffer per
non-overlapping function. Receipt reads use one no-follow descriptor and
read(cap+1), so file growth cannot first allocate unbounded bytes. Before/after
descriptor/path identity and exact length must agree. Text/encoded sidecar
copies are charged in their later serialization phase. Named dictionaries,
stat results, hash owners, paths, scalar/reference/exception/result roles and
the extra overflow byte are included in the host phase inventory, whose proposed
maximum is103,777/131,072 bytes. Opaque Python/JSON/hash/FileIO physical memory
is unqualified. General hostile-process races and complete adversarial custody
qualification remain outside this finite fixture result.
