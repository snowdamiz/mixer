# Android default shared appearance packaging proposal

Proposed next development slice: create one canonical shared V2 appearance
descriptor with the existing qualified SDK API, include it in the generated
Android adapter's immutable source snapshot, and package its exact bytes as
`assets/MixerAppearanceV2/descriptor.json` in the unsigned APK. This makes the
installed asset available for a future public V2 owner. Public Activity routing
continues through V1; this proposal authorizes no rendering or release switch.

This is a frozen proposal, with source review and a small host experiment only.
The [probe receipt](../verification/android-default-appearance-packaging-proposal/probe-2/receipt.json)
records commands, tool versions, outputs, source inputs, artifacts and cleanup.
The [source manifest](../verification/android-default-appearance-packaging-proposal/probe-2/source-manifest.json)
binds revision `05c1ebf0378fb479ba8595d71cde577f447d0025` plus the observed working
tree. Root subsequently accepted and delivered the authored-toggle export repair
as `99d6384306ea17643b70c472f93b57418c674f86`; its two product inputs have the exact
same hashes in this proposal. That HEAD change is delivery context, not a fresh
native or public-routing receipt.
Its selected-input tree digest is
`db76c0597ef9ae365b35ad6df52dfb6f94cc0ae52acd5063c6a2f667279dfb35`.
The [numbered excerpts](../verification/android-default-appearance-packaging-proposal/source-excerpts.txt)
and retained source copies make the source observations reviewable. This digest
describes only the selected inputs; it is not the whole repository or an immutable
build attestation. No product files changed in this proposal.

## Observed contracts

`UIAppearanceDescriptorCodecV2.mixerDefaultV2()` already returns the SDK's canonical
configuration (`sdk/Sources/MixerUI/AppearanceDefaultV2.swift:6–10`). Encode it with
`UIAppearanceDescriptorCodecV2.canonicalData(_:)`, rather than `JSONEncoder`, a
copied theme table, Java defaults, or text extraction. The closed codec admits
1–65,536 bytes, validates shape and semantics, and requires exact canonical bytes
(`AppearanceDescriptorV2.swift:3–34`). Its comments explicitly deny native,
installed, presentation, health and release authority.

Fresh host execution of the snapshotted SDK confirms:

- ID `mixer.measured-candidate.v2`, format `mixer.native-appearance.2`, mode
  `shared`, no resources and `systemSans` typography. Keep the accepted ID and
  theme values; this is no new brand or theme selection.
- Exactly 9,587 canonical bytes, SHA-256
  `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`, equal to the
  retained V2 golden descriptor. Swift decode/encode round-trips those bytes.
- The actual pure Java `AppearanceDescriptorV2` and `AppearanceGeometryV2`
  sources compile with `--release 17 -Xlint:all -Werror -implicit:none` and an
  empty source path. Host decode selects one shared theme for both platforms,
  preserves the empty catalog/system font, and rejects an appended space as
  noncanonical. No Android framework, installed capture, JNI or renderer ran.

The wire model already distinguishes `.shared(UIThemeV2)` from
`.platformSpecific(iOS:android:reason:)`
(`AppearanceValuesV2.swift:5–9`). The codec requires the complete two themes and
reason only for explicit platform mode, and does not permit a shared `theme`
field in that mode (`AppearanceDescriptorV2.swift:879–909`). The existing explicit
platform test exercises distinct themes and rejects missing/blank reasons
(`sdk/Tests/MixerUITests/AppearanceDescriptorV2Tests.swift:188–204`). These are data
contracts, not proof of a public configuration path or platform support.

`InstalledAppearanceV2.capture` reads
`context.getAssets().open("MixerAppearanceV2/descriptor.json", ACCESS_STREAMING)`
on the main thread; bounds the stream while reading; decodes both full themes
and the whole resource catalog; and rejects every nonempty catalog or bundled
font. Its private constructor captures bytes, SHA-256 and identity-owned native
provenance (`native/android/app/src/dev/mixer/android/InstalledAppearanceV2.java:11–60`).
App-supplied configuration or packaging a source file cannot construct that owner.

The current generator writes an explicit fourteen-Java source closure, reusable
Swift runtime and driver, then hashes the whole `Generated/MixerAndroid` tree.
It creates no descriptor (`AndroidProject.swift:27–77`). The SDK is a separate
snapshot under `Generated/MixerSDK`; `mixer.lock` records both SDK and adapter
tree digests (`ProjectGenerator.swift:26–49,242–251`). The CLI's `MixerBuild`
target currently depends on `MixerCore` and `MixerUpdates`, not `MixerUI`
(`cli/Package.swift:11–14`).

