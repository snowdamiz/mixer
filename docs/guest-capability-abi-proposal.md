# Proposed opt-in guest HTTP/storage capability ABI

Status: contract design for coordination, 2026-10-22. No implementation, import
admission, OTA approval, full Swift execution, device receipt, or GA gate is supplied
by this document. Root accepted this implementation direction on 2026-10-22;
version changes remain separately coordinated, and exact native layouts, ceilings
and exit-ack design need executable proof before consumers land. No current profile
or activation admission changes. The binding scope is product-plan sections
[9–11](../mixer-product-plan.md).

## 1. Decision and current boundary

Propose an explicit `mixer-capability-v4` execution profile and guest ABI **2**. Its
opcode/type/table/memory rules and existing ceilings start exactly from
[`mixer-table-memory-v3`](../vm/profiles/table-memory-v3.json). The only additions
are the six imports below and bounded native request/completion state. This does
not add WASI, threads, guest references, start functions, full Swift runtime imports,
arbitrary callback functions, native pointers, sockets, filesystem paths, or other
capability families. The full Swift compiler/executor ABI is a separate dependency.

Keep profiles 1–3, `guest_abi=1`, their import allowlists, defaults, C symbols,
struct layouts, limits, and release-v1/v2 acceptance unchanged. In particular, the
old session-create function must still reject profile 4. A new profile cannot be
selected by a downloaded module, unsigned configuration, or capability declaration.

The implementation baseline already provides useful but disconnected contracts:

| Current source | Observed contract and implication |
| --- | --- |
| [`capabilities/schema/v1.json`](../capabilities/schema/v1.json), [`Wire.swift`](../sdk/Sources/MixerCapabilities/Wire.swift) | Closed HTTP and key/value types, exact schema hashes, strict JSON, fixed errors, and host-issued UUID/slot/generation request identities. Preserve these value semantics. |
| [`Host.swift`](../sdk/Sources/MixerCapabilities/Host.swift) | Per-instance actor intersects installed/release grants, issues IDs, serializes terminal transitions, and retains a running adapter's slot after cancellation/deadline until it exits. Reuse this native enforcement. |
| [`GuestClient.swift`](../sdk/Sources/MixerCapabilities/GuestClient.swift) | Typed async closures over encoded envelopes; these are not actual Wasm imports or an implemented guest scheduler. Keep its public behavior. |
| [`validate.rs`](../vm/src/validate.rs), [`execute.rs`](../vm/src/execute.rs) | Only `mixer.checkpoint ()->()` and `mixer.abort (i32)->()` are approved. Inventory alone never authorizes imports. |
| [`vm-session-v1.json`](../contracts/vm-session-v1.json), [`session.rs`](../vm/src/session.rs), [`Session.swift`](../runtime/Sources/MixerRuntime/Session.swift) | Generation handles, 16 process sessions, serialized invoke/read/write, cooperative terminal cancellation, retained in-flight storage, and copied memory transfers. No async capability channel. |
| [`RuntimeIdentity.swift`](../runtime-identity/Sources/MixerRuntimeIdentity/RuntimeIdentity.swift), [`release-v2.json`](../contracts/release-v2.json) | Fingerprint and signed grants exist; current identity and release protocols require guest ABI 1. Hashing a configuration does not bind an arbitrary supplied adapter/policy object to that configuration. |
| [`InstalledExecution.swift`](../activation/Sources/MixerActivation/InstalledExecution.swift), [`StartupWork.swift`](../activation/Sources/MixerActivation/StartupWork.swift) | Activation explicitly rejects nonempty capability hashes/grants and creates the existing synchronous session. Removing those checks before the following dependencies land would be unsafe. |

## 2. Guest imports: typed enqueue, cancellation, and polling

The proposed module name is exactly `mixer.capability.v1`. It is an allowlisted
transport namespace, not a native plugin lookup name. No generic operation dispatch
import is admitted. The module may also use the unchanged `mixer` imports.

