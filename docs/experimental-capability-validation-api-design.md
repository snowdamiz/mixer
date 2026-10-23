# Experimental capability validation and typed failure API

Draft for root review, 2026-10-23; no implementation or authority change. This is
an additive follow-on to bridge `641b844e566c12c3ffda5f461512d1819faedd02` and the
contracts at `aca686bfc72b8f18db727de5307977fb51790e0a`. The intervening metrics
compiler-compatibility patch changes no proposed API. Existing candidate receipts
remain immutable. Only this new design file belongs to this slice.

The native prerequisite already exists:
`mixer_vm_capability_validate_v1` calls `CapabilityGuest::validate_only`, which
uses the same private `validated` path as construction. It decodes and validates
every body, the exact imports, defined startup/wake and declared memory under
v3 capability admission. It creates no Instance, mailbox, host or adapters and
executes no export. It allocates bounded decoder/validator structures; it is not
allocation-free or generally recoverable under OOM. There is no validation
interrupt hook in the current C ABI.

## Concrete additive interface

```swift
public enum ExperimentalCapabilityValidator {
    public static func prepare(
        module: Data,
        startupExport: String,
        configuration: ExperimentalCapabilityConfiguration = .init()
    ) throws -> ExperimentalCapabilityValidation
}

public final class ExperimentalCapabilityValidation: Sendable {
    public func validate() async throws  // Void; one shot
    public func cancel()                // synchronous, idempotent
}
```

Keep the namespace separate from Session. There is no policy/adapters argument,
predecoded Module, C handle, native session, execution permit, completion callback,
export invocation or transferable success token. A normal return means only
that this operation's captured tuple passed complete native admission. It cannot
authorize another module, startup name or configuration. Construction continues
to validate and instantiate independently; it does not accept a prior result.

Use the same private native limit conversion and the exact same single
`libmixer_vm_capability_experimental.a` as construction, with the pinned headers
(`mixer_vm_capability.h` SHA256 `9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6`,
legacy header `18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd`).
Do not call a legacy/profile/inventory validator, co-link another archive, or
reimplement partial admission in Swift. Validate every configuration field using
the existing common checker even when a field only affects later execution.

Synchronous prepare first checks module length `0...4_194_304`, nonempty startup
UTF8 length at most4096, and all configuration ceilings, then acquires a fixed
validation permit **before** an owned snapshot or queue/Task capture. Make explicit
owned byte/name snapshots after this admission; foreign Data backing must not
change queued validation bytes. Snapshot cost is bounded by the admitted lengths,
but allocator/DTO/RSS overhead remains a separate category. Empty modules pass
this structural bound and receive the native malformed-module rejection.
Inspect at most4097 startup UTF8 bytes during preflight; do not scan an arbitrary
caller name or allocate its byte array before admission.

This public development API mirrors existing construction name semantics. The
new authorizing factory must separately enforce its installed no-control startup
name contract before calling either API; do not silently widen that contract or
change existing development construction name behavior in this slice.

## Two permits and finite cancellation ownership

There are exactly two process validation permits, separate from the existing
sixteen pending/live/draining construction/session permits. C validation publishes
no registry owner, so it must neither reserve a native session slot nor starve
existing session permits. One dedicated serial off-UI queue runs C validation;
at most one other admitted validation can be prepared or queued. Total accepted
validation captures remain two, including cancelled work awaiting cleanup.

The one-shot state machine is `prepared → queued → running → finished`:

- Cancel/deinit while unused clears its input and releases its permit without
  scheduling anything. A second validate, or validate after unused cancellation,
  throws `validation_consumed` before installing a cancellation handler; a
  rejected second caller cannot cancel the original operation.
- Validate atomically claims the prepared state, then queues one closure retaining
  only the operation owner/continuation. Store its bounded input in that owner.
  A caller task already cancelled or cancelled while queued records cancellation;
  the queue skips C. Keep the permit until the queued closure actually dequeues
  and disposes its input. Releasing it earlier would permit an unbounded queue of
  cancelled tiny jobs, even if module bytes had already been cleared.
