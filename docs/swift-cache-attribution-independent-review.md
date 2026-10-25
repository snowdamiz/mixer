# Independent review of the current Swift cache observer

**Accepted for diagnostic preparation only.** No blocking defect was found in
the sealed test-only observer. This review does not select a full diagnostic
attempt, integrate production code or approve runtime, native, dogfood or GA
behavior. The binding product plan and all W01–W18/G01–G38 obligations remain.

The reviewed candidate seal is
`e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305`.
Independent reconstruction verified its 43 members, the accepted diagnosis's
46 members, all 132 source files and the exact three-file delta. The remaining
129 files and the original test prefix are byte-identical to the accepted
baseline closure
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
The source revision context is the supplied historical `6403eea9`; root supplied
current context `6b8aba35`. Exact manifests govern this review. No Git or live VM
source query was performed. Current AGENTS/PLAN/STATUS are archived observations,
not acceptance authority or an immutable live-index claim.

## Source conclusions

The original checkpoint and `work_with_wasi` run before observation, in their
original order. The returned original Result is retained and returned. Successful
credits and calls update only after `Ok`; the first rejected requested debit is
copied after `Err` and is never charged into successful totals or overwritten.
Its cursor and original failure identities remain separate. Non-work checks can
fail without creating a rejected-debit record, as the candidate states.

The sixteen sites account for constructor, lookup, pin probe, resident lookup,
scan policy, plan probe, scan body, scan publication, empty-slot search, victim
search, plan count, resident remove, build policy, build body, resident insert
and publication. Policy construction is separately tagged before its original
one-credit debit. Publication has an original check but no successful work debit;
its zero-credit total is consequently expected. Four plan events distinguish
empty, conflicting, complete matching and successfully published scan plans.

The completed bitmap is updated only after the original
`usage.decoded(next_decodes, bytes)` and before adjacent infallible slot
publication. The observed identity is the original absolute function index.
Count-plan publication, partial build and rejected insertion cannot mark a
completed decode. First/repeated scan and build partitions use the bit sampled
at original meter entry. An evicted IR entry retains its completed bit; failed
first attempts do not acquire one. Fixed arrays, checked counter additions and
range guards keep telemetry bounded. Invalidity remains sticky diagnostic state
and is not mapped into an original runtime error or admission decision.

A matching count-plan hit does **not**, by itself, prove a completed decode:
the original algorithm can publish the count plan before a later build fails.
The candidate's normal-lifetime invariant is justified by the original control
owner. Every such fallible path returns a failure retained by
`RuntimeControl::fail`; later `check_with_wasi` returns that first failure before
new work. A retry cannot use the retained plan in that failed lifetime. If the
original operation succeeds, completed publication precedes its return. The
independent build-policy control demonstrates the otherwise tempting
counterexample: a plan exists with zero completion bits, but the same-identity
retry returns the original failure without new events or credits. This reasoning
depends on the same original cache/control ownership, with no reset or recovery
splice. It must not be generalized to a detached plan cache.

Frozen's `DecodeMeter` implementation inherits the new `cfg(test)` default no-op
callbacks. It has no observer implementation or new work/check behavior. Shared
decoder, policy and legacy source bytes remain exact. This is source evidence;
no complete legacy or VM regression was run by this reviewer.

## Independent finite controls

The review appended only
[independent-controls.rs](../verification/swift-cache-attribution-independent-review/independent-controls.rs)
to the sealed candidate's test file in an owned clone. The retained manifest has
132 files, not 133. No producer test was selected. This exact filter ran offline:

```sh
cargo test --lib --locked --offline --no-default-features \
  --features experimental-swift-reactor --release \
  experimental_swift_reactor::cache_tests::independent_attribution_ \
  -- --nocapture --test-threads=1
```

**3 passed, 0 failed, 0 ignored, 390 filtered out**. Compilation plus controls
took 12.921 seconds; tests reported 0.00 seconds. Cargo/Rust 1.99.0, Python
3.14.8 and macOS 27.0.1 arm64 are recorded with executable hashes. Two inherited
compiler warnings remain. Exact argv, environment, timeout, source digest and
raw streams are retained in the
[command](../verification/swift-cache-attribution-independent-review/command.json).
These are original finite same-ABI synthetic proof/cache operations. They
instantiate no guest and execute no instructions, Initialize, invoke or corpus.