| Import | Exact Wasm signature | Bound operation and argument JSON object |
| --- | --- | --- |
| `http_request` | `(i32 args_offset, i32 args_length, i32 token_offset) -> i32` | `network.http.v1/request`, `HTTPRequestArguments` |
| `storage_get` | Same | `storage.keyValue.v1/get`, `KVGetArguments` |
| `storage_put` | Same | `storage.keyValue.v1/put`, `KVPutArguments` |
| `storage_delete` | Same | `storage.keyValue.v1/delete`, `KVDeleteArguments` |
| `cancel` | `(i64 token) -> i32` | This originating VM session's request only |
| `poll` | `(i64 token, i32 output_offset, i32 output_capacity, i32 length_offset) -> i32` | This request's terminal completion only |

These are synchronous, bounded mailbox operations. They do not wait for an actor,
network, disk, timer, UI thread, or another guest invocation. The import returns
after copying/admitting bytes; a successful enqueue does **not** assert that its
arguments are valid, permitted, or that native I/O has begun.

The executor drains calls only after the originating guest invocation returns
successfully. Import return alone does not yield the invocation or permit native
dispatch. If the invocation traps, runs out of fuel, is cancelled, or closes before
returning successfully, its queued calls are discarded without starting I/O. A guest
that waits for a native I/O completion in the same invocation cannot make progress; it must
record its continuation/token and return. After successful turn return and native
dispatch, a later guest turn's trap/cancel/close can suppress delivery but cannot
undo an effect that began or committed. A cancellation racing already admitted I/O
may still allow it to start/commit before cancellation is observed. This ABI is not
a transaction over a guest invocation and external systems.

Guest transport return codes are fixed and distinct from C report statuses and
`CapabilityFailure`: `0 accepted/success`, `1 pending`, `2 bufferTooSmall`,
`3 invalidArguments`, `4 staleRequest`, `5 quotaExceeded`, `6 sessionClosed`,
`7 alreadyTerminal`. Unknown codes are a transport protocol error in the guest
adapter. Enqueue uses 0/3/5/6; cancel uses 0/4/6/7; poll uses 0/1/2/3/4/6.
An instruction-level VM failure such as insufficient fuel still traps normally.

Enqueue requires one defined, nonshared memory at index zero; it must exist even if
the guest never otherwise uses memory. Interpret offsets/lengths as unsigned i32
bit patterns. `args_length` is 1...524,288. `token_offset` addresses exactly eight
bytes, written little-endian, with no alignment requirement. Check the full input
and output ranges, checked arithmetic, non-overlap, session state, slot quota, and
byte reservation before any copy or mutation. Rejection writes nothing and issues
no request. Success snapshots the arguments, allocates one request, writes its
nonzero token, and returns 0 as one serialized transition. No linear-memory borrow
or allocator pointer survives the import; subsequent mutation/growth cannot alter
the request.

The argument payload is **only** the exact generated argument object from
capability schema v1. It contains no guest-selectable session, operation, grant,
native implementation, executor, schema hash, destination directory, or callback.
Each import fixes its capability ID, operation, and exact installed v1 schema hash.
The trusted bridge strictly decodes this object before any I/O, with the existing
v1 UTF-8/escape/duplicate-key/integer/base64/depth/type/unknown-field rules and bounds.
The generation tool must expose owned payload codecs; using a raw `Codable` DTO
decode or an unchecked cast to bypass the current codec preflight is forbidden.

`poll` validates the complete destination capacity and the four-byte little-endian
`length_offset` range, including a zero-capacity destination (`offset <= memory
length`). Those output ranges cannot overlap. On pending it writes length 0 and
returns 1; on buffer-too-small it writes the required length, leaves destination
unchanged, and retains the result. On success it copies the full completion, writes
its length, and consumes delivery exactly once. No partial copies occur. Repeated
poll after consumed delivery returns 4, even if native cleanup is still pending.
Other failures leave both outputs unchanged. Capacity is 0...524,288. Guest memory
is never a destination for a native callback or for a post-completion C call.

## 3. Completion payload and native value semantics

A successful poll yields strict UTF-8 JSON with exactly these keys:

```json
{
  "abi": 1,
  "capability": "network.http.v1",
  "schemaHash": "<exact current capability schema hash>",
  "operation": "request",
  "outcome": {"kind": "success", "value": "<operation-specific result object>"}
}
```

The example uses placeholders for the hash/result; it is not a wire fixture.
`abi=1` versions this new transport payload, independently of overall guest ABI 2.
The JSON encoding/validation restrictions and 524,288-byte message ceiling are the
same as capability schema v1. Key order is irrelevant on decode; owned encoders
emit sorted keys. Completion identity is the session/token supplied to `poll`, not
a guest-supplied JSON identity. Capability/hash/operation must equal the retained
request's fixed metadata on both native post and guest decode.