Both CLI and direct-driver admission reject app resources. The driver verifies
source locks before creating `.mixer` output; later AAPT2 linking includes no
asset directory. ZIP augmentation adds native libraries and DEX only
(`AndroidProject.swift:97–105`; `android-build.py:207–231,280–294`). The driver
already records per-entry content hashes and checks the source tree again after
packaging, but this is local before/after observation, not a stable-input sandbox
(`android-build.py:306–328`).

The installed official AAPT2 help states that `-A` includes an unprocessed assets
directory. A fresh synthetic AAPT2 link with that flag produced exactly one
`assets/MixerAppearanceV2/descriptor.json` entry with the canonical hash above.
This 2,729-byte container has only a synthetic manifest, resource table and
descriptor. It has no classes or native library, and is not a generated app.
The source-observed missing connection is therefore independently implementable;
actual generated-app packaging still requires the verification below.

## Proposed implementation ownership

One owner makes the following coherent slice on the accepted authored-toggle
export repair. Do not edit its frozen producer/reviewer packet.

| Owned file or directory | Smallest concrete change |
| --- | --- |
| `cli/Package.swift` | Add the existing first-party `MixerUI` product to `MixerBuild`'s dependencies. No third-party dependency is needed. |
| `cli/Sources/MixerBuild/AndroidAppearance.swift` (new) | Own the copied-SDK default compatibility check described below. Use the established codec API in both producers and invoke only the packaged bounded helper. Return only validated exact canonical bytes and preserve separate bounded diagnostics on failure. |
| `cli/Sources/MixerBuild/Resources/android-appearance.py` (new) | Own one isolated host emitter package, compiler/executable subprocess groups, explicit deadlines/output limits, and cleanup described below. This uses Python's standard library and the already-required host Swift compiler; it does not change the general process runner or invoke the Android builder. |
| `cli/Sources/MixerBuild/ProjectGenerator.swift` | After copying/hashing the SDK and before publishing the staged Android project, execute that compatibility check; abort on failure. Pass the approved descriptor bytes to the adapter snapshot. No iOS generation change is needed. |
| `cli/Sources/MixerBuild/AndroidProject.swift` | Import `MixerUI`; at adapter snapshot creation call `canonicalData(try mixerDefaultV2())`, require the expected shared/empty-catalog/system-sans configuration, and write the bytes to `app/assets/MixerAppearanceV2/descriptor.json` before the existing adapter-tree digest is returned. Keep the explicit Java source closure and V1 Activity. |
| `cli/Sources/MixerBuild/Resources/android-build.py` | Before output/tool execution, require the one supported regular, bounded descriptor asset and no other asset-tree entries or symlinks. Include `-A Generated/MixerAndroid/app/assets` in AAPT2 linking. After alignment require exactly one matching ZIP member and byte equality with the locked input; include its identity in the existing build receipt. Keep pre/post source-lock checks. |
| `cli/Tests/MixerBuildTests/AndroidProjectTests.swift` | Add exact canonical asset/snapshot checks and descriptor drift/refusal cases; retain the fourteen-source closure and authored-toggle tests. Add a bounded focused driver asset-preflight test where needed. |
| `cli/Tests/MixerBuildTests/AndroidAppearanceTests.swift` (new) | Exercise copied-SDK default compatibility, compiler/API rejection, distinct valid default rejection, staging cleanup and final-destination absence on failed creation. |
| `verification/android-default-appearance-packaging/**` | New isolated implementation collector and receipts for the actual CLI-created app, host tests, full unsigned cross-build and archive checks; preserve failures and cleanup. |

Public config schema, `mixer.lock` schema, SDK default table/codec, Java/native
implementations, JNI/C/Swift ABI, UI packet fields and
Activity lifecycle need no change for this development packaging slice. The
descriptor belongs to the locked engine-generated adapter tree; it is not a
special exception allowing arbitrary files under app-owned `Resources`.
The complete asset-path inventory must include hidden/skipped-extension names
when enforcing the one-asset limit; the source-digest exclusion list must not
silently admit undeclared assets. Missing, empty, oversized, directory, renamed,
symlinked or additional assets fail before `.mixer` output is created.

The descriptor producer is the qualified SDK linked into the CLI. `--sdk-path`
separately selects the copied SDK; the two existing locks do not establish
semantic equivalence between arbitrary distributions. The smallest complete
descriptor-compatibility gate is therefore part of the proposed slice:

