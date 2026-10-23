# Native capability session ABI follow-on

Status: root integration proposal, 2026-10-23. These are proposed declarations,
not exported functions or a qualified native ABI. Implement only after the Rust guest
composition has a frozen, independently reviewed implementation. No existing C
header, session, profile, activation, identity or release contract changes here.
The [Rust composition](experimental-capability-guest-implementation.md) and
[transport contract](../contracts/guest-capability-transport-v1.json) define the
behavior to expose. Phones remain disconnected.

The follow-on must turn the Rust value's caller-managed lifetime into counted
native session ownership. A second independent registry with another sixteen
slots would violate the existing process ceiling. All legacy and capability
reservations, live sessions, closed native-draining sessions and destructors must
share the existing sixteen slots. Capabilities remain an explicit create route;
legacy create still rejects profile4. Legacy symbols reject capability handles,
and new symbols reject legacy handles, with no implicit upgrade or negotiation.

## Separate header and fixed versioned structures

Use a new optional `mixer_vm_capability.h` including the unchanged `mixer_vm.h`.
Do not add fields to any legacy structure. The intended supported native layouts
are LP64 arm64/x86_64; other targets require their own proof before admission.
All proposed structures use fixed-width integers; external byte-buffer lengths
use `size_t` with the existing bounded pointer contract.

```c
typedef struct MixerVmCapabilityLimitsV1 {
    uint32_t struct_size;             /* offset0, must be32 */
    uint32_t abi_version;             /* offset4, must be1 */
    uint32_t maximum_requests;        /* offset8, 1..8 */
    uint32_t timeout_milliseconds;    /* offset12, 1..30000 */
    uint32_t turn_milliseconds;       /* offset16, 1..50 */
    uint32_t reserved;                /* offset20, must be0 */
    uint64_t reservation_bytes;       /* offset24, narrowed<=8388608 */
} MixerVmCapabilityLimitsV1;           /* size32, alignment8 */

typedef struct MixerVmCapabilityMessageV1 {
    uint32_t struct_size;             /* offset0, returned40 */
    uint32_t abi_version;             /* offset4, returned1 */
    uint32_t kind;                    /* offset8: none0, call1, cancel2, tooSmall3 */
    uint32_t operation;               /* offset12: HTTP1, get2, put3, delete4 */
    uint64_t token;                   /* offset16: originating session only */
    uint32_t remaining_milliseconds;  /* offset24: private clock duration */
    uint32_t payload_length;          /* offset28: complete/required bytes */
    uint64_t reserved;                /* offset32, returned0 */
} MixerVmCapabilityMessageV1;          /* size40, alignment8 */

typedef struct MixerVmCapabilityResultV1 {
    uint32_t struct_size;             /* offset0, returned24 */
    uint32_t abi_version;             /* offset4, returned1 */
    uint32_t kind;                    /* offset8: accepted0, terminal1, acknowledged2 */
    uint32_t remaining_milliseconds;  /* offset12: deadline narrowing only */
    uint64_t reserved;                /* offset16, returned0 */
} MixerVmCapabilityResultV1;           /* size24, alignment8 */
```

The new limits pointer may be null for documented defaults; nonnull values must
match exact size/version, zero reserved bits, and every Rust narrowing check.
Pure output structures are not read before initialization: callers supply their
full version1 writable storage, and the function returns size/version itself.
Input/output aliasing must be rejected before mutation in these new functions;
do not read uninitialized output bytes to discover their capacity. Null reports
return3 without mutation, as in the legacy boundary. After all pointer/range/alias
checks, initialize valid out-handle/output structures to their documented zero
state before processing. Pointer validity remains a trusted native caller duty;
numeric range checking cannot make dangling pointers safe.

`none` has all message fields zero except size/version. `call` has the fixed
operation, nonzero token, remaining duration and complete argument length.
`cancel` has operation/token only and no payload. `tooSmall` has required length
only, does not issue a native lease and does not consume the queued call. A zero
remaining duration must be handled as expiry before I/O, not a fresh timeout.
All unused output fields stay zero.

The result kinds describe only successful mailbox protocol handling. Repeated
post can report `terminal`; repeated exit can report `acknowledged` only while
that request identity is still retained. Once released, the token is stale and
rejects. Neither result is a native effect/rollback assertion. Legacy report
statuses remain0..4: success, validation, execution/terminal, API rejection,
contained panic/poison. Stale/foreign handles, malformed inputs and operation
mismatch are API rejection, not a new meaning for status0.

## Explicit function family

Every new declaration ends in `_v1`. The following signatures describe arguments
in addition to the required final `MixerVmReport *out` and `uint32_t` status return:

| Name prefix `mixer_vm_capability_` | Arguments before report | Behavior |
| --- | --- | --- |
| `session_create` | module/length, startup-name/length, legacy VM limits, new capability limits, out-handle | Reserve shared capacity before parse/instantiate; private capability admission only; validate defined startup/wake; publish disabled session last |
| `session_startup` | handle | Invoke the immutable installed-selected startup once, effects disabled |
| `session_enable` | handle | Enable only after successful startup; repeat is idempotent |
| `session_invoke` | handle, export-name/length, legacy value arguments/count | Serialize one ordinary turn; publish queued calls only on success |
| `session_wake` | handle, out-did-invoke | Invoke the fixed wake at most once if ready; otherwise return0 with flag0; no internal spin or callback |
| `session_read` / `session_write` | handle, unsigned offset, buffer/length | Existing one-MiB host-copy bound and full checked ranges; no guest pointers escape |
| `session_cancel` / `session_close` | handle | Permanent cooperative stop; close invalidates ordinary access immediately and preserves native exit accounting |
| `take` | handle, out-message, byte output/capacity | Bounded arguments/control copy; dispatch lease and its count commit atomically with successful call take |
| `post` | handle, token, operation, completion/length, out-result | Trusted strict-bridge output only; Rust checks structural bounds/identity/state, not full JSON or grants |
| `ack_exit` | handle, token, operation, out-result | Allowed through a retained closing generation; acknowledge once; may trigger final destruction |
| `limit_deadline` | handle, token, operation, timeout-ms, out-result | Only shorten relative to original enqueue time; report remaining whole milliseconds |
| `expire` | handle | Apply private monotonic time, with no guest/native caller-supplied clock |

An independent capability validation entry point will also be needed before
activation staging. It must share the exact full private module validation and
startup/wake checks with create, without executing or allocating instance memory.
It must not make a predecoded privileged Module available to legacy callers.
Its exact API follows the reviewed Rust validation split, not an invented weaker
inventory-only check.

Closed capability handles permit only `ack_exit` on retained operation identities.
They cannot take, post, enable, read, invoke or be revived. Swift owns a bounded
mapping for already dispatched work, so close cancels those tasks through the
installed host; draining cancellation messages from a closed guest is unnecessary.
Cancellation and actual native exit remain separate. A caller that never reports
exit keeps a slot counted instead of allowing unlimited replacement sessions.

## Registry and lock requirements

The registry owns one session variant plus a common cancellation/terminal state.
Capability native operations obtain a short native session lease, then use its
port outside the registry lock. Invoke/read/write serialize on the instance;
post/expiry/exit acknowledgement never acquire the instance lock. No native or
guest callback executes under a registry, instance or mailbox lock. Destruction
still occurs outside the registry lock, while its slot remains `Reclaiming` until
the destructor completes. Old generation retirement remains unchanged.

Reclamation requires both zero in-flight native API/VM calls and zero dispatched
exit obligations. Counting transient Rust ticket objects is insufficient: C holds
opaque integers, and dropping a temporary ticket cannot mean native exit. The
registry therefore needs an independently observable outstanding-obligation count
whose updates are atomic with successful take/ack state transitions. Review its
lock ordering and memory ordering explicitly. Do not query a mailbox while
holding the registry lock or release a slot from a stale pre-lock usage snapshot.
In particular, take racing close must commit its exit obligation before dropping
the transient session lease. Duplicate/stale ack must never decrement twice.

Poison is fail-closed. The Rust experiment intentionally has no poisoned mailbox
recovery. Native wrappers must contain unwind, mark admission terminal and retain
unresolved obligations/capacity; they cannot fabricate successful cleanup to make
room. This can exhaust availability and is a documented limitation until a
separately reviewed recovery design exists. It is not an end-to-end OOM or
no-abort guarantee; existing standard-library allocations can abort the process.

## Evidence required before consumers

Before publishing the header, assert every proposed size/alignment/offset with
compiled C and Rust consumers on the host and official iOS/Android arm64 compilers.
Test unaligned structures, reserved/version/size rejection, null/zero/oversized
buffers, checked-address overflow, every input/output overlap and unchanged
sentinels. Compile and run real public C clients against an archive containing the
experimental feature; default archives must not accidentally expose a usable
capability route. Match each archive and copied header to exact source identities.

Exercise a mixed legacy/capability sixteen-slot pool, creation failure/unwind,
close during invocation/take/post/ack, last exit during deallocation, blocked
destructor, duplicate/foreign/stale operation identities, generation exhaustion,
poison, and a hung adapter retaining capacity. Re-run the existing public C/session
tests to prove old handles, layouts, profile admission and numeric values stay
compatible. Independent review must examine the combined guest/port/registry/C
boundary before Swift bridge implementation relies on its lifetime promises.

No profile4 release admission, signed grants, installed identity-v2, release-v3,
full Swift runtime, scheduler, actual HTTP/storage guest flow, device lifecycle,
immutable package dogfood or GA gate is established by this proposal.

The proposed C structure sizes, alignments and every field offset now pass compiled
assertions on macOS arm64, macOS x86_64, iOS arm64 and Android arm64. Only the host
program was executed; mobile checks produce objects. The first host link omitted
an explicit SDK and failed to find the System library; its log/runner are retained,
and the corrected command uses the observed SDK. See
[`verification/capability-native-layout-proposal/receipt.json`](../verification/capability-native-layout-proposal/receipt.json).
This preliminary layout check supplies neither Rust parity nor any function,
pointer, registry, concurrency, linking or bridge behavior from the requirements
above.
