# Experimental capability runtime

Separate Swift package for the explicitly enabled experimental native capability
archive. It depends on `MixerCapabilities`, uses the strict guest transport codec,
and owns a private host plus eight token mappings. It does not depend on
`MixerRuntime`; never link the legacy and experimental Rust archives together.
Existing runtime, SDK, identity, activation and default VM behavior remain separate.
This package supplies no verified activation or release authority.

Build the native dependency from the reviewed full revision, into a fresh output:

```sh
python3 experimental-capability-runtime/build-vm.py \
  --revision b25e3b7de2391a80d12e7fd75e60903495bec120 \
  --target host --output /absolute/fresh/experimental-stage
swift test --package-path experimental-capability-runtime \
  -Xcc -I/absolute/fresh/experimental-stage/include \
  -Xlinker -L/absolute/fresh/experimental-stage/lib \
  -Xswiftc -warnings-as-errors
```

The staged library must be `lib/libmixer_vm_capability_experimental.a`, alongside
the two exact pinned headers in `include/`. Do not use a Cargo target directory.
The builder has its own receipt and scope; the bridge qualification additionally
records the headers, archive and SDK source actually consumed.

Call synchronous `ExperimentalCapabilitySession.prepare` with installed-selected
module bytes, startup export, policy and concrete adapters. It acquires one of
sixteen process permits before enqueueing any module-capturing work. Call the
returned construction's one-shot `create()` asynchronously. Unused construction
release/cancel performs no native work; cancelled in-flight creation holds its
permit until cleanup. `startup()`, development-only `enableEffects()`, `invoke`,
`readMemory` and `writeMemory` admit at most one command per owner. Native handles,
mailbox tokens, host IDs, completions and exit acknowledgement stay private.
`close()` synchronously latches admission shut and schedules cleanup off UI.
Public-owner deinit also closes; accepted native exits retain their own lifetime.

`ExperimentalCapabilityValidator.prepare(module:startupExport:configuration:)` is
separate bounded admission-only work. Its one-shot `validate()` returns `Void`
after the same private C validator used by construction checks every body, exact
imports, defined startup/wake and declared memory. It creates no native instance,
mailbox, host or adapters and executes no export. Success is not an instantiability,
startup, authorization or transferable validation proof; construction revalidates.
Two independent process permits cover unused, queued, running and draining
validations on one serial off-UI worker. Synchronous prepare checks the 4MiB module,
4096-byte startup and shared configuration bounds before a permit and explicit
owned byte/name snapshot. A third validation rejects as `validation_busy` before
snapshot or queueing. Unused cancel/deinit frees capacity; queued/running cancel
retains it through actual dequeue/C return. Cancellation cannot interrupt native
validation and has no latency/50ms validation guarantee. A malformed report or
status4 quarantines only its validation permit, retaining no input or C session.
The existing synchronous updater validator has no async integration here.

`ExperimentalCapabilityError.failure` and `status.failureDetail` carry a closed
kind/reason, native call context, checked machine code/status and bounded reported
function/absolute byte offset. Human message text never classifies a failure.
Validation and instantiation rejection, deterministic guest traps, cancellation,
turn deadline, resource interruption, panic/quarantine and unknown reports stay
separate. Unknown code/status/context combinations stay unknown; malformed metadata
fails closed. Error equality still compares only the original code and status.
The first status failure string/detail remain immutable, including autonomous wake
failure; typed diagnostics do not relax exit or quarantine ownership.

The shared configuration accepts an exact memory ceiling of zero pages. A valid
module must still declare its one defined memory; a declared minimum or maximum
above zero rejects under that ceiling. Signed-byte narrowing belongs to a future
authorizing factory and must floor bytes/65536, never round up.

A single serial off-UI pump checks the installed batch budget before transfer,
codec and turn phases, processes at most four turns or eight milliseconds before
yielding, and retains incomplete phases. Individual C/codec operations can
finish after that cutoff; this is a cooperative bound, not a hard wall-time SLA.
VM turns separately have a cooperative maximum fifty-millisecond bound. Active
work uses one coalesced event and one ten-millisecond timer per owner; idle owners
park the timer. Eight mapping slots admit at most one worker each. Rate admission
uses a monotonic token bucket (default burst8/refill32 per second); a rejected
request gets a terminal quota result without retry. Host reservation failure is
one terminal unavailable result, including the transient interval between native
exit notification and asynchronous host-slot reclamation.

The bridge narrows an HTTP request's C deadline before reserving a host ID. It
samples Swift ContinuousClock before the C remaining-duration query, uses C's
floored remaining milliseconds, and carries that absolute cap through actor
queueing. The host additionally narrows it to its existing installed deadline.
Expiry/cancellation, result delivery and actual native exit remain separate;
only accepted `didExit` or explicit no-I/O cleanup authorizes acknowledgement.
Close cannot undo an already admitted durable storage effect or framework I/O.

Ordinary checked C status3 command rejection remains recoverable. Checked native
metadata/value faults and status4 fail closed with conservative process-lifetime
capacity quarantine. Malformed create reports or untrustworthy create/cleanup
outcomes likewise retain only their construction permit. A later close0 cannot
prove sticky quarantine was cleared. No recovery API or general OOM/no-unwind
claim is supplied. Swift/Foundation allocations, Tasks, locks, opaque installed
adapters and Rust Arc/Mutex initialization can still have infallible failures.

Input limits and `retainedPayloadBytes`/`maximumLogicalPayloadBytes` are logical
byte counts, not allocated backing capacity or RSS. Caller Data slices/String,
policies and installed adapters can retain larger backing allocations. Status
payload counters exclude typed DTOs, transient copies and framework/native
buffers. C takes use explicit byte copies and host callbacks take one independent
snapshot outside locks. `acceptedCalls` counts C Call records taken, not host
acceptance or I/O. Timing/worker counters are observations; runtime Task object
retirement and allocator recovery are not implied by the logical worker tail.

Run `python3 -B experimental-capability-runtime/verification/verify.py --name <fresh-name>`
for frozen source export, debug/release, native Swift TSan, separate measurement,
public cross-probe link and official iOS/simulator/Android compilation/linking.
The exact commands, source/SDK/header/archive hashes and logs are in the generated
receipt. The cross probe is a link consumer using only public API; it deliberately
rejects an empty module through typed validation and construction and is not a guest-effect happy-path test.

The implementer suite also tests uncalled invalid bodies, exact import/wake/startup/memory admission, independent validation capacity/cancellation, zero-page construction, checked report mutations and real runtime typed failures. Its original real Wasm verifies concrete app-private storage
put/get/delete/missing results, traps before successful turn commit, strict
malformed arguments, deadlines, rate/fairness and retained native exit ownership.
HTTP URLProtocol tests are explicitly framework interception. A separate local
TLS fixture exercises normal-trust rejection of an ephemeral untrusted loopback
certificate, with no trust/keychain/credential changes; it proves a network
failure path, not HTTPS success. Process-wide allocator/RSS/CPU samples and idle
wake counters are observational. System frameworks and the Rust archive are not
Swift-TSan-instrumented. Cross builds are compile/link evidence only. No physical
device, release, identity-v2, activation, C-registry composition beyond the pinned
candidate, FieldLog, publication or GA gate is qualified here.