1. Within the unpublished creation staging directory, create a temporary host
   executable package with the copied `Generated/MixerSDK` as a local dependency
   and `MixerUI` as its sole SDK product. Its own emitter calls
   `canonicalData(try mixerDefaultV2())` and writes a bounded result file. Use
   explicit argv and an isolated scratch path with `-j 2`; do not scrape SDK
   source or read a verification fixture as the product input.
2. Require successful compiler/API execution, a regular nonsymlink result of
   1–65,536 bytes, successful CLI-linked codec decode, shared mode, no catalog
   entries, system sans, and byte equality with the CLI-linked canonical default.
   Recheck the SDK source digest before accepting the result. Missing APIs,
   failed compilation, invalid shape or unequal bytes fail with an explicit
   creation compatibility error before a project is published. Delete the helper
   and its build outputs on every path; never put them in either locked tree.
3. Only then copy those equal canonical bytes into the adapter asset and record
   its enclosing `adapterDigest`. Build admission checks both SDK and adapter
   digests before output, and final archive inspection checks those asset bytes.
   Keep this local observed-mutation scope explicit; it is not a signed lock or
   an immutable sandbox.

The helper must implement its own operation boundary. The current general
`ProcessRunner.run` waits indefinitely and merges stdout/stderr; do not use that
behavior as a timeout or diagnostic-separation claim. Resolve one host Swift
executable, bind its version/path/hash, and require the expected creation-time
host version. Allow 60 seconds for the emitter build, five seconds for
`--show-bin-path`, five seconds for the emitter execution, and 75 seconds total.
Each operation starts one owned process group. Spool stdout and stderr separately
with a 1MiB limit each; reaching either limit rejects the operation. Keep the
canonical result in a separate regular nonsymlink file, admit its size before
reading at most 65,537 bytes, and reject a limit violation. Do not interpret
compiler diagnostics as descriptor data.

On timeout, output overflow, cancellation or any failure, terminate the owned
group with SIGTERM, allow two seconds, use SIGKILL if needed, and reap the child
within two more seconds. On success also confirm no owned group remains; a
remaining child, cleanup failure, truncated diagnostics or ambiguous result is a
failed creation. The helper's final structured result contains separately named
bounded diagnostic values before removing scratch; tests retain the raw streams
and commands in their receipt. The Swift caller must also put a 90-second
watchdog around the packaged helper and own its outer process group; cancellation
must reach that group and the active compiler group. Keep these narrowly scoped
operations in the new appearance helper files rather than broad changes to
`ProcessRunner.swift`. No host-source evaluator is a hostile-code sandbox or
provenance authority. Tests must exercise the deadline and child cleanup paths
with owned synthetic children before this helper is accepted.

This extra host probe costs a local compile during Android project creation;
it avoids pretending a version label or fixture hash proves agreement between
the selected SDK and CLI. It proves descriptor-default compatibility only.
General mixed-version SDK/ABI compatibility and published distribution
qualification remain separate requirements before public routing. No source
fingerprint approximation, fallback default or warning-only bypass is selected.
If that isolated helper cannot be justified or implemented within this slice,
the explicit alternative is compatibility rejection: refuse default-descriptor
Android creation when the supplied SDK's API output cannot be verified, keep
packaging/public routing pending, and propose a separately reviewed compatible
distribution admission mechanism. Do not silently omit the comparison or claim
that a version string or host verification run proves it for all user SDK paths.

No public theme override is introduced here. A subsequent authored-appearance
configuration slice must expose explicit platform-specific opt-in using the
existing mode and reason contract; it must never infer opt-in from the OS or
manifest's Android window theme. A default-only descriptor packager cannot be
reported as completion of custom themes, resources or fonts.

## Executable implementation acceptance during the pause

Use a fresh snapshot, two host build jobs, bounded owned children and isolated
scratch. Capture exact argv, all stdout/stderr, tools, source trees and artifacts.
These commands/checks are proposed acceptance; they have not run against a
product implementation in this proposal.

1. Run focused CLI Swift tests in Debug and Release, for example
   `swift test --package-path cli --scratch-path <owned>/cli-debug -j 2 --filter android`
   and the corresponding `-c release` command. Require exact canonical asset bytes
   and its contribution to `adapterDigest`. Keep source/bridge byte identity and
   the existing authored-toggle omission/drift regressions green. SDK codec tests
   remain the canonical schema/explicit-platform coverage; do not replace them
   with Python JSON or regex authorization.
