# Experimental Swift capability bridge and executor

Status: bounded design for root review, 2026-10-23. No implementation or consumer
qualification is supplied here. The experimental native C boundary was independently
reviewed and committed at `b25e3b7de2391a80d12e7fd75e60903495bec120`.
Use only archives/header built from that pin and matching the
[final native receipt](../vm/verification/capability-native/2026-10-23-final/receipt.json),
[independent review](../verification/capability-native-review/receipt.json), and
[root integration audit](../verification/capability-native-integration-2026-10-23.json).
Those qualify the native boundary, not this pending Swift composition. This document does not widen
identity, release, activation, old profiles, guest ABI 1 or any shipping API.
The final native 90-input manifest SHA-256 is
`76372fd254e646141e991b3289b14c8380f13ea68602b21d4aa746080fddc8cf`;
its receipt is `e3d31407e3542484aadadd2b3b9134763ddaee8a29b9b307475711c02a6b4b9f`,
and independent review receipt is
`e308e3cc4aeb5a579c62f671506ba8b9eddc3487e3d552189132d18760dc64af`.

## Separate package and one archive

Add a separate `experimental-capability-runtime/Package.swift`, with product
`MixerExperimentalCapabilityRuntime`, Swift target of that name, and a private
`CMixerVMCapability` target. Depend only on the `MixerCapabilities` SDK product;
do not depend on `MixerRuntime`. Reproduce the small private C report/value adapter
with exact checked representations; sharing pure Swift helpers can be a later
review. Do not change `runtime/Package.swift`, `Session.swift`, copied legacy
headers, or `runtime/build-vm.py`.

An explicit new experimental builder must export a frozen revision, build only
with `experimental-capability-native`, and stage one static archive under the
distinct name `libmixer_vm_capability_experimental.a`. Its C target links that
name. Bundle the matching experimental header and unchanged included legacy
header, and record feature selection, tools, source/archive/header hashes, platform
and link command. Never point Swift library search at Cargo's directory containing
both static and dynamic libraries. No automatic feature/environment fallback.

The experimental archive contains both C function families and one shared native
registry. Never co-link it with a default Rust archive or link this package with
the normal `MixerRuntime` product in this experiment. Mixed old/new C tests call
both families from this **one** archive. Future full-app integration must explicitly
select one archive and prove the shared sixteen-session registry; combining two
archives is not an integration strategy. Default build/symbol/profile regression
evidence remains required independently.

Expose a small explicitly experimental session/executor with asynchronous startup,
ordinary export invocation, an explicit development-only effects-open transition,
and idempotent stop/close. Keep raw handles, tokens, host objects, post/ack methods,
mutable policy and arbitrary wake names private. The package is for trusted native
experiments with installed-selected module/startup/policy/adapters. A raw grant DTO
or effects-open call is not verified activation authority. No profile-4 selection
is added to `VMSession`, `VMProfile`, validation inventory or existing activation.

Construction starts with a **synchronous** `prepare` admission permit before
retaining/scheduling a closure or Task holding module Data. At most sixteen Swift
pending constructions, live owners and closed/draining owners share that budget.
A one-shot asynchronous construction value then runs heavy C validation/create
off the UI executor. Busy rejects before scheduling, and failed creation holds
its permit until cleanup finishes. A native registry reservation acquired only
inside C create cannot bound an earlier Swift queue of 4 MiB module captures.
Keep scheduler registration under the same aggregate owner bound. Test concurrent
prepare/create/cancel/failure and permit handoff, not just native pool exhaustion.
Input byte limits and retained-payload diagnostics measure logical byte counts.
A caller's Data slice or String may retain a larger backing allocation; policies,
adapters, DTOs, allocator overhead and framework/native buffers are separate.
The sixteen permits bound retained attempts, not aggregate process RSS. Raw C
take and host callback payloads use explicit owned copies; codec transient copies
and actual allocator/RSS high-water observations require separate measurement.

## One session, eight mappings and retained exit ownership

Construct one private `CapabilityHost(maximumRequests: 8, timeoutMilliseconds: T,
installedAdapters: ...)` per native session, or a narrower common capacity. Pass
the same narrowed installed timeout `T` and request ceiling to C. Never accept a
guest-supplied host UUID or look up a host by wire identity. The immutable attempt
generation, C handle/generation, expected operation and host belong together.

Use exactly eight mapping positions indexed by the checked guest slot portion,
with the full 64-bit token and operation retained. Equal bits in another session
do not identify this request. Each entry retains:

