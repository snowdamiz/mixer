# Fixed current Swift cache attribution observer

This packet completes a **test-only observer prerequisite** for independent and
root review. Four finite host controls pass, preserving all thirteen preceding
observations and adding the completed-decode bitmap, first/repeated scan/build
partitions, boundary checks and failure-prefix checks. It selects no production
optimization or full diagnostic retry. Production source was not written or
queried by this lane.

The baseline is the accepted 132-file VM closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`, with revision
context `6403eea98031207f6e40a72b55dfd3bd4e7e6ec2`. The preceding diagnosis seal
`3a52d3f20cf852da7521fc3345a177ef6f8a7f157ebf2da7e3e63d01bc725b3d` and all
46 members verified before reconstruction. Its sealed source archive and three
original files reconstruct the exact baseline without a live VM or Git query.
The completed full-result seal remains
`8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526`: Corpus 1
failed CacheWork at 23,358,291 instructions and final consuming cleanup was zero.
Those are accepted historical inputs, not new execution by this packet.

Only the owned copy of `experimental/cache/borrowed.rs`, Swift cache wrapper and
Swift cache tests changes. The exact three-file
[patch](../verification/swift-cache-current-attribution-observer/instrumentation.patch),
[contract](../verification/swift-cache-current-attribution-observer/observer-contract.json)
and [receipt](../verification/swift-cache-current-attribution-observer/receipt.json)
are retained. Original tests remain byte-identical before the appended observer
and controls; the shared decoder, policy, legacy implementation and remaining
129 files match the accepted baseline. Generic callbacks are `cfg(test)` with
default no-op methods, so Frozen receives no observer implementation. No new
dependency is introduced.

## Observation contract

The sixteen semantic successful-credit and successful-call counters remain:
constructor, lookup header, free-pin probe, resident hash/chain, scan policy,
plan probe, scan body, plan publication, empty-slot search, victim search, plan
count, resident remove, build policy, build body, resident insert and publication.
The four plan events remain initial empty cell, conflicting identity, complete
matching hit and successful complete scan publication.

Original `checkpoint` and `work_with_wasi` execute in their original order.
Observation happens after that original result. Only `Ok` adds credits and calls;
a rejected requested debit contributes neither. The first returned work error
copies the site, requested amount, cursor function/offset, original failure
kind/resource/function/offset/attempted/limit. Later sticky retries do not replace
it. Cancellation at an original non-work check can correctly leave this record
empty; it records a rejected debit, not every terminal error.

A single fixed `[u64; 1250]` bitmap covers absolute function indices below 80,000
and occupies exactly 10,000 bytes. Original `SwiftMode::meter` entry records the
function and whether its bit was already set. The bit is set only after original
`usage.decoded(next_decodes, bytes)` and before the adjacent infallible slot
assignment, using the original function identity. Count-scan completion alone,
rejected scan publication, partial build and rejected resident insertion never
mark completion.

Fixed two-element arrays partition successful scan-body credits/calls, successful
complete scan publications and successful build-body credits/calls. Element zero
means the function has no earlier completed IR decode; element one means it does.
The classification is fixed at meter entry. An earlier failed first attempt can
therefore still be classified first on another isolated operation. Partial work
before a failure stays in the appropriate successful-credit partition. No dynamic
map, histogram, top-function sample, observer clock or guest-loop logging is used.

Valid snapshots require all sixteen credits to sum to original cumulative
`cache_work`; scan/build partition credits and calls to sum to their respective
site totals; partitioned successful scans to sum to plan-publication events;
distinct plus repeated completions to equal original `decodes`; and bitmap
population to equal distinct completions. Normal matching-plan fixtures require
an earlier completed identity. A reset belongs before a fresh cache construction;
snapshots during that lifetime must retain the bitmap and cumulative counters.

Out-of-range indices, checked telemetry-counter overflow, invalid observer context
and bounded formatter overflow set sticky diagnostic invalidity. The observer
never converts that invalidity into a VM error, changes an original result,
permits an instruction or enlarges a limit. Invalid telemetry cannot support an
attribution claim. The reusable formatter returns failure to its diagnostic
caller on overflow; that boolean must never become runtime authority.

## Layout and output bounds

On the recorded arm64 macOS host with Rust 1.99.0, actual Rust value sizes are:

| Value | Bytes |
| --- | ---: |
| Observer state, alignment 8 | 10,504 |
| Bitmap within observer | 10,000 |
| Fixed aggregate counters within observer | 392 |
| Optional first-rejection record within observer | 88 |
| Separate bounded formatting value | 4,112 |
| Aggregate output capacity | 4,096 |
| Zero aggregate payload | 323 |
| All-wide aggregate payload | 1,602 |

The all-wide payload uses maximum integers, absent identity sentinels and the
longest relevant closed enum text, and is retained verbatim in finite stdout.
The 4,096-byte writer checks every write. An intentionally inadequate 64-byte
limit invalidates diagnostics without changing the original fixture result.
The bitmap is never emitted. The reusable payload contains fixed counters and
one optional first rejection, without a guest string or arbitrary label. Fixture
case labels and control summaries are finite evidence outside that serializer.

These are external **test-only value sizes**, not product-accounted reservations,
RSS or whole-process peaks. RefCell/TLS machinery, compiler stack temporaries,
fixture allocations, allocator overhead and stdout runtime are outside those
measurements. Callback and formatting CPU time is not charged as guest cache work
and can consume real deadline time. No CPU-speedup, peak-memory or zero-overhead
claim follows. Any future driver must separately bind its lifecycle/envelope
output limit; this packet creates no full-run driver.

## Finite executable evidence

The exact command, environment, hashes and raw streams are in
[command.json](../verification/swift-cache-current-attribution-observer/command.json).
The command compiles and selects only four names with this filter:

```sh
cargo test --lib --locked --offline --no-default-features \
  --features experimental-swift-reactor --release \
  experimental_swift_reactor::cache_tests::current_attribution_ \
  -- --nocapture --test-threads=1
