# Stage 5 proposal: fixed Android signed UI JNI boundary

Status: **proposal for root review; no implementation assigned**, 2026-10-23.
The binding scope is `mixer-product-plan.md`, especially §§8, 10, 20 and 22.
`docs/android-signed-ui-binding-contract.md` remains authoritative, including
§§2, 4, 8 and 10. Both stage 4 addenda apply. This document proposes new seams;
it does not amend the transport or enable a runtime/profile.

The accepted input is private host checkpoint
`61c5c8b2e0af59ea98d3ff85f208ad97df069411`, plus the exact file hashes in
`verification/android-jni-stage5-contract/input-lock.json`. Root acceptance is
`verification/android-binding-stage4-root-review/acceptance.json`, SHA-256
`69bd4ab51dc8ebe7eb968baade461114dad48e35040da527dc946953575bfe79`.
HEAD may move while other lanes work; it is an observation, not an input identity.
The binding §8.3 update requires design parity: same shared app design, with only
explicitly declared platform-specific appearance. Its exact section SHA-256 is
`184934dd462f0f46d42fb13d1076433f0d538c37770e991f49812ddbbd323ef4`;
the collector also binds the complete updated product-plan bytes.

Stage 4 has real private Swift/C host joins and resource destruction. It has no
native Android authority, JNI delivery, Java-main-Looper wrapper, signed core or
Prepared integration. Its `CMixerUIAndroidHostBridge`, `CapabilityAndroidHost*`
capsules/results/receipts and fixed host object stay host-scoped. A Boolean,
platform enum, module rename, typealias, cast or reinterpreted host receipt cannot
produce any native receipt. S4-21 actual stale JNI delivery and S4-29 optimized
Release lifetime-counter injection remain pending. No full original dynamic32,
native integration, published FieldLog or GA acceptance follows from this proposal.

## 1. Deliverable split and ownership to be assigned

Root may accept the declaration/ownership contract without authorizing code.
Implementation requires separate assignments in this order:

| Slice | Proposed sole owner and exact files | Acceptance boundary |
| --- | --- | --- |
| 5A: closed Java subset | One Java lane: new `native/android/app/src/dev/mixer/android/SignedUiPacket.java`, `SignedNativeRenderer.java`, `SignedGuestScreen.java`, `SignedGuestDrawProbe.java`; verification in new `verification/android-jni-stage5-java/` | Decoder/identity/listener/overlay algorithms and Android API30 compilation. Without 5N/5B these are data/UI tests; no accepted input, native witness or health qualification. |
| 5T: shared theme prerequisite | Root must freeze a separate shared design-token/metrics contract and assign its SDK/Apple/Android sources before 5A visual acceptance. Proposed new Java consumption edge `native/android/app/src/dev/mixer/android/SignedUiStyle.java`; no existing Apple or renderer file assigned by this proposal | Same app theme, layout metrics, text scale, colors and component states across native adapters. UI-v1 has no complete shared theme/font/asset descriptor today. Absence is pending, not permission to substitute Android/Material styles. |
| 5N: native authority prerequisite, **separate root acceptance required** | One Swift integration lane: the five existing `CapabilityGuestUIAndroid{Binding,Registry,Lifetime,Resources,Progress}.swift` files and existing `CapabilityGuestUIPresentationLifetime.swift`, plus new `CapabilityGuestUIAndroidNativeBoundary.swift` in `capability-activation/Sources/MixerCapabilityActivation/`; new `sdk/Sources/MixerUI/NativePacketV1.swift` and focused SDK tests assigned to this same lane or serialized by root | Closed native backend, real native-acquired capsule/Task/common permit, native resource helpers, fixed ingress exports and sealed native evidence. Reuse engine algorithms with explicit native edges; preserve all accepted host and Apple behavior. No core/Prepared changes. If root does not accept this prerequisite, defer it to stage 6 and keep native acceptance pending. |
| 5B: JNI implementation | One C/JNI lane: new `native/android/signed-guest-ui/jni/jni.c`, `native/android/signed-guest-ui/jni/include/mixer_ui_native.h`, `module.modulemap`; verification in new `verification/android-jni-stage5-native/` | Exact final wrapper cache, thread/entry checks, sixteen weak slots, fixed `mxis_*`, scalar ingress and native-slot postconditions, using unchanged real transport/platform objects. Depends on frozen 5N declarations. |
| 5V: native boundary execution | Root or explicitly assigned verification lane: new `verification/android-jni-stage5-integration/` only | Fresh native closure + actual Android emulator Looper/JNI/widget run against 5N/5B. Resolves named native cases only, after implementation review. No physical devices. |
| 6: product integration | Root's later coordinated contract | Real signed core/Prepared/factory/observation and concrete-attempt fallback ownership, installed identity/profile, dependency/source closure, APK/generator integration, signed VM/KV/recovery/coordinator health, positive visible-window regression, separately published FieldLog. |

This lane owns only this document and `verification/android-jni-stage5-contract/**`.
It edits no production/header, old contract, workflow, STATUS, PLAN, work graph or
gate. It creates no commits/pushes. The proposed ownership table is not a grant.

Preserve `native/android/bridge/jni.c`, `NativeBridge.java`, `MixerActivity.java`,
`Json.java`, `UiPacket.java`, `NativeRenderer.java`, `AndroidSessionRegistry`,
`AndroidDocumentSession`, all normal factories, immutable contracts and transport
files. `Json` is a reusable low-level parser only: 1MiB/depth196/100000 values,
strict UTF-8/surrogates and exact unsigned decimal already exist. `UiPacket` permits
4096 nodes/depth64/16KiB strings/many controls; `NativeRenderer.Events` captures
packet/node objects. Neither is a signed type. No instance of either flows into
the new signed renderer. No compiled reducer operation1/event adapter is used.

All shared Swift modifications belong to one owner after root freezes the seam.
No parallel edits to the six existing files; no second coordinator or copied
binding engine. The extraction may share concrete scalar scheduling/registry
algorithms with two closed, separately constructed host/native edges. Do not add
an externally conformable backend protocol, callback driver or caller-selected
scope. Host and native bridge modules are mutually exclusive in one binary; a
build seeing both fails compilation/link. `canImport` alone grants no authority.

## 2. Necessary native types; no host promotion

The following are proposed internal Swift declarations, with bodies intentionally
absent. Native definitions compile only with `CMixerUITransport` and the actual
`CMixerUIAndroidNativeBridge`, and without `CMixerUIAndroidHostBridge`. The module
contains declarations; a native acceptance build must also prove exact linked
JNI, Android platform, Swift and SDK objects. A header or synthetic library is
not an installation witness.