There are exactly three outcome variants, each with its exact listed fields:

| Outcome object | Meaning |
| --- | --- |
| `{"kind":"success","value":<typed object>}` | `HTTPResponse`, `KVGetResponse`, or `KVMutationResponse` bound to this operation. Strict result validation precedes posting. |
| `{"kind":"failure","code":<CapabilityFailure>}` | One of the unchanged eight capability v1 error strings. Cancellation/deadline do not imply that an external mutation was undone. |
| `{"kind":"rejected","code":"invalidArguments"}` | The copied guest arguments failed strict typed decoding before native dispatch; no I/O started. This is a transport rejection, not an added capability v1 error. |

Do not forward an existing host envelope wholesale: the trusted bridge first binds
and decodes it against the actual `CapabilityCall`, then emits this payload. The
new payload does not change existing call/cancel/completion envelopes or their
schema hashes. The ordinary `GuestCapabilityClient` remains supported; a new
transport adapter exposes the same four typed async operations and maps the
separate rejected outcome to a typed transport error.

Preserve all current operation semantics: HTTPS exact origin/method grants; six
methods; request body 64KiB, response body 256KiB; 32 bounded unique headers;
1...30,000ms HTTP timeout; no redirects, retries, ambient cookies/credentials,
streaming, or resumable transfers. Storage retains 64KiB values, app-private exact
namespaces, 4MiB/1,024-entry store ceilings, atomic replacement, and its existing
uncertain-commit behavior. Payload base64 limits count decoded bytes. Empty stored
values remain distinct from missing values. No key is a filesystem path. This ABI
adds neither secrets nor a database/migration abstraction.

## 4. Request ownership, bounds, and terminal transitions

The VM issues opaque 64-bit request tokens: high 32 bits are a nonzero generation;
low 32 bits are slot+1. They are bit patterns, not signed integers or pointers.
Tokens are scoped to one capability VM session and are not authorization secrets.
Two live sessions may have equal token values; neither can address the other's
mailbox. Start each new slot at generation 1, increment only after full release,
and retire a slot permanently at `UINT32_MAX`. Zero, an unused slot, a stale
generation, consumed delivery, and another session's request context reject.

Proposed v4 fixed ceilings, all separately visible in the installed fingerprint:

| Resource | Ceiling and accounting |
| --- | --- |
| Outstanding requests | 8 per session; includes queued, executing, terminal-unconsumed, and consumed-but-native-draining requests. The bridge constructs `CapabilityHost(maximumRequests: 8)` or a narrower value. |
| Mailbox reservation | 8MiB per session; each enqueue reserves `args_length + 524288` before admission, so every admitted request has room for one maximum completion. A reservation is accounting, not a command to preallocate all bytes. |
| Retained transport payload | At most 524,288 bytes per request and per completion; each ownership tier has a separately bounded copy. Queue copies do not include opaque OS networking buffers. |
| Dispatch rate | Before starting I/O, native bridge token bucket: burst 8, refill 32 starts/second using monotonic time, configurable downward in native policy. Exhaustion completes with `quotaExceeded`; no retry is automatic. |
| Native response lifetime | Installed monotonic deadline 1...30,000ms, configured downward. Starts at successful VM enqueue, including mailbox/actor admission delay; HTTP's smaller request timeout is applied by the bridge and may only shorten it. |
| VM work | Existing fuel, host-call, memory, stack and depth ceilings remain unchanged; each new import charges one host-call plus normal dispatch fuel and `ceil(copied_bytes/64)` byte fuel before copying. Poll retry/pending calls also consume host-call/fuel. |
| Executor turns | Ordinary and completion-wake invocations: 50ms cooperative native deadline, at most four consecutive ready turns or 8ms accumulated scheduler time before yielding, whichever first. Startup retains the existing signed/installed startup deadline. All values may be configured downward. |

These limits do not prove total process RSS or a hard real-time deadline. The
existing process ceiling of 16 sessions includes v4 sessions, reservations, closed
in-flight sessions and reclamation. Mailbox storage must stay counted until actual
destruction, following the existing session reclamation rule. Swift bridge tasks,
argument snapshots, codec construction, transport leases and completion copies
need independent bounded accounting; their bytes must not be presented as covered
by the VM's linear-memory limit. No unbounded auxiliary completion/cancel queues.

