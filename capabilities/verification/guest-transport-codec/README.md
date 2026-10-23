# Strict guest transport value codec evidence

This implements the four public methods and fixed operation/rejection/outcome
enums published in frozen commit `3ba601332dab7c2aba98d7a50d7f0e893b1ea776`:
[`contracts/guest-capability-transport-v1.json`](../../../contracts/guest-capability-transport-v1.json).
The schema-driven generator emits `GeneratedGuestTransport.swift`; it reuses the
existing strict object preflight and generated operation/result type validators.
Direct DTO encoding is revalidated and a success result must have the exact
operation enum case, including put/delete even though they share a DTO.
Only the new decode entry points normalize non-wire JSON/preflight errors to fixed
`CapabilityWireError.invalid("guest transport JSON")`; the legacy codec is unchanged.

Run from the repository root:

```sh
python3 capabilities/verification/guest-transport-codec/verify.py
```

The new `guest-transport-probe` is a separate public consumer. It passes the
standalone raw argument bytes and complete new wrapper bytes directly to the
actual codec, then encodes the validated typed result. Frozen outcome-only fixtures
are inserted verbatim into fixed new wrapper metadata; their raw JSON is never
parsed/repaired before validation. The probe's offline input ceiling exceeds the
transport limit so the 524,289-byte case reaches the codec's own guard.

All 90 frozen fixtures execute in both debug and release, including the 21 wrappers
and two standalone byte-limit fixtures that were previously pending. Successful
outputs also compare semantically to the original accepted input. Per-case JSONL
logs preserve exact bounded UTF-8 stdout/stderr, exit status, command, input/output
digests and fixture identity. Decode each JSON string then encode it as UTF-8 to
reconstruct the original output bytes. The historical development contract,
original fixtures and old projection receipt are unchanged.

Programmatic tests add encoder validation of directly constructed invalid DTOs,
every operation/result routing mismatch, failure/rejection roundtrips for every
operation, exact argument/wrapper message limits, malformed raw input, decoded
64KiB/256KiB limits and legacy completion-owner validation before conversion.
The tests retain HTTP302 and `found=false` with nonempty canonical bytes as
type-valid results; native redirect/store behavior remains a separate policy.

The runner records byte preservation of schema v1, old models/adapters, old Swift
and Java codecs/probes, and semantic hashes against the frozen revision. Only the
native implementation hash changes to include the new installed codec. A private
owned-source snapshot starts without the new generated file, runs generation,
independently hashes actual output source files and checks that omitting the new
file changes the identity. A second generation and `--check` must be identical.
The snapshot is destroyed after that test; no other lane's artifacts are removed.

The receipt also records debug/release host suites, old Swift/Java differential
regressions, iOS arm64 library compilation, Android aarch64 API28 public-probe
linking, WASI module compilation, exact tools/commands/output hashes and source
tree/content digest. Cross-target builds reuse existing compatible scratch paths.
They are not physical execution, signed apps or native dependency qualification.

No native bridge, VM import registration, C ABI layout, activation, identity-v2,
release-v3 or Swift async executor is implemented here. These results do not
authorize OTA or close device, published-package FieldLog, store, operational or
GA gates. Phones remain disconnected and no device command is attempted.

The [superseded run marker](superseded-pre-error-normalization.json) points to an
archive retaining the exact earlier source, receipt and raw logs before the new
API's error normalization was completed. That run is superseded; the current
receipt covers the final codec and typed-error assertions.