```swift
struct CapabilityAndroidNativeLifetimeKey: Sendable, Equatable {
    let facade: UInt64
    let lifetime: CapabilityPresentationLifetimeID
    let endpoint: UInt64
    fileprivate init(facade: UInt64,
                     lifetime: CapabilityPresentationLifetimeID, endpoint: UInt64)
}
final class CapabilityAndroidNativeLifetimeCapsule: @unchecked Sendable {
    // Private constructor: fixed spawn consumes the real native registry's
    // acquired endpoint token; accepts no caller Task, driver or receipt.
}
final class CapabilityAndroidNativeInstallation: @unchecked Sendable {
    func move() -> CapabilityAndroidNativeInstallation?
    func bind(_ exchange: GuestUIExchangeV1) throws
    func requestStop(_ cause: CapabilityAttemptLocalStop)
    func finish() async -> CapabilityAndroidNativeJoinStatus
    var status: CapabilityAndroidNativeJoinStatus { get }
}
extension CapabilityGuestUIPresentationLifetime {
    static func consumeAndroidNative(_ capsule: CapabilityAndroidNativeLifetimeCapsule)
        throws -> CapabilityAndroidNativeInstallation
}
```

Native `consume` selects a new **closed concrete native backend** and issues the
same existing one-shot common `CapabilityPresentationJoinPermit`; it does not
expose that permit. Its finish actually awaits its sole `Task.value`, creates
file-private native task-return evidence, invokes the fixed native join edge,
then publishes immutable native status. Existing Apple `installation/attach/
isBound/status/finish` reject this case before Apple receipt/permit creation just
as they reject host. Host installation cannot be passed to native `consume`,
finish, common Prepared gate or native validators. Constructors remain private
even with `@testable` imports. No `Host -> Native` conversion exists.

Native-only evidence is scalar and has private constructors at the actual proof
edge; these names are distinct from all host/common receipts:

| Type | Only producer and required fact |
| --- | --- |
| `CapabilityAndroidNativeTaskReturnEvidence` | Statement after actual `await task.value` in common lifetime source; exact native key. |
| `CapabilityAndroidNativeAttachmentEvidence` | Native boundary's leased inner attach commit; exact reference, attach serial and real JNI slot generation, fixed slot inspection and successful saved-snapshot apply where present. |
| `CapabilityAndroidNativeFacadeCleanupEvidence` | Resources inner final RETIRE, after fixed exact Java cleanup, real weak deletion, Swift exchange/render clear, fixed native slot postcheck, lookup disable and checked cleanup serial publication. |
| `CapabilityAndroidNativeEndpointRetirementEvidence` | Native join edge after real C endpoint reclaim under admission; exact key and actual callback/UI-entry fences, optional native cleanup evidence. |
| `CapabilityAndroidNativeLifetimeReceipt` | Common lifetime private validator combines native actual-Task and native endpoint evidence for the same key. |
| `CapabilityAndroidNativeFinalReceipt` | Final binding owner after exact cleanup, all actual joins/fences, zero aliases, facade reclaim and return of reservation-owned resource destructor. |

`CapabilityAndroidNativeJoinStatus` has `.pending`, `.finished(.retired(receipt))`,
`.finished(.quarantined(failure))` and `.invariant(...)`; final-close status has
pending/finished native final receipt/quarantined/invariant. No `isNative: Bool`
or `nativeOK` parameter. All successful receipt fields match the accepted host
shapes but cannot be constructed from those shapes. Host scopes remain intact.

```swift
enum CapabilityAndroidNativeFailureCode: Sendable, Equatable {
    case invalidState, unavailable, wrongThread, staleTuple, malformedPacket
    case jniException, transportIO, retireFailed, missingPublishedResources
    case identityExhausted, setupFailed, cleanupPending
}
struct CapabilityAndroidNativeFailure: Sendable, Equatable {
    let key: CapabilityAndroidNativeLifetimeKey?
    let code: CapabilityAndroidNativeFailureCode
    // Diagnostic only; nil key only before endpoint allocation.
}
enum CapabilityAndroidNativeFinishResult: Sendable, Equatable {
    case retired(CapabilityAndroidNativeLifetimeReceipt)
    case quarantined(CapabilityAndroidNativeFailure)
}
enum CapabilityAndroidNativeJoinStatus: Sendable, Equatable {
    case pending
    case finished(CapabilityAndroidNativeFinishResult)
    case invariant(CapabilityPresentationInvariant)
}
enum CapabilityAndroidNativeFinalCloseStatus: Sendable, Equatable {
    case pending
    case finished(CapabilityAndroidNativeFinalReceipt)
    case quarantined(CapabilityAndroidNativeFailure)
    case invariant(CapabilityPresentationInvariant)
}
```

5N may expose only this internal standalone preparation entry for native boundary
qualification, **if root explicitly accepts it**:

```swift
extension CapabilityGuestUIAndroidBinding {
    static func prepareNative(reservation: CapabilityAttemptReservation) async throws
        -> CapabilityAndroidNativePreparedPresentation
}
final class CapabilityAndroidNativePreparedPresentation: @unchecked Sendable {
    var reference: GuestUIAndroidPresentationReference { get }
    func transferToBinding() throws
    func bind(_ exchange: GuestUIExchangeV1) async throws
        -> CapabilityAndroidNativeInstallation
    func requestFinalClose(_ cause: CapabilityAttemptLocalStop)
    func finishFinalClose(using installation: CapabilityAndroidNativeInstallation?) async
        -> CapabilityAndroidNativeFinalCloseStatus
    func cleanupAfterFailure() async -> CapabilityAndroidNativeFinalCloseStatus
    // Private construction; same real reservation/setup/final-owner rules.
}
```

The read-only reference holds checked lifecycle/presentation IDs in a private
scalar shell, exposes neither raw IDs publicly nor runtime objects and cannot
reopen. A fixed internal embedding trampoline reads them. Stage 5 verification
can use real reservation + exact real `GuestUIExchangeV1` transitions and native
prepare, not a fixture-minted witness. Its privileged test embedding creates the
actual final Java wrapper through its fixed private constructor. It does not
prove signed selection, VM execution, concrete runtime retirement or health.
No production public embedding/factory changes are included here.

Until 5N exists, 5A/JVM declaration or JNI marshalling tests must remain
`pending_native_backend` for positive signed ingress. Do not implement a host
`submitEvent`, synthetic native capsule, success-returning stub or receipt maker
to close S4-21. The native stale test requires the actual closed native backend,
real input/attachment/probe publication, same snapshot/exchange routing, real
JNI wrapper weak-slot publication, and unchanged Android C transport/Looper.

## 3. Fixed Java/JNI methods and cached metadata

The Java wrapper is package-private `final class SignedGuestScreen`. Its sole
private constructor is `(android.app.Activity, long lifecycle, long presentation)`;
descriptor `(Landroid/app/Activity;JJ)V`. It owns one final private root and fresh
signed renderer. The Activity owns the screen for its window lifetime; the screen
keeps a weak Activity reference, never a static Activity/context. Views use the
owning Activity's Context in the normal Java tree. No Java object enters Swift
Tasks or C transport. The four signed classes are product-owned fixed code.

