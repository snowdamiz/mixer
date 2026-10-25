# Independent review of full current-attribution preparation

**Changes required before root exact selection.** The original guest Result,
phase operations, work/cancellation behavior and consuming cleanup are preserved.
One diagnostic-validity defect remains: the host telemetry classifier accepts
impossible aggregate schemas as valid attribution. This review selects no full
target and approves no production or GA gate.

The reviewed preparation seal is
`c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1`
(104 members), source manifest
`8eccfedefb8a64fd828743ecb4899ea2624be2359ef879229be00d90a4d5185d`
(132 files), and executable
`fc27c22f8f771e7f148bcb73781b09a974a2bcebce7be7466b951ff85d9fafaf`.
The root-supplied source revision context is
`6b8aba350224ed19f678669bdbea6b359d8de68b`; root later reported delivery as
`7b6048642b42e4900cccff4e14aa0fe8949ab35e` with candidate bytes unchanged.
No Git or live VM query was made. Exact hashes are the review authority.

The accepted observer and its independent review remain prerequisites. The
read-only candidate verifier passes all 104 members, external bindings, the
two-file delta from the accepted observer, existing finite receipts, retained
compressed executable, and cleaned candidate scratch. Those producer executions
are preserved evidence, not independent executions by this review.

## Actionable finding

**P2: Validate the closed telemetry schema before reporting valid attribution.**
In the candidate's [`telemetry.py`](../verification/swift-current-attribution-full-preparation/telemetry.py),
lines 30–55 compare numeric values and aggregate sums without enforcing exact
types, integer ranges, array lengths, field sets, or the optional rejection
schema. Python treats `True == 1` and `1.0 == 1` as equal. Matching sums can also
conceal negative credits. Fields unused by those sums pass unchecked.

Six independent mutations of the producer's successful tiny-control telemetry
all return `status: valid` with an empty issue list:

| Exact retained mutation | Required classification | Observed |
| --- | --- | --- |
| `reset_count: 1.0` and floating-point credit values | Invalid schema | Valid |
| First `sequence: true` | Invalid integer type | Valid |
| Credit site 1 becomes `-1`, site 2 increases by 1 | Invalid unsigned credit | Valid |
| Append `99` to the sixteen-element `calls` array | Invalid fixed array length | Valid |
| Add an unknown aggregate field | Invalid closed schema | Valid |
| Replace `first_rejection: null` with a string | Invalid rejection schema | Valid |

The exact mutated stdout inputs, untouched original events, full classifications,
six failing assertions and command receipt are retained under
[`verification/swift-current-attribution-preparation-review/`](../verification/swift-current-attribution-preparation-review/).
This is one schema-validation defect with six independent reproductions. It
does not show that the bound Rust emitter generates these impossible values,
and it does not change the original guest failure or cleanup authority. It does
show that the separately reported telemetry-validity result is too permissive.

Before acceptance, add closed envelope/aggregate/rejection schemas; enforce
actual integer types excluding booleans, unsigned ranges, exact fixed array
lengths, typed optional first-rejection fields and source-bound enum forms;
reject nonfinite JSON constants. Preserve the existing duplicate-key, output,
lifecycle, original-usage and invariant checks. Rerun these negative fixtures and
valid producer/failure-prefix fixtures. Keep this validation separate from the
original Result, and reseal the corrected driver packet before root selection.
The reviewer made no producer edit.

## Preserved source contract

The accepted observer archive reconstructs the exact preparation. Only
`cache_tests.rs` and `lifecycle_tests.rs` differ from that accepted archive; the
other 130 files match. This review appends its controls only to `cache_tests.rs`
inside an owned clone. Its review manifest is
`8f46d1fe3924e7763b5c128ffd6e36d82a9ebdd4e9abb1633e642cbe276e19d3`.
No dependency or production algorithm changes.

Seven exact single-occurrence reversals recover the original harness bytes.
The original native comparator, `MIXER_EXACT` emitter, completion handling,
phase Result match and complete target test are byte-identical. The driver
supervisor, process observation, event parser, build and cleanup functions are
literal original bodies. The target `execute` additions bind the new source,
classifier and output contract, then classify telemetry after persisting the
original result. The original success return remains based on the original
command result.

