# Proposed finite Rust protocol v1 (awaiting root coordination)

This is the implementation contract for a finite-only copied-VM experiment. It
selects no target, native execution, analyzer, production policy or live VM edit.
The immutable input is the named 132-file manifest, SHA-256
16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd.

## Wire

All numbers below are little-endian u64. Ordinary record word indexes are:
0 seq, 1 kind, 2 phase, 3 operation, 4 successful cache_work,
5 instructions, 6 function, 7 body_offset, 8 body_len, 9 type_index,
10 slot, 11 pin_slot, 12 actual pin_nonce, 13 a, 14 b, 15 c.
Absent identity/slot is MAX; unused payload words are zero. Function <80000,
slots <64, plan index <512; every field is closed per event below. There is
no scalar-authority/shadow resident ledger in the observer. Every body identity
comes from the already validated descriptor; release identity comes from the
already checked actual resident/token. Events do not borrow an owner after take.

Kinds: 1 AcquireBegin, 2 Lookup, 3 PlanBegin, 4 PlanEnd, 5 MissReady,
6 EvictBegin, 7 EvictTaken, 8 EvictCommit, 9 BuildBegin, 10 BuildReady,
11 PinPublished, 12 Release, 13 Phase, 14 Failure.
Phases: 0 construction, 1 Initialize, 2 Corpus1, 3 Corpus2,
4 preconsumption, 5 final-cleanup. A finite caller may exercise a subset;
its expected phase mask is an explicit selection input, never inferred complete.

Field contract (all unmentioned slots/pin slots absent, nonce zero, a/b/c zero):
* AcquireBegin: operation is a new nonzero checked counter; function is the
  requested u32, body_offset/body_len/type_index are MAX. Fires before the
  original check_header in CacheOperationPhase::pin.
* Lookup: current operation and full immutable body; a=0 miss or 1 hit;
  slot=hit slot for hit, absent for miss. Fires only after resident_lookup Ok.
* PlanBegin: current operation/full body; c=function&511. Fires immediately
  before original policy() debit in SwiftMode::scan; no plan identity read yet.
* PlanEnd: current operation/full body; a=0 empty scan, 1 conflict scan,
  2 matching plan; b=conflicting function only for conflict, otherwise MAX;
  c=function&511. A prior plan function is captured only after the original
  function-probe debit; success after matching counts copy or full publication.
* MissReady: current operation/full body; a=requested decoded bytes,
  b=original base, c=capacity. After original Counts::bytes and entry/base checks.
* EvictBegin/Taken/Commit: current operation/full acquiring body; slot=victim,
  a=victim bytes. Begin precedes original resident_remove; Taken follows take;
  Commit follows successful drop_entry and usage.evicted. No fabricated Commit.
* BuildBegin/Ready: current operation/full body; a=requested decoded bytes.
  Begin before M::build; Ready only after its successful Result and before check.
* PinPublished: current operation/full body; slot=entry, pin_slot=pin record,
  nonce=actual returned token nonce (old next_nonce, NOT its successor);
  a=0 hit or 1 built, b=resident bytes, c=post-publication pin count.
* Release: operation=0; actual resident function/body_offset/type_index,
  body_len=MAX (not retained by DecodedFunction), real entry/pin slots/token nonce,
  a=resident bytes, c=post-release pin count. After original checked_record,
  release control, usage/slot mutation and pin-record clear. No success on error.
* Phase: operation=0; absent full identity; a=new phase, b/c=0. Caller supplies
  only original synchronous seams; no lifecycle harness edit is selected here.
* Failure: operation=current nonzero attempted pin for a failed pin, or zero for
  a terminal original Result. Full body identity absent, function=original optional
  failure cursor or MAX; slot/pin_slot absent; a=closed original failure kind,
  b=closed source code ID, c=original stage. Unknown source code flags invalidity;
  no allocated error text, classification error or successful-work invention.

The source-code ID table is source-code-table.json (IDs 1..24); unknown code refuses
complete telemetry while preserving the original Result. The unchanged original
failure object is retained by its existing caller before supplement classification.

## Frames