Java-origin methods are private static native methods on that final class.
Names/descriptors are fixed; there is no overloaded dispatch, event-name string,
caller callback, export, action ID, value or arbitrary object parameter. Wrapper
is the only object parameter and occurs only in the fixed attach trampoline.

| Java declaration | Descriptor | JNI C symbol suffix and arguments after `JNIEnv *, jclass` |
| --- | --- | --- |
| `int nativeInstall()` | `()I` | `nativeInstall` |
| `int nativeAttach(long lifecycle, long presentation, SignedGuestScreen wrapper)` | `(JJLdev/mixer/android/SignedGuestScreen;)I` | `nativeAttach(jlong,jlong,jobject)` |
| `int nativeActivate(long lifecycle, long attachment, long input, long revisionBits, byte[] nodeID, long generationBits)` | `(JJJJ[BJ)I` | `nativeActivate(jlong,jlong,jlong,jlong,jbyteArray,jlong)` |
| `int nativeObserve(long lifecycle, long attachment, long probe, long drawSerial, long frameTimeNanos)` | `(JJJJJ)I` | `nativeObserve(jlong,jlong,jlong,jlong,jlong)` |
| `int nativeRequestClose(long lifecycle, int reason)` | `(JI)I` | `nativeRequestClose(jlong,jint)` |
| `int nativeDetachUI(long lifecycle, long attachment)` | `(JJ)I` | `nativeDetachUI(jlong,jlong)` |

Every exported symbol is exactly
`Java_dev_mixer_android_SignedGuestScreen_<suffix>`, returns `jint`, and uses
`JNIEXPORT ... JNICALL`. Dynamic symbol exports are limited to these names and
the fixed required C bridge hooks. No `RegisterNatives` setter exposed to callers.
The checked declaration inventory is `api.json` beside this proposal's collector.

At install, independently require Java `Looper.myLooper() == getMainLooper()`
using `IsSameObject`, a nonnull main Looper, API30+, no pending exception and the
same native captured installation pthread. Call unchanged `mxuit_install()` on
that thread so real `ALooper_forThread/addFd` mapping is exercised. No MainActor,
main DispatchQueue or host pthread is equivalent. Installation is once per
process; failure after partial transport installation is sticky unavailable,
never retry to substitute a different VM/classloader/thread.

The permanent cache contains exactly one `JavaVM *`, two strong global `jclass`
references (the exact final wrapper class and `android/os/Looper`), one pthread
identity, fixed method IDs and scalar install state. The wrapper class is resolved
from its native caller/classloader once; another class with the same name from a
different loader rejects. Candidate class globals are locally counted until cache
publication, deleted on install failure. No `JNIEnv *` is stored, and neither
`AttachCurrentThread` nor detach is called. Native-to-Java calls use `GetEnv` only
after `mxuit_ui_validate`; a detached/wrong thread fails closed.

Cache only these known instance methods on the wrapper and two Looper statics:

| Private wrapper method | Descriptor | Fixed postcondition |
| --- | --- | --- |
| `int applySigned(long attachment, long input, long probe, byte[] packet)` | `(JJJ[B)I` | Full signed candidate validation, synchronous native tree installation, current tuple publication; interaction remains disabled. |
| `int setInteraction(int enabled)` | `(I)I` | Accept only 0/1; recompute each button as authored ancestor-enabled AND native overlay. No reconciliation/revision advance. |
| `int retireSigned(int finalFacade)` | `(I)I` | Clear all listeners/tree/packet/tuple/probe; final also permanently closes wrapper. Does not claim weak deletion. |
| `int consumeObservation(long attachment, long probe, long drawSerial, long frameTimeNanos)` | `(JJJJ)I` | Consume only its exact pending real draw/later-frame observation after fresh wrapper/window/lifecycle checks. Fixed method, not a Boolean field read. |
| `Looper.myLooper()` and `Looper.getMainLooper()` | `()Landroid/os/Looper;` | Compare actual returned objects on every admitted JNI resource entry. |

Missing method/class, classloader mismatch, exception or wrong thread has no
fallback. Native C calls only these cached methods. Java flags, return codes and
diagnostic structs alone cannot construct native cleanup or health authority.

## 4. Immutable bridge ABI and proposed Swift-C ingress

Leave the existing transport header/APIs, `mxuit_drain/complete/progress`, and
these `mxis_*` signatures byte-for-byte unchanged:

```c
int32_t mxis_apply(uint64_t facade, uint64_t entry, uint64_t attachment,
                   uint64_t input, uint64_t probe,
                   const uint8_t *packet, uint32_t packet_bytes);
int32_t mxis_interaction(uint64_t facade, uint64_t entry, uint32_t enabled);
int32_t mxis_retire(uint64_t facade, uint64_t entry, uint32_t final_facade);
```

The new private native header imports that header and declares only these
additional fixed exports. All pointers below are synchronous bounded byte regions
or scalar output records; none is stored. C transport gets none of them.

```c
/* Implemented by Swift native boundary; entry was already admitted by C. */
int32_t mxisi_attach_begin(uint64_t facade, uint64_t entry,
                          uint64_t presentation, uint64_t *attach_serial);
int32_t mxisi_attach_commit(uint64_t facade, uint64_t entry,
                           uint64_t presentation, uint64_t attach_serial,
                           uint64_t slot_generation);
int32_t mxisi_attach_abort(uint64_t facade, uint64_t entry,
                          uint64_t attach_serial, uint32_t failure);
int32_t mxisi_activate(uint64_t facade, uint64_t entry, uint64_t attachment,
                      uint64_t input, uint64_t revision,
                      const uint8_t *node_id, uint32_t node_id_bytes,
                      uint64_t generation);
int32_t mxisi_observe(uint64_t facade, uint64_t entry, uint64_t attachment,
                     uint64_t probe, uint64_t draw_serial,
                     uint64_t frame_time_nanos);
int32_t mxisi_request_close(uint64_t facade, uint32_t reason);
int32_t mxisi_detach_ui(uint64_t facade, uint64_t entry, uint64_t attachment);

/* Implemented by the exact JNI object; read under a valid entry only. */
enum mxis_native_disposition {
    MXIS_NATIVE_NEVER = 0, MXIS_NATIVE_STAGED = 1,
    MXIS_NATIVE_PUBLISHED = 2, MXIS_NATIVE_ATTEMPT_RETIRED = 3,
    MXIS_NATIVE_FINAL_DELETED = 4, MXIS_NATIVE_POISONED = 5
};
struct mxis_native_slot {
    uint64_t facade, slot_generation, attach_serial, final_entry;
    uint64_t attachment, input, probe;
    uint32_t disposition, packet_bytes;
};
/* Scalar-only fixed reservation after real C facade acquire, before resources. */
int32_t mxis_native_slot_reserve(uint64_t facade, uint64_t *slot_generation);
/* Scalar-only acquired-empty rollback; never a cleanup/retirement witness. */
int32_t mxis_native_slot_abort_empty(uint64_t facade, uint64_t slot_generation);
int32_t mxis_native_slot_read(uint64_t facade, uint64_t entry,
                             struct mxis_native_slot *out);
int32_t mxis_native_observation_take(uint64_t facade, uint64_t entry,
                                     uint64_t attachment, uint64_t probe,
                                     uint64_t draw_serial,
                                     uint64_t frame_time_nanos);
/* Scalar-only trusted final-owner call; no JNI and no receipt constructor. */
int32_t mxis_native_slot_release(uint64_t facade, uint64_t slot_generation,
                                uint64_t final_entry);
```

