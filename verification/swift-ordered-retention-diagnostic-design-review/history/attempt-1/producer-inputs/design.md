# Bounded ordered Swift cache diagnostic proposal

Propose one isolated **baseline-policy ordered stream**, followed by bounded
offline replay. This packet is design and synthetic codec evidence only. Root
has not selected Rust implementation, source restoration or another actual-target
attempt. No live VM source or root execution metadata changes here.

The original host workload still fails Corpus 1 after **23,358,291 guest
instructions**, requesting CacheWork 64,000,001 against 64,000,000; Corpus 2 never
starts. The accepted attribution measures 61,627 completed decodes, 485 distinct
completed identities and 34,500,496 repeated-build credits (**53.907025%** of the
fixed work budget). Its five snapshots do not contain call order. See the
[accepted runtime audit](swift-current-attribution-runtime-review.md) and
[remaining-work diagnosis](swift-plan-cache-remaining-work-diagnosis.md).

All three retention rejections remain authoritative. Segmented LRU regresses
actual-target progress; cost/age regresses all six finite traces; count-plan cold
insertion improves three finite rows but regresses three and adds **20,472**
operation reservation bytes. Neither the eight-credit model estimate nor an
aggregate repeated-build mean estimates the benefit of avoiding a particular
actual-target decode. This diagnostic selects no new retention policy or tuning.

## Choice and immediate deliverable

| Approach | Information retained | Boundary / reason |
| --- | --- | --- |
| Lossless ordered events until a fixed cap | Actual acquisition, pin lifetime, resident transitions, plan collisions, byte admission and successful work/instruction coordinates | **Proposed.** A contiguous prefix can be replayed under more than one later hypothesis without another target run. I/O may change the observed deadline prefix. |
| Online bounded shadow policies | Outcomes only for the policies and simplifying rules chosen in advance | Defer. Requires multiple accounted resident/pin/byte histories, policy work and failure semantics before the actual order is known. Shadow misses do not execute actual scans/builds or reproduce counterfactual CacheWork timestamps. |
| Aggregate histograms / top functions | Popularity and coarse windows | Insufficient alone: cannot reconstruct a working-set turnover, held-pin obstruction or interleaving collision. |
| Ring buffer or sampled events | Recent suffix or samples | Defer. Lost transitions prevent exact resident/pin replay; a final suffix cannot explain earlier retention. |

The next selectable implementation slice is **finite only**: create one exact
132-name baseline copy, add the test-only writer and hooks below, run selected
synthetic Rust parity/failure/allocation/layout tests, seal source/patch/binary and
independently review them. Root then decides whether to prepare a separately
reviewed one-attempt original-target driver. This document does not authorize
that execution or any native test.

## Source seam and unchanged authority