State transitions are serialized per session, without executing external code
under the VM instance/registry lock:

1. Enqueue creates `queued` and tags its current guest turn; only that turn's
   successful return makes it drainable. The next native drain hands out its bytes
   once and transitions it to `dispatched`. Native dispatch has no permission to invent a
   different token, operation, identity, or originating session.
2. First terminal transition wins: a validated native result, cancellation, or
   deadline installs one immutable terminal result. Repeated/late results cannot
   replace it. A cancelled/expired request queues a coalesced cancellation control
   record if dispatch started. Cancel-before-drain suppresses native I/O entirely.
3. `cancel` returns 0 when it installs cancellation, 7 if a terminal result already
   exists, and 4 for an invalid/consumed token. Cancellation neither closes the VM
   session nor cancels unrelated requests. A cancelled queued request can be polled
   once like any other completion; an unsubmitted reservation does not exist.
4. `poll` consumes only guest delivery. Reuse requires both consumption and native
   exit acknowledgement (or proof the request never dispatched). An adapter that
   ignores cancellation keeps its slot and native lease; it cannot free capacity
   by emitting an early terminal result. Never reuse a slot merely on timeout.
5. Session cancel/close/trap invalidates all request ownership, stops admission,
   cancels native work and drops undelivered results. Admitted effects may remain.
   Late native delivery is discarded by session+request generations. In-flight
   native leases and retained storage continue to count until exit/destruction.

The VM cancellation/deadline terminal transition linearizes before a competing
native completion if it acquires the request state first. A bridge must not claim
that a host actor's earlier result overrides a later-cancelled VM mailbox. Conversely,
once a terminal success is installed, a later cancel cannot rewrite it. Native
effects and durable commit are not transactionally coupled to this response race.

Use Rust `std::time::Instant` privately for the authoritative enqueue/deadline clock;
no clock callback or time value supplied by a guest/Swift caller is accepted. The
guest receives no clock/timer capability. Each `take`, `post`, `poll`, cancellation
and watchdog expiration checks this clock before a success transition. Drain
metadata supplies a bounded remaining duration, never an absolute Rust timestamp;
the Swift bridge may shorten it with its own monotonic deadline. Typed decoding
then applies the HTTP request's smaller timeout relative to enqueue, before I/O.
The bridge calls the native deadline-narrowing operation below before reserving a
host request; this makes the shorter deadline authoritative in the mailbox too.
Bridge admission checks cancellation/deadline immediately before starting I/O;
this is cooperative and cannot prevent a thread from being suspended between that
check and an OS call. The authoritative VM check still rejects a late successful
response. Native effects may commit after expiry. OS suspension may delay delivery
and cleanup; resume rechecks elapsed deadlines before allowing a stale success.

## 5. Native ABI and Swift/executor division

Use a new opt-in create symbol and a narrow mailbox API. The existing ABI-1 header
and symbols keep their behavior/layout; new mailbox structures have their own
`struct_size`, `abi_version=1` and zero reserved fields. Proposed logical signatures
below are contract requirements, not existing exported symbols:

```c
mixer_vm_capability_session_create_v1(module, length, vm_limits,
    capability_limits, out_session, report);
mixer_vm_capability_enable_v1(session, report);
mixer_vm_capability_take_v1(session, out_message, output, capacity,
    out_length, report);
mixer_vm_capability_post_v1(session, token, operation,
    completion, length, report);
mixer_vm_capability_ack_exit_v1(session, token, operation, report);
mixer_vm_capability_limit_deadline_v1(session, token, operation,
    timeout_milliseconds, out_remaining_milliseconds, report);
mixer_vm_capability_expire_v1(session, report);
```

`session`/`token` are uint64 bit patterns, lengths are native `size_t`, operation is
uint32 (`1 HTTP request`, `2 get`, `3 put`, `4 delete`). The new create selects only v4;
it does not accept a profile argument. Capability limits may only narrow section 4.
The VM captures its private monotonic clock at enqueue; no C call sets or rewinds
it. The detailed C structure offsets and
platform layout assertions are required during contract publication, before coding
consumers; this document does not declare an untested binary layout.