- The originating native session/attempt owner and exact `(handle, token, op)`.
- A typed operation, then an issued host ID and expected `CapabilityCall`, if any.
- Admission phase, a pending cancel bit, and whether host submission returned as
  accepted or threw. An issued host reservation is recorded before another await.
- Independent result-handled, actual-exit-observed, and C-acknowledged facts.
- At most one retained completion phase (callback payload or staged wire result),
  an absolute Swift deadline, and at most one admission/control worker.

Install the entry **before** any host await or observer can fire. Both callbacks
may arrive before `submitObserved` returns; neither callback changes ownership
based on the worker's unfinished return. A matching `didExit` is authoritative only
for an accepted observed call. No observer is accepted when that method throws.
No task cancellation, callback drop, terminal result or host slot removal proves
native exit.

An independent strong `NativeExitOwner` retains the immutable native handle and
bounded event mailbox after the public session/executor closes or deinitializes.
Do not copy the legacy wrapper's zeroing of its only handle into this exit path.
The owner/pump remains available for `ack_exit` through the retained closing
generation. Host callbacks strongly retain the needed exit owner, not a weak
reference that can lose the last acknowledgement. Break entry/observer cycles
after acknowledged exit; a hung adapter intentionally retains bounded native
capacity. Do not promise a finite wall-clock cleanup time or fabricate an ack.

A slot becomes a small finalized generation tombstone only after result handling
or suppression, host-reservation cleanup, and successful C exit acknowledgement.
Discard its DTOs, buffers and worker then. A later successful C take with a higher
generation may replace it. A stale callback cannot affect the replacement.
Guest consumption is C's responsibility; Swift never infers consumption or permits
reuse from a terminal delivery alone.

## Strict admission and absolute deadlines

Every C call uses live owned disjoint storage for its full duration, checks outer
status/report consistency and ABI/reserved fields, then validates the output kind
and all used/unused metadata. A zero-initialized kind is not success after a failed
outer status. Call tokens must have nonzero generation and slot 1...8, operation
1...4, length 0...524288, and remaining duration 0...30000. An empty Call payload
is valid C structural metadata; strict empty-JSON rejection follows the local
invalidArguments/no-I/O path below. None/cancel/tooSmall
must satisfy their exact zero-field rules. A full 524288-byte reusable take buffer
avoids a resizing protocol; a larger required size is a boundary fault, not an
allocation request. No guest memory pointer escapes C.

For each successful Call take:

1. Atomically register its entry against the local open attempt latch. A take
   that returns after the latch closed gets no host reservation or adapter call:
   record explicit no-I/O exit and acknowledge its retained closing C ticket.
2. Strictly decode copied bytes with
   `GuestCapabilityTransportCodecV1.decodeArguments(_:operation:)`, using only
   the C operation tag. This enforces the unchanged schema/JSON rules, including
   duplicate keys, numeric syntax/ranges, closed objects, depth, URL/header and
   canonical base64 semantics. There is no permissive JSONSerialization path.
3. **Before reserving a host ID**, apply HTTP's decoded timeout through
   `mixer_vm_capability_limit_deadline_v1` relative to the original Rust enqueue.
   For storage use the common installed timeout `T`; a nonextending 30000 ms query
   is also valid once an earlier limit exists. Never supply a guessed elapsed
   duration as a new timeout. Repeated limits only narrow the existing deadline.
4. Sample `S = ContinuousClock.now` **before** the C call that returns remaining
   milliseconds. Accept its checked floored integer `R`; do not round upward or
   replace zero with one. If the call reports an existing terminal or `R == 0`,
   no I/O is admitted. C owns the existing terminal; wake it and record local
   no-I/O exit. Otherwise form `D = S + milliseconds(R)` with checked conversion.
   Sampling after C would renew time spent inside C and is forbidden. Retain the
   minimum of all previously derived deadlines; an older sample never extends it.
5. Check the attempt latch, deadline and monotonic rate bucket before reservation.
   Burst is at most 8, refill at most 32 starts/second, configurable down. Rate
   rejection produces fixed `quotaExceeded`, with no automatic wait or retry.
   Charge an admission attempt conservatively; do not refund it by guessing I/O.
6. Make **one** `await host.issueRequestID()` attempt. On success retain the ID,
   build the expected call and strict legacy envelope, and recheck latch/time.
   A second nonextending C remaining query may tighten `D` after this await;
   it uses another before-call Swift sample and still cannot extend the first D.