The named baseline is the manifest at
`verification/swift-count-plan-retention-candidate/baseline-source-manifest.json`,
SHA-256 `16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
Read only those 132 current `vm/` names when checking/copying the VM closure.
Cargo files and production control/limits stay byte-identical. Proposed copied
changes are limited to:

* `src/experimental/cache/borrowed.rs`: `pin`, `pin_acquired` and `release`
  transition hooks. Add `cfg(test)` mode callbacks whose Frozen default is an
  empty body; Swift callbacks reach only the isolated test observer.
* `src/experimental_swift_reactor/cache.rs`: `CacheOperationPhase::pin`,
  `SwiftMode::scan`, `SwiftMode::build` / `build_payload`, and the existing
  Swift-mode override. Read scalar state already validated by the original
  operation; never use a diagnostic value as a product decision.
* `src/experimental_swift_reactor/cache_tests.rs`: fixed external observer and
  finite controls, appended without removing original assertions.
* `src/experimental_swift_reactor/lifecycle_tests.rs`: only a later separately
  selected preparation may connect begin/phase/final snapshots to the original
  harness. That later delta requires its own review.

The accepted prior observer is an inspected precedent, **not an additional
observer silently installed alongside this one**. Its archive, original driver,
strict schema and original result remain immutable. The new observer needs no
per-work-debit logging and does not reuse its 10,504-byte bitmap owner. It has no
new field in cache slots, scratch, meters, control, scan outcomes or Results; no
pin, proof, decoded owner, reservation ticket, worker or guest import is retained.
No new dependency is proposed. Any unavoidable implementation deviation returns
to root before implementation selection expands.

Preserve every original debit, cancellation/deadline check, allocation, identity
validation, index mutation, pin nonce, lowest-slot tie, work timestamp and sticky
failure in the same order. Hooks cannot return `SwiftRunFailure`, reset control,
retry a terminal owner, refund work, move a check, or roll back completed
evictions. Product error/Result and consuming cleanup remain authoritative.
Frozen-mode and diagnostic-disabled outputs must match baseline in finite tests.

## Fixed stream and coverage

The dedicated owned regular file contains a **512-byte header**, at most
**4,194,304 ordinary 128-byte records**, and a **512-byte termination frame**:
**536,871,936 bytes maximum**. No compression, strings, guest data, JSON per
event, ring overwrite or sampling. A fixed 4,096-byte buffer holds 32 records;
only a full block or final partial block is flushed. No memory mapping, async
writer, queue or background child is permitted. Exclusive no-follow creation
and device/inode ownership checks precede begin; no existing file is truncated.

Why this cap: the retained baseline has H=537,576 hits, M=61,628 misses,
A=H+M=599,204 acquisitions and E=61,564 evictions. Allow three acquisition
records, one release per acquired pin, five extra records per miss, three per
eviction, six phases and two failures (pin return and terminal harness):
`4A+5M+3E+8 = 2,889,656` records,
**369,875,968 bytes**, about 352.741 MiB before framing. This deliberately
overcounts the final unsuccessful publication/build and cleanup releases. The
512 MiB cap gives approximately 45.1% record headroom for that *recorded* prefix.
It proves neither future coverage nor a complete run: actual order, error paths,
instrumentation and later phases can consume the cap differently. The default
cap cannot be increased automatically after truncation.

Each record is sixteen little-endian u64 words:

`seq, kind, phase, operation, cache_work, instructions, function,
body_offset, body_len, type_index, slot, pin_slot, pin_nonce, a, b, c`.

`seq` is contiguous from one; phase is a closed enum (construction, Initialize,
Corpus 1, Corpus 2, preconsumption cleanup, final cleanup); operation increments
once per attempted pin. Function/type fields are bounded by the source profile;
function <80,000; slot/pin slot <64, with u64::MAX as an explicit absent-slot
sentinel. Unused scalar fields are zero; absent identity is a separately specified
sentinel in the future closed schema, never a fabricated function. All writes,
counter additions and offsets are checked. Event-specific field meanings and
reserved zero fields must be frozen before Rust implementation acceptance.

| Record | Exact boundary and payload |
| --- | --- |
| AcquireBegin | At the outer Swift pin entry, before its original header check/debit. Function and operation only until original descriptor validation supplies body identity. |
| Lookup | After successful original resident lookup, before hit/miss branch. `a`: hit=1/miss=0; hit slot; validated body identity. A failed lookup has no synthetic completed lookup. |
| PlanBegin / PlanEnd | Immediately before original `SwiftMode::scan` policy debit; then after original matching return or complete scan publication. End `a`: empty-scan / conflict-scan / matching-plan; `b`: prior conflicting function or absent; `c`: `function & 511`. Capture prior function only after its existing probe debit succeeds. No partial scan publishes an End. |
| MissReady | After original Counts::bytes and original entry/base capacity checks, before planning. `a`: requested decoded bytes; `b`: original fixed+scratch base; `c`: cache capacity. Actual reconstructed residents/pins distinguish slot exhaustion from byte pressure. |
| EvictBegin / EvictTaken / EvictCommit | Begin immediately before original resident_remove, with victim slot/bytes and unpinned validation from the original resident. Taken immediately after original slot.take removes the resident, before its fallible drop/refund. Commit only after drop and original usage.evicted. No new fallible product operation separates original index/slot actions. Taken/Commit match their Begin within the operation; a later failure retains the actual removal and any completed usage prefix separately. |
| BuildBegin / BuildReady | Immediately before original build call; Ready after its successful return, before existing publication checks. Work difference covers original build policy/body and their original operations; temporary built owners are not residents. A failed build remains an open interval ending at original failure. |
| PinPublished | After the original infallible decoded/slot publication and complete pin tail. `a`: hit=0/built=1; `b`: entry bytes; `c`: post-publication pin count; actual slot, pin-record slot and nonce. This is the only completed resident publication. |
| Release | After checked_record, original release control and successful original record/slot mutation. Record actual function, entry slot, pin-record slot, nonce and post-release pin count. Invalid/stale release produces no success record. |
| Phase / Failure | Closed phase boundaries at the unchanged harness seam; Failure borrows the original Result after it exists. An operation failure has its pin operation coordinate and closes that attempted operation. A terminal harness failure uses operation=0 and its actual optional cursor identity (absent=u64::MAX), including construction, execution, WASI, cancellation or deadline failure with no active pin. It must not invent an operation. No copied large error or guest string is required. Rejected requested work is never added to successful cache_work. |

For EvictBegin the `function` field remains the acquiring function; victim
identity is reconstructed from the referenced resident slot. Thus no extra
retained victim owner or field is needed after `take`. Release is independent
of the last acquisition operation and carries its real token identity.

The header binds a canonical selection-context SHA-256. That context includes
all 132 baseline file lengths/hashes, instrumented file lengths/hashes and patch,
tool/executable versions and hashes, source revision context, target length/hash,
original harness/parser/argv/environment/limits, exact event schema and cap.
Binary identity is bound after compilation in the external selection and repeated
in runtime receipts. The fixed binary header uses raw digest bytes and zero
reserved padding; no path/string is serialized in an event.

## Observer memory, work, clock and errors

All observer storage is explicitly **external test-only diagnostic storage**.
It is not funded by product reservation slack and is not zero overhead. Proposed
live writer fields are a `[u8;4096]` buffer, `[u8;128]` record, sixteen u64
counters/coordinates, one `File`, and one u32 flag mask. On Darwin arm64 with
File=4 bytes/alignment four, that proposed `repr(C)` value is 4,360 bytes. This
is a design calculation, not a measured Rust layout.

The implementation must publish actual size/alignment/offsets for that owner,
TLS/RefCell state and guards, the independently accessible run-validity latch
and owner coordinate below, each whole `Result<usize, io::Error>`/error/borrow,
encode copies, slice iterators, short-write offset/retry state, header/footer
owners, every complete existing SwiftRunUsage/Option<WasiUsage> returned by a
snapshot accessor, and every named argument/return/reborrow in the callback chain. The
sum of disjoint value inventories, including conservative three complete helper
copies, has a **16,384-byte new external logical ceiling**. It must be measured
and independently reconciled before acceptance; 16 KiB is not permission to
omit fields or to call unmeasured values free. No target may be prepared if
complete inventory exceeds it or allocator probes show hidden per-event storage.
The old observer, fixture/module memory, stdlib file/runtime internals, kernel
file cache and physical stack/RSS are separate; this ceiling is not a physical
memory claim. Measure and report physical RSS/stack only if separately selected.

Opening/canonicalizing paths and building the 512-byte binding header happens
outside the original runtime lifetime. There is one file handle. During hooks:
no heap allocation, format machinery, owned string, dynamic map, sorting,
resident scan or clock read. Serialize 16 fixed words and copy exactly 128 bytes
into the fixed buffer. Flush has at most **32 write attempts per block**;
short writes and Interrupted each consume an attempt. No infinite retry or
write_all loop. WriteZero/error/attempt exhaustion sets sticky I/O invalidity.
Finite fault-injection and allocation probes must validate those paths.
There are at most 131,072 full ordinary blocks, plus one terminal-frame block;
header writing is one separate bounded block. Thus at most **4,194,368 write
attempts** including header/footer. `File::drop` supplies no observable close
Result; this proposal claims only explicit write results and file-custody checks,
not close-error or durable-storage acceptance. No fsync success is implied. The actual
full-prefix counts will be smaller. These are authored operation bounds,
not CPU instructions, machine speed, production CacheWork or syscall timings.

Hooks debit no additional **production** CacheWork, so they preserve original
work-based replacement timestamps. Their callback/serialization/write cost and
file bytes are recorded as diagnostic cost; do not advertise this as production
performance or a free policy. No observer clock is used. Synchronous I/O still
consumes the unchanged real 30-second cumulative runtime/WASI deadline and
120-second validation deadline. Host supervision retains its original 170+5+5
second envelope. A block can stall until the supervisor intervenes; a syscall
attempt bound does not bound kernel latency. No deadline pause/reset/extension
or extra target attempt is allowed to force the historical CacheWork failure.
If the observed result changes to deadline/cancellation, retain that actual
failure and prefix alongside the original historical failure.

At cap: freeze ordinary output at the last whole accepted record, set cap flag,
continue guest execution with original Result, and retain only fixed scalar
attempt/drop accounting. Never resume ordinary logging after a gap. I/O,
reentrant/wrong-owner/thread context, function range or checked-counter overflow
likewise freezes ordinary output with sticky invalidity. Use try_borrow rather
than a diagnostic panic. The invalidity latch must be outside the writer
RefCell: use process-wide AtomicU32 sticky flags, AtomicBool active and checked
AtomicU64 lifetime coordinate, plus an owner-thread TLS Cell<u64>. Begin claims
the inactive lifetime before setting the owner TLS coordinate; a duplicate begin
invalidates rather than resets it. Each callback during an active lifetime checks
the TLS coordinate against the process coordinate before borrowing the writer.
A wrong thread or failed try_borrow can atomically latch invalidity without
accessing the borrowed writer; an inactive wrong-thread TLS value cannot hide it.
End reads that latch into the termination frame before deactivating. These
atomics/TLS cells and complete callback temporaries are part of the measured
16-KiB inventory; they add diagnostic operations, never product authority.
Failed diagnostic initialization produces unavailable
telemetry and cannot create a new guest error. No signals/cleanup are dispatched
by observer callbacks.

The termination frame is outside the ordinary cap, has fixed 512-byte storage,
and is attempted once after original consuming cleanup, even on cap exhaustion.
It binds stored/attempted counts, last sequence/work/instruction/op coordinates,
sticky flags, observed terminal work/instructions, closed original failure code,
observed lifecycle mask and the original final consuming reservation/live counts.
No release or cleanup transitions after truncation are pretended to be present.
Resident/pin replay covers the guest-operation stream through preconsumption;
final owner drainage is a separate original consuming-ledger observation in the
termination frame. Missing per-slot drainage events cannot prove its internals,
and the analyzer must not silently zero its reconstructed resident/pin state.
The finite Rust gate must separately cover construction and non-cache terminal
failures with absent/independent cursor identities, plus cache-operation failure
followed by terminal observation; historical CacheWork is not the only legal
failure after adding synchronous I/O.
A closed file is insufficient: complete coverage additionally requires zero
flags, matching frame/file/sequence counts, expected original phase/failure
bindings, valid transition replay and the authoritative original result. An
original failed operation may legitimately end with a partial build or completed
eviction prefix. Missing/malformed footer or I/O corruption is invalid; cap with
an intact strict prefix is **truncated-prefix**, never complete coverage.

The host persists the unchanged original result **before** classifying this
supplement. A <=8,192-byte closed sidecar binds original-result SHA-256, whole
stream SHA-256/length, selection/header identity and status: complete-records,
truncated-prefix, invalid or unavailable. Host hashing streams bounded blocks.
Custody is checked after writing too: retain the initial and final descriptor
device/inode/type/length and explicit metadata-read results. The classifier opens
the exact path without following links, compares descriptor identity to the
writer's bounded custody receipt, checks the precise framed length, and hashes
through that descriptor. Compare descriptor/path metadata before and after the
read; reject replacement, growth, truncation or metadata drift. Copy only that
verified descriptor into an exclusively created owned evidence member while
rehashing, then seal and immediately reverify its length/hash. Any custody/read/
copy drift makes the supplement invalid and preserves the original result.
The custody receipt and final classification together remain within the 8,192
sidecar bytes; no whole-file bytes are buffered. This detects observed drift;
it is not authentication against an adversary rewriting evidence and its hashes,
nor a claim that timestamps alone establish immutability. Implementation review
must freeze the concrete descriptor/custody encoding and include its metadata
values, Results, copy buffer and handles in the separate complete inventories.
Stream failure never becomes command success, cleanup truth or guest failure.
Original stdout/stderr remain a distinct inherited limitation: the historical
driver had no separate file-byte cap. New writer output goes only to its capped
file and bounded sidecar, never per-event stdout. Before any future target
selection, the driver review must supply explicit bounded stdout/stderr draining
or decline preparation; it may not describe inherited unbounded redirection as
an overall bounded packet. A driver transport limit, if reached, yields a retained
host-output failure and can shorten the observable prefix; guest log limits stay
unchanged.

## Offline analysis and finite acceptance

Offline replay reads one 128-byte record at a time. A later implementation must
use bounded typed storage: 64 resident slots, 64 pin records, 512 count-plan
cells, 80,000 per-function records, a 64-identity distinct-recency list, 128
windows of 8,192 acquisitions and fixed histograms/top-32 reports. An **8 MiB
logical arena plus 64 KiB complete named transient inventory**, a **268,435,456
authored analysis-step ceiling**, and a **65,536-byte report cap** are proposed
hard limits; the actual type/field inventory and step schedule must be frozen
and measured before that analyzer is accepted. Exhaustion returns an explicitly
shorter analysis prefix, with the raw bounded stream preserved. No map grows
with event count and no all-events list is permitted in the real analyzer.

Report actual acquisition/interarrival gaps, exact distinct reuse distance 0..63
and >=64/first bins, scan-plan hits/conflicts by immutable function identity,
build/scan successful-credit intervals, completed evictions, held-pin intervals,
resident-byte headroom and per-window turnover. A 64-element recency list cannot
give exact distances beyond 63. Include partial-operation successful work at an
original failure separately from completed-interval totals. Credit intervals
include whatever original checks/work occur between their named endpoints;
they are not elapsed time. Reconstruct the fixed baseline timestamp/tie rules
and verify actual victims against the recorded state. More complex counterfactual
policies remain a separate future finite experiment, with exact accounting.

The executable [synthetic model](../verification/swift-ordered-retention-diagnostic-design/codec_model.py)
and [tests](../verification/swift-ordered-retention-diagnostic-design/test_codec_model.py)
exercise framing and a deliberately smaller independent resident/pin oracle.
They never import product, prior producer scripts or archived code, allocate the
maximum file, execute a guest, or claim to implement the Rust writer. They cover
fixed-width/file arithmetic, every tiny cap position, round-trip/gap/duplicate/
truncated/reserved/context/type/range checks, sticky error flags, final-count
drift, pin publication/release identity, pinned eviction rejection and completed
eviction prefixes without rollback. Python model allocations are finite fixture
cost, not the proposed observer memory inventory. Full closed event payloads,
plan collision/work replay, bounded actual writer errors and the listed Rust
parity/ledger/layout gates remain **pending**.

Before any target preparation: finite baseline-on/off differential must include
all original selected Swift and generic tests without changing expectations;
work/cancellation failure prefixes; capacity admission and malformed identity;
all-pinned/held borrowed instruction safety; allocation ordinals and short-write/
I/O/cap failures; multiple lifetime/reset/phase guards; actual final consuming
zero-ledger checks; and measured complete diagnostic memory/allocation inventory.
An independent reviewer must reconstruct the hook reversals and baseline bytes,
execute an independent finite stream/state oracle, and review bounded output and
selection/refusal controls. Syntax inspection alone is insufficient.

## Scope, receipts and cleanup

The packet binds exact selected inputs, source closure and revision context,
Python executable/version/hash, command argv/environment, raw outputs, failed
attempts and their corrections. Its seal excludes only itself/sidecar, avoiding
a recursive hash. `run_checks.py` runs only the finite Python tests. It creates
no temporary source tree, compiler product, selection marker or target process;
`-B` suppresses bytecode. No process discovery, UI, capture or native runtime is
used. No scratch removal is needed; retained packet files are evidence.

The original 16/8-MiB cache/entry, 64 resident/pin, 86 ticket, 64M CacheWork,
256-MiB combined and all original time limits stay fixed. New Rust/target/native
execution, policy benefit, Corpus 1/2 completion, published-package FieldLog,
signing/store/provider/customer/operational acceptance and all accountable GA
gates remain pending. A complete stream would describe only the executed
baseline prefix ending at its actual budget/deadline/failure, including observer
effects. It cannot reveal later phases, prove counterfactual exact work, forecast
a full-target pass or authorize a release.