- During C, cancellation sets a flag but cannot free C's input, abandon ownership
  or release capacity. Await completion only after C returns and cleanup finishes.
  This has no cancellation-latency or50ms validation guarantee; the50ms limit
  governs VM execution turns. No semaphore wait, Task fanout or actor lock wraps C.
- At publication, ordinary checked native success/rejection loses to a previously
  recorded cancellation and throws Swift `CancellationError`. A published result
  stays immutable under later cancel. A malformed report or checked status4
  remains an explicit native-boundary fault, even if cancellation raced it.
- Ordinary completion/rejection/cancellation releases the permit after input and
  C frame cleanup. A malformed report/status4 conservatively quarantines that
  validation permit for the process lifetime, retaining no module or worker.
  This availability policy bounds uncertain repeated native faults; it does not
  claim a C session existed or fabricate a session close/exit. Unknown but
  structurally valid code/status combinations return an unknown failure and
  release normally after return.

Use one continuation and at most one queue item per permit. Dropping the public
handle cannot drop the queued/running owner. No arbitrary completion closure,
per-cancel Task or unlimited retry is added. Busy rejects synchronously as
`validation_busy`, before snapshot/queueing. Keep existing construction cancellation,
capacity, error strings and cleanup behavior unchanged.

## Typed diagnostics without changing existing error semantics

Add the following read-only surface; initializers remain internal:

```swift
public struct ExperimentalCapabilityFailure: Sendable, Equatable {
    public let kind: ExperimentalCapabilityFailureKind
    public let operation: ExperimentalCapabilityFailureOperation
    public let code: String
    public let nativeStatus: UInt32?
    public let location: ExperimentalCapabilityNativeLocation?
}
public struct ExperimentalCapabilityNativeLocation: Sendable, Equatable {
    public let functionIndex: UInt32?  // UINT32_MAX maps to nil
    public let byteOffset: UInt32     // exact reported absolute offset
}
public enum ExperimentalCapabilityFailureKind: Sendable, Equatable {
    case callerAPI(ExperimentalCapabilityAPIFailure)
    case validation(ExperimentalCapabilityValidationFailure)
    case instantiation(ExperimentalCapabilityInstantiationFailure)
    case guestTrap(ExperimentalCapabilityGuestTrap)
    case cancelled
    case deadlineExceeded
    case resource(ExperimentalCapabilityResourceFailure)
    case panicOrQuarantine(ExperimentalCapabilityInternalFailure)
    case unknown(ExperimentalCapabilityUnknownFailure)
}
// Existing public types gain getters:
// ExperimentalCapabilityError.failure: ExperimentalCapabilityFailure
// ExperimentalCapabilityStatus.failureDetail: ExperimentalCapabilityFailure?
```

`operation` is a closed enum: localAPI, validation, construction, startup,
enableEffects, invocation, wake, readMemory, writeMemory, take, post, ackExit,
limitDeadline, expire, close. It is captured privately at the actual call site,
never supplied by a caller or inferred from error text. The associated reason
families below are closed enums, not String escape hatches. Original `code`,
`nativeStatus` and `description` remain unchanged. Implement error `==` explicitly
as original **code + nativeStatus only**; do not synthesize equality over the new
fields. New Failure equality includes all its fields.