Create starts with effects disabled. `enable` is a one-way native activation
transition on that live session after successful startup; repeat enable succeeds,
and it cannot enable another generation or revive a closed session. Disabled
enqueue still returns an owned token/completion, with `failure/unavailable`, never
a drainable native call. Enabling later does not reinterpret those old requests.

`take` returns either no message, a call, or a coalesced cancellation control. It
copies full call arguments, never a guest offset/pointer. It reports the required
length without consuming when capacity is too small; an active guest invocation
leaves calls undrainable but cancellation controls can still drain. A successful take owns one
dispatch acknowledgement obligation. Cancellation controls take priority over new
calls and require no payload allocation. `post` copies a bounded immutable payload
and checks live session, dispatched lease, token generation, retained operation, duplicate/terminal
state and response deadline. `ack_exit` is separate: receiving a terminal outcome
does not establish adapter exit. Post-after-close/stale/duplicate rejects without
mutation; an exit acknowledgement may still release a private retained lease for a
closed instance without resurrecting guest delivery. `expire` performs bounded
deadline transitions only and does not execute guest code or native adapters.
`limit_deadline` takes uint32 timeout 1...30,000ms and applies
`min(recorded_deadline, original_enqueue_instant + timeout)`; it never resets the
deadline relative to its own call. It returns the floored nonnegative remaining
uint32 milliseconds. Zero expires before I/O. Repeated narrowing cannot extend
time. Native grant/decode delay consumes the same budget.

Each successful call take retains one native-operation lease. Close moves the VM
to its existing counted closing/reclaiming lifecycle and returns without waiting.
Only `ack_exit` may resolve that lease in a closed session, checking the retained
session generation, request generation and operation; all other mailbox operations
on the closed handle reject. The last native exit plus last in-flight VM operation
permits actual deallocation outside the registry lock. A hung adapter therefore
keeps bounded capacity occupied instead of permitting unbounded replacement sessions.
The Swift bridge must retain its private exit observer through `CapabilityHost.close()`;
that method's cancellation delivery or removal of slot ownership is not an exit ack.

The new C functions use existing outer `MixerVmReport` statuses 0...4. No-message,
buffer-too-small and duplicate-terminal are explicit mailbox result discriminants
in `out_message`/a new mailbox result, not new meanings for a successful invocation
report. All pointers are caller-owned buffers borrowed only for that call, checked
for null/length/range/alias according to the published C contract. No buffer address,
Swift closure, Java reference, native object, or function pointer is retained.
Panic containment and no-unwind requirements apply to every exported function.

Rust's C mailbox boundary validates structural metadata and bounds; it does not
duplicate the full JSON/schema implementation. The private Swift posting wrapper
must strictly validate and bind the typed payload before calling C, and the guest
strictly validates it again. Direct C callers are trusted installed engine code,
not a public untrusted extension dispatch surface. Rust can construct its fixed
cancellation/deadline/unavailable payloads without parsing guest values.

| Owner | Responsibility |
| --- | --- |
| Rust VM | Exact module import/signature validation; bounded request tokens/mailbox; guest memory snapshots/copies; byte/fuel/host-call accounting; terminal/generation checks; no arbitrary native dispatch. Keep existing registry critical sections short and destruction outside them. |
| Swift capability bridge | Private one-session mapping `(VM session generation, request token) -> CapabilityRequestID + expected CapabilityCall + activation generation`; strict codecs; compiled adapter registry; immutable policy binding; rate/deadline enforcement; draining, cancellation, result validation and native exit accounting. Never look up a host by a guest wire UUID. |
| `CapabilityHost` and native adapters | Existing schema/grant checks, typed dispatch, cancellation/deadline handling, HTTP transport safety, serial durable storage and adapter-capacity leases. Add a private exit-ack observation; its public completion closure currently cannot prove cleanup. |
| Native feature executor | Serialize guest turns and mailbox transfers; schedule bounded drains outside VM invocation. I/O/callbacks occur off the UI executor. Native callbacks post owned data and wake the executor; they never invoke guest exports directly or while a VM lock is held. |
| Guest library | Typed arguments/results, token-to-continuation ownership, bounded polling on a wake, cancellation propagation, duplicate/stale result rejection, and yielding back to the host between async turns. No native heap access. |

