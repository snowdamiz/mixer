# Independent review result: private Android observer and source profile 2

The exact admitted candidate is suitable for acceptance as the selected private
development slice. No actionable implementation finding remains within that
scope. This is an independent review recommendation; root still owns acceptance,
integration metadata, delivery and CI. It does not qualify public V2, Android
runtime behavior, an OTA release or GA.

The observer is SHA-256
`814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac`;
the selected proposal is
`80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a`.
Root's [independent admission](../android-environment-observer-root-review/independent-candidate-admission.json)
binds the producer's frozen 946-member packet and this reviewer's separately
authored source seal. The context revision is the selection's
`4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d`, not a later commit claim.

## Independence and lifecycle behavior

The [preaccess plan](preaccess-plan.json), its document and read receipt were
sealed before candidate access. All 28 independent Android/renderer leaves,
the actual-observer assertion harness and runner were then authored and sealed
from that plan and the old source before any candidate content or producer test
content was read. No producer leaf was reused. The original 30 authored files
and all original seals remain unchanged in place.

The [successful independent host receipt](execution/host-attempt-2.json) compiles
the exact actual observer with those independent leaves using JDK 25.0.4.1,
`--release 17 -Xlint:all -Werror -proc:none`, explicit empty class/source paths,
stripped implicit JVM options and assertions enabled. It passes **287 cases and
24,363 assertions**. The controls cover all eight adds before/after acquisition,
prefix and uncertain cleanup, close/detach before and after acquisition including
resumed late acquisition, notifications during construction, first retirement,
all saved callbacks and wrong-thread entries, generation exhaustion, every
removal failure/reentry position, ordinary/fatal primary combinations, eight
simultaneous cleanup Errors, self/disabled suppression, exact stored/replaced/
dead VTO and resolver targets, and delayed removal with inert late callbacks.
The clean capture/current control also passes.

Source review agrees with those observations: attempted slots are recorded
before add; the active add is deferred during reentrant cleanup and unwound
after it settles; initialization blocks partial captures; retirement precedes
external work; cleanup consumes slots before removal and continues through
failures; exact targets are retained; cleanup states and failure arrays are
fixed at eight. Dead and failed targets remain uncertain, returned removal is
named `RETURNED`, and no actual reclamation is inferred. Suppression is best
effort after cleanup, while fatal acquisition/invalidation/cleanup Errors escape.
The private dedicated insets ownership restriction remains explicit. Public V1
Activity and its padding listener are unchanged.

The [first host attempt](execution/host-attempt-1.json) is deliberately retained
as failed. Its H04 oracle incorrectly demanded an empty modeled registry when a
remembered renderer Error was rethrown by reentrant close before the component
removal effect. Root reviewed and authorized the precise
[test-only correction](h04-amendment-seal.json): exactly that slot stays uncertain,
the other seven effects complete, all eight attempts occur, the original Error
escapes and terminal/no-retry assertions remain. Clean branches still require
an empty registry. Only this assertion branch and the versioned runner's
manifest filename changed in `host-v2/`; no producer source changed.

## Profile, actual consumers and compilation

The [fresh independent consumer/signature receipt](profile-signature-controls-3/receipt.json)
passes 22 recorded control families. Independent comparison with the sealed old
Swift literal finds the same exact **22 SDK + 20 adapter** member names. All SDK
identities, 19 adapter identities, descriptor and six wire fields are unchanged.
Only the observer identity changes. Profile ID is explicitly
`mixer.android-source-pair.2`; independent projection recomputation matches the
fixed literal. The rendered-driver source change is only its accepted ID literal;
no admission relaxation or automatic refresh was added.

An independently rebuilt actual Swift CLI created a fresh app under profile 2.
The actual rendered driver admits its exact source pair and descriptor. The
generated ordinary preset's three session tests pass. A separate app-owned
factory seeded a distinguishable draft and its app-owned reducer transformed
input to uppercase; an independent test observed that state and revision 1 to 2.
This is ordinary generated app code, not the repository checklist engine.

Both the actual CLI binary and actual rendered-driver process reject eleven
negative fixture families: old profile, ID-only old profile, missing or wrong-type
record, unknown profile field, same-size observer edit, recomputed generic lock,
edited SDK and descriptor with recomputed generic locks, a recomputed profile
projection and extra SDK source. Six rendered-policy failures reject before lock
read: unknown field, wrong schema type, old ID, wrong map count, duplicate key
and unrendered marker. Independent driver traps prove rejection before generic
tree hashing, tool inspection and output creation. Actual CLI diagnostics and
absence of output agree with its source ordering. No OS-level filesystem trace
of the CLI was collected; that stronger access observation is unverified.

The [first](profile-signature-controls-1/receipt.json) and
[second](profile-signature-controls-2/receipt.json) consumer attempts remain
failed, with their exact scripts, fixture tests and streams. The first assumed
revision 0/1 where the unchanged mapped `DocumentSession` contract specifies 1/2.
The second assumed a common diagnostic for a wrong-type record; the unchanged
Python entrypoint reports profile-required while the Swift decoder reports
profile-mismatch. Separately recorded oracle corrections preserve fail-closed
behavior and every negative control. These were independent test assumptions,
not producer defects.

The complete real 14-source adapter independently compiles against the pinned
Android API 37 SDK jar using Java 17 policy and independently passes D8
`--min-api 28`. Its **160 class files and DEX are byte-for-byte identical** to the
producer's retained output identities. The producer's actual generated app-owned
Swift 6.3.3 Android/NDK r27d JNI cross-compilation commands, full streams, source
bindings, arm64 ELF headers and exported app/JNI symbols were independently
audited; that expensive Swift/JNI compilation was not repeated. The producer's
two ELF identities are recorded in the machine-readable result.

The [post-qualification check](post-qualification-checks.json) verifies all 46
frozen proposal/source bindings, the original preaccess members, original and
amended source manifests and before/after tool hashes. Host Swift was Xcode
Apple Swift 6.4 through `/usr/bin/swift`; Android Swift 6.3.3 was used only for the
audited Android cross target. JDK was 25.0.4.1 with Java 17 target; D8 was
9.2.4-dev. Every owned child was reaped and every owned scratch directory was
removed, including failed attempts. Retained fixture source directories are
review evidence, not running instances or disposable compiler scratch.

## Remaining acceptance boundaries

No native simulator, emulator, phone, UI automation, capture, process inventory,
signing, installation, publication or credential operation ran in this review.
No prohibited frozen hosted catalog/authority/rejected-worker/broad harness was
imported or executed. There are no new dependencies or callback retries.

Host modeled leaves do not establish Android main-Looper/platform registration
or removal behavior. API-37 compilation and D8 min 28 do not establish API 28–35
support. Native runtime remains paused; physical phones remain pending without
requesting reconnection. Outer effect-runner fences, public V2 routing and inset
composition, unsupported accessibility/resources/fonts, saved-state continuity,
device/OS/performance coverage, separate-repository immutable FieldLog packages,
signing/store/customer/operational gates and accountable GA review remain pending.

This reviewer made no product-source, root metadata, commit or push changes.
Root may accept and deliver the selected private slice using this evidence while
preserving every pending runtime/public/GA boundary.
