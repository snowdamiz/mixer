# Settings first-failure instrumentation derivative

This packet adds a bounded local first-failure diagnostic to the exact Settings
client POST path selected by the accepted offline timeout diagnosis. It changes
no deadline, request scheduling, transport semantics, setup/importer predicate,
or native selection. It is a frozen derivative for independent review, not a
new native packet or a correction to the failed V5 run.

The accepted diagnosis handoff is SHA-256
`162ffcc666e601263a70a6226289eab833e6335d84fa9a36b89c91426e248209`;
[root acceptance](../verification/apple-settings-bridge-timeout-root-review/acceptance.json)
selects this instrumentation only. The retained run establishes that the
terminal observation had at most 646.35 ms left and the last committed chunk
had at most 12.16 ms left. Its timed-out request identity and causal server
phase remain unknown. All prior failures remain authoritative.

## Source and change boundary

[Source bindings](../verification/apple-settings-failure-instrumentation/source-bindings.json)
identify the two exact original Swift files extracted from the bound V5 frozen
archive's nested `accepted-sources.tar.gz`. Their retained copies are under
`original/`; no live UI source or frozen original was edited. The derivative
`DiagnosticTransport.swift` is byte-identical to its original. The derivative
`ToggleUITests.swift` changes only `SettingsTelemetry.post()` and adds its private
first-failure latch property. Every byte from `func start()` through the end of
the original file remains unchanged. The new helper is
[SettingsFailureDiagnostic.swift](../verification/apple-settings-failure-instrumentation/derivative/SettingsFailureDiagnostic.swift).
The complete [source patch](../verification/apple-settings-failure-instrumentation/source.patch)
and [provenance](../verification/apple-settings-failure-instrumentation/provenance.json)
are part of the sealed handoff.

For the first local POST failure, the helper emits one
`MIXER_SETTINGS_FIRST_FAILURE` JSON line. Its JSON has a 2,048-byte ceiling
(2,078 bytes including prefix and newline). It records:

- Explicit start identity, or allowlisted request kind, UUID generation, sequence,
  stage, slot, and chunk index/count where present in that request.
- Issuing request ordinal and URLSession `taskIdentifier`; the latter is null
  when admission or local preparation fails before task creation.
- Client monotonic begin/end uptimes, the absolute client deadline, the actual
  allowance returned by the original `begin()`, and whether it was below 2 s.
- A fixed failure branch and numeric HTTP status/Foundation error code when
  observed safely. No status/error code is guessed after semaphore expiration.

An absent, malformed, or unsupported identity field is null. UUIDs must be
36-byte UUID strings; stages/kinds use explicit finite allowlists; slots must
match the exact bounded `settings-NNNN-ax/png` form; integers use explicit types
and bounds. Chunk requests have no stage in the original record, so their stage
is null. The helper does not infer a stage or a sequence from a URLSession task
identifier. The request ordinal includes the initial start request; sequence
zero is explicit start only.

The diagnostic never emits URL, headers, capability, response/error text,
payload hashes, snapshot/detail dictionaries, AX text, PNG bytes, or encoded
chunk data. It constructs metadata only after selecting the first failure.
A lock allows only one selection. Serialization/output errors are swallowed;
there is no bridge reference, retry, or replacement transport error in the
helper. Later failures cannot replace or re-emit the first diagnostic.

The original `transport.latch()` remains authoritative for semaphore and
response failures. The semaphore-expiration branch cancels and latches the
same original error before diagnostic emission. That branch reads no callback
box field. Callback data/status/error are read only after successful semaphore
completion, as in the bound original. The original request cap (2,500),
request/response body caps (8,192 bytes), 2-second request ceiling, relative
semaphore wait, 29-second client deadline, deadline shortening, serial upload
order, and original guards remain intact. This deliberately does not correct
the existing difference between the absolute deadline and the later relative
wait. Configuration/body/admission errors retain their original latching
behavior, including errors that were not sticky before this derivative.

## Executable host evidence

[Host receipt](../verification/apple-settings-failure-instrumentation/host-controls.json)
records 19 passing controls. A pinned Swift 6.3.3 compiler and explicit macOS 26
SDK target compile a host executable containing the byte-exact derivative
`SettingsTelemetry` declaration through `post()` plus unchanged
`DiagnosticTransportState`, the new helper, and host-only accessors/controls.
The full UIKit/XCTest file was not compiled. This satisfies the host derivative
compile boundary; it is not an iOS simulator build or runtime receipt.

The host executable uses a custom `mixerhostcontrol:` URLProtocol scheme to
supply responses without a socket, listener, or bridge server. Controls cover
success without diagnostic output; deadline/request-limit/local preparation
rejections; semaphore expiration with an actual clipped allowance; Foundation
-1001; HTTP 503; malformed, empty, and oversized responses; exact safe
start/mark/chunk identities; malformed-field redaction; nonfinite diagnostic
time redaction; output-sink failure; 128 concurrent first-diagnostic attempts;
and 32 concurrent serialized POST calls. The latter produces one synthetic
request, one original sticky timeout, and 31 prior-failure rejections.

Original failure values, request counts, and no-second-request behavior are
asserted at execution time. The original transport also passes an ample
2-second allowance and the approximately 12.16 ms example from the retained
last-commit timestamp. Those identities/times are synthetic control inputs,
not a recovered native timeout identity or latency measurement.

All four host attempts retain command/version/output/source hashes and exact
control/assembled source snapshots. Attempt 1 failed because of errors in the
new host test harness. Attempts 2 and 3 reached invalid serialization probes
(Date and NaN), which raised Foundation `NSInvalidArgumentException`, rather
than a catchable Swift error. These failures are preserved; the invalid probes
are excluded from the final bounded suite. The derivative preserves that
original serializer behavior. Its Swift serialization-error branch is not
claimed to handle Objective-C exceptions or process crashes. Attempt 4 passes
all 19 final controls. Its executable/module cache were removed; only compact
source and receipts remain.

Run the executable host controls with
`python3 verification/apple-settings-failure-instrumentation/run_controls.py`.
This creates another retained owned attempt and removes its owned build scratch.
A later attempt changes the packet and requires resealing/review. The independent
read-only check is
`python3 verification/apple-settings-failure-instrumentation/verify.py`.
It hashes the handoff, exact source/archive bindings, patch, controls, receipts,
and derivative boundary; it executes no producer, compiler, network, UI, device,
or native-runtime tool and writes no file.

## Limitations and acceptance

No simulator/emulator/device was queried, created, launched, or retried. No UI,
screenshot, native listener, or hosted catalog-inspector/authority-driver or
rejected outbound-transport V2 source was read/imported/executed. Cleanup removed
only the packet's owned host scratch. Other projects' instances/processes/data
were untouched. No dependency was added beyond the existing platform Foundation,
XCTest/UIKit/CryptoKit imports and Python standard library tooling.

This packet has no native packaging or selection authority. Root must review
it before any later native preparation. Native instrumentation behavior, full
UIKit compilation, and recovery of the next failed request's actual identity
remain unverified. Settings remains failed; dependent `test010ReferenceFirstTab`
remains skipped; the incomplete run still fails its importer. Physical phones
remain disconnected/deferred. There is no transport fix, durability/origin
relaxation, setup success, keyboard/carrier/full-matrix completion, immutable
FieldLog dogfood, signing, store, operational, or GA acceptance.