7. Submit through `submitObserved(_:noLaterThan:deliver:didExit:)`, carrying D
   unchanged across the actor hop. Its accepted deadline is the minimum of D,
   HTTP timeout and host default. Decode, bridge queue and host actor queue time
   are never reset. Host pre-invoke and completion checks remain authoritative
   for its delivery, while Rust independently selects the guest terminal.

Rust timestamps are never imported or compared to Swift absolute instants. The
before-query duration conversion is conservative for call/admission delay; the
two platform clock domains still need host/target elapsed and suspend/resume
qualification. On resume, process expiry before new admission/post and discard
expired successes. No wall-clock Date value is accepted as request authority.
The native HTTP adapter has its own relative timer, but cannot extend the carried
host cutoff or authoritative Rust deadline. A thread suspended after its last
pre-invoke check can still begin or commit an effect; response deadlines are not
durable-effect rollback or hard real-time I/O prevention.

### Host reservation failure and cleanup

`didExit` currently runs before the host asynchronously releases its actor slot.
C can therefore reuse a token while the host still has eight occupied slots.
Never infer host availability from C occupancy or spin until a slot opens. The
single failed host reservation attempt completes this live request with
`failure/unavailable`, then follows local no-I/O post-before-ack. Do not parse an
error string to grant additional admission or retry. This conservative policy may
reject a transiently busy host; later independent requests can succeed normally.

If an ID was issued but submission was not accepted, release that reservation
using the existing public
`host.submit(CapabilityCodec.encodeCancel(expectedCall), deliver: ...)`. A reserved,
unused ID is cancelled without creating work or an observer. This same cleanup
is required after encoding failure, elapsed deadline, close, or a throwing
`submitObserved`. Retain the reservation record until cleanup returns. If cleanup
cannot establish release, close this private host/attempt and await its idempotent
close transition; do not leave the reservation in an orphaned retry task.

Valid typed arguments can still fail strict legacy envelope encoding after ID
reservation (for example, the complete wrapper exceeds its byte bound). Dispose
of the reservation and stop the **whole attempt** fail closed, then acknowledge
the taken C ticket's explicit no-I/O exit. This is not a guest invalidArguments
result: arguments already passed their transport schema. Never orphan the issued
ID or keep retrying a different envelope.

A throwing observed submit accepts neither work nor an observer, so this call's
native exit can be proven locally after reservation cleanup. An accepted submit,
even when it immediately reports permissionDenied/unavailable, requires its real
`didExit`. A cancellation callback or thrown **wait** on an already accepted
operation cannot be relabelled a no-I/O rejection.
Cancellation of an **accepted** call can throw stale after its real exit and the
host's asynchronous slot release. Classify that race using the recorded accepted,
exit and closed facts, without parsing error strings. It does not undo acceptance
or establish a no-I/O path. If exit is still unresolved, retain its observer and
close the private attempt on an unexplained cancellation failure; only didExit
authorizes the native acknowledgement.

## Results, exit, malformed data and close

Callbacks do not call C, run codecs, invoke guest exports or create Tasks. They
validate a payload's byte count, take an immutable bounded snapshot, and set one
entry event/result field under a short lock, then coalesce one pump signal. An
oversized or duplicate payload sets a fixed fault flag instead of growing a queue.
An exit callback sets its exact entry's exit bit even after close. User/native
callback code never runs under the mapping/event lock.

On the serialized pump, decode a host completion using
`CapabilityCodec.decodeCompletion(_:expected: expectedCall)`. Convert typed
success/failure to `GuestCapabilityCompletionV1` and encode it with the frozen C
operation's `GuestCapabilityTransportCodecV1.encodeCompletion`. This removes the
host UUID/slot/generation from the guest wrapper. Never copy a host envelope into
the guest or trust payload-selected capability/operation/schema metadata.

