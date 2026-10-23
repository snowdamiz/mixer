# C facade, UI-entry and progress transport stage

This stage implements section 4 of the accepted private binding contract in
`docs/android-signed-ui-binding-contract.md`. The document's proposal header is
superseded for staged implementation by the root's external acceptance receipt
`verification/android-binding-contract-acceptance.json`. The verifier checks the
accepted contract SHA-256 before compiling. No contract document was changed.

Reproduce from the repository root:

```sh
python3 native/android/signed-guest-ui/transport/verify.py
```

The command now writes this stage's evidence here, preserving the earlier
`android-guest-ui-transport` and `android-transport-review` evidence. `receipt.json`
records actual commands, versions, environments, source revision, selected source
manifest/tree digest, output paths and Android artifact hashes. Build products are
local ignored files. Root independent review and any subsequent commit binding
remain separate from this implementation receipt.

## Observed checks

| Suite | Debug | Release | ASan + UBSan | TSan |
| --- | ---: | ---: | ---: | ---: |
| Original transport tests, unchanged source | 26 | 26 | 26 | 26 |
| Previous independent review probes, unchanged source | 9 | 9 | 9 | 9 |
| New facade/entry/progress probes | 27 | 27 | 27 | 27 |

The driver verifies the two old test source hashes against their frozen evidence
manifests. The old bodies link a separate inert test-only `mxuit_progress` symbol;
no assertion or case is removed. New probes exercise actual progress dispatch and
the actual `platform_android.c` callback wrapper with a small POSIX implementation
of the official NDK ALooper symbols. Strict warnings are errors in all builds.

Official installed NDK r27d API30 arm64 builds compile both product C sources,
reject a no-undefined shared link with all three fixed hooks absent, separately
reject a link missing only `mxuit_progress`, and link the inert test-only hook probe
against `libandroid`. ELF dependency/alignment and product symbols are recorded.
No test control appears in product objects. No new dependency was introduced.

## Implemented boundaries and adversarial schedules

Sixteen additional scalar facade records issue checked positive Java-safe IDs.
Each facade links at most one replaceable endpoint, survives attempts, closes
independently, and may allocate only one successful terminal endpoint. Endpoint
capacity failure leaves the terminal issuance bit untouched. Acquiring or
reclaiming records creates no hook, fault or pipe demand, supporting the specified
external admission lock order.

One global UI-entry lease records an exact facade/serial. Direct INGRESS/CLEANUP
admission precedes the simulated JNI/weak lookup. PRESENT/RETIRE admission requires
the exact linked owner, active drain kind and waiter. A claimed PRESENT remains
admissible after reentrant scalar close. Entry leave never advances a return
fence; it adds one coalesced pipe demand. Entries also pin a facade without any
endpoint, and an endpoint acquired during a cleanup lease inherits that serial.

The nested-entry probes use a fixed native-to-Java helper schedule: verify the
lease, simulate resource lookup, then synchronously invoke the registered native
callback from Java's conceptual nested turn. BUSY preserves the pending byte,
both fences, hook counters and registration. An ERROR event in this rejected
callback cannot create a fault. A lease with no existing byte also emits no new
wake when the nested attempt rejects. The scalar leave creates the later demand.

Other probes cover wrong facade/waiter/kind/thread/serial, invalid combinations
and zeroed outputs, stale entries, capacity, checked ID exhaustion, final cleanup
without an endpoint, entry fences after successful RETIRE, failed RETIRE pinning,
stable facade identity across fresh attempts, and rejection of a second terminal
endpoint. Held drain-entry, completion and platform callback tails keep both
endpoint and facade capacity pinned. Releasing the held tail still cannot reclaim
until the original UI thread enters its later callback. A separately held
process-only healthy progress hook permits old scalar records to be reclaimed and
reused after the published fences while that process-only hook remains active.

Healthy progress publishes only changed callback/UI-entry fences, before the
owner scan and outside the C lock. First sticky faults publish once outside the
lock, including worker pipe failure, callback read/event failure, installation
failure, entry exhaustion and UI-leave pipe failure. The test hook reenters
inspection to check lock release. The final no-helper callback creates no further
byte; repeated facade retirement preserves exactly two process pipe FDs and one
Looper registration/reference baseline.

## Evidence limits

These are C state-machine and Android object/link receipts. The ALooper driver is
a host model, and the direct-entry schedule executes no JNI or Java. There is no
Android Looper execution, main-Looper identity proof, actual Swift Task.value,
resource-alias/deinit proof, weak-global lifecycle, native View/health observation,
emulator qualification, signed selection or public Android support in this stage.
The caller must still supply the exact final Swift cleanup receipt before facade
reclaim; C proves only scalar accounting. Actual Task joins, JNI helper scalar
return tails and resource destruction require the later binding integration.

ASan leak detection is disabled; no RSS, energy, performance or leak claim is
made. No phone discovery, physical runs or reconnect request occurred. Physical
checks remain pending under the user's restriction. Android signed UI remains
unsupported, and no publication, signing, store, customer or GA gate is verified.
