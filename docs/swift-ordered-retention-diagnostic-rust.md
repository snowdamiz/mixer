# Finite isolated ordered diagnostic Rust prototype

This is a **provisional finite feasibility packet**, pending independent review.
It is not acceptance of the complete Rust diagnostic requirements, a full event
replay analyzer, target preparation, a retention policy, native execution or GA.
The live 132-name VM closure remains byte-identical to the accepted baseline.
No live VM, Cargo/dependency, production limit, timestamp policy, root execution
metadata, hosted lane, target or native/capture process was changed.

The exact schema was coordinated with root before hooked execution. The
[contract](../verification/swift-ordered-retention-diagnostic-rust/schema-coordination.md)
closes fourteen event payloads, sentinel fields, header/footer, sticky bits,
phase/count/cap rules, supported source codes and sidecar/custody shape. Root
agreed to Release body_len=MAX because the actual decoded resident does not
retain that value; release otherwise uses its real resident and token. The
24-code subset has 502 literal bytes. An original unrecognized allocation code
correctly yields CODE invalidity while preserving the actual original failure.
A supported-code subset is not full-target failure coverage.

The complete pristine and candidate 132-file closures, four-file patch and
manifests are retained. `control.rs` is the agreed fourth copied file: its added
cfg(test) scalar accessor reads only existing cache_work/instructions. Added
hooks do not call the clock-reading usage accessor or copy a WASI observation.
The other copied changes are `experimental/cache/borrowed.rs`, Swift `cache.rs`
and `cache_tests.rs`. No production reservation or new cache/control/meter field
funds observation. The independently authored observer/writer lives only in the
copied test module; Frozen defaults do not forward to it.

The final selected host results are:

| Context | Observed result |
| --- | --- |
| Pristine original Swift private suite | 340 passed |
| Candidate Swift suite | 356 passed: the same original 340 plus 16 new methods |
| Fresh final candidate finite replay | 16 passed: eight writer/frame and eight hook methods |
| Pristine and candidate generic private cache | Five passed in each; complete stdout hashes match |
| Pristine and candidate generic cache/allocator integration | Nine plus one passed in each; complete stdout hashes match |
| Actual reverse application of candidate patch | All 132 exact pristine hashes restored |

These suites overlap. They ran with the unchanged Cargo manifest/lock, explicit
Rust 1.99.0 and Cargo 1.99.0, offline release compilation, one build job and one
test thread. Per-command argv, selected environment, timeout, raw output, tool
hashes, source manifests and before/after closure checks are retained under
`commands/`. Existing two Swift dropping-Copy warnings and generic staged-code
warnings remain visible. Expected panic probes in original tests are preserved;
the original suites still finish successfully. No compiler warning was treated
as an unobserved clean build.

The finite hook controls cover successful cold scans/builds/publications,
actual token nonce versus its successor, a held pin across later acquisitions,
release joined to its prior publication, real successful three-stage eviction,
all-pinned failure with two retained stream pins, partial successful CacheWork
and cancellation prefixes, actual allocation ordinal zero/one parity,
construction failure with absent cursor, and a non-cache original terminal
failure with an independent cursor. Consuming ledger zeros are copied from the
original control after its consuming API; they do not remove the two retained
pins/residents from the reconstructed stream. No per-slot drain is invented.
Original failure and final usage objects are borrowed for bounded raw Debug
receipts before End or supplemental classification, rather than replaced with
an observer result. Their raw bytes and SHA-256 bindings are retained.

The writer uses 128-byte records, a 32-record buffer, separate 512-byte frames,
cap<=4,194,304 and <=32 write attempts per block. Tiny cap positions, checked
short writes, Interrupted, WriteZero, ordinary error, sticky freeze, malformed
header/footer fields and duplicate finish are executable controls. A two-record
actual-hook cap fixture records attempted=11, CAP only and actual phase mask49;
its complete original cleanup does not fabricate missing ordinary records.
The cap does not allocate a 512-MiB file. File::drop has no claimed close Result,
and no fsync/durability claim is made.