The adapter resets after successful adoption and immediately before original
construction. It refuses a second begin during an active lifetime. Counters and
completed bits stay cumulative through phase snapshots and final consumption.
Its six closed labels, duplicate/order detection and six-attempt limit bound
the envelope to 4,608 bytes and the lifetime to 27,648 bytes. Formatter false
erases the whole partial payload and rereads sticky observer invalidity. A true
formatter with observer, invariant, adapter or prior-write invalidity emits
`payload: null`. Fallible telemetry writes do not replace a guest Result.

Final telemetry uses original consuming `final_cleanup_usage.cache_work` and
the decode count captured before the cache owner is consumed. Original cleanup
events and consuming reservations remain cleanup truth. No cache/control reset,
detached owner, changed hook or recovery splice is introduced between phases.

The real input remains the same 53,777,114-byte module. Original Initialize 35
and Corpus 62 twice, the eleven-field comparator, 120,000-ms validation,
30,000-ms cumulative runtime/WASI, 170+5+5-second host envelope, 64-million
cache work, 16/8-MiB cache/entry limits, 64 residents/pins, 86 tickets,
256-MiB combined memory, 65,536-byte guest log/transfer/native suffix bounds
and other source limits remain exact. The original stdout/stderr redirection
has no separate file-byte cap; this packet adds none. Observer storage and CPU
overhead are test-only and can consume the unchanged real deadline. They are
not runtime reservations, RSS, peak-memory or speedup evidence.

The restoration script was inspected as source and not run. It verifies the
sealed packet before reconstructing exact source and the compressed executable;
it selects no target. Guard controls intercept dispatch before any subprocess
and materialize no selection or attempt marker. Candidate runtime scratch and
executable remain absent.

## Independent finite evidence and cleanup

Cargo/Rust 1.99.0, Python 3.14.8 and macOS 27.0.1 arm64 are recorded with
tool hashes, command argv/environment, raw outputs and source bindings.
Offline Cargo uses two build jobs and one test thread. Only this filter runs:

```sh
cargo test --lib --locked --offline --no-default-features \
  --features experimental-swift-reactor --release \
  experimental_swift_reactor::cache_tests::independent_full_attribution_ \
  -- --nocapture --test-threads=1
```

Two Rust tests pass, with zero failures/ignores and 395 filtered tests.
Compilation plus execution takes 13.382 seconds; the tests report 0.00 seconds.
The two inherited compiler warnings remain. Four cancellation/output cases
preserve original `Cancelled`, original work, absent rejected-debit record and
the later sticky retry while exercising formatter failure, sticky observer
invalidity and failed output. Two successive lifetimes independently decode
functions 63 and 64 as first completions, reset once per lifetime, preserve the
final bitmap, and return all original reservations/live counts to zero. These
are finite synthetic validation/proof/cache operations: no guest instantiation,
guest instructions, Initialize, invocation or corpus executes.

Six host methods pass. They cover fifteen exact-selection binding mutations,
missing selection and existing-marker refusal, exact source reconstruction and
source-drift refusal, intercepted exact argv/170-second dispatch, zero-snapshot
validation failure, missing telemetry, and two original-result outcomes with
invalid telemetry. These are mocked dispatch controls, not target attempts.
The six independent schema rejection tests fail and remain blocking evidence.
An initial host-control setup used the copied driver's embedded include path;
its one failed assertion is retained. Correcting only that review fixture yields
the six passing host methods. No failed run was erased or counted as a pass.

All six owned command process groups were absent. Scoped holder checks were
empty, directory device/inode identities were stable, and cleanup removed
**24,334,739 logical bytes** of owned source/build/temp data without signals.
No redundant source archive or review executable is retained. The candidate
packet remains unchanged. The full review seal and read-only verifier retain
the exact evidence and the blocking verdict:

```sh
python3 -B verification/swift-current-attribution-preparation-review/verify.py
```

This review performs no real-target validation, Initialize or Corpus; no live VM,
native instance, UI, phone, network/provider, signing, frozen hosted lane, Git or
root-index operation. The prior real result remains Corpus 1 CacheWork exhaustion
at 64,000,001/64,000,000 after 23,358,291 instructions, with original final
cleanup empty and Corpus 2 unrun. Current real-target attribution, successful
Corpus 1/2, native/public/signed behavior, immutable published-package FieldLog
use, final physical phones and accountable GA gates remain pending. The complete
W01–W18/G01–G38 scope is preserved.