Give request state its own short mailbox lock. The only allowed nested order is
instance lock then mailbox lock; native post/expiry/ack never acquire the instance
lock. Registry leases are acquired/released without holding either during external
work. Invocation success publishes its queued requests as drainable under this
ordering; an invocation failure invalidates them. Existing session cancellation is
terminal for the whole session; request cancellation is scoped to one token, and
ordinary invocation return resets only the existing invocation fuel/host-call budget.
Do not interpret guest `cancel(token)` as `VMSession.cancel()`.

Use one fixed installed wake export `mixer_guest_capability_ready_v1 ()->()` with
an exact validated signature. It is invoked by the feature executor only after the
previous invocation returned and a completion became available. One wake is
coalesced while work remains; no arbitrary export name or table index comes from a
native completion. A guest may poll from an ordinary turn too. Each wake has the
existing per-invocation fuel/host-call bound and a native monotonic turn deadline;
repeated immediate turns have a native scheduling budget and yield to other feature
work. A busy VM returns the existing busy result; the queued wake remains pending.
An invocation trap still permanently terminates the session.

The wake export does not preserve a guest call stack or implement Swift concurrency.
A small independently authored Wasm guest can implement this protocol without a
Swift runtime. Swift async functions require separately qualified compiler lowering,
continuation/executor ownership, actor isolation, allocator/runtime imports and
cancelled-task cleanup. Passing the small guest tests cannot claim those gates.

## 6. Verified grant and implementation identity binding

Construct a private `BoundCapabilityExecution` from one immutable installed
descriptor and one `VerifiedArtifact` issued by the pinned verifier. Do not expose
an activation initializer that accepts an arbitrary already-built `CapabilityHost`,
policy, transport, directory, or manifest-like dictionary.

Before creating a v4 session:

1. Require exact app/environment/platform/runtime fingerprint, selected profile,
   guest ABI, payload hash/bytes, schema hashes, and signed resource constraints.
   A manifest cannot select the implementation or raise a ceiling.
   Derive required capability families from the fully validated module's exact
   imports and require corresponding installed/manifest schema hashes and compiled
   factories before staging/selection. Regex or a partial inventory is insufficient.
2. Parse the compiled installed grant/configuration bytes using the same closed
   canonical rules whose exact bytes/digest are recorded in the identity. Compare
   the actual bytes to `grants_sha256` and `configuration_sha256`. Reject absent or
   mismatching sources. A DTO supplied separately from hashed bytes is insufficient.
3. Construct adapters from a closed compiled factory keyed by the exact capability
   ID/native source artifact identity. Verify the factory's built-in identity,
   configuration hash and capability schema hash against the descriptor. Installed
   HTTP/storage origins, methods, namespaces, quotas, root-directory selection and
   networking configuration come from this factory. A native directory path is
   resolved from compiled app-private location policy, never downloaded JSON.
4. Take grants only from the opaque verified artifact's signed grant value. Require
   the versioned grant schema and map binding, then intersect permissions, exact
   origins, methods and namespaces with installed policy. Missing grants grant
   nothing. A narrower release never enables a broader installed right. Nonempty
   hashes alone grant no authority. Check policy again for each operation before I/O.
5. Bind the resulting bridge, `CapabilityHost`, VM session and activation generation
   privately for their entire lifetime. The guest can supply argument data but cannot
   replace this association. Cross-artifact/configuration/host substitution fails.

The existing generated `CapabilityNativeIdentity` must be regenerated after source
edits; it is only one input. The new runtime identity must cover the complete bridge,
mailbox/wake contract, request/rate/deadline/turn budgets, actual adapter dependencies,
permissions/entitlements, installed grant bytes and configuration, compiler/SDK,
native fallback and other build inputs. Do not claim an implementation hash attests
the final binary without the separate build/provenance work.

Activation needs a fresh generation per candidate/retained-healthy/native-fallback
attempt. Closing one attempt cancels/drains its bridge and invalidates its wakes;
the next attempt cannot inherit tokens, callbacks or grant state. **Do not start
capability I/O for a provisional startup attempt.** Startup enqueue returns the
typed `unavailable` terminal completion until startup succeeds and the coordinator explicitly
opens effects for that instance. This conservative first version avoids a failing
candidate mutating network/storage before fallback; startup requiring an effect is
unsupported and must fail visibly. The native fallback remains the real compiled
implementation. Later health milestones may observe enabled effects but neither
startup success nor an effect completion alone establishes update health.