Exact Swift C entry signatures map every `uint64_t` to `UInt64`, every
`uint32_t` to `UInt32`, `int32_t` to `Int32`, output identity to
`UnsafeMutablePointer<UInt64>?`, and node region to `UnsafePointer<UInt8>?`.
Each uses `@_cdecl` with the identical symbol above, no `throws`, `async`, JNI
type, Swift object, `Bool`, generic or closure. Bodies call private fixed native
helpers; no Swift failure unwinds across C. `mxis_native_slot_read` is a
postcondition query, not a public witness constructor or mutable test seam.
Swift constructs sealed evidence only after directly calling the real fixed
JNI implementation and checking exact leased state. A fixture implementing
this header cannot earn native evidence or a native acceptance receipt.

Exact proposed Swift definitions in the new native boundary source are:

```swift
@_cdecl("mxisi_attach_begin")
func capabilityAndroidNativeAttachBegin(_ facade: UInt64, _ entry: UInt64,
    _ presentation: UInt64, _ attachSerial: UnsafeMutablePointer<UInt64>?) -> Int32
@_cdecl("mxisi_attach_commit")
func capabilityAndroidNativeAttachCommit(_ facade: UInt64, _ entry: UInt64,
    _ presentation: UInt64, _ attachSerial: UInt64, _ slotGeneration: UInt64) -> Int32
@_cdecl("mxisi_attach_abort")
func capabilityAndroidNativeAttachAbort(_ facade: UInt64, _ entry: UInt64,
    _ attachSerial: UInt64, _ failure: UInt32) -> Int32
@_cdecl("mxisi_activate")
func capabilityAndroidNativeActivate(_ facade: UInt64, _ entry: UInt64,
    _ attachment: UInt64, _ input: UInt64, _ revision: UInt64,
    _ nodeID: UnsafePointer<UInt8>?, _ nodeIDBytes: UInt32,
    _ generation: UInt64) -> Int32
@_cdecl("mxisi_observe")
func capabilityAndroidNativeObserve(_ facade: UInt64, _ entry: UInt64,
    _ attachment: UInt64, _ probe: UInt64, _ drawSerial: UInt64,
    _ frameTimeNanos: UInt64) -> Int32
@_cdecl("mxisi_request_close")
func capabilityAndroidNativeRequestClose(_ facade: UInt64, _ reason: UInt32) -> Int32
@_cdecl("mxisi_detach_ui")
func capabilityAndroidNativeDetachUI(_ facade: UInt64, _ entry: UInt64,
    _ attachment: UInt64) -> Int32
```

`mxisi_request_close` accepts only close reason1=pause,2=detach,3=ownerClose,
4=presentationFailure. These finite diagnostics have the same sticky final-close
effect. Unknown reason rejects INVALID without allocation. IDs zero/invalid
combinations reject INVALID; nonexistent IDs are STALE. Entry functions return
the existing MXUIT statuses. `mxis_*` returns OK on exact fixed postconditions,
otherwise a finite failure status. No status means actual Task joined, native
reclaimed, final destructor returned or durable health committed.

## 5. Entry, weak-slot and final-return algorithms

**Count first.** After checking primitive numeric argument form only, each attach,
activate or observe C JNI outer trampoline calls
`mxuit_ui_enter(facade,0,0,MXUIT_UI_INGRESS,&entry)` before `GetEnv`, array length,
Java class/Looper/weak checks or Swift record/resource lookup. Detach first calls
the scalar close export, then obtains `MXUIT_UI_CLEANUP`. Installation has no
facade and is its own once-only prerequisite. RequestClose touches permanent
scalars only and calls no JNI, model, weak object or resource helper; it remains
valid reentrantly and between attempts. Transport's pthread check rejects a
wrong-thread ingress before JNI; each accepted inner JNI helper additionally
compares the cached actual Java Looper objects. No lock spans these calls.

The process has exactly 16 JNI slots, owned by facade, separately from transport
and Swift storage. Each holds one `jweak` at most plus finite scalar state in
`mxis_native_slot`. Slot generation/attach serial are checked positive counters;
no wrap/reuse. Weak/object operations are UI-thread-only; slots are never indexed by an unchecked
Java integer. The stable facade resolves a fixed slot; no dictionary or Activity
singleton. A wrapper cannot be retargeted to another facade/presentation. A short
JNI metadata mutex protects scalar slot reservation/publication/read-use counts
and final release; it never spans JNI, Swift calls or destruction. All weak
creation/promotion/deletion remains UI-thread-only. Worker-side final slot release
touches only scalars after that facade can admit no further UI entry.

Native prepare requires actual completed installation and, immediately after real
C facade acquire and before resource publication/endpoint creation, calls fixed
`mxis_native_slot_reserve(facade,&generation)`. This worker-safe scalar operation
reserves one JNI record in NEVER state with a checked nonzero generation and no
weak reference. It stores no env/object/transport pointer and invokes no callback.
There is therefore a native tombstone owner even for never-attached final
cleanup, and no ambiguous generation-zero or lazily missing slot can mean success.

If prepare fails after successful native slot reservation but **before enabling
resource lookup, publishing a presentation reference or creating/publishing an
endpoint**, the same async setup guard takes the
acquired-empty rollback path. It first latches close and performs actual unchanged
`mxuit_facade_begin_close`/`mxuit_facade_try_reclaim` for that known-empty facade,
removing its exact Swift acquired-empty lookup under admission only on proven C
success. There was no endpoint/Task, so it asserts no consumer join. Then fixed
worker-safe `mxis_native_slot_abort_empty(facade,generation)` checks exact NEVER,
null weak, attach serial0, no prior staged/published state, no object/packet/input/
probe and zero helper/read uses under the metadata lock. Only then may it free
that scalar record. It emits no native final-cleanup or retirement witness.
Release any unexposed local empty resource alias before explicitly retiring the
unused obligation under the guarded open failure path; no deinit async cleanup.

Force failure after every post-reserve/prepublish allocation, including resource
construction/retained-owner transfer before publication, and repeat beyond16
attempts. Exact known-empty rollback must return capacity and slots. Any published
resource/endpoint, ever-staged weak, inability to prove empty C reclaim or sticky
fault forbids this abort; use the real leased final RETIRE/Task/fence path if it
exists, otherwise quarantine/pin. A normal NEVER cleanup after publication must
still run actual leased Swift/native final clearing and the ordinary release
handshake. Do not turn an absent object into an acquired-empty proof.