Header is 512 bytes (64 words). Word 0 magic=0x315244524f58494d
(bytes MIXORDR1), 1 version=1, 2 header_bytes=512, 3 record_bytes=128,
4 footer_bytes=512, 5 record_cap (1..4194304), 6 max_function=80000,
7 max_slot=64, 8 max_plan=512, 9 expected_phase_mask, 10 flags=0,
11..15 reserved=0. Bytes 128..159 selection-context SHA256,
160..191 exact schema SHA256, 192..223 baseline-manifest SHA256,
224..255 candidate-manifest SHA256. Bytes 256..511 reserved zero.
No per-frame allocation/hash/path serialization happens in hooks.

Footer is 512 bytes. Word 0 magic=0x31444e454f58494d (MIXOEND1),
1 version=1, 2 stored, 3 attempted, 4 dropped, 5 last_seq, 6 last_work,
7 last_instructions, 8 last_operation, 9 sticky_flags, 10 terminal_work,
11 terminal_instructions, 12 terminal_failure_kind (0 success),
13 terminal_code (0 success), 14 terminal_stage (MAX success),
15 observed_phase_mask; 16..23 original final consuming reservation currents
(source,metadata,cache,state,wasi,shared,construction,combined),
24 live_tickets, 25..30 live currents (entries,pins,frames,values,controls,pages),
31 cleanup_invariant (0 absent, 1..5 closed actual enum), 32 original-result-kind
(0 success,1 original failure), 33 final_phase, 34 writer write_attempts before terminal-frame block,
35 cap; 36..39 selection digest, 40..43 schema digest as raw bytes;
44..63 reserved zero. This is original consuming-ledger observation,
not per-slot drain events or inferred zeros.

Only exact field/sentinel/reserved enums and length/count-consistent frames
are accepted. No footer is written after failed admission closure/quiescence.

## Sidecar and custody

A closed UTF8 JSON object <=8192 bytes has exactly keys version, status,
selection_sha256, schema_sha256, header_sha256, original_result_sha256,
stream_sha256, stream_bytes, writer_initial, writer_final, reader_before,
reader_after, copy_before, copy_after, copy_sha256, copy_bytes, copy_attempts,
metadata_results, failure. Hashes are lowercase 64 hex, version=1;
status is complete-records/truncated-prefix/invalid/unavailable.
Custody values are null only on the separately recorded failed operation, or
exact objects {dev,ino,mode,len,mtime_sec,mtime_nsec,ctime_sec,ctime_nsec}.
metadata_results is a fixed 8-element closed code array (0 success,1 unavailable,
2 IO,3 identity drift,4 type mismatch,5 length drift); failure is a closed code
0..15. copy_attempts is 0 or 1. No extra keys/paths/variable error strings.
Original result persistence precedes all supplementary classification. One
exclusive/no-follow original plus at most one exclusive evidence destination;
regular-file and descriptor/path identity before/after reading and copying;
one copy attempt, no retry; retain partial destination on failure. Two stream
files total <=1073743872 bytes, plus this sidecar. Host-copy inventory is
separate <=131072 bytes, one [u8;65536], two live descriptors maximum;
32 combined read/write/Interrupted attempts per block. No target driver or
stdout/stderr draining is implemented in this slice.

## Hook ownership and clock seam

Copied changes initially named: experimental/cache/borrowed.rs,
experimental_swift_reactor/cache.rs and cache_tests.rs. Trait callbacks are
cfg(test) with empty Frozen defaults; only SwiftMode forwards. No callbacks in
Frozen mode, production builds, constructors, meter work debits or cleanup drain.
Generic callbacks take only immutable scalar arguments/body views and the
existing meter/release-control mutable reborrow. Swift forwards into the
cache_tests-owned fixed observer; callbacks return (), never a product Result.

NEW NECESSARY SEAM REQUIRING ROOT AGREEMENT: current RuntimeControl::usage()
reads Instant::now(). Calling it from added hooks violates the no-observer-clock
rule. Add only a copied cfg(test) scalar accessor in control.rs returning
(cache_work,instructions) directly, no clock/usage/WASI snapshot. This is a
fourth copied-file deviation, no live edit. Inventory complete SwiftRunUsage,
Option<WasiUsage>, Result/SwiftRunFailure helper shapes nevertheless for existing
caller return/snapshot roles, rather than hiding them as zero-sized borrows.