Session replacement and cancellation cannot roll back committed storage or an HTTP
mutation; applications need their own idempotency/read-after-uncertain-result policy.
No transaction, automatic replay, automatic retry, or persistent guest token is
implied. State restoration uses versioned value data, never these tokens.

## 7. Versioning and required dependent edits

Publish distinct `vm/profiles/capability-v4.json`, guest-capability-ABI-1 and native
mailbox-ABI-1 contracts. Preserve existing files as frozen contracts. Keep the
capability v1 IDs, schemas, value limits, failure vocabulary and exact hashes; the
new payload wrapper has its own hash. Profile 4/guest ABI 2 is a store-binary change.

Current identity-v1/release-v1/v2 explicitly fix guest ABI 1. The proposed migration
is **runtime-identity-v2 and signed release protocol 3**, with new identity/signature
domains and explicit `guest_abi=2`/v4 acceptance. Release-v3 may reuse the v2 signed
grant descriptor unchanged, but must publish its full closed shape and exact version
rules. Do not loosen old verifier constants, infer protocol 3 from capabilities,
negotiate automatically, or relabel ABI 2 as ABI 1. Service/CLI compatibility and
canonical/signature parity must land before this path can be distributed.

The evidence is concrete: `RuntimeIdentity.init` restricts `engine.guest_abi` to
`1...1` and allowlists only profiles 1–3; `ReleaseVerifier.init` requires
`host.guestABI == 1`, while `manifestObject` requires manifest `guest_abi == 1`
independently of host metadata. Go `Manifest.Validate` requires `GuestABI == 1`;
v2 validation goes through that unchanged value contract, and its regression tests
explicitly reject ABI 2. A future coordinated protocol could explicitly support a
new ABI; a profile name alone cannot do so. Cryptography does not inherently require
a version bump for every new import. It follows here from the proposal's distinct
guest ABI 2 plus the requirement to preserve the published old acceptance sets.
Changing old v2 validators to accept ABI 2 would be an intentional contract widening,
which this proposal excludes. **Root has not approved any identity/release schema
version change; these are proposed dependency edits, not authorization to make them.**

Required sequence, with public contracts coordinated before dependent edits:

| Slice | Required edits and executable proof before activation admission |
| --- | --- |
| Frozen-contract regression | Pin existing profile/schema/header digests; tests prove old validators, CLI modes and session-create reject all new imports/profile IDs, and existing symbols/layouts/results remain unchanged. |
| VM mailbox/profile | `vm/src/{lib,decode,validate,execute,session,ffi}.rs`, profile JSON, both copied VM headers and C shim declarations. Test exact import names/types, required memory/wake export, bounds/overflow/overlap/zero capacity, snapshots across memory growth, fuel failure before mutation, quota accounting, generation exhaustion, terminal races, poison/unwind, busy/close/reclamation, and absence of callback execution under locks. Exercise debug/release Rust and compiled C consumers. |
| Payload/native host adapter | Owned schema-derived payload codecs and guest adapter in `sdk/Sources/MixerCapabilities`, generator/source identity updates, private host exit observation and bounded bridge tasks. Swift/Java/Rust fixture parity as applicable; invalid JSON/models/hash/operation/result, malformed base64/numeric tokens/escapes, permissions/adapter failures, cancel-before-reserve and stale completion tests. Check generator determinism. |
| Swift runtime scheduler | Add opt-in wrapper without widening `VMSession` ABI1 construction. Test non-reentrant fixed wakes, coalescing, completion during invocation, delayed watchdog, fair bounded turns, cancellation while native drain/post is busy, suspension/resume simulation, no UI-executor blocking, and native exit lease accounting. Hand-authored guest performs real HTTP loopback/TLS-failure and temporary private-store get/put/delete through actual imports; injected native callbacks alone are insufficient. |
| Identity/release | New closed identity/release contracts, Swift/Go verifier and service protocol support, public CLI tooling and canonical fixtures. Test new domains/guest ABI/profile/hash/grant binding, unsigned/raw grants, foreign scope/artifact/configuration/adapter, missing grants, narrowed sets, replay/downgrade, old/new protocol rejection, and service/client parity. Run real service transport tests, not just object-to-object conversion. |
| Activation composition | New explicit factory using immutable verified selection and bound adapter configuration. Keep every old empty-capability path intact. Test grant-carrying artifacts execute only after full binding; mismatches reject before I/O; provisional effects fail unavailable; opening effects is generation-bound; failure/close/fallback cancels and suppresses old wakes; health remains milestone/time based. Never replace the current guards with a simple `profile == v4` exception. |
| Qualification after implementation | Record tools, commands, source/tree digests, outputs and scope; independent bridge/VM/security review; immutable package consumer; compiler/Swift executor evidence; OS/device lifecycle, TLS trust, store and operational evidence. Physical-device work remains pending while phones are disconnected. These are not satisfied by this design or Mac tests. |

