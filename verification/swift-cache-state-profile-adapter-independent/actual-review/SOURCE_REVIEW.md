# Independent source and accounting review

The reviewed implementation is the 131-member copied Rust crate source tree
`d65ea46493da772cdbf15c3f00da366feb43113c52104079147449c0aa9789cf`.
The adapter is SHA256
`7f4458ddadb0480fe48a5ec57cbc1a11bfa074037eb41eeeb5edd8465fff87d8`.
All 481 released packet members were checked independently. All 129 original
VM members match their precompile freeze except the declared private mod.rs
addition; removing precisely that addition reproduces the original bytes.
The selected validator/shared inputs and all three closed fixture library
sources match the independent preaccess snapshots. HEAD is contextual only.
No live/canonical file, public API or cache/control algorithm was changed.
This closure is Cargo.toml/Cargo.lock/src/tests, not a byte-complete archived132
distribution. Three archived include/*.h files are outside Rust compilation.
No equality to that entire archived distribution is claimed. The disclosed
borrowed.rs/cache.rs/control.rs/cache_tests.rs differences against archived
completion receive no cache-construction or diagnostic runtime acceptance.
Equality of nine validator/shared files is not whole-distribution equivalence.

## Sealed owner and row identity

The actual owner stores a private Box source, private metadata/policy and fixed
imports. The selected constructor completely validates bodies before sealing it;
there is no public field, Clone, mutable source, alternate constructor, metadata
deserializer or implemented external owner trait. The new module accepts exactly
that owner borrow. Its new module and row helper are private, and its writer,
observation and error are crate-private with private fields. No new public
export or authority constructor appears in mod.rs.

`admit` checks fixed revision, the sealed policy identity, 34 imports, equal
defined/validated body counts, type narrowing and checked total <=80,000. The
constructor's unchanged fixed type/source/function policies close stronger
invariants; a synthetic owner is neither necessary nor allowed to test defenses.
The `execution_function` callee subtracts the fixed import count, makes one
metadata index lookup and creates one borrowed source span. `Span::slice` uses
the original validated absolute byte coordinate. No new Wasm parser, body scan,
pointer subtraction, body copy or descriptor-from-event constructor is added.

Every row is checked against its requested absolute index, actual type count,
checked body end and retained source extent. Imports and unused rows must have
no descriptor and get exact undefined sentinels. Missing metadata within the
declared defined range fails. The writer serializes each field in little endian
and never serializes a Rust memory image. All three independently encoded
positive candidates passed the actual validator in both modes. Their complete
80,000-row Files match independent expected bytes, including absolute79,999,
type128, body lengths127/128, a call to absolute128, equal-content distinct spans,
imports and undefined tail. The five independently encoded malformed candidates
actually return no owner. No refusal is miscredited as a profile error branch.

Safe accepted owners cannot reach snapshot inconsistency, missing descriptor,
inconsistent descriptor, or 64-bit checked narrowing overflow. Codes1/3/4 and
those code13 paths have source/invariant review only. Code2 is actually checked
at80,000 and u32::MAX with widened coordinates2,560,000/137,438,953,440. Admission
is a zero-offset preflight. `with_progress` changes only output counters and
preserves any row error's coordinate; propagation from an inconsistent owner
is not represented as runtime coverage.

## Actual File and bounded writer

The safe writer borrows its caller's File. It admits snapshot, regular File,
initial length0 and position0 before creating the block. It does not reopen,
truncate, retry another path, close, transfer or retain the File. The caller must
keep the File/open-file-description offset quiescent, including aliases.

The sole output block has4,096 bytes. The range has625 iterations, each deriving
128 rows, so first+local is at most79,999. All blocks are complete; no partial
last-block case can silently change the protocol. `done <=4096`, and each valid
acknowledgement is in1..remaining. This bounds global bytes by2,560,000. Calls
increment before the callback, reset only for a new block and are checked before
a prospective33rd call, bounding attempts by20,000. Error, zero and overreport
on call32 retain9/10/11. An incomplete short write or Interrupted on call32
reaches12 before a33rd call. A completing32nd call exits successfully. Returned
overreports never enter byte arithmetic. Finish only constructs scalars; it
performs no syscall, flush, fsync, digest or durability operation.

All29 predeclared schedules ran against this actual private loop through its
selected callback seam in both modes. Valid prefixes were forwarded by one
safe actual File.write per acknowledged callback; retained Files were read and
compared byte for byte in Rust, then hashed independently in Python. Interrupted,
zero, ordinary error and overreport are callback injections, not claims that
the kernel produced each fault. Error/overreport side-effect controls retain3/7
physical bytes while acknowledging0, explicitly disproving rollback inference.
The public File entry separately passes exact complete body, nonempty,
nonzero-position, directory and actual read-only first-write failure controls.
Its code9 error for read-only output has stage4/offset0/bytes0/attempts1.
Metadata/position syscall failures5/7 remain safely uninjected and source-only.

## Measured layouts and complete source places

Fresh Debug and optimized compilation agree on row32/align8, observation64/8,
error32/8, complete row Result40 and writer Result72, row caller88 and writer
caller152. The complete snapshot constructor Result is664, equal to the actual
owner object's664; its error is136. This was measured, not inferred from a tag
or payload. A tuple reserving both constructor Result and owner is1,328.
Metadata Result152 includes Metadata144; I/O Results16 include error8. Descriptor
and Option<descriptor> both32, observation copy136, Option<usize>16, conversion
Result16, range8 and StepBy24 are measured. These are type/layout observations,
not stack-frame, RSS, allocator or machine-register measurements.

I reviewed the producer's per-place table for every lexical adapter function.
Its7,504-byte whole sum adds all phases, both mutually exclusive external
callers, all lexical errors and conversions. I retain that table as a
conservative base, then explicitly add called source-view return/argument and
closure/iterator places rather than assume implicit return-slot reuse:

| Additional whole-source place group | Bytes |
| --- | ---: |
| Three observation return destinations136 plus argument8, all call sites summed | 432 |
| execution_function / Span::slice arguments, checked index Option, metadata borrow, span, range, source/body slices, constructed/returned view; includes conservative per-place padding | 512 |
| policy_identity argument, str return and discriminant place | 32 |
| Both source() argument/deref/return-borrow sites,48 each | 96 |
| Row/finish progress closures and checked-error captures, all sites summed | 128 |
| Additional range/StepBy construction/return places | 40 |
| Added source places | 1,240 |
| Adapter/caller/callee subtotal before source-expression Result transfers | 8,744 |
| All17 try/map/checked-expression transfer banks, four complete places per expression (16x40 plus1x152), all sites summed | 3,168 |
| Complete adapter/caller/callee whole-source union | 11,912 |
| Full constructor Result, helper owner return, and caller-owned snapshot,664 each, all phases summed | 1,992 |
| Conservative combined fixed source-place sum | 13,904 |

The512-byte lookup/span group deliberately rounds up this bounded source chain:
owner/index args16; checked-sub Option8; defined value8 rounded; metadata lookup
Option/reference8+8; copied span8; offset/cast8; constructed view32; returned
Option/view32; Span/source args24; range16; both range bounds16; source and body
slice returns/borrows16+16; and fixed scalar/index/transfer/padding places. Its
explicit subtotal is216, below512, with no array or recursive call in that chain.
The128-byte closure group reserves five16-byte progress captures plus five8-byte
row-error captures (120), rounded up. No backing body is owned by these views.

The17 expression banks cover admit's checked total; the row helper's admission,
checked end, descriptor extraction, checked body end and two conversions; output
metadata/position mapping; writer admission, row mapping and four finish
conversions; and the two public-wrapper admissions. Fresh targeted compilation
measures complete Result<usize/error>, Result<u64/error>, descriptor/error and
their try ControlFlow places as40, mapped metadata Result/ControlFlow as152,
and residual Result<Infallible,error> as32. Each site's bank reserves four full
largest relevant places (source receiver/input, mapped return, try ControlFlow,
residual/propagation), even when some do not coexist or are already counted in
the base table. Thus this proof does not omit a complete generic Result because
only its payload appeared in an original function's named locals.

This combined sum adds mutually exclusive construction and writing phases and
both external callers. Thus each actual simultaneously-live subset fits it
without return-slot reuse or charging another owner's spare capacity. In the
actual test callers, validate(...).unwrap() returns its owner and its constructor
Result is consumed before the later writer borrow. I still sum its full source
place plus a distinct owner return and caller owner. Row-helper descriptor/body
borrows end before scalar encoding. During I/O the row/helper frames have ended;
the buffer, slice, callback borrow and full I/O Result remain. Error paths retain
only fixed scalar errors. All these lifetimes follow actual source, not the
layout of an imagined owner trait or a fabricated snapshot.

Retained source (<=64MiB), metadata (<=16MiB), constructor scratch (<=1MiB),
source-visible caller input, allocation capacity and validation work/deadline
remain separately owned/charged. The arbitrary test fixture/expected Vecs and
other unrelated caller allocations are not component memory. Later real callers
must repeat their complete lifetime/reservation join. There is no new debit,
engine reservation, relaxed cap or use of the old fixture29,344-byte/G totals.
No explicit new product allocation exists; observed positive row/File regions
make zero allocation requests. This does not prove standard-library/kernel
allocation behavior on every fault or include an arbitrary private test callback.

## Explicit source-work bound

The accounting unit is a scalar operation, byte transfer/comparison, branch,
counter or complete source-level Result transfer; it is not CPU instructions,
VM work credits, time or a standard-library implementation bound. I use the
following deliberately conservative allowances, independently of97,301,024:

| Item | Allowance | Multiplicity | Bound |
| --- | ---: | ---: | ---: |
| Row admission/derivation and called source helpers/errors/Results | 4,096 | 80,000 | 327,680,000 |
| Five LE conversions, source/destination slices and32 wire-byte transfers | 256 | 80,000 | 20,480,000 |
| Row induction/index/bounds/call transfers | 128 | 80,000 | 10,240,000 |
| Block induction/resets | 128 | 625 | 80,000 |
| Write classification, progress/error and counter transfers | 512 | 20,000 | 10,240,000 |
| The one initial buffer zero | 4,096 | 1 | 4,096 |
| Wrapper/output admission/finish and all fixed transfers | 8,192 | 1 | 8,192 |
| Maximum cumulative requested I/O byte extent | 4,096 | 20,000 | 81,920,000 |
| Total source-action plus requested-byte bound | | | 450,652,288 |

The4,096 row allowance closes the exact nonrecursive source chain: two136-byte
observation return/caller copies (544), policy return/string comparison (<=224),
index/span/type/body-end lookup and bounded slice transfers (<=512), complete
argument/Option/Result/row transfers including mutually exclusive branches
(<=1,024), scalar control/comparison/checked arithmetic (<=512), and every fixed
error/progress construction/return path (<=512). Their subtotal3,328 is below
4,096. There is no body scan in that chain. Policy comparison is bounded by its
27-byte fixed literal. LE conversion/copy work is fixed; indices have maximum
4,096. Callback classification is fixed and cannot repeat beyond the declared
32-call allowance. The final requested-byte term conservatively counts even
repeated Interrupted slices. Actual successful acknowledgements remain exactly
2,560,000. The bound explicitly includes initialization and called source places;
it does not assert equivalent VM debit or qualify host syscall latency.

## Replay, warnings, joins and limits

Fresh behavioral replay has86 successful bounded commands: exact17/403 selected methods
(386 filtered) and independent5/408 methods (403 filtered) per mode, no ignored
or failed methods; selected16 plus independent18 bridge invocations per mode.
Names, listings, output, expected counts and every bridge input are retained.
The derivative appends only the fixed cfg(test) module declaration and its
independent test file; the original131-member copy remains exact. The first
shared-target attempt refused missing derivative methods and grants no
derivative credit. Fresh exact/derivative target directories are separate.
Six additional bounded commands compile/list/run the single missing-layout
closure method in each mode (404 listed,1 passed,403 filtered,0 ignored/failed).
That third source copy appends only a different cfg(test) layout module to the
unchanged producer base; it does not mutate either qualified behavior copy.

The unchanged fixture library has normal unsuppressed diagnostics in both modes:
148 warnings, exactly matching the retained inherited source locations/kinds.
The bridge compiles with-Dwarnings and no warnings. The new adapter has its
selected scoped deny(warnings) with a documented isolated-prerequisite
allow(dead_code); the two inherited VM Copy-drop warnings remain outside it.
No warning exception is extended to new unreviewed source. This review uses
actual Rust1.99.0/aarch64 macOS only, not Rust1.98.1/Linux/CI qualification.

The complete independent owner File body is compared to its oracle before the
synthetic bridge. Ten row-schema patches and four concrete body/event mismatch
patches refuse in their applicable consumers; equal bytes at different offsets
still fail identity substitution. The phase-only in-range mutation is observed
without a body join. The collusive import/tail defined rows plus matching events
are actually synthetically admissible, so the unchanged analyzer is not an owner
provenance verifier. All getter assertions remain false for every invocation.
Failure14 applicability is unavailable, CAP is unknown tail, and late footer
suppression is exercised. Concurrent drift and report-output failure are
unchanged upstream paths, not newly qualified here.

Hostile inherited RUST_TEST/flags/wrapper/tool/TMP variables were scrubbed; every
child got owned TMPDIR=TMP=TEMP, explicit existing compiler, offline Cargo and
owned separate targets. No launcher sentinel ran. All children were reaped;
disposable products were hashed and scratch removed. No native/UI/capture,
process inventory, Git, forbidden hosted harness or full target/103-command pack
was used. The supervisor is trusted quiescent host-test support; it is not the
future hostile filesystem/CLI custodian.

The independent recommendation is limited to this isolated row-body prerequisite
and its new source-level proof. Real profile header/cache/configuration/layout
binding, original typed result/final ledger joins, cryptographic descriptor
custody/CLI, full replay/semantic metrics, runtime/target/native behavior,
published-package FieldLog, signing/store/customer/operations and GA remain
unqualified. Root controls any acceptance, integration and delivery.
