# Bounded finite Rust diagnostic completion contract

Root approved this bounded contract, including synthetic ticket adversity, before
copied-candidate implementation. The new packet implements selected finite
controls and corrects provisional custody/accounting claims. Independent
review of the original packet remains authoritative for that packet and may
require changes to this contract. It does not select live integration, a full
Swift workload, a target driver, or a complete replay analyzer.

## Observed completion result, pending independent review

Fresh pristine Swift execution passes 340 methods. The exact new copied candidate
passes 362: the same 340 original methods, 16 inherited finite methods and six new
completion methods. The new methods exercise actual publication cancellation,
wrong-owner/stale release failures, approved synthetic foreign-ticket eviction
refund failure, actual post-guard-Drop hook refusal, the receipt formatter's exact
8,192-byte boundary, and the measured phase inventory. Twenty-one separately
authored custody controls pass, including three corrupt 1,280-byte CAP streams
and receipt growth after the initial size observation. These suites overlap.
Commands, raw outputs, exact complete source closures, failed attempts, fixture
artifacts, binaries, reverse-patch restoration and cleanup are in the
[new packet](../verification/swift-ordered-retention-diagnostic-completion/result.json).

The supported source table remains 24 codes/502 literal bytes. Unknown original
release/refund codes produce CODE invalidity with their actual complete Result
preserved. A newly exposed inherited writer limitation remains open: CODE can
prevent a partial ordinary buffer from flushing while the footer still reports
its stored count. The release fixtures observe stored=9 but serialize zero
ordinary records; they explicitly report invalid prefix/footer count mismatch.
In-memory increments are not evidence of serialized Release records. Four real
warm hit/release pairs, identical with observation off/on, place actual EvictTaken
at record32, causing the inherited writer's real buffer flush before the unknown
refund code. That trace retains 32 ordinary records and no EvictCommit. The actual
owner cleanup reaches zero; the foreign owner's real consumed-ticket quarantine
retains one byte and one ticket. It is never described as successful zero cleanup.

Every newly produced closed sidecar, including CAP and malformed-frame cases,
is `invalid`/failure15. Raw supplementary flags/counts and
`fullReplayAccepted=false` exist only in the outer receipt. The original sealed
packet and its historical sidecars remain unchanged. No stream in this slice is
semantically accepted. Header/footer-only CODE traces remain invalid evidence.

The new source-value inventory proposes a peak of **16,114/16,384 bytes**, only
**270 bytes** below the unchanged ceiling. Writer initialization/Begin are the
largest phases; retirement is16,106 and bounded serialization15,466. Exact
`Writer<File>` and its Option are both4,408 bytes under the recorded Rust1.99.0
toolchain. The inventory charges complete writer return/move roles, three complete
544-byte receipt formatter owners, argument/Formatter and I/O Result/error roles,
eight measured Debug helper levels, all full original outputs, checked PathBuf
capacities, and post-retirement readers. These are provisional logical source
inventories subject to independent lifetime review, not physical compiler stack,
TLS runtime, library internals, OS memory, RSS or timing measurements. The
[lifetime explanation](../verification/swift-ordered-retention-diagnostic-completion/logical-inventory.md)
distinguishes source moves and non-overlapping phases. The inherited receipt
formatter's complete memory qualification remains pending.

## Immutable inputs and ownership

The original `verification/swift-ordered-retention-diagnostic-rust/` packet and
its document remain unchanged. Its seal JSON SHA-256 is
`c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf`
(186 sealed members); candidate manifest SHA-256 is
`cd9c832496a144538c755bdd3551d8a93bbfb29d4de0c268e42460f45857e723`.
The pristine 132-file VM manifest SHA-256 is
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
Before/after checks must verify every named live file against that manifest,
every archive member against its manifest, and the original seal against its
frozen digest. No prior cleanup or suite count is a new execution receipt.

This lane owns only this document, the new
`verification/swift-ordered-retention-diagnostic-completion/` packet, and its
identity-recorded temporary copied VM/build/output directories. The independently
reviewed original packet, review lane, live VM, Cargo files, dependencies,
production limits, timestamp policy, root execution metadata, hosted lanes, and
other projects' processes are outside this lane's write ownership.

The new candidate starts from the exact complete original candidate archive.
Its only permitted changed VM names remain
`src/experimental/cache/borrowed.rs`,
`src/experimental_swift_reactor/cache.rs`,
`src/experimental_swift_reactor/cache_tests.rs`, and
`src/experimental_swift_reactor/control.rs`. The existing `control.rs` scalar
accessor is retained unchanged; no new control mutation, field, allocation,
counter, clock observation, or reservation is introduced. The completion delta
is test-owned observer/fixture code appended to `cache_tests.rs`; a copied
`cache.rs` change requires renewed root coordination if investigation proves it
necessary. Existing production operation bodies remain identical to the original
candidate. No code from a frozen hosted inspector/authority driver or rejected
WorkerV2 packet is read, imported, or executed.