Activation may admit nonempty capability hashes/grants **only** after all preceding
implementation/contract tests pass as one coherent opt-in composition and an
accountable review approves its boundary. Production/GA admission still requires
the specified independent and device evidence. Root coordinates metadata and any
push; this design lane changes only this document.

## 8. Tradeoffs requiring explicit review

- Copying JSON preserves the existing strict value contract and avoids native heap
  sharing, at the cost of base64 expansion, extra bounded copies and codec work.
  A later binary payload codec needs a new transport version and measurements.
- Eight slots, 8MiB reservations, 32 starts/second and the 50ms/four-turn/8ms budgets need
  measured consumer feedback. They may be narrowed immediately; raising frozen
  ceilings requires another explicit profile/contract and installed binary identity.
  Review/measure these proposed defaults before freezing the contract; scheduling
  fairness and real frame behavior are not inferred from VM fuel.
- Rust `Instant` and Swift monotonic duration handoff require platform tests for
  suspension, rounding, delayed watchdogs and cancellation/lock ordering. A timer
  that only cancels late, without success-path deadline checks, is insufficient.
- Host completion and adapter exit are different events. `CapabilityHost` currently
  exposes only terminal delivery; review the exit-ack addition and close retention
  before assigning final native mailbox structure layouts. Never equate cancellation
  of a Swift task with OS request/store-operation exit.
- Disallowing I/O during provisional startup is deliberately restrictive. A future
  effectful startup needs a documented reconciliation/idempotency contract before
  relaxing this rule; simply allowing effects during fallback attempts is unsafe.
- A new release protocol/identity version has service/CLI cost, but preserves the
  fixed guest-ABI promises of shipped v1/v2 formats. Root must accept this version
  decision before protocol work; changing it requires an explicit revised proposal.
- The fixed wake export provides a transport event loop, not full Swift concurrency.
  Swift actor/task lifetime and FieldLog's actual import/resource inventory remain
  separate blockers even if an independently authored tiny guest works.

## 9. Inspection evidence for this design

Inspected repository revision `48217b5ebdb1ed15cdc010a67c009f534b5e37dc`
on branch `main`. Existing unrelated working-tree modifications were present and
were not edited. Tools observed: `git version 2.56.0`, `Python 3.14.8` and macOS
`shasum -a 256`. Commands were read-only `rg`, `cat`, `sed`, `git status`,
`git rev-parse`, and `shasum`; no VM/device or release qualification was run.

Selected SHA-256 inspection anchors (file bytes, not capability semantic hashes):

```text
2b7519e0daea5a1dd25f8d2f93d2dc25c32caa376b8cf21a15e69505c621d77e  capabilities/schema/v1.json
6921f707b943ab76cdc3dae996ac7448d3c720676f290e259c892afcab1bf41a  contracts/vm-session-v1.json
454daf6fdc16955b32a725fd5fa230a4f7cc0c1f3327223bf73d8e6331fcf30c  contracts/runtime-identity-v1.json
ab4f5d881b1fd0cb91d01bd1da25a0b864690d29936063e0144304bfd275ba4b  contracts/release-v2.json
5884becbfc1a8b71137cbfcea18abd64cb46e123ba140dea0a9ed399fdb9f5d7  activation/Sources/MixerActivation/InstalledExecution.swift
75fccc10f123b3761c5814018045df3efc7a74889f1f581b81f410b49fc33af3  vm/src/session.rs
e603568d64b73513c27d72a6bfef7d82fadad3e1dc5344bd52a1ac93899805a6  sdk/Sources/MixerCapabilities/Host.swift
```

These anchors establish what informed the proposal; they are not executable
capability evidence. No gate is marked verified by this document.