The associated enums use exactly the named reasons in the mapping below. API
reasons are invalidInput, consumedOperation, unknownExport, invalidInvocation,
invalidNativeArguments, invalidLifecycleState, nativeBusy, invalidNativeSession.
Validation reasons are malformed, unsupported, invalidBodyOrStructure,
configuredLimit, invalidLimits, requiredDefinedExport. Instantiation reasons are
initialDataBounds, initialElementBounds, admissionRejected. GuestTrap cases are
unreachable, integerDivideByZero, integerOverflow, invalidConversionToInteger,
memoryOutOfBounds, tableOutOfBounds, indirectCallNull, indirectCallTypeMismatch,
hostAbort. Resource reasons are fuel, hostCalls, callDepth, operandStack,
nativeInstantiationAllocation, capabilityPayloadAllocation,
requestIdentityExhaustion, nativeSessionCapacity, validationCapacity,
constructionCapacity, commandCapacity. Internal reasons are poisoned,
containedPanic, invariant, registryPoisoned. Unknown reasons are
malformedNativeReport, unexpectedStatusOrOperation, unrecognizedCode,
terminalState, unsupportedEnvironment, nativeProtocol, bridgeInvariant,
nonBridgeError. No associated caller-supplied message determines these cases.

Populate `status.failureDetail` when the first existing failure string is recorded,
using the same diagnostic as a thrown error. This covers autonomous wake failures.
Never overwrite it with a later close/cleanup error, reinterpret a terminal-state
report as the earlier cause, or introduce failures for the already explained
ordinary closed-handle3 race. First failure, owner stop/quarantine, actual exit and
permit semantics remain unchanged. Swift-local bridge invariant failures are
`unknown(.bridgeInvariant)` with their existing code. Pure Swift input errors are
`callerAPI(.invalidInput)`; consumed one-shot operations are
`callerAPI(.consumedOperation)`, and admission/command busy is a named resource
capacity reason. Existing create cancellation still throws `CancellationError`.
The coordinator handles that exact Swift type separately; it never parses its
message. Arbitrary foreign Error values remain unknown.

## Checked native mapping

First validate report ABI1, reserved0, returned/report status equality, status
range0...4, value representation, operation-specific success shape and bounded
counters. Error codes must be nonempty NUL-terminated ASCII within48bytes; do not
use replacement UTF8 decoding to manufacture a recognized code. Message256 is
human diagnostic only and may contain truncated UTF8. It is never classified,
searched, compared or used to fill missing metadata. Keep malformed-report errors
under their existing local `invalid_native_*` code and nil nativeStatus, with
`unknown(.malformedNativeReport)`.

This is the complete allowlist for the current capability family; every omitted
code/status/operation combination is `unknown(.unexpectedStatusOrOperation)` or
`unknown(.unrecognizedCode)`. In particular, a known code under the wrong status
never acquires its known classification. Status2 alone never proves a guest trap.

