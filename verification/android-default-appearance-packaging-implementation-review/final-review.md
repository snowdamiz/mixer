# Independent implementation review result

Recommendation: **accept the selected development data/packaging slice** for
the exact six implementation files in root's selection. No actionable product
finding remains. This is not public V2, SDK compatibility, native runtime,
signed authority, release or GA acceptance.

The [preaccess review plan](../../docs/android-default-appearance-packaging-implementation-review.md)
and its 50-vector matrix were frozen before reading the implementation. They
remain unchanged. Final observations are recorded here rather than altering
that baseline. The [final acceptance receipt](acceptance.json) and final seal
bind the exact source, retained failures, command streams and artifacts.

## Source and ownership

The reviewed producer handoff is
`ddbaabec45eaac4fc8862bec0011f518167919a8032842cb19769e9cd5e76f1d`, with seal
`e7b005b12e6534db0c32ce213e52b2a20c5313ef744bae0411b6344b6a80941f`.
All 102 producer packet members and seven owned external files were verified.
The source archive has 241 files, SHA-256
`2f6268251008747bcb60dbacba44d8d8a7dfb30f7b3b55d8c1caa4e16d9e70c5`.
Its independent selected-source digest is
`2d3058772475493328a86abd8f4417aae87cf517337184e615da8344b5ca5aed`.

An independent comparison with Git
`99d6384306ea17643b70c472f93b57418c674f86` found exactly the six selected
CLI/package/test changes. Native Java/JNI/Swift runtime, public V1 Activity,
SDK, updates, ProjectGenerator and ProcessRunner bytes are unchanged. The
first-party MixerUI dependency is the only dependency change. Historical
accepted source is bound to Git and copied bytes; current product edits are
not misreported as drift in an earlier export receipt.

The implementation has one CLI-linked canonical producer. It obtains the
existing default through the real MixerUI API, encodes once, decodes with the
real closed codec, checks shared mode/empty resources/system sans, and writes
those exact bytes before calculating the adapter digest. It introduces no
table, theme, emitter, watchdog, copied-SDK compile gate or new public schema.

## Executed evidence

The [independent execution receipt](independent-run-3/receipt.json) maps every
frozen vector to its executed result. Evidence supports the contracts below,
not acceptance by a test count alone.

- The 42 adversarial host vectors exercised complete asset inventories,
  hidden/skipped names, redirected paths, special files, empty/oversized/sparse
  files, admission before hashing/tools/output, existing source locks and app
  resource refusal, layout-only recomputed-lock behavior, and final ZIP
  missing/extra/renamed/duplicate/wrong-byte controls.
- The exact-source 20-method Python suite passed independently. Every existing
  staging containment assertion is retained; its fixture only gains the minimum
  valid asset and corresponding digest. The producer's exact-source focused
  Swift Debug/Release outputs were hash-checked and reviewed rather than rerun.
  The new canonical snapshot and lock assertions execute there. Independently,
  the actual CLI was freshly built and used for the consumer below.
- Actual creation produced the exact fourteen-Java closure and source-locked
  descriptor. Existing-destination refusal preserved its sentinel. iOS-only
  creation emitted no Android adapter/asset. A create-only copied SDK fixture
  deliberately missing `mixerDefaultV2()` still created the same CLI-owned
  descriptor; that fixture establishes the selected provenance boundary and is
  not used for the qualified consumer cross-build.
- A fresh actual CLI-created project completed the generated unsigned
  Swift/JNI/Java/D8/AAPT2/zipalign build. The final aligned APK's entire asset
  inventory is one `assets/MixerAppearanceV2/descriptor.json`, with multiplicity
  one and exact admitted bytes. All 160 newly compiled Java class hashes equal
  the frozen producer class evidence. Generated sources and the 241-file build
  source closure were unchanged across execution.
- Actual CLI descriptor/Java edit, remove/rename and SDK drift controls returned
  the specific `lock.android-drift` / `lock.sdk-drift` failures. Ordinary,
  hidden and excluded-extension app resources were refused through the actual
  CLI. All those failures preserved the preceding unsigned APK and receipt.
- The extracted final descriptor was freshly decoded with production pure
  Java class bytes and the real Swift codec built from this consumer's copied
  MixerCore/MixerUI sources. Fresh API-derived canonical bytes equal the
  extracted asset. Both codecs rejected an appended-space noncanonical control.
  No installed capture or native runtime was invoked.

The independent 22-member APK contains **28,028,969 bytes**, SHA-256
`f700ab410f1d2e3ac90a4e64ca205560748af057906d7df38f035f4af55a370a`.
Its descriptor contains **9,587 bytes**, SHA-256
`1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
The APK differs from the producer's separate build; no whole-APK reproducibility
claim is selected. Both builds bind the same descriptor and production classes.

## Failures and operational scope

Two review collector setup attempts stopped before any product build: resolving
the official Swift launcher to `swift-driver` changed its required invocation
name; a standalone D8 version probe lacked the configured JDK environment.
Both failed command streams, original collector copies and cleanup receipts
remain retained. The corrected run preserves launcher invocation separately
from its resolved identity and uses the configured JDK. Completed source-identical
host evidence was reused. No product test or build failure was observed.

All collector-owned command groups were gone before removing owned scratch.
Temporary adversarial fixtures were closed, including failed paths. No native,
capture or other project's process was started or stopped. No general process,
device, simulator or doctor discovery ran. No producer collector or forbidden
hosted inspector/authority/WorkerV2/broad harness was imported or executed.
Only this review document and verification namespace were written.

## Required pending boundaries

Python direct-driver admission proves complete layout, ordinary file/type/size,
local lock identity and exact archive bytes. An intentionally recomputed local
lock can carry bounded nonsemantic bytes; that is neither real codec admission
nor authentic default provenance. Local source/asset rechecks remain before/after
observations and provide no race-free sandbox or signed attestation.

Copied `--sdk-path` default/API/ABI and published distribution compatibility
remain prerequisites before public V2. Public V1 is unchanged. Installed V2
capture, environment/lifecycle join, API28–35 support versus the private API36
gap, custom/platform-specific appearance, resources/fonts, native interaction,
TalkBack/design parity, physical-phone matrix, external immutable published
FieldLog consumption, signing/OTA/health/store/release/operational and GA
qualification all remain pending. The runtime/capture pause and disconnected
phone constraints remain in force.