Attach is a single leased transaction:

1. Enter C; check native/Java main thread and exact final wrapper/classloader.
   Call fixed `mxisi_attach_begin` to validate the native presentation reference,
   live facade, single attachment and alias scope. It issues a one-use attach
   serial; no weak global/model owner is stored in C transport.
2. Claim that exact already-reserved NEVER JNI slot under the entry.
   `NewWeakGlobalRef(wrapper)`
   creates a **local counted obligation** before publication. Until the exact
   slot owns it, this JNI frame is responsible for deletion on this UI thread.
   Hold the prepublication schedule in tests, including close/exception races.
3. Publish the real weak global and staged exact facade/attach/generation tuple,
   with no intervening callback. Commit calls fixed `mxisi_attach_commit`; the
   Swift inner helper reads the real slot, installs fresh Java-safe positive
   attachment/input/probe identities and applies the exact saved snapshot if any.
   First attach does not call the reconciler with the same revision as successor.
   Without a saved snapshot attach remains empty/disabled and earns no observation.
4. Publication/commit failure invokes exact abort while entry is held; synchronously
   retire any partially installed Java tree, delete the newly created weak global
   on this thread and clear staged state. If cleanup is uncertain, mark poisoned,
   stop/quarantine and pin accounting; never publish successful attachment/final
   evidence. A first failed attach does not permit object retargeting/retry.
5. All Java/JNI/Swift inner frames and owned local refs/buffers return/destroy,
   including `PopLocalFrame`, before dropping the checked UI alias and calling
   `mxuit_ui_leave`. No `defer` leaves while inner locals are alive. After leave
   the C outer and private Java listener/entry tail perform only scalar return.

Every `mxis_*` validates the exact active C facade/entry **before** GetEnv or
slot/weak lookup. Promote weak once with `NewLocalRef`, use the local for the whole
fixed call, then delete it before entry leave. Published weak promotion failure
is a presentation failure/stop/quarantine. It never converts a published slot
into NEVER, clears the tree by assumption or yields final-cleanup success.

PRESENT may prepare an authoritative snapshot before any attachment. A genuinely
never-published native slot can later produce known-empty cleanup only after
native registry/entry checks and actual Swift clear; a nonzero old generation or
poisoned slot cannot. Never-published and published-but-collected are distinct.

Attempt `mxis_retire(final=0)` synchronously disables interaction, removes every
listener, invalidates/removes the pending probe callback, clears Java tree/current
packet/attempt tuple and records ATTEMPT_RETIRED. The facade retains its one weak
wrapper across attempts. Replacement uses a fresh endpoint/Task/reconciler/tuple
only after the old actual common join has returned and C endpoint reclaimed;
real concrete runtime retirement remains stage6. Old listener/probe tokens are
never looked up against a successor merely because revision/node IDs coincide.

Final `mxis_retire(final=1)` must call the exact promoted wrapper's fixed cleanup
successfully, clear all native state, **DeleteWeakGlobalRef before returning OK**,
record exact FINAL_DELETED/final entry/slot generation, and finish local cleanup.
Swift clears its snapshot/reconciler/exchange/ticket/results, validates that exact
fixed slot state, disables lookup and privately publishes native cleanup evidence.
Deletion itself is not Task/native/facade/destructor completion. The permanent
scalar cleanup record remains readable after resource lookup is disabled.

**Explicit slot reuse:** FINAL_DELETED is a tombstone, not a free slot. After the
last fixed slot read has returned, exact native cleanup evidence is stored in the
resource-free shell, lookup is disabled/removed, the last actual Task/endpoint has
joined/reclaimed, C facade return fences and actual facade reclaim completed, and
both transient alias counts are zero, the unique final binding owner calls
`mxis_native_slot_release(facade,slotGeneration,finalEntry)` once. That fixed
scalar-only call additionally checks the exact FINAL_DELETED tuple, null weak
global, no staged obligation and zero native helper/read uses under its metadata
lock. It frees only this JNI slot; generation/attach/draw process counters never
reset. It cannot assert cleanup, Task return, C reclaim or Swift destruction for
its caller. The proof-bearing Swift source must already have those facts; no
Boolean/status/diagnostic caller can request early release through public APIs.

After release the old resources are terminal, empty and permanently forbidden
from reading the slot or doing JNI, including in deinit. The final owner can then
call the real obligation `retire()` outside locks; only after its actual destructor
returns may final completion/capacity release be reported. A held destructor may
coexist with JNI slot reuse only because it has no slot/JNI access left; its outer
reservation capacity remains pinned. If scalar slot release fails, do not retire
the obligation: quarantine and pin ownership. The tombstone is retained on every
uncertain cleanup/fence failure. Require at least 17 sequential fully closed real
native facades and a held-final-read/fence negative schedule; otherwise fixed16
could silently become a process-lifetime allocation limit.

Final close while a helper is active latches scalars; detach cleanup returns BUSY
without tree work, and the helper's mandatory postcheck disables/retires before
its leave. Nonreentrant detach performs exact cleanup under its own lease.
Detach while closed/after final cleanup returns scalar CLOSED without a weak
lookup; wrong stale attachment cannot clean a successor, while scalar close
remains valid. No cleanup queue or Looper-blocking join is introduced.

Late final close after the nonfinal RETIRE decision still requires the accepted
single TERMINAL endpoint path. Endpoint absence or a sampled close flag is not
final cleanup. The same real task/permit/fences/progress cell and authoritative
final owner rules apply. The join-admission addendum applies unchanged: a local
fault before beginJoin prevents consumer-joined; a registry fault before real C
reclaim prevents retirement; a fault after actual reclaim may preserve only that
completed endpoint fact and never frees quarantined facade/resources/capacity.
No lock spans JNI, callbacks, weak promotion, destruction, resume or await.

## 6. Scalar, codec and renderer boundary

Revision/generation preserve **all UInt64 bits** through `jlong` by `memcpy`
bit-preserving conversion in C (not implementation-defined signed narrowing).
Positive Java-facing lifecycle/presentation/attachment/input/probe/attach/draw IDs
stop at `Int64.max`; zero, overflow and stale identities reject. Unsigned revision
comparison uses `Long.compareUnsigned` or exact decimal, never signed order,
floating-point, `double`, `NSNumber` coercion or `Long.parseLong` on UInt64 text.
Revision/generation are positive for signed screens; max UInt64 remains valid.

Native packet generation first takes the **same** authoritative `UIRenderSnapshot`
used by `exchange.completePresentation`. There is no exported SDK packet encoder
today: `AndroidDocumentSession.encode` and checklist `Engine` contain private
snapshot+identities encoders. Do not call their sessions or reconstruct identities.
Propose a data-only SDK facility in the new file:

```swift
public extension UIRenderSnapshot {
    func encodeNativePacketV1() throws -> Foundation.Data
}
public enum UINativePacketEncodingError: Error, Sendable {
    case missingIdentity, outputLimit
}
```

It emits existing schema1 `{schemaVersion,document,identities}`; bounded preorder
traversal obtains every generation using `snapshot.identity(for:)`, exactly once
per node, and preserves original UTF-8 bytes. It never runs a reducer, reconciles
again, increments a generation or takes caller-provided identities. Fixed JSON
wire conventions are sorted keys and unescaped slashes, with 1MiB output ceiling.
This public data facility independently preflights standard UI-v1 limits (4096
nodes/depth64/1000children/16KiB strings/1MiB content) before serialization; a caller
may have obtained a snapshot from a custom reconciler with much larger limits.
Traversal checks child count/depth/count before pushing children and bounds its
pending stack; checked arithmetic rejects overflow. A bounded writer checks every
append against the fixed 1MiB budget, emits escaped strings incrementally and
never builds a larger whole JSON/string temporary first. A post-JSONEncoder size
check alone is not sufficient. There is at most one bounded output buffer; sorting
is limited to closed small property/action sets. Native
signed resources use the 256/depth16 guest-configured `UIReconciler` and exact
already-validated <=65536-byte guest frame; the new packet ceiling does not widen
guest validation. No normal session change is needed for this new data facility.

`SignedUiPacket.decode(byte[])` is the only constructor of its immutable signed
candidate. It may reuse unchanged `Json.parse` for generic strict JSON, then
requires exact schema/fields, positive exact UInt64 revision/generations, complete
one-to-one identity coverage and unique nonzero generations, raw identifier byte
identity, all UI-v1 closed property types, and **only vStack/text/button**.
Reject at 257 nodes, depth17 (root depth1), 65 children, 4097 UTF-8 bytes/string,
129 bytes/identifier, extra actions/properties/fields and packets >1048576 bytes.
Button has exactly `.activate`, text/vStack no actions; text/button are leaves.
All generic parser allocation bounds remain in force. Signed Java does not claim
to establish original raw guest byte length after JSON reencoding; exact original
<=65536-byte validation belongs to real Swift exchange ingress. Test both ceilings.

Packet/ID bytes use standard strict UTF-8. Never use `NewStringUTF`,
`GetStringUTFChars` or modified-UTF8 length for guest bytes. JNI copies node ID
through `GetByteArrayRegion` into a <=128-byte local buffer and performs strict
scalar validation before exact Swift UTF-8 construction; Java uses strict decoder
REPORT and checks surrogate pairing on every string. Do not normalize composed/
decomposed identifiers. Embedded NUL is invalid in identifiers but valid text;
supplementary characters use standard four-byte UTF-8. Escaped-key duplicates,
overlong encodings, malformed scalars, unpaired surrogates, numeric exponents,
fractions/signs/leading zeros/overflow for identities all reject.

Current Swift `Set<String>`, dictionary lookup and synthesized identity equality
use canonical Unicode equality. They do not establish raw-byte identity. Do not
change that SDK-wide behavior in this lane. Test canonically equivalent composed/
decomposed spellings in separate real snapshots; a document containing both
continues to reject as an existing duplicate collision. Before native input routes,
look up the actual stored identity and additionally require
`incomingID.utf8.elementsEqual(storedIdentity.id.utf8)`; an equivalent alternative
spelling must reject even if `snapshot.identity(for:)` finds it. Packet generation
emits the exact authored `storedIdentity.id` bytes. No normalization or caller ID
reconstruction is allowed.

`SignedNativeRenderer` accepts only `SignedUiPacket`; no Events interface,
arbitrary handler, packet.event or object sink. It validates the whole candidate
and all successor identities before any existing View mutation. Prebuild new
bounded widgets/records while disabled, then apply the batch synchronously; a
mutation/allocation/JNI exception after validation clears the visible candidate
and old tree under the same lease, stops/quarantines as appropriate, and never
shows partial/degraded success. Removed/replaced Views lose listeners. A surviving
same-kind node keeps generation; replacement/remove-reinsert cannot reuse it.

The visual contract is the updated product-plan §8.3. Layout/hierarchy/content,
colors, typography scale, iconography, spacing and component appearance come from
the same shared app theme as iOS. `SignedUiStyle` consumes a root-frozen immutable
theme/metrics descriptor, not device-default Android or Material appearance.
Native widgets remain available for semantics, but explicitly set background,
tint/text colors, border/corner/ripple or pressed-state treatment, elevation,
minimum size, insets/padding, font family/weight/scale/line metrics, alignment,
spacing, enabled/disabled/focus/pressed appearance and motion from that profile.
No implicit platform default may define the app's screen design. Font/asset
identity and descriptor hash are part of the eventual installed native source/
dependency closure; missing or unsupported required token/asset fails closed.

The shared profile uses logical metrics with a documented density conversion,
explicit text scaling/accessibility behavior, stable layout rounding and declared
light/dark/RTL/localization states. Stage5's frozen UI-v1 packet stays unchanged;
there is no arbitrary style map or downloaded theme/font extension here. The
actual compiled common theme source and Apple mapping require 5T root review;
today's Apple semantic fonts/default Button and Android hardcoded mappings do
not establish it. Until that contract exists, positive signed visual acceptance
is pending. Do not silently invent an Android palette or call this a visual waiver.

Reference-screen acceptance compares iOS and Android screenshots side by side
for the same shared document/theme/content, logical viewport, text scale,
locale/RTL, light/dark mode and interaction state (normal/pressed/disabled/focus/
busy). Include geometry/hierarchy/spacing, text scale/wrap/truncation, colors,
assets/icons and state transitions/motion. Legitimate text shaping/font
rasterization/density/safe-area differences are recorded; they do not excuse
platform-default control appearance. Native VoiceOver/TalkBack, focus order,
back/predictive-back and native input/keyboard semantics remain. System status
bars, permission prompts, share sheets and keyboard keep their platform look.
Any app-screen platform variation must be explicitly authored, not inferred.
The specified final design-parity review requires physical iOS/Android evidence
and an accountable reviewer; phones are disconnected, so that gate is pending.
Host lifetime, declaration, emulator or screenshot-algorithm tests cannot pass it.

Each button uses a fixed static final listener with only immutable scalar
lifecycle/attachment/input/revision/generation plus privately copied 1..128-byte
node ID. It captures no packet/node/map/root/View/Activity/snapshot/exchange/Swift
owner or closure. Its sole native call is `nativeActivate`; payload is always
constructed in Swift as `UIEventEnvelope(..., .activate, .null)`. Current action ID
comes only from `snapshot.route`/the exact exchange; Java never supplies one.
Recheck full tuple, byte-exact ID, revision/generation, current snapshot and
exchange, stop/effects/busy state in the native Swift inner helper before `offer`.
Accepted input occupies the existing single slot. No JNI guest invocation, Task
creation, new queue, retry, replay or health shortcut occurs in the listener.