| Control | Observed result |
| --- | --- |
| Scan-policy and build-policy rejection | Original limits 4,932 and 5,078 reject a one-credit request at sites 4 and 12. Rejected site credits/calls remain zero; successful sums equal original work. The later case has a published count plan and zero completed bitmap bits. Same-identity retries preserve the original typed failure and all totals. |
| Bitmap word boundaries and repeated conflict | Absolute indices 63, 64 and 127 occupy the expected same/adjacent words. After 64 other identities evict their IR, identity 575 conflicts with 63's plan. First scan/build credits are 4/5; rebuilding 63 after conflict credits 4/5 to repeated partitions. Original completed bits persist. |
| Invalid telemetry and output | Independent context and counter invalidity preserve original WorkExhausted 5,079 / 5,078. A 64-byte formatter returns false, leaves exactly 64 partial bytes, and the illustrative caller discards them. The original failure and later sticky retry remain unchanged. |

The producer's four passing finite controls, thirteen inherited observations,
409 work prefixes and 173 cancellation prefixes were integrity-checked as
sealed existing evidence, not rerun or presented as independent execution. Its
three earlier unsuccessful attempts remain preserved by the candidate packet;
this review required no correction or retry.

## Required boundary for a future driver

These are requirements for a separately selected diagnostic driver, not a new
driver implemented or approved here:

- Keep the original guest result authoritative. Report telemetry invalidity
  separately. Do not route `invalid != 0`, formatter false or a failed telemetry
  invariant through an assertion, unwrap or replacement error that conceals the
  original guest failure. The finite assertion helpers are test oracles.
- If formatting returns false, discard the entire partial payload. It can
  contain an earlier `invalid` field written before output-overflow invalidity
  was set. Do not emit it as a complete snapshot or parse it for acceptance.
  A true formatter return still requires checking the sticky invalid mask.
- Reset exactly once before a fresh isolated cache/control lifetime; preserve
  counters and the bitmap through all selected lifecycle snapshots and final
  consuming cleanup. Do not interleave another cache into the same TLS state,
  detach plans from their original control, or retain a RefCell borrow across a
  cache operation. Bind lifecycle labels and the total output envelope outside
  the reusable serializer.

The serializer contains fixed integer aggregates and closed source-bound enum
Debug text, without guest strings or arbitrary labels. Candidate finite evidence
measures a 10,504-byte observer, its 10,000-byte bitmap, a separate 4,112-byte
formatter and 4,096-byte capacity; the all-wide payload is 1,602 bytes. These
are Rust value/payload bounds, excluding RefCell/TLS machinery, compiler
temporaries, fixture allocations, allocator/process overhead and stdout runtime.
Real CPU time can consume the original deadline. This review makes no zero CPU,
zero RSS, whole-process peak, performance improvement or product-accounting claim.

## Cleanup and retained scope

Consuming cleanup in every independent cache control returned original primary
reservations, live counters and tickets to zero without extra cache work or a
cleanup invariant. The owned test process group was absent, scoped `lsof` checks
were empty, and device/inode identities were rechecked before removing owned
source/target/temp directories. Cleanup removed **24,105,170 logical bytes**
without signals. No redundant source archive or compiled binary is retained;
the exact review source reconstructs from the sealed candidate plus the appended
controls. The
[receipt](../verification/swift-cache-attribution-independent-review/receipt.json)
and read-only verifier bind the complete small review packet.

No network, provider, signing, native, UI, phone, production or frozen hosted
lane was queried or changed. No 53-MB target, real-module validation, Initialize,
invocation/corpus, complete VM regression or new full harness was run. Actual
target attribution remains unmeasured. A fresh full source/harness/executable/argv
selection remains root's separate decision. Corpus 2, native/public/signed
behavior, immutable published-package FieldLog consumption, final physical phones
and all accountable GA gates remain pending.

```sh
python3 -B verification/swift-cache-attribution-independent-review/verify.py
```