Begin prebuilds header, exclusively owns File, claims inactive atomic gate once,
then sets owner-thread TLS lifetime coordinate. Dispatch uses a Rust non-Send
lifetime guard (PhantomData<Rc<()>>) owned by one test thread; every callback-
capable finite cache call is synchronous lexical guard dispatch. End consumes
that guard, closes admission first, rejects nonzero in-flight or wrong owner,
and only then borrows/flushes/footer-writes. An ended guard cannot dispatch.
No callback worker exists; explicit wrong-thread/reentrant finite controls join
fixture threads before custody. Gate entry must register before owner/latch or
RefCell touch; no spin/wait, <=8 atomics/transition. Concrete bounded gate proof
is a separate required implementation result, not claimed by this proposal.

Observer has one RefCell<Option<Writer>>, external AtomicU32 sticky flags,
AtomicU64 combined mode/in-flight gate, checked AtomicU64 lifetime allocator,
TLS Cell<u64> owner coordinate; no extra cache/meter/control field. A callback
uses try_borrow_mut, faults latch invalidity while admitted, then leaves with
release ordering. End acquire observes all admitted flags. Cap/IO/context/
overflow is sticky: ordinary writes never resume after a gap; Result unchanged.
Writer is [u8;4096], [u8;128], finite scalar coordinates/counters, one File.
Every block has <=32 write attempts including short writes and Interrupted;
WriteZero/errors/exhaustion sticky freeze. Header/footer 512-byte owners,
full io::Result/error, iterators, every helper argument/return/reborrow, gate
atomics/TLS/guards/layout and three conservative helper copies are measured
in the disjoint external <=16384-byte logical inventory. No allocator call
per event, no dynamic map/queue/string/fmt/scan/sort, no product slack funding.

## Closed enum and acceptance amendment

Failure kind IDs 1..21 in this exact order: InvalidBudget, Cancelled, Deadline,
Allocation, Adoption, CategoryExhausted, CombinedExhausted, ResourceExhausted,
FuelExhausted, WorkExhausted, HostCallLimit, PinLimit, FrameLimit, ValueLimit,
ControlLimit, DecoderMismatch, UnsupportedEnvironment, GuestTrap, GuestExit,
Wasi, Invariant. Zero means no failure only in the footer, never Failure event.
Stage IDs 1..6: Adoption, Cache, Initialization, Invocation, Wasi, Cleanup.
Cleanup IDs 1..5: ReservationOwner, ReservationUnderflow, MissingConstruction,
ConstructionBound, LiveUnderflow; 0 means None. No Rust enum discriminant is
serialized by casting; exhaustive explicit match supplies each integer.
The source-code table supports exactly 24 selected original cache/control codes.
It is an explicit match, no hook table scan or allocated lookup. Unknown static
code latches CODE, invalidates the supplement and preserves the original error.
Its 24 literal byte lengths and match temporaries count in the logical inventory;
no binary literal deduplication is assumed. Full-target code coverage is pending.

Sticky flag bits: CAP=1, IO=2, CONTEXT=4, BORROW=8, RANGE=16,
OVERFLOW=32, LIFECYCLE=64, CODE=128, GATE=256. Bits >=512 are invalid.
Flags are monotonic during an active lifetime and reset only while closed,
quiescent, with no writer and after prior finite fixture threads join. A dropped
cap record sets CAP; all later writer calls add one attempted/dropped only.
IO/range/counter/context/borrow/gate faults never clear CAP or resume records.
Observer failure cannot become SwiftRunFailure. Initialization failure yields
unavailable telemetry, no hook-owned file or product error.

Writer attempted counts only exclusive writer invocations (not refused-context
or failed-borrow calls). With checked additions, attempted=stored+dropped,
0<=stored<=cap<=4194304, last_seq=stored; dropped=0 when flags=0.
Stored counts accepted whole logical records, including unflushed buffer bytes;
partial writes are IO invalidity and cannot pass exact framed-file length.
File bytes must equal 1024+128*stored for a valid frame, including cap prefixes.
Cap-only requires stored==cap and attempted>stored and dropped>0; shorter
cap-only streams are invalid. Write attempts are checked and <=4194368 at the
maximum cap, including separately bounded header and footer blocks. A single
512-byte frame/block or <=4096-byte ordinary block has <=32 attempts.