Every enable requires authored ancestor-enabled AND attached AND effects-confirmed
AND live AND no guest turn/event outstanding AND displayed==latest revision.
Java applies the authored disabled tree plus the fixed overlay; Swift rechecks
all exchange gates. Refresh updates overlay without applying the same revision
as a successor. A reentrant scalar close after Java apply forces the same leased
helper to disable/retire before returning.

## 7. Draw-return/later-frame observation

`SignedGuestDrawProbe` is one fixed weak probe per wrapper with one pending
`Choreographer.FrameCallback` maximum. It retains only a weak screen plus checked
scalars, no snapshot/exchange/ticket. No polling, timer, Handler or per-frame Task.
The opaque `GuestUIPresentationTicketV1` stays solely in Swift resources.

The final owned root's `dispatchDraw` calls `super.dispatchDraw` and records a
checked draw serial only after a nonempty real child draw. It does not notify JNI,
remove Views/listeners, run arbitrary callbacks or declare health in that stack.
A fixed root traversal marker and hardware/window checks distinguish the platform
draw path from a direct `draw/dispatchDraw` or Bitmap/RecordingCanvas call; an
OnDraw listener, if used as a traversal marker, supplies only before-draw scalar
context and is never treated as after-draw evidence or removed in its callback.
The private wrapper never calls `View.draw` manually. The frame callback runs
after that draw stack returned in a strictly later Choreographer display frame,
not in a nested loop: exact pending attachment/probe/draw serial and later frame
timestamp must match, and draw-depth must be zero. No public method can set or
serialize an eligible draw marker. The API30 real Window tests must establish
this schedule and reject manual/offscreen draws, including an attached root and
manually rendered hardware canvas; platform callback names alone are insufficient.

Before enabling the observation path, run the bounded
`draw_origin_marker_experiment` in a new API30 emulator-only fixture: one final
root, one fixed OnDraw traversal marker, one draw-depth/serial cell and one weak
Choreographer callback. Log actual platform traversal, dispatchDraw entry/return,
later-frame order and invalidation as scalars. Compare real Window rendering with
direct Bitmap draw, attached-root manual draw and manual hardware RecordingCanvas;
hold the real draw stack and attempt nested/same-frame dispatch. The experiment
creates no exchange receipt and calls no health/coordinator API. Root reviews its
observed marker mechanism before implementation can use it in `consumeObservation`.
If it fails, submit a bounded revised platform mechanism; do not weaken exclusion.

The trust model is the fixed reviewed Java/JNI/native source closure and actual
platform traversal under these observed schedules. This is not a defense against
hostile injected native code or reflection modifying private engine state, and
does not demand an unforgeable Android platform attestation. Guest code has no
such native/reflection authority. No compositor-pixel or human-perception claim
is made. The production marker must prove the contract's ordinary manual/offscreen
exclusion within that trusted closure.

At callback time a synchronous inner Java function promotes the weak screen,
checks eligibility and returns only scalar observation data; its strong screen
local ends before the outer fixed static JNI call. After the native call, the
frame callback's tail returns without another screen lookup/callback. JNI first
obtains the counted ingress. Inside `mxisi_observe`, Swift's fixed synchronous
native helper directly calls `mxis_native_observation_take`, which validates the
entry, promotes the exact weak wrapper and invokes cached `consumeObservation`
to consume that exact pending draw. Only after this actual fixed operation returns
can the helper privately construct native draw-return evidence and use its ticket.
No caller supplies an observation-success flag or a preconstructed witness.
That method rechecks actual Java main Looper, current tuple/frame and all of:

- Owning Activity is resumed, non-finishing and non-destroyed; root is still in its
  current actual Window and no close/pause/detach/root replacement intervened.
- Root attached, shown, window-visible, window-focused, positive laid-out size,
  nonempty child and nonempty clipped visible intersection; neither root nor its
  ancestor path hides it. No layout request is pending for this frame.
- Current probe/draw/frame serial and revision match the tree that drew; pending
  callback is one-shot. Revision change/pause/detach/close invalidates it.

Still inside the entry, Swift independently matches current native attachment/
probe, bound live exchange generation and **exact stored ticket's frameSerial and
revision**, effects confirmation, displayed snapshot and stop latch, then calls
only `exchange.observePresentation(ticket)`. Ticket may never arrive from Java.
Recheck after the Java call and before exchange observation to cover reentrant
close. No flag/status/diagnostic means first_screen or health; existing coordinator
alone consumes the receipt, requires all milestones/full interval and commits
health. A pending receipt may survive a newer same-attempt revision under existing
exchange rules; stopped/replaced attempts discard it.

If the actual public-platform traversal cannot reliably exclude manual hardware
draws or establish returned-stack ordering, **keep positive observation unavailable**
and return a typed unsupported/pending result until root separately reviews a
stronger platform proof. Do not relax the condition to make a test pass. This is
an explicit implementation proof gate, not an assertion that Java timestamps
establish draw provenance. Actual Window positive/negative regression remains
required; emulator results are not physical or compositor/human visibility proof.
Apply, resume, layout, manual/offscreen draw, same-frame callback and Java booleans
alone never call the coordinator's health path.

## 8. Resource graph, bounded JNI and failure transfer

| Retained storage | Bound and ownership |
| --- | --- |
| Process JNI metadata | One VM pointer, two class globals, fixed IDs, pthread and install scalars; deliberate process lifetime. No stored env. |
| JNI facade slots | Sixteen entries; one weak global per published facade, scalar state only otherwise. New weak local obligation counts before publication. |
| Swift records/resources | Accepted sixteen facade/endpoint/progress records and one reservation strong resource owner/facade; native proof types at trusted edges. Same maximum one setup/closing alias + one leased synchronous UI alias. |
| Java wrapper | One signed root/renderer/current packet and one weak Activity; root owns <=256 native widget records/listeners. No static wrapper registry. |
| Per-apply transient | One Swift encoded <=1MiB packet, one Java candidate plus existing current packet; bounded new widget candidate and old records during atomic validation/apply. No frame/packet survives a Swift suspension. |
| Draw probe | One weak probe, one pending frame callback, finite serials; stop invalidates/removes pending callback synchronously under cleanup lease. |
| JNI local scope | `PushLocalFrame(16)` for each fixed helper, explicit <=16 simultaneously live locals; loop-created locals deleted per iteration. Region copies, no pin/critical-array API. At most one packet array/helper; no native node-object traversal. |