| Checked status and exact machine code | Allowed operation/context | Kind/reason |
| --- | --- | --- |
|0, empty code | Canonical success shape for that operation | Normal result, no failure |
|1, `malformed`, `unsupported`, `validation`, `limit`, `invalid_limits`, `capability_export` | validation or construction | validation: malformed, unsupported, invalidBodyOrStructure, configuredLimit, invalidLimits, requiredDefinedExport respectively |
|2, `memory_out_of_bounds`, `table_out_of_bounds` | construction only | instantiation: initialDataBounds or initialElementBounds |
|2, the six validation codes above | construction only, second decode/validation | instantiation: admissionRejected; never a runtime trap |
|2, `unreachable`, `integer_divide_by_zero`, `integer_overflow`, `invalid_conversion_to_integer`, `memory_out_of_bounds`, `table_out_of_bounds`, `indirect_call_null`, `indirect_call_type_mismatch`, `host_abort` | startup/invocation/wake, with checked function/location metadata | guestTrap: exact corresponding enum case |
|2, `cancelled` | startup/invocation/wake | cancelled; no rollback implication |
|2, `capability_turn_timeout` | startup/invocation/wake | deadlineExceeded; this is the turn deadline |
|2, `fuel_exhausted`, `host_call_limit`, `call_depth_exceeded`, `operand_stack_exceeded` | startup/invocation/wake | resource: fuel, hostCalls, callDepth, operandStack |
|2, `allocation` | construction | resource: nativeInstantiationAllocation |
|2, `capability_allocation` | startup/invocation/wake/post | resource: capabilityPayloadAllocation |
|2, `capability_identifier_exhausted` | startup/invocation/wake | resource: requestIdentityExhaustion |
|2, `unknown_export`, `invalid_arguments` | invocation | callerAPI: unknownExport or invalidInvocation; existing terminal behavior remains |
|2, `capability_closed`, `capability_terminal` | session operations | unknown: terminalState; they do not reveal the earlier cause |
|2, `unsupported_float_environment` | startup/invocation/wake | unknown: unsupportedEnvironment; never guest blame |
|2, `capability_protocol`, `unsupported`, `invalid_limits` | startup/invocation/wake/enableEffects | unknown: nativeProtocol; never a deterministic trap |
|2 or4, `capability_poisoned` | status2 guest turn/enableEffects; status4 session operations | panicOrQuarantine: poisoned |
|3, `invalid_arguments` | Any native operation | callerAPI: invalidNativeArguments; do not parse messages to subdivide stale/range/operation errors |
|3, `capability_state` | startup/enableEffects/invocation/wake | callerAPI: invalidLifecycleState |
|3, `session_busy` | startup/enableEffects/invocation/wake/readMemory/writeMemory | callerAPI: nativeBusy |
|3, `session_limit` | construction | resource: nativeSessionCapacity |
|3, `invalid_session` | close, from the shared registry | callerAPI: invalidNativeSession |
|4, `internal_panic` | Any native operation | panicOrQuarantine: containedPanic |
|4, `capability_invariant` | Session operations | panicOrQuarantine: invariant |
|4, `registry_poisoned` | construction/session operations, never validation | panicOrQuarantine: registryPoisoned |

The resource enum additionally names local validation/construction/command capacity.
Known legacy-only `session_terminal`/`session_poisoned` on this capability route
are unknown rather than silently treated as another family. Unknown status4
still retains the existing quarantine behavior even though its typed cause is
unknown. Classification is diagnostic and does not relax owner lifetime rules.
Guest import0...7, native status0...4 and typed HTTP/storage completion failures
remain separate namespaces. An HTTP deadline payload is not a VM trap report.

Function metadata is diagnostic, not an executable proof or permission:

- Every structurally checked native error carries its reported location, including
  `(functionIndex:nil, byteOffset:0)`. Nil location means a local error or an
  untrustworthy native report; it is not inferred from a human message.
- Preserve UINT32_MAX as no known function; otherwise require index below the
  native fixed ceiling2048. Do not add a second Swift module parser to pretend
  to prove the exact function count. Record that bounded reported index only.
- For validation/construction, allow offsets `0...module.count`, including EOF
  decoder errors. Runtime instruction offsets must be within the retained module
  length;0 is also a real native sentinel for export/argument/import-boundary
  diagnostics and cannot be advertised as a proven instruction address.
- Runtime deterministic-trap mapping requires a reported function and a bounded
  offset in startup/invocation/wake context. Creation's initial-segment failures
  have no function and offset0. Plain C API/registry/panic failures require their
  canonical no-function/offset0 shape. Out-of-range or contradictory metadata is
  unknown malformed report, never evidence of deterministic guest failure.
- Store only module length, fixed scalar metadata and the bounded code, not module
  bytes or the human message, in a retained session diagnostic. Preserve existing
  numeric result checks, including signed i32 range and f32 upper-bit rejection.

## Exact zero-page narrowing

Change only the common configuration memory guard from `1...64` to `0...64`, and
use it identically for validator.prepare and session prepare/create. Defaults and other
ceilings remain unchanged. No Rust/C change or legacy profile expansion is needed.
A capability module still requires one defined memory: a missing/imported/shared/
memory64 memory rejects even when the configured page ceiling is0.

