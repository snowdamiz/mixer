# Android public appearance routing prerequisite

Proposed next slice: export and lock the already accepted
`AuthoredToggleInputV2.java` in newly generated Android applications, and compile
the actual exported Java closure as a regression. This closes a concrete source
distribution gap before public V2 routing. This proposal performs source and
retained-evidence review only; no product code, compiler, native runtime, device,
capture or UI automation was executed.

The source inventory, exact hashes, excerpts, commands and review scope are in
[the review receipt](../verification/android-public-appearance-routing-proposal/receipt.json).
The selected input digest is defined in its source manifest. These are proposal
observations, not implementation acceptance or a release decision.

## Observed boundary

The [accepted authored integration](../verification/android-authored-toggle-integration/acceptance.json)
integrated exactly three Java sources and binds 89 product inputs to the private
API37 arm64 native candidate. Its 20-action coordinator matrix and 45-component
matrix are bounded private evidence. The integration receipt explicitly leaves
public routing, renderer lifecycle beyond fixtures, parity and TalkBack pending.

`NativeAppearanceViewsV2.java:602–614` now implements
`AuthoredToggleInputV2.CheckedBinding`, constructs the class and calls its geometry
routine. However, `AndroidProject.swift:32–49` explicitly exports thirteen Java
files without `AuthoredToggleInputV2.java`; `AndroidProjectTests.swift:13–16`
asserts that same incomplete set. The generated driver compiles only exported
adapter Java and app-owned Java (`android-build.py:280–283`). Thus the required
source is missing from a fresh generated adapter. This is a source-observed
closure defect; this proposal did not reproduce a compiler failure.

The exact accepted source SHA-256 is
`4b5f890ee7d3d7f4f4b17ba79bc8a44a8f26fa916e5ecd3c04a3c21fa98978fd`.
Its current bytes agree with the accepted integration binding. Copy these bytes;
no authored-input algorithm or native control change is needed for this slice.
The retained accepted compositional build binds its 5,119-byte top-level class
to `f71c191f2727295065092c9e072598a79647bdd8e9b85616bfea60468bed50df`;
all four authored class hashes are copied from the acceptance-bound
`host-1/fresh-artifacts.json` into this proposal's observations. That is retained
class evidence, not a fresh class compilation in this proposal.

## One bounded implementation assignment

| Owned file or directory | Concrete change |
| --- | --- |
| `cli/Sources/MixerBuild/AndroidProject.swift` | Add the exact accepted `app/src/dev/mixer/android/AuthoredToggleInputV2.java` to the explicit snapshot. It participates in the existing adapter digest and `mixer.lock`. |
| `cli/Tests/MixerBuildTests/AndroidProjectTests.swift` | Require the fourteen-file Java set and byte identity; add edit/remove/rename lock rejection for this newly required source. |
| `verification/android-authored-toggle-generated-export/**` | Fresh bounded collector, generated consumer and command/artifact receipts for the actual exported Java/D8 closure; retain failures and scratch cleanup. |

No new public configuration, UI wire field, JNI/C/Swift ABI, resource capability
or dependency is required. Keep the explicit export boundary: checklist engines,
instrumentation, host leaves and unrelated source remain outside generated apps.
The existing JNI exports, opaque token semantics and value-owned reducer contract
remain the prerequisites for a later join. Root owns coherent commits, pushes,
CI inspection and metadata updates after independent review.

## Executable verification available during the pause

Use a fresh isolated source snapshot with command argv, tool identities, source
hashes, complete outputs, class/DEX hashes and cleanup receipts. Do not replay an
old collector whose historical acceptance pins predate the authored integration.

1. Run the focused Swift snapshot/lock tests in Debug and Release. Require all
   fourteen exported Java files to match production bytes and the accepted input
   binding. Edit, remove and rename the new source independently; both CLI lock
   verification and the direct build-driver admission must reject drift before
   build output is created.
2. Build the CLI and use its actual `create --platform android` command to create
   a fresh application. Compile **only its exported Java closure** against the
   official SDK37 `android.jar`, using Java 17 bytecode, `-Xlint:all -Werror`, an
   empty source path and no repository/precompiled adapter classes on the class
   path. Require the authored class and its nested classes in output. A negative
   control that omits this one exported source must fail compilation for the
   missing authored type, without relying on string checks alone.