2. Independently edit, remove, rename and symlink the descriptor, and add a second
   asset. With the original lock, both CLI lock admission and copied direct driver
   must reject each mutation before `.mixer` output. Separately test preflight
   failures for invalid asset shape/size with a synthetic recomputed local lock;
   those tests prove explicit packaging limits, not lock authenticity. Keep app
   resource rejection in both entry points and cover undeclared files whose
   names the general source digest normally excludes.
   Run the new creation-compatibility tests against the copied real SDK, a
   copied SDK with a different valid canonical default, and a copied SDK missing
   the required API. The latter two must fail without publishing the destination
   or retaining helper scratch. These are executable creation errors, not only
   verification-packet comparisons.
   Exercise oversized/missing/symlinked result files, stdout/stderr overflow,
   compiler/emitter timeout, cancellation and a spawned child; verify the owned
   groups are retired and diagnostic channels remain distinct.
3. Build the actual CLI and create a fresh Android consumer with the selected
   qualified SDK and adapter. Require all fourteen exported Java sources plus
   the one exact asset. Run the default codec from the copied SDK and compare
   bytes with the packaged input. Preserve exact producer/copied-SDK bindings.
4. Invoke the actual generated build driver for the complete unsigned
   Swift/JNI/Java/D8/AAPT2/zipalign cross-build. Inspect the final archive, require
   exactly one descriptor member, exact byte count/SHA-256, and equality with
   the source-lock-bound asset. Preserve the existing library, symbol, DEX,
   application, ABI and alignment checks. Record before/after source digests,
   every APK entry and the receipt. A synthetic AAPT2 archive is insufficient.
5. Decode bytes extracted from that actual APK with the production pure Java
   codec and Swift codec. Confirm shared mode, the same complete theme, the empty
   resource catalog and system sans font; preserve a noncanonical negative
   control. Do not invoke installed capture or native runtime tests while paused.
   Clean all owned scratch and record child completion.

## Product and qualification boundaries

Product §8.3 still requires the same app design across iOS/Android by default:
shared layout, hierarchy, content, colors, typography scale, iconography, spacing
and component appearance; explicit platform styling opt-in; native accessibility,
navigation, text input and system-owned surfaces. Genuine text shaping,
rasterization, density and safe-area differences are allowed. No website branding
decision is part of this slice, and the generated iOS starter is not made into a
shared V2 consumer by shipping an Android asset.

Preserve both existing `android.unsupported-resources` / direct-driver resource
refusals and installed-capture nonempty-catalog/bundled-font rejection. The
product's promised bundled/remote assets, fonts, resource validation and
appearance customization remain required later capabilities; do not silently
drop them, substitute platform defaults, or mark them unsupported permanently.

`MixerActivity.java:12–15` still uses `exchange` → `UiPacket.decode` → legacy
`NativeRenderer.apply`. A public switch separately needs the native coordinator's
installed capture, environment/lifecycle ownership, prepare/commit/finish order,
gated event forwarding, rejection cleanup and retirement contracts described in
the [routing proposal](android-public-appearance-routing-proposal.md).
Source and asset inclusion alone cannot authorize that switch or an OTA update.

Android API28+ remains the proposed product baseline (§19.1), subject to toolchain
and device qualification. Private `NativeEnvironmentV2` currently rejects API<36
and unsupported weight/high-contrast conditions (`NativeEnvironmentV2.java:67–74,121–130`).
AAPT2/DEX min28 packaging does not close that API36 runtime gap or select a raised
baseline.

Public native interaction, lifecycle/environment refresh, pointer/keyboard/IME/
scroll, TalkBack/focus/actions, resource/compositor coverage and further OS
profiles remain pending during the computer-use/capture/native-runtime pause.
Phones remain disconnected. Final physical-phone acceptance, side-by-side
iOS/Android design parity, immutable published SDK consumption by FieldLog from
a separate repository, signed installed presentation/health authority, release
and GA acceptance remain pending. No GA gate is promoted by this proposal.

## Proposal execution scope

The bounded experiment used Apple Swift 6.4 on arm64 macOS, OpenJDK 25.0.4.1
emitting Java17 bytecode, and official Android build-tools37 AAPT2
`2.20-15087165`. Its custom host package copied only MixerCore/MixerUI source;
its Java closure comprised the two pure production sources and one local probe.
The [first attempt](../verification/android-default-appearance-packaging-proposal/probe-1/receipt.json)
stopped because AAPT2 help returns exit1; the help text and failed receipt are
retained. The second attempt accepts that documented observation only for the
help command; every compile, execution and link command exited zero.
Both attempts removed owned scratch and left no background jobs. No broad
collector, hosted catalog/authority driver/rejectedWorkerV2 code, native runtime,
capture, UI automation, device/process discovery, install, signing, publication,
commit or push ran in this lane.