```

The absolute Cargo path, `CARGO_NET_OFFLINE=true`, two build jobs, one test thread,
owned source/target/temp paths and 120-second host timeout are recorded. Tools are
Cargo/Rust 1.99.0, Python 3.14.8 and macOS 27.0.1 arm64, with binary hashes.
Compilation plus controls takes 12.515 seconds; tests report 0.11 seconds.
**4 pass, 0 fail, 0 ignore, 386 filtered out**, with two inherited compiler warnings.
This is not a complete VM regression. The fixtures validate original finite
same-ABI synthetic modules and exercise actual cache owners; they instantiate no
guest and run no guest instructions, Initialize or invokes.

The retained controls establish:

- All thirteen prior observations match exactly in work, calls, plan events,
  completions and original hit/miss/decode/eviction counts. The 64/65-resident
  sequences keep default limits, including direct-map conflicts at 34/546.
- Cycling 65 identities twice yields 65 first and 65 repeated completions, with
  build credits split `[329, 329]`. An evicted matching plan has no scan credits
  and repeated build `[0, 5]`. First conflicting 546 has scan `[4, 0]`; repeated
  conflicting 34 has scan `[0, 4]`, successful scans `[0, 1]` and build `[0, 5]`.
- Every one of 164 flat and 245 nested shorter work budgets fails with the
  original typed work failure, exact requested/attempted/limit observations,
  sticky precedence and no rejected debit in the successful sum. These **409**
  controls cover partial scan, rejected plan publication, successful scan before
  build, partial build and resident-insert rejection. No failed decode marks the
  bitmap. Only negative synthetic fixtures narrow the work budget.
- All **173** original pre-completion checkpoint cancellation positions are
  exercised across the two bodies. Two further controls cancel after completed
  publication. Plan and decode publication boundaries, successful-credit sums
  and sticky original failures stay consistent.
- Synthetic indices 0 and 79,999 cross the first/repeated mark boundary; every
  bitmap bit is filled and checked. Synthetic 80,000 invalidates without indexing
  beyond the array. The unchanged profile rejects a module with 79,967 defined
  functions at its 79,966 limit; 34 imports make 79,999 the actual highest accepted
  identity. Actual-cache index 79,999 passes. Separately injecting out-of-range
  telemetry does not reject a subsequent otherwise valid cache operation.
- Counter and output overflow preserve the same original success or work failure.
  Fresh isolated cache lifetimes reset twice with first, rather than repeated,
  attribution. Every completed fixture drains original primary reservations,
  live counters and tickets to zero, without extra cleanup work or an invariant.

Three earlier finite development attempts remain auditable with exact source
manifests, raw streams and small successive correction patches: a test assertion
incorrectly expected zero after an earlier boundary completed; the upper fixture
exposed the original profile bound; and a compile error came from `unwrap_err`'s
Debug requirement on the unchanged proof type. The final test uses a Result
match. No validation limit or proof type was changed. Those attempts are not
passes. Earlier exact test source is reconstructible from the final source and
correction patches, without redundant full source archives.

The exact source-only compressed archive contains 132 files and is 1,246,524
bytes, SHA-256
`cdbf6b5826a354fa7796d3f4e4573b2fe62a213e4f3f5adf944cc2d2e44fbf18`.
The final copied-source manifest hashes to
`b825aa00bbc545863c7ab9bc12b0c8745395869ca44e533b541da8766e8a5bbb`;
the minimal patch hashes to
`0c0f99d5c38db3f39c9cc05be898a82f88634928ccbe1e009ffd6f772e3d531b`.

## Cleanup and remaining boundary

All four exact owned process groups are absent. Scoped holder checks are empty;
device/inode identities are checked before removal of owned source, target and
temporary directories. Cleanup removes 24,076,594 logical bytes without signals.
Only the compressed source and evidence remain. No other project process or
native instance is used or changed. No network, Git, UI, phone, provider, signing
or frozen hosted lane is accessed. Archived AGENTS/PLAN/STATUS observations supply
context without sealing or editing mutable live root indexes.

This changes no original 16-MiB cache, 8-MiB entry, 64 residents/pins, 86 tickets,
64-million cache-work, 256-MiB combined or 120-second validation/30-second runtime
limit. Target scan/build/repeat attribution is still unmeasured. Independent/root
review is required before root separately selects any fresh diagnostic
source/harness/executable/argv and a full attempt. No such selection follows from
these controls. Corpus 2, complete native/public/signed behavior, immutable
published-package FieldLog consumption, final physical phones and every specified
accountable GA gate remain pending. This advances W08 within the complete
W01–W18/G01–G38 product scope and narrows none of it.

Read-only verification performs no compilation or guest execution:

```sh
python3 -B verification/swift-cache-current-attribution-observer/verify.py
```