| Event or state | Terminal handling | Exit handling |
| --- | --- | --- |
| Malformed guest argument object | Post strict `rejected/invalidArguments`, no host ID | Explicit local no-I/O exit, ack after post decision |
| Rate rejection / host reserve unavailable | Post fixed quotaExceeded / unavailable | Same local no-I/O path |
| Valid host result | Strictly bind/convert, then C post; kind1 means an existing terminal won | Keep exit obligation until didExit |
| Malformed, foreign or oversized host result | Fixed invalidResponse or fail closed on an invariant fault; never exception text | Still require didExit for accepted work |
| Exit before a result is processed | Record exit, preserve pending result handling | Do not early-ack and thereby block a later post; expiry/terminal confirmation can complete the decision |
| Guest cancel or expiry | C's first terminal wins; deliver one mapped host cancellation | Cancellation itself is not exit |
| Close/trap/whole-session cancel | Suppress queued/late delivery and all later wakes | Retain every accepted observer and acknowledge actual cleanup |

When result and exit bits arrive together, process the result/post decision first,
then acknowledge exit. C `ack_exit` can otherwise make a pending request reject a
later post. If exit arrives without a result while live, retain its fact and use
the one deadline timer/query to establish terminal expiry before ack. Do not wait
forever for an absent payload after the bounded response deadline. Only actual
accepted-host exit or explicit never-submitted work authorizes an acknowledgement.

C remains the terminal arbiter. A host success may lose to an earlier C cancel or
deadline; status0/kind1 is suppression, not a new success. A known terminal whose
delivery was consumed may reject a late post as stale; drop its payload and retain
the independent exit fact. Drain known cancellation controls first to establish
that context. Unexpected statuses/metadata, stale identity without an explained
terminal/close, or operation mismatches stop admission instead of rerouting data.
Do not treat every status3 as success. On `capability_allocation` post refusal,
choose bounded fail-closed session stop rather than an unbounded payload retry
loop. Retain actual-exit obligations through stop. Poison/quarantine/failed ack
retains counted ownership and diagnostics; there is no fabricated reclamation.
Cleanup close/cancel status0 on a quarantined but unpoisoned owner proves only
that stop transition: it does not clear sticky quarantine or release its capacity.
Checked native command metadata/value faults latch closed and conservatively
retain capacity even if cleanup later reports0. A malformed create report,
status4, a successful create without a valid handle, an unexpected error handle,
or failed cleanup similarly quarantines its Swift construction permit for the
process lifetime without retaining the module. Valid ordinary failed creates
with initialized zero handles release their permits. There is no recovery API.

Close first latches the private attempt closed synchronously, before scheduling
host cancellations or native close. All admission registrations and wake posts
check that generation under the same short lock; recheck after every host await.
Late takes cannot register. A pre-close registered admission is already owned and
may race cancellation/I/O; the design makes no stronger side-effect claim.
Close schedules at most one off-UI C close job and one private host-close task,
without waiting behind an executing guest turn or holding Swift locks across C.
Repeated close/cancel coalesces. An admitted take racing close is acknowledged
even if no host call ever existed. No draining from a closed C handle is needed;
the mapping supplies all already-dispatched native cancellations.

## Serialized scheduler and bounded data

Use a private off-UI serial Dispatch executor/pump for all guest turns, copies,
take/post/expiry/ack work. Close has the separate short control path above, relying
on the reviewed C contract that close need not wait for the instance mutex. No
`MainActor` execution, reentrant guest invoke, guest call inside a callback, or
lock held across await. An ordinary invocation has one fixed pending command
position; reject additional submissions as busy rather than accumulating an
unbounded actor/continuation queue. Keep argument count/name byte limits unchanged.

One coalesced pump and one monotonic 10 ms timer per session are sufficient for
the first experiment. Arm the timer only while mapped work, known ready work or
a deadline decision remains. A completely idle session, after take None and
authoritative wake didInvoke0, parks until an external command/event. Late timer
firings coalesce; never enqueue one work item per missed tick. Suspension/resume
rechecks expiry before dispatch. Timer-only work is at most 100 scheduled batches
per second per active session; this is a scheduling bound to measure, not a
claimed idle-energy or worst-case CPU result.

Per batch, scan the fixed entries and expiry once, drain cancellation controls
before calls, and process at most sixteen take records (eight calls plus eight
coalesced controls). Limit guest work to four consecutive ready turns **or** 8 ms
accumulated monotonic scheduler time, whichever is reached first; include ordinary
and wake turns in the budget. Check elapsed time before each further transfer,
codec conversion or turn and after it returns. Retain a fixed round-robin cursor
when the budget expires, so a full entry cannot starve later exit/control records.
After a successful turn, drain only newly published work within the same
bounded batch. `session_wake` with didInvoke0 is the authoritative stop condition;
didInvoke1 may leave unconsumed ready work, so retain one hint for the next timer
quantum. Busy preserves the hint; a VM trap stops the attempt. Never spin on a
ready hint or retry a busy turn immediately without yielding.