After every fallible JNI call, test exception before another ordinary JNI action.
Record only finite failure code, clear exception in the fixed error boundary,
delete owned locals/weak obligations using allowed cleanup calls, and stop exact
exchange; no throwable object/global, stack trace or guest text retained. A failed
`PushLocalFrame`, allocation, method call or local promotion never means empty
success. Do not call Java cleanup with an exception pending; clear/classify first.
JNI teardown failure poisons/quarantines; uncertain resources remain counted.
No lock covers JNI calls or continuation resumes. Actual weak deletion, current
Java tree cleanup, entry leave, later callback fence, Task return, native reclaim
and final Swift destruction are separate ordered facts.

| Failure/schedule | Result and required ownership |
| --- | --- |
| Wrong pthread/Java Looper, API<30, absent VM/cache/class/method | Reject unavailable/wrong-thread before model admission; no Swift executor fallback. Install candidate globals locally cleaned; partial install remains unavailable. |
| Invalid/zero/overflow IDs, invalid byte region/UTF-8/subset | INVALID before event capture; malformed apply stops presentation and clears tree under lease. Source/UI validation alone authorizes no OTA. |
| Unknown facade/reference or stale attachment/input/probe/revision/generation | STALE/CLOSED as appropriate; no successor lookup/offer/observation, event sequence unchanged. |
| Busy entry / nested ALooper callback | BUSY; no pipe read/fence advance/resource lookup/retry wake. Existing registration stays; later nonreentrant callback handles coalesced byte. |
| Scalar close during apply/attach/observe | Close latch/revoke immediately, no JNI. Current helper postcheck retires/disables before leave; no health/input afterward. |
| Attach weak created, publication loses close/fails | Same-thread DeleteWeakGlobalRef before leave, exact abort; no receipt. Failed actual cleanup quarantines and pins. |
| Published weak missing / Java renderer or JNI exception | Failure/stop/quarantine; never reinterpret as never-attached or final cleaned. Preserve before/after-intent classification. |
| Final Java clear succeeded but weak deletion/slot/Swift postcheck uncertain | No cleanup evidence, no facade/destructor/capacity release; quarantine. |
| Final cleanup succeeds but callback/entry/Task/native fence stalled | Pending; no polling or timeout success, native owner stays counted. |
| Local fault before join / registry fault before reclaim | Join-admission addendum: deny the corresponding bookkeeping/reclaim; retain uncertain ownership. |
| Registry fault after actual endpoint reclaim | Preserve only immutable completed endpoint fact; facade/resources/obligation remain pinned. |
| Counter/capacity exhausted, terminal endpoint unavailable | Distinct exhausted/capacity or cleanupPending/quarantine. No wrap, retarget, retry-created Task or synthetic receipt. |
| Apply/resume/manual draw/Java flag or old frame | No observation/health; current exact ticket and verified platform draw+later frame still required. |

## 9. Executable verification inventory and proposal collector

`acceptance-matrix.json` contains executable **names and required runners**, exact
schedules/oracles, build modes and pending prerequisites. All native implementation
cases are pending; the runner paths are proposed files, not present executables.
A missing runner must remain pending/error, never zero-case success. Future runners
accept `--case NAME --mode MODE --output DIR`, build fresh actual sources and emit
one structured receipt for each case. Run `collect.py --plan` now to list the exact
commands without executing unavailable implementation. No `adb`, device discovery,
device run or reconnect request is made by this proposal or collector.

Proposal reproduction:

```sh
python3 verification/android-jni-stage5-contract/collect.py
python3 -O verification/android-jni-stage5-contract/collect.py
python3 verification/android-jni-stage5-contract/collect.py --plan
python3 -m unittest discover -s verification/android-jni-stage5-contract -p 'test_*.py'
```

The collector verifies locked exact source/API/spec-reference hashes, stage4
acceptance boundary, ordered complete matrix and ownership. It records argv/tool
versions, interpreter hash, HEAD/status observations, bounded input content digest,
output/result and its own hash. It does not infer source authority from HEAD,
pattern checks, a module guard or matrix structure. Spec inputs record official
URLs/anchors, fetched body hashes and access dates without copying platform
implementation; pages can change. `--check-network-specs` optionally re-fetches
the locked official pages and fails on drift instead of blessing a replacement.

Declaration compilation, parser JVM tests, real host JVM JNI/CheckJNI, Android
cross-compile/link, emulator actual main-Looper/native widgets/draw and signed
product integration receive distinct scope labels. A host JVM has no Android
Looper/Activity/Window. Debug/Release and available native sanitizers must rebuild
real sources; Swift/C TSAN support gaps are pending, not success. Test holds wrap
real operations; fault injectors may force only failure or hold actual state and
never fabricate Task-return, deletion, return fence or cleanup evidence. Include
ordinary and `@testable` negative constructor/conversion compilation, missing
native/host mixed module and missing-symbol strict-link failures.

Every implementation receipt must bind exact Swift/C/Java/SDK/toolchain/archive/
APK hashes and source manifests, execution environment, commands, output, mode,
case, observed counters, honest skips, and reviewer. Stale-delivery cases require
unchanged accepted-event/observation counters and real weak-slot/resource lifetime
assertions, not just returned STALE. S4-21 can close only its executed JNI subcase;
S4-29 needs its independently pending optimized Release injection. Final original
dynamic matrix, hosted pinned Swift6.2.4, positive visible-window, full native signed
integration, physical Android/iOS, immutable separate-repo published FieldLog,
signing/store/customer/operational and accountable GA evidence remain pending.
Shared-theme/metrics qualification and side-by-side physical iOS/Android design
parity are additionally pending under updated §8.3; no host acceptance covers them.

## 10. Official specification inputs and limits of inference

[JNI functions](https://docs.oracle.com/en/java/javase/17/docs/specs/jni/functions.html)
define weak promotion/deletion, local-reference frames and byte-region operations.
[Android JNI guidance](https://developer.android.com/ndk/guides/jni-tips) distinguishes
thread-local environments from the VM and modified UTF-8 from ordinary UTF-8.
The fixed cache/reference budgets and failure protocol above are Mixer design
requirements, not guarantees inferred from a successful status alone.

[Java Looper](https://developer.android.com/reference/android/os/Looper) and
[NDK Looper](https://developer.android.com/ndk/reference/group/looper) supply the
platform thread/FD primitives. The counted entries, later nonreentrant return
fences and source/type separation are Mixer's independently implemented proof
requirements, still requiring actual Android execution.

[ViewGroup.dispatchDraw](https://developer.android.com/reference/android/view/ViewGroup#dispatchDraw(android.graphics.Canvas))
describes child drawing, and
[Choreographer.FrameCallback](https://developer.android.com/reference/android/view/Choreographer.FrameCallback)
supplies subsequent frame callbacks. Neither API alone proves a visible screen.
[ViewTreeObserver](https://developer.android.com/reference/android/view/ViewTreeObserver)
also documents traversal callbacks and draw-listener restrictions. The exact
manual-draw exclusion and returned-stack proof are implementation gates; no API
name, diagnostic flag or class visibility is treated as a platform attestation.