The future authorizing factory computes
`effectivePages = min(installedPages, signedMemoryBytes / 65_536)` using checked
unsigned arithmetic before UInt32 conversion. Positive signed byte limits1...65535
therefore yield0,65536 yields1, and65537 still yields1. Never round up or silently
replace0 with1. With limit0, `(min0,max0)` and min0 with implicit max bounded to0
are allowed; any declared minimum or maximum above0 rejects. Validate/create use
that exact tuple. A zero-length memory read/write at offset0 remains legal; a
nonempty transfer rejects and must not make a page appear.

Admission success is not an instantiation/startup guarantee. Native validate-only
does not apply active data/element segments; valid modules can still trap during
initialization, and allocation can fail. The factory must retain create/startup
checks before enabling effects. This is why those failures have separate kinds.

## Required async updater integration and qualification

The existing synchronous `ColdStartUpdater.ExecutableValidator` cannot await this
API. Preserve it and all existing routes. The first v3 verifier slice may produce
only bounded verified proof values; it must not pretend async durable staging is
already implemented. A later separately reviewed v3 selection/staging lifecycle
must acquire its own single-operation admission before retaining verified payload,
assignment, installed startup and effective-limit snapshots, then await this exact
validator off UI. Do not block an actor/MainActor with a semaphore or accept a
public caller-supplied success closure.

Keep the updater's generation reserved across the await without holding an actor
lock. Cancel/close retires that generation. On resumption recheck current
selection, exact payload/assignment digest, startup, configuration and generation
before any durable staging/commit. A stale/cancelled validation cannot stage or
complete a newer selection. Reuse no success across changed bytes/configuration;
construction rechecks the same immutable tuple. Signature/grants/installed-material
binding and effect authorization remain the higher-level factory's responsibility.

The implementation slice needs original executable evidence before dependency:

1. A valid defined-startup/void-wake module validates with no owner/adapter/export
   execution. An uncalled invalid body, wrong import module/name/signature/kind,
   missing/imported/nonvoid wake, missing/imported/argument-taking startup, Wasm
   start section, missing/multiple/shared/memory64 memory and out-of-limit declared
   maximum all reject through the same C path. Cover allowed startup numeric
   result separately from mandatory void wake. No inventory-only acceptance.
2. Match validate/create configuration at ceilings and narrowed limits. Test exact
   4MiB/4096-byte structural admission and first excess, invalid limits before any
   capture/queue, zero-page cases and signed-floor boundary examples. Observe no
   new legacy profile/API/symbol route. Include validation success followed by
   intentional initial-data/element create failure, classified as instantiation.
3. Hold a derived C-start/return gate: two accepted validations retain capacity;
   the third rejects before snapshot/queue. Cover abandon, unused cancel, already
   cancelled caller, queued/running cancel, late success, double/concurrent validate,
   and dropped public handle. No permit release or C-input destruction before
   actual return; no unlimited cancelled queue. Existing16 construction permits
   remain usable because validation creates no registry entry.
4. Original report-mapping tests cover every table row and operation restriction.
   Mutate status/code/ABI/reserved/value/counters/NUL/ASCII/function/offset fields
   in review-only copies. Known trap code under status1/3/4, trap text with native
   cancelled/allocation/unknown code, status2 with no function, unknown future
   code, malformed location and truncated human UTF8 never become a guest trap.
   Verify old error equality/code/status/description and ordinary failure behavior.
5. Trigger genuine guest traps, fuel/depth/stack/host-call limits, cancellation,
   turn deadline and allocation refusal in isolated cases. An autonomous wake
   failure publishes the same first typed detail as the throwing path; later close
   cannot replace it. Preserve successful storage/HTTP/exit/deadline behavior,
   explained close3 handling, and retained ack/quarantine obligations.
6. Freeze source/headers/one archive and record exact commands/tool versions/logs.
   Run debug/release, native Swift TSan and an unmodified public consumer; compile
   supported iOS/Android targets and prove the pinned CI compiler. Measure bounded
   validation latency/retained logical input under worst admitted modules without
   claiming an interrupt SLA, hard RSS bound or general OOM recovery. No device,
   signing, publication, release or GA qualification is implied.