The 8 ms batch budget is not preemption: a single guest turn can last up to the
configured cooperative 50 ms bound, with instruction/import boundary checks and
the unchanged fuel limit. Record overruns and scheduling latency. Round-robin
eligible sessions on a shared non-UI scheduler before granting another batch;
the common C sixteen-session pool bounds owners. No repeated immediate wake may
monopolize the executor. Short C/codec work also consumes the batch's elapsed
budget; a finite large conversion may overrun it and needs measurement.

The bridge adds no unbounded stream or completion task fanout. Each entry has at
most one admission/control worker; a cancel while admission awaits sets a bit
that the same worker handles. At most eight such workers and one host-close task
exist per session. The host already bounds its work/watchdog tasks by eight slots;
its asynchronous release tasks are included in lifetime measurements. Callbacks
only signal the fixed mailbox. Yielding retains one scheduled pump, not a chain
of suspended Tasks capturing payloads.

Account each ownership tier separately: C/Rust keeps its 8 MiB reservation;
bridge take scratch is one 524288-byte buffer; each of eight entries may hold one
argument/encoded call and one completion, each capped at 524288 bytes. Adopt or
replace buffers by phase, rather than retaining an extra copy at each transition.
Treat an incoming callback Data and outgoing guest Data as those completion
phases, releasing the old one before retaining another in the slot; transient
conversion overlap is separately measured. Typed DTOs, JSON snapshots, worker
captures, allocator overhead, linear memory and opaque URLSession buffers are
additional costs, not covered by the Rust reservation. Measure live/peak copies,
metadata and callbacks explicitly; no total-process RSS, recoverable OOM or
no-abort guarantee is introduced.

## Missing primitives and implementation gates

| Dependency | Present or proposed boundary |
| --- | --- |
| Native C session/ticket/registry | Independently reviewed native pin `b25e3b7de2391a80d12e7fd75e60903495bec120`; each bridge test must bind its actual archive/header to the final receipt. Swift composition remains unqualified. |
| Typed payload transport | Current public generated codec supports strict args and wrappers. Expected-call legacy completion decode plus explicit typed conversion needs bridge code/tests, not a new permissive codec. |
| Carried host cutoff | `submitObserved(_:noLaterThan:deliver:didExit:)` is implemented in SDK prerequisite commit `ce002a812a66308fc7e501af9be19e4bd8dc385c`. Host capacity release still follows didExit asynchronously. |
| Host reservation disposal | Existing encodeCancel + submit releases an unused ID. No new disposal API is required for the bounded one-attempt policy. A typed admission/release-complete signal would be a separately reviewed optimization. |
| Ready/next-deadline notification | C has no query/callback for these. Fixed timer, bounded expiry and authoritative wake are sufficient experimentally; notifications may be a later measured optimization. |
| Strong exit owner, fixed event slots, executor and rate bucket | Missing bridge implementation. Their ownership/fairness/memory invariants require original tests and TSan. |
| Installed verified factory / release binding | Missing full identity-v2/release-v3/activation integration. Current policy and native hash do not establish it. Remains out of this slice. |
| Successful normal-trust loopback HTTPS fixture | Not currently supplied. Do not modify trust/keychains/credentials or add a production bypass. Actual TLS rejection can be tested now; HTTP success needs an explicitly provisioned trusted test fixture. |

## Original executable test strategy

Author tiny hand-encoded real Wasm modules with exact imports and fixed wake,
without competitor helpers. Use the new experimental archive and public bridge
entry points. The storage primary success flow is: startup attempts a put while
disabled and polls unavailable; explicit development enable; put a known byte
value; return; wake/poll success; get and verify exact bytes; delete; get and verify
missing versus empty. Inspect the actual temporary private store, host capacity,
native handle reuse/count and exact terminal bytes. A second instance with equal
raw token bits must remain isolated. Trap/loop/fuel failure in the enqueuing turn
must leave the concrete store unchanged. No injected completion counts as this
end-to-end happy path.

For real network negative evidence, start a bounded loopback HTTPS server with a
fresh untrusted matching-address certificate. The guest calls its exact granted
origin using the concrete default URLSession adapter. Verify actual TLS handshake
attempt, rejection through the guest wrapper, one terminal and exit, no leaked
capacity and no application request accepted under untrusted TLS. No trust-store,
keychain, credential or production verification change. Successful real HTTPS is
pending a controlled trusted fixture. Internal URLProtocol interception can cover
success/redirect/header/body/error lifecycle matrices but is labelled framework
interception, never a successful real-network receipt.