## Failure controls and exact wire meaning

The fourteen event kinds, 128-byte record, 512-byte frames, 24 supported source
codes, and 502 source-code literal bytes remain unchanged. No new supported code
is proposed. An unknown original code sets sticky CODE and does not fabricate a
Failure record with a supported code. Its footer preserves the actual original
kind and stage with code zero, and its sidecar is invalid. A finite source
assertion independently sums the unchanged source-code table literal bytes.

1. **Publication cancellation.** Use the existing cfg(test) `Hooks` checkpoint
   with `pause=Some(CacheStep::Publication)` and `cancel_pause=true`. It cancels
   the original control at the original check after successful build and before
   resident insertion/publication; the existing fixture's 30-ms pause is retained
   and disclosed. It does not replace an operation Result. The expected prefix
   includes AcquireBegin, BuildBegin, and BuildReady; it has no PinPublished for
   that attempted acquisition. The existing pin wrapper's Failure has kind 14,
   the attempted nonzero operation, original function and failure coordinates,
   payload kind 2 (Cancelled), code 1 (`swift_run_cancelled`), and stage 2 (Cache).
   A separately observed terminal failure has operation zero and the same actual
   original failure, followed by original consuming cleanup observation. A
   deterministic successful-work limit around original resident_insert may add
   publication failure coverage only after a successful finite calibration and
   explicit source proof; no limit retune is proposed for the product.

2. **Release errors.** Exercise actual `SwiftFunctionCache::release`, including
   wrong cache owner and stale nonce, retaining its complete
   `Result<(), SwiftReleaseFailure>` before extracting the returned pin. Both
   errors precede the original usage, slot-pin, and PinRecord mutation and must
   emit no successful Release (kind 12). `wrong_cache_owner` and `stale_pin` are
   unknown to the unchanged 24-code table: the original Err remains authoritative,
   original kind is Invariant (wire 21), stage is Cache (wire 2), and its original
   cursor is absent. The caller observes the borrowed actual failure as a
   terminal operation-zero failure; CODE prevents any invented Failure record.
   No release wrapper change is needed. Preserve the returned pin's exact
   slot/nonce and prove that the valid returned token remains usable against its
   original owner when appropriate. A stale duplicate is never used as authority
   and is dropped after rejection. Consuming cleanup uses original APIs. The
   control's existing first-failure semantics are preserved; it is never reset.

3. **EvictTaken followed by failed drop/refund.** The valid owned-ledger path
   cannot naturally fail at this boundary: original SwiftMode::drop_entry drops
   the actual decoded owner, refunds its actual ticket, then removes a live
   CacheEntries count. Root must explicitly approve synthetic ticket-ownership
   adversity before this control is implemented. Using existing cfg(test)
   `inspection::replace_entry_ticket`, install one actually admitted foreign
   Cache-category 1-byte ticket in an actual unpinned resident, preserving the
   displaced valid ticket. Admit and retain the foreign owner's real proof and
   ledger; do not forge or clone a ticket or change a ledger. A second actual
   acquisition that needs the selected victim reaches original resident_remove,
   EvictTaken, then original decoded storage drop and refund owner refusal.
   The prefix must contain EvictBegin and EvictTaken, no matching EvictCommit,
   no BuildBegin or PinPublished for the failed acquisition, and no fabricated
   eviction usage increment. The actual failure is Invariant (wire 21), original
   code `swift_run_release_owner`, Cleanup stage (wire 6), with absent original
   cursor. The existing pin failure observation and later operation-zero
   terminal observation both set CODE without inventing a supported record.
   The actual original failure/code and after-consumption observations are
   retained separately. Once actual decoded storage has been dropped, refund the
   displaced valid ticket against its original owner using original
   `drop_reserved((), ticket)`, consume the actual remaining cache/proof/control
   owners, and retain the foreign ledger's unrecoverable 1-byte/one-ticket charge
   as a quarantine receipt. The consumed foreign ticket is never reused or
   refunded and the quarantine charge is never relabeled as zero. No new ledger
   mutation seam, token repair, or successful cleanup claim is allowed.

Each control runs the same ordered operation sequence with observer off and on.
Compare the complete original failure fields and coordinates, cache usage,
reservations/live counts before and after consuming cleanup, token slot/nonce,
and allocation attempts/failures/bytes. Owner identities and elapsed/deadline
clock observations are reported but not equated across independently constructed
owners; the chosen fixtures use no deadline-origin failure. Event-free operation
results and ledger transitions must agree exactly. Normalize no failure code,
stage, work, instruction, capacity, live count, retained pin, or quarantine charge.
Any sequence difference is a failure requiring investigation, not observer gain.