Phase starts construction=0. Every emitted Phase changes to a strictly greater
phase <=5; its record phase and payload a are equal. No duplicate/regression or
unknown phase/mask bit. The exact selected expected mask is nonzero, <64,
includes construction and final-cleanup; observed mask includes each actually
entered phase. Zero-flag finalized telemetry requires observed==expected and
final_phase=5. Expected masks are finite fixture/selection scope only; even
mask=63 never proves product lifecycle completion. A pin Failure prohibits
further AcquireBegin; cleanup/release/phase/terminal observation may follow.
Construction/non-cache failure has operation=0 and an absent or independent
actual cursor. At most one original terminal Failure event; a prior failed-pin
Failure is distinct and must refer to its actual attempted operation. New
operations are strictly sequential and nonzero. Release remains operation=0.

Footer finalized means: End closed admission; count was zero; owner/lifetime
matched; synchronous-call boundary proof held; no concurrent writer borrow;
footer was attempted once from original terminal/final-consuming observations.
Finalized does not mean valid. complete-records additionally requires zero
flags, exact header/schema/selection/context and file framing; counts and phase
mask agree; original terminal/failure kind/source/stage match the preserved
original Result; all original final consuming reservation/live currents and
live_tickets are zero, cleanup_invariant=0; and independently validated event
replay. The full bounded replay analyzer is deferred, so the finite writer must
report framed-finite-fixture scope, not claim product complete-records coverage.
A successful consuming ledger cannot erase retained replay residents or pins;
no per-slot cleanup events or inferred drain are emitted. cap-only with a
valid exact prefix is truncated-prefix. IO/CONTEXT/BORROW/RANGE/OVERFLOW/
LIFECYCLE/CODE/GATE alone or mixed with CAP is invalid. Missing footer, malformed
reserved/closed fields, unstable custody or unreadable stream is invalid; no
stream initialized is unavailable. A diagnostic failure never rewrites result.

Sidecar success consistency: complete-records/truncated-prefix has all six
custody objects nonnull (writer_initial/writer_final/reader_before/reader_after/
copy_before/copy_after; descriptor/path checks are represented by
metadata_results), all hashes present, copy_attempts=1, copy_bytes=stream_bytes,
matching stream/copy hashes, metadata_results=[0;8], failure=0. writer_initial
length=0, other final objects have exact relevant length; dev/ino/type agreement
is checked within each descriptor/path pair; copy has a distinct owned inode.
Invalid/unavailable uses failure=1..15 and at least one actual failed operation,
with null only for a not-obtained custody/hash value; it never invents zero-valued
metadata. unavailable requires stream_bytes=copy_bytes=0, copy_attempts=0 and
no stream hash; invalid retains actual bounded partial lengths, hashes when
obtained and copy_attempts 0/1. No second copy destination or retry is allowed.
Failure IDs: 1 init,2 exclusive-create,3 no-follow,4 nonregular,5 metadata-IO,
6 identity-drift,7 length-drift,8 read-IO,9 write-IO,10 attempts,
11 frame/schema,12 original-result,13 hash/copy mismatch,14 quiescence,
15 other closed observer invalidity. There are six custody objects (not eight);
metadata_results has exactly eight ordered checks: writer-before,writer-after,
reader-fd-before,reader-path-before,reader-fd-after,reader-path-after,
copy-after,copy-reverification. Each object contains raw st_mode; regular file
is independently required. Whole-file custody drift has invalid precedence.

Non-Send lexical dispatch is only one part of quiescence evidence. Static
SwiftMode hooks remain callable after End, so callback entry always tests the
combined active/closed gate before TLS/latch/RefCell. A refused closed hook
cannot borrow the writer, update frozen flags, emit/flush records or write a
footer. Finite tests must invoke actual hook entry after End and show unchanged
frame bytes/flags/writer count with a separate returned refusal observation.
Each success fixture's counted actual callback-capable calls occur before End,
return synchronously, and original cleanup consumes every cache/control owner
before End; no callback-capable worker or call is retained by observer guards.
Negative in-flight fixtures use only bounded joined test threads; nonzero count
refuses footer and every writer borrow at End. Concrete atomic ordering/count
proof and complete measured inventory remain required implementation results.

Release identity correction: DecodedFunction retains no body_len. Release writes
body_len=MAX, and directly reads function/body_offset/type_index from the actual
checked resident. It does not perform a new snapshot lookup or retain a side
identity map. Independent replay must join the release token to its prior actual
PinPublished identity. This is deliberately event-specific absence, not an
invented complete descriptor. Footer word34 is the pre-footer attempt count;
the actual footer-block attempts/result are retained in the external receipt.