Add deterministic gates around original test adapters/worker boundaries without
weakening production checks: before/after take, before host reserve, after ID
reservation, before/inside host acceptance, delayed watchdog/completion, after
native cleanup but before host slot release, and after close before late ack.
Test malformed JSON and exact limits; sample-before-C against an intentionally
delayed remaining query; HTTP timeout narrower than enqueue default; deadline
elapsed during decoding/actor queue; zero remainder; old/new generations; result
and exit in either order; first terminal immutable; cancellation during reserve;
throwing observed submission with reservation cleanup; one-attempt host capacity
failure; no-I/O late take; close/deinit with only exit ownership left; duplicate
callbacks/acks; post allocation failure; stuck exit and poison retaining capacity.

Test wake arriving during invocation, no polling twice, unconsumed wake fairness,
four-turn/8 ms yield including a single slower bounded turn, fixed command/event
queue rejection, no growing Task count under completion bursts, and timer parking.
Record monotonic batch/turn/callback latency, active/idle timer counts, idle CPU and
peak retained bytes for one and sixteen sessions, including a guest that never
consumes ready data. Do not turn finite measurements into real-time/RSS claims.

Run host debug/release integration and race repetition, native Thread Sanitizer,
legacy runtime/default symbol/ABI tests, and separate official iOS/Android compile
and archive link checks. WASI may compile the value codec; the native bridge is
not a WASI target. No phone, reconnect, physical-device receipt, signed app,
store delivery, OTA admission, publication, immutable FieldLog package or GA gate
is implied. Preserve initial failed experiments and exact sources/tools/commands,
logs and archive/header hashes. Review the combined Swift/C/host composition
independently; prior Rust or host-only reviews do not qualify it.

## Inspection identity

Design-only inspection used Git HEAD `bec5731e8f684e759bebb604721443dcad45e9dc`
plus the current uncommitted C candidate. No builds/tests/device commands were run
for this design. A hash recheck observed the header change during drafting from
`631b0c62008ecda2fdbe332f71de7ba860e1c29b5c91ee64741a4f6ecd76d4c0`
to the candidate below; it was reread, including the quarantine cleanup exception.
Root also corrected the draft's earlier nonempty-payload assumption: a structurally
valid zero-length Call must reach strict JSON rejection, not a boundary fault.
The important inspected SHA-256 values are:

| Input | SHA-256 |
| --- | --- |
| `docs/guest-capability-abi-proposal.md` | `56f09eb49e206515c426e4bb0b7d579e0bcc0dd8862f4f2f5e9665f6fef47555` |
| `docs/capability-native-abi-proposal.md` | `7773c3fde09fafa4ec7d3cfe39d1886b3af25ef5a8a84f965ad253c76ee9a801` |
| candidate `vm/include/mixer_vm_capability.h` | `9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6` |
| `runtime/Package.swift` | `f45bdb15337bd7c408a598d895a9ee8a478bb328063f65461db0a7e94cbbcb59` |
| `runtime/Sources/MixerRuntime/Session.swift` | `e3e86165703423c885612b50c45ab28b5346c320c9f08679f52b7794214769e6` |
| `runtime/build-vm.py` | `33f5e0e8218296913e88673130fcfa83616e8a9f245511ca6252ac34cbd252ea` |
| `sdk/Sources/MixerCapabilities/GeneratedGuestTransport.swift` | `c8dfdcf51ba216129ee9d305b13c17c55d31a48abc63d728484c67cadfab0ed7` |
| `sdk/Sources/MixerCapabilities/Host.swift` | `e49591ca89c1ce7b14178a062cfe22dd016066d4e9e51383e498734f665aa4bb` |
| `sdk/Sources/MixerCapabilities/InstalledCapabilityAdapters.swift` | `f5926ddd09bd705ec487068a1ea966feac89977924bb2dd975dd2927ed55fa9d` |
| `capabilities/schema/hashes.json` | `5407bea4cbb2a43be1a2bd8faa9983b06fe158ecc1bca99b2123e7f0869bc185` |
| `contracts/guest-capability-transport-v1.json` | `052ebe9fbdc20a41307332086767e7903680bc83ba273c696edf9187be6b6439` |