Callback admission uses a combined atomic mode/count gate before TLS, flags or
writer access. The source-selected finite closure has one synchronous owning
thread; negative fixtures create one joined wrong-thread callback and an
explicit retained in-flight entry. All valid callbacks therefore have count<=1;
negative controls stay <=64, far below the packed count's 32-bit carry. Entry
uses at most four atomic operations including fault publication/leave; Begin
has at most eight including failure closure, End at most four. No CAS retry,
spin or wait occurs in these transitions. This is a proof for this exact finite
source closure, not an unrestricted concurrent runtime claim. The INIT
publication race is not dynamically qualified; a failed initialization keeps
admission noncanonical/closed and prevents another Begin until explicit
quiescent retirement. General concurrent initialization remains pending.

End closes admission before observing count/flags and never borrows, flushes,
closes or footers a writer when an admitted callback remains. The guard is
non-Send, checks its lifetime coordinate before Drop/End can affect a run, and
closes before panic cleanup accesses its writer. Static hooks remain callable
after End; actual callback-entry probes return refused and preserve bytes and
flags. Wrong-thread and failed-borrow faults latch outside RefCell; a later
owner callback now propagates that sticky latch before writing. The initial
prototype's failure to do that was corrected before the final source freeze.

Logical accounting is deliberately explicit. `Writer<File>` is 4,408 bytes,
alignment8; File is4/alignment4, TLS RefCell<Option<Writer>>4,416, atomics plus
TLS owner36, complete helper584 with three copies, frame inventory2,864, whole
pin/release/retained-failure/cleanup/usage/WASI output inventory5,040, guard24,
source literals502, retirement's extra complete writer4,408, metadata/results/
borrow456 and Drop locals56. The full pin Result/SwiftRunFailure is1,096,
release Result1,120, SwiftRunUsage504, Option<WasiUsage>112, io::Result16 and
io::Error8. Actual writer field offsets are recorded by the standalone layout
command. Every whole nested Result is counted, not only a pointer.

The measured all-phase union is **19,554 bytes**. The proposed simultaneous
peaks are callback **12,282**, footer **13,394**, retirement **15,578** against
16,384. This uses an explicit lifetime boundary: callback frames have returned
and admission is closed/countzero before End; End/finish/encode frames return
before retire; retirement still charges the caller's footer, receipt, all full
original/cleanup/release output owners and the moved complete writer. The
independent reviewer must verify these source lifetimes and reconcile all named
values. The union must not be called a <=16-KiB simultaneous allocation. These
are logical value inventories, not measured compiler stack, optimizer copies,
TLS runtime, opaque standard-library internals, kernel buffers, RSS or timing.

The finite host custody probe verifies actual Rust-recorded initial/final
writer descriptor identity and regular-file shape, source descriptor/path
stability around a bounded one-copy hash, destination stability, and a second
hash through a verification descriptor after both copy descriptors close. Each
input gets one exclusive no-follow destination; the two copy descriptors and
65,536-byte buffer are bounded. Nine tiny final streams total20,480 retained
copy bytes. Its separate Python named-value host inventory is115,739/131,072;
this is also a provisional logical inventory, not measured opaque hash/FileIO
internals or physical memory. The first custody attempt's incorrect copy_before
metadata is retained in history; the correction copied a freshly executed
finite lifetime once, rather than retrying the old source. The probe is not a
complete adversarial custody/failure protocol or the future target driver.

The following remain **unverified** and prevent complete Rust diagnostic
acceptance: newly hooked Swift publication/release failure controls; actual
Swift EvictTaken versus fallible drop/refund failure; complete collision,
immutable-body, timestamp/tie/victim/work and event-state validation; independent
full field/sentinel mutation coverage; general concurrent INIT/finalization;
all source-code coverage; complete custody short-read/write/error/drift controls;
independent logical-inventory reconciliation and quiescence review. Finite
headers intentionally use synthetic digest bindings; real selection/header/
binary/harness/target binding is not implemented by this fixture. Normal framed
streams therefore receive conservative invalid sidecars pending full replay,
not a false complete-records status. The separate complete bounded analyzer,
stdout/stderr transport, original full workload, native tests and all external
signing/store/provider/customer/operational/FieldLog/GA gates remain pending.

Initial failed preparation, compiler and assertion attempts, pre-correction
source closures, raw outputs and custody evidence are preserved in history.
Owned scratch/build/native cleanup and final seals are recorded in the packet;
no process discovery, signal, native/UI/capture run, commit or push occurred.