3. Convert that complete class output with official D8 `--min-api 28`; inspect
   the resulting DEX for the authored class and preserve exact source/class/DEX
   bindings. This establishes compilation and packaging only. The private V2
   runtime floor remains a separate API36 limitation.

The existing ordinary Swift registry/transaction tests and a full unsigned
generated Swift/JNI/APK cross-build are also permitted host/cross-build checks
if the implementation changes their inputs. They are not substitutes for the
exported-closure regression above. No such checks ran for this proposal.

## Public join contracts and explicit dependency gaps

Today `MixerActivity.java:12–15` creates the ordinary session and calls legacy
`exchange` → `UiPacket.decode` → `NativeRenderer.apply`, with event callbacks
returning through `exchange`. `AndroidProject.swift:133–139` emits that Activity
with minimum API28. Merely exporting the accepted source cannot change routing.

A later public join can reuse `NativeCoordinatorV2`: main-Looper ownership;
installed/environment capture; ordinary `prepareV2`; gated native attachment and
final validation; scalar commit immediately followed by native finish; publication
of the committed packet only afterward (`NativeCoordinatorV2.java:18–40,84–105`).
Known rejection requires confirmed abort and permitted cleanup; ambiguous
delivery/commit, failed cleanup and rejected native edits retire both owners
(`:110–142`). Environment refresh reuses the exact committed packet without a
new engine transaction (`:146–182`). Retirement closes forwarding, clears local
authority, then attempts renderer disposal and session destruction independently
(`:213–243`). The accepted authored source preserves these event/gate rules.
An Activity join must wait for a real attached, nonzero window and coordinate
refresh/retirement with its lifecycle; the private fixture is not a public owner.

| Missing dependency before a public switch | Required contract |
| --- | --- |
| Descriptor/theme packaging | `InstalledAppearanceV2.java:13,31–55` requires an installed `MixerAppearanceV2/descriptor.json`, bounded to 64KiB. The generator packages none and rejects all app resources (`AndroidProject.swift:103`). Define and lock ordinary generated appearance data using the shared theme by default; platform-specific appearance must be explicitly declared. |
| Resource/font support | The current capture rejects every nonempty resource catalog, even unused entries, and bundled fonts. Implement/qualify promised resource behavior or retain explicit unsupported errors; never silently substitute platform defaults. |
| Platform/environment coverage | `NativeEnvironmentV2.java:69–74,125–128` rejects API<36 and nondefault weight/high contrast. Preserve the product's proposed API28+ baseline subject to qualification, physical arm64 and supported emulator-architecture matrix (product plan §19.1). No baseline increase is selected, and D8 min28 is not runtime support. |
| Shared app document and lifecycle | V2 resolves the existing schema-1 packet plus a separate descriptor; it needs no invented packet appearance field. The Android starter uses stateful `document(state:revision:)`; generated iOS uses read-only `document(entries:)` and `MixerNativeView` (`ProjectGenerator.swift:117–141,209–213`). Coordinate shared content, interaction, native owner refresh, teardown and supported operations before claiming the same app design. |
| Public renderer qualification | Retain unsupported-operation rejection, revision/generation routing, disabled/gated event checks, authored input cancellation, retained editor rules and transaction ordering. No alternate renderer may reopen a retired presentation or treat source inclusion as installation authority. |

Product plan §8.3 remains binding: shared layout, hierarchy, content, colors,
typography scale, icons, spacing and component appearance by default; explicit
platform styling opt-in; native accessibility, navigation, text input and
system-owned surfaces. Legitimate shaping, rasterization, density and safe-area
differences remain allowed. Website Flick branding is not a replacement app
theme, and this prerequisite changes no brand or theme decision.

Public Activity execution, fresh actual JNI/native lifecycle and environment
refresh, pointer/keyboard/IME/scroll, TalkBack/focus/actions, compositor/resource
coverage and other OS profiles remain **pending** during the runtime pause.
Final physical iOS/Android side-by-side design review, the physical-phone matrix,
immutable external FieldLog consumption, signed presentation/health authority,
release and GA acceptance remain pending. A narrowly configured development
consumer cannot complete those product requirements.