Original returned objects are retained before supplement observation. A bounded
raw original-result receipt is persisted before stream classification, with the
actual final consuming usage retained separately; a formatter or observer Result
never replaces the operation Result. Release's complete Result is charged even
when a later fixture keeps only its copied failure and original returned token.
Final consuming ledger zeros do not delete retained pins/residents from offline
stream inventories. These controls verify specific source-seam assertions only;
none semantically validates a complete stream.

## Conservative custody correction

All copied streams, including CAP-only streams, receive status `invalid`, with
the existing closed failure code 15, until a separate complete bounded replay
validator accepts the entire bounded prefix and frames. No footer flag, byte
length, helper validator, or successful custody hash promotes a stream to
`truncated-prefix` or `complete-records`. Preserve observed flags/counts as
untrusted supplementary observations with `fullReplayAccepted=false`. Short or
malformed frames remain invalid; inability to obtain any source is unavailable.

The host-copy correction is authored in this new packet and does not modify the
old sidecars. It keeps one exclusive no-follow destination, one copy attempt,
two live copy descriptors, one 65,536-byte buffer, <=32 combined attempts per
block, <=131,072 named logical host bytes, <=8,192 sidecar bytes, and at most two
stream files totaling 1,073,743,872 bytes per lifetime. Retain a partial exclusive
destination and a closed failure receipt on read/write/identity/length errors;
never retry into another destination. Adversarial controls cover short reads and
writes, Interrupted, zero/error, initial/final descriptor or path identity drift,
nonregular input, source/destination length drift, and bounded-attempt refusal.
Only fixture-owned files and injected I/O adapters are changed. No target
transport, external provider, process discovery, or stdout/stderr driver is
included. Physical hash/FileIO/kernel/RSS memory and fsync durability are unclaimed.

## Complete logical observer inventory

The 16,384-byte logical observer cap is fixed. Record exact sizes, alignments,
field offsets, ownership moves, helper multiplicities, and source lifetimes with
Rust 1.99.0/Cargo 1.99.0 from the explicit stable-aarch64 toolchain paths. The
prior 4,408-byte writer, 1,120-byte release Result, 1,096-byte pin Result/failure,
504-byte usage and prior phase peaks are inputs to reconcile, not accepted peaks.

The new inventory must include at least: header construction/encode/return,
Writer::new local and whole Option return, caller writer binding and begin's
whole writer argument, TLS Option storage even while None, failed/duplicate
begin disposal, guard success/end/Drop and closure captures, all scalar-argument
and helper/borrow Results, final/footer construction/encode/return, EndReceipt,
File/Metadata Results, take/retirement's complete writer temporary and File Drop,
plus whole original pin/release/cleanup/failure/usage/WASI outputs and literals.
The synthetic-adversity fixture additionally charges every simultaneously
retained displaced ticket and foreign-owner output/borrow attributable to the
observer receipt. General fixture cache/control allocations remain product
fixtures, not hidden observer storage.

Separate measured initialization, callback, footer, retirement, and abnormal
guard-Drop peaks, with exact lexical scopes and a simultaneous ownership table.
Where initialization owns no original operation output, its absence needs an
explicit scope proof. Where source moves invalidate an owner, explain that
boundary; do not infer a lifetime end merely from intended phase names. Keep
the all-phase union and opaque/runtime exclusions visible. Executable inventory
checks must fail if any conservative simultaneous named-value peak exceeds the
cap. If the bound fails, preserve the failure, coordinate a bounded test-only
owner-lifetime correction with root, or report that this finite prototype fails
the cap. Never increase the cap or claim compiler stack/TLS physical qualification.

The combined atomic mode/count gate remains <=8 atomic operations per transition,
without spin, wait or CAS retry. One synchronous owner and joined negative
fixtures define this closure. End closes admission before flags and refuses all
writer access/footer when callbacks remain; actual hooks after End must refuse
without mutating bytes or flags. General concurrent INIT/publication/finalization
remains unqualified. Inventory alone cannot establish quiescence.

## Required receipt and acceptance boundary

After root approves this contract, prepare identity-recorded complete 132-file
pristine and candidate copies and exact manifests/patches. Run bounded offline
release host suites with one build job and one test thread, recording argv,
environment, tool versions/hashes, revision/tree digest, timeout, raw output,
and before/after source and original-packet hashes. Re-run all original 340 Swift
methods, all inherited 16 finite methods, new controls, and original generic
private/integration tests; report overlaps. Baseline/candidate generic output
equality and actual reverse patch restoration cover the complete closure.
Preserve all failed attempts, then remove only identity-matching owned scratch
and build/output directories after sealing their required source/evidence.
Record cleanup even if a command fails.

No computer use, capture, native runtime, simulator/emulator/device query,
physical run, process discovery, commit, push, full-target execution, analyzer,
target-binding, customer/provider/HTTP work, or GA promotion occurs in this lane.
All such gates remain pending. Root approval of this finite implementation does
not approve those activities. Independent review must accept the new packet
before root treats its selected finite gaps as closed.
