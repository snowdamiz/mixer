# Android copied SDK and appearance compatibility proposal

Propose one exact first-party **source-pair profile** for newly generated Android
development projects before considering public V2 routing. The CLI should reject
unreviewed MixerCore/MixerUI and exported Android source combinations. Keep the
descriptor producer selected in the [root decision](../verification/android-default-appearance-packaging-root-review/implementation-selection.json):
the CLI-linked `MixerUI` produces the one canonical asset. No copied-SDK executable,
emitter, process supervisor, copied default table, runtime negotiation or public
Activity switch is needed for this proposal.

This is a contract proposal for root selection, not an implementation assignment
already accepted. The current packaging implementation is frozen awaiting its
independent review; its `handoff.json` still says `implementation_accepted: false`.
The broader helper/supervisor proposal was not selected. This document does not
revive it. Product plan §§8.3, 11.1, 16.1 and 19.3 remain binding, including shared
design, independent versioning, exact installed runtime fingerprints and immutable
distribution qualification.

The [source-only packet](../verification/android-copied-sdk-appearance-contract/receipt.json)
retains 65 named inputs, their complete bytes, command argv, raw outputs, tool
versions and before/after identities. Its proposed compatibility projection has
22 SDK files and 20 adapter files. All 42 currently match their identities in the
sealed packaging run's source manifest. The [observed profile](../verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json)
records the maps and digest recipe; it is evidence data, never product authority.

## Current contract and concrete gaps

| Boundary | Source-observed behavior | Remaining gap |
| --- | --- | --- |
| SDK selection | `cli/Sources/MixerCLI/main.swift:81` chooses explicit `--sdk-path`, then `MIXER_SDK_PATH`, then the checkout SDK. The argument applies to `create`, including iOS-only creation. | No published supported SDK version/range or first-party compatibility admission. |
| Copy and publication | `ProjectGenerator.swift:22–39` requires `Package.swift` to exist, resolves the SDK root, copies the `SourceDigest.files` projection into private staging and hashes that copy. Only successful construction moves the project to its final destination (`:64–65`). It does not evaluate the selected manifest or type-check the selected SDK during creation. | An SDK with a missing public API, a changed default or a changed encoder can be copied and locked. A matching filename is sufficient for the initial package check. |
| SDK lock | `Configuration.swift:68–78` records `sdkDigest`, `sdkDistribution: bundled-source-snapshot`, host Swift version and `local-development-only`. `ProjectGenerator.swift:240–250` rehashes the copy and checks the local lock/compiler. | The lock records the selected bytes. It neither identifies which SDK was linked into the CLI nor proves the selected bytes compatible with it. Recomputed local locks are unauthenticated. |
| CLI-owned asset | `AndroidProject.swift:80–91` uses the linked `UIAppearanceDescriptorCodecV2.mixerDefaultV2`, `canonicalData` and typed `decode`; it requires exact round-trip, shared mode, no resources and system sans. Snapshot writes it before computing the adapter digest (`:73–77`). | This validates the CLI-linked producer only. It executes no API or semantics from `Generated/MixerSDK`. |
| Native Swift API | The generated packages use the copied `MixerUI` and `MixerCore` (`AndroidProject.swift:129–146`). `DocumentSession.swift:16–54` depends on `UIReconciler`, `RoutedUIAction`, `UIDocument`, event decoding and `encodeNativePacketV1`. | Default JSON equality does not prove these APIs exist, have the same types or retain the same behavior. Ordinary actual compilation can reject missing/incompatible types; successful compilation alone does not prove semantic equivalence. |
| Java wire | `UiPacket.java:16–25` requires packet schema 1 and document schema 1, with exact fields and identity coverage. `AppearanceDescriptorV2.java:16,112–135` separately requires `mixer.native-appearance.2` and the closed `measuredShared2` recipe. There is no appearance field in the schema-1 UI packet. | No generation admission joins the copied SDK's producer implementation to these independently selected Java decoders. Schema numbers alone permit incompatible behavior within a version. The Java decoders fail closed on unsupported actual input when called. |
| Native bridge | The selected closure includes C headers/JNI, `NativeBridge` and the Swift runtime. `mixer_android_v2.h:10–11` explicitly says its staged API is private and not a stable public ABI. | Symbol existence, matching JSON or equal header filenames cannot establish calling convention, token/lifetime/transaction semantics, exception behavior or a stable public ABI. These need their own versioned contract and target evidence before public promotion. |
| Build and archive | `android-build.py:251–278` admits the asset, checks SDK/adapter locks, then creates output and inventories tools. It cross-compiles the actual app, links JNI with `--no-undefined`, compiles Java and D8, and checks ELF, symbols, DEX and final asset bytes (`:289–375`). | These mechanisms reject concrete compilation/link/package failures. They do not turn local locks into an SDK support policy, validate arbitrary SDK semantics or authenticate a published distribution. |

The frozen asset is 9,587 bytes, SHA-256
`1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
The packet binds the selected sealed Swift and Java codec output logs. Their
earlier equality observation applies to that copied SDK and those exact inputs;
this proposal did not rerun either codec or a compiler. Installed capture will
still read and type-check the bounded asset itself (`InstalledAppearanceV2.java:31–56`)
when a later lifecycle owner is implemented. Public `MixerActivity` still uses V1.

## Recommended admission contract

Use an internal, compiled `MixerBuild` profile, provisionally named
`mixer.android-source-pair.1`. It accepts one reviewed source pair and records
separate SDK source, adapter source and default-data identities. An equality
result means **matched reviewed implementation within its recorded test scope**.
It does not mean a stable binary ABI, supported OS matrix, signed authority or
published-package authenticity. Do not introduce a public SDK SemVer/range claim
in this development slice.

The source profile must be compiled into the CLI from a committed internal Swift
value. It must not be learned from `--sdk-path`, environment variables,
`mixer.lock`, mutable verification output, a bundle JSON file, source comments or
a self-declared version in the selected SDK. The implementation should expose no
override, wildcard, range or allow-unknown switch for this profile.

| Profile member | Exact selection and rationale |
| --- | --- |
| SDK compatibility map | Exact `Package.swift` plus the complete recursive files/directories beneath `Sources/MixerCore` and `Sources/MixerUI`. Every file must have an explicitly pinned, case-sensitive relative path, expected byte length and SHA-256; only the pinned `.swift` files are admitted. Include the manifest because it fixes target paths and dependencies. Current manifest has no external package dependency and makes MixerUI depend on MixerCore. A different manifest fails, even if it declares the same products. |
| Adapter compatibility map | The exact fourteen exported Java sources, `bridge/jni.c`, both C headers, `contracts/android-profile-v1.json`, and complete `engine/Sources/MixerAndroidRuntime` Swift inventory. These are the 20 inputs already selected by `AndroidProject.snapshot`. Use exported destination paths as the logical map labels: input `engine/Sources/MixerAndroidRuntime/...` maps to generated `Sources/MixerAndroidRuntime/...`; other paths pass through. Pin source bytes, not only filenames or symbols. The CLI-generated runtime package, driver and app entry remain separately bound to the exact CLI implementation and full adapter lock. |
| Default data | Exact byte count and SHA-256 of the current CLI-produced descriptor. Produce and type-check it through the existing producer once; require its identity to match the compiled profile before writing it. The profile contains no substitute theme table or descriptor bytes. |
| Wire declarations | Record UI document 1, native packet 1, `mixer.native-appearance.2`, `measuredShared2`, `mixer-android-native-v1-development`, and explicit private staged C/JNI status. These are diagnostic dimensions of this source pair, not negotiated compatibility or a replacement for source admission. |

Use the existing digest construction on the admitted relative paths:
SHA-256 over sorted `path + NUL + lowercase-file-SHA256 + LF` records. Compare
the complete path/length/hash maps as well as their digest. Under this recipe the
observed SDK projection is
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`;
the observed adapter projection is
`05cd1c21b598d4b610ab19e10679982aabe618d62eb5784ef723777e1754c5fa`.
These are proposal observations at revision
`99d6384306ea17643b70c472f93b57418c674f86`, not new production constants to adopt
without root selection and the independent packaging review.

Choose this compatibility closure deliberately rather than the whole copied SDK:
the current whole-SDK digest also includes unrelated targets, tests, documentation
and `sdk/verification` logs. Changes there should not purport to change the Android
Core/UI contract. The existing whole `sdkDigest` remains in force for every copied
file, including those outside the compatibility projection. This proposal makes
no API or behavior claim about excluded SDK products. Because the manifest is
pinned, changing dependencies, adding a plugin, redirecting target paths or making
another SDK target part of this native dependency graph rejects the profile.

Do not apply `SourceDigest` exclusions inside the required source directories.
Current `SourceDigest.files` has no ordinary-file extension whitelist, skips
selected caches/credentials, rejects enumerated symlinks and returns regular
files (`Configuration.swift:89–115`). The Python whole-tree implementation has a
different case treatment for `.env` filenames (`android-build.py:66–84`). A new
compatibility enumerator must therefore admit the exact map directly, including
hidden/unknown/excluded names in its inventory, and fail closed on extras,
missing/renamed entries, symlink components, nonregular files or changed sizes.
An unexpected `.build`, `.env`, `.txt` or special file inside the required closure
is a rejection, not something to skip. Reject an unexpected size/type before
opening it; bound each read to its pinned size and reject growth/short reads.
Preserve the existing SDK-root resolution behavior; paths within the resolved
required closure must have ordinary directories and no symlink redirection.

Files outside this projection retain the existing full-snapshot rules. This
profile is not a new safety boundary for arbitrary package code or hostile
concurrent filesystem writers. Whole-tree special-file hardening outside the
required closure, if demanded as a separate security contract, needs its own
bounded assignment; do not claim this projection implements it.

## Generation, build and profile ownership

For Android creation, preflight the required input closures before copying or
hashing their contents. After copying into the existing private staging directory,
admit the actual copied SDK closure again. Admit the actual exported adapter
closure, validate the existing CLI default against the compiled profile and only
then inspect Android tools or publish the final project. Reject an incompatible
selection as `create.android-sdk-compatibility` with the profile ID, failing path
or digest and an instruction to install the matching first-party distribution.
Failure must remove owned staging and leave the requested final destination
absent. iOS-only creation keeps its current SDK selection behavior.

This intentionally narrows Android `--sdk-path`/`--android-adapter-path`: a directory
with `Package.swift` is no longer sufficient for new generated Android projects.
An identical relocated compatible distribution is accepted. A different valid
SDK/default needs review and a new CLI profile; it must not be accepted merely
because it compiles or emits equal JSON. This observable restriction requires
root's explicit contract selection before implementation.

Export the same **compiled** profile into the generated Python driver's fixed
policy constant. One bounded way is one required template marker, replaced at
snapshot time by the hexadecimal UTF-8 encoding of `JSONFile.data(profile)`;
`json.loads(bytes.fromhex(...))` reconstructs it. Hex insertion is deterministic
and cannot inject Python syntax. Require exactly one marker in the trusted
template, none after replacement, and test the generated script itself. This is
ordinary driver generation using the current snapshot path, not another executable
helper. It avoids an independently maintained second profile table and avoids a
digest cycle: the source-pair maps do not include the generated driver; the
existing complete adapter digest does include the rendered driver.

The direct driver should check its embedded profile, required SDK and adapter
inventories, admitted descriptor identity and existing local locks before generic
source hashing, tool inspection or output creation. Keep the existing strict
asset preaccess gate first. Recheck the profile alongside the existing before/after
source checks. Record profile ID, projection digests and descriptor identity with
the current receipt; record `matched-reviewed-source-pair`, never ABI-compatible
or release-qualified. A legacy generated driver lacking this profile is an
unqualified historical development consumer; it cannot become V2-qualified by
adding fields to its lock. This slice need not migrate or overwrite old projects.

The generated policy is mutable local source. Editing the driver, its embedded
profile and both local locks can bypass local policy. No unkeyed hash or repeated
before/after read prevents that. The compiled CLI is the policy source at creation;
a later signed, immutable CLI/SDK distribution and build provenance must bind the
CLI executable, resource template, source maps and source-pair profile together.
No authenticity claim is added here.

Keep profile changes reviewable. A development rebuild must use the committed
profile and fail its consistency checks if linked Core/UI, selected adapter or
default changed; never auto-pin the working checkout or silently regenerate an
allowlist as part of build/test. Updating a profile is a deliberate source change
after freezing a candidate, executing the bounded API/wire tests, reviewing the
affected contract and root accepting the result. Release packaging must preserve
the exact tested CLI/resource/profile identities and verify the signed installed
distribution separately. Local source copying remains local-development evidence.

## Smallest next implementation and tests

Root should select this contract only after independently reviewing the frozen
packaging handoff. A bounded lane could then own a new internal
`cli/Sources/MixerBuild/AndroidSDKCompatibility.swift`, its focused test file,
and coordinated changes to `ProjectGenerator.swift`, `AndroidProject.swift` and
the existing driver/test files. No SDK public API, Java/JNI/runtime implementation,
Activity, general `ProcessRunner`, package dependency or hosted code change is
needed. Other active lanes retain ownership of their sources. The profile should
be formed from the accepted frozen candidate, not this proposal's live checkout
merely because its observed hashes currently agree.

1. Test exact source-pair admission in Debug and Release. Cover relocated matches;
   missing/renamed/extra/API/default/manifest/packet-encoder drift; hidden/skipped
   names; symlink/nonregular and length violations; absent destination and staging
   cleanup on refusal. Keep mutations in synthetic temporary copies. Add a linked
   source/profile consistency test and a typed reference to all current producer
   APIs. Host tests may use the source checkout only to verify the compiled profile;
   installed production must never discover authority through `#filePath`.
2. Test the actual rendered direct driver with the selected ordinary closure and
   independently recomputed local SDK/adapter locks. Mutating a profile-covered
   source must still reject against the embedded expected map before output or
   tools. Missing/altered template markers must reject generation. Preserve current
   asset admission, source locks, output containment and full asset byte checks.
   These tests are local admission tests, not proof against replacement of the
   driver or its embedded policy.
3. Use a fresh actual CLI-generated consumer for API/wire qualification of the
   accepted source pair. In its existing host test target, type-check and execute
   the copied SDK's codec/default round-trip against the packaged asset and the
   existing value-owned session/prepare/commit/abort cases. Use the actual copied
   Core/UI, exported runtime and app entry, without a repository SDK fallback.
   Passing these tests establishes those operations only.
4. Feed that consumer's actual schema-1 packet output and exact descriptor into the
   production pure Java codecs from its fourteen exported sources. Include wrong
   document/packet schema, wrong appearance format, unknown fields, stale revisions
   and full UInt64 identity cases. Run this as a bounded host test with official
   Java tools and empty accidental source/class paths. Require rejection outcomes,
   not source-string agreement. Preserve actual source/class/output bindings.

The slice adds no native implementation. Existing accepted target compilation and
the packaging cross-build can be cited at their exact hashes; rerun the relevant
export/target compile if its inputs change. A fresh whole APK is unnecessary for
this proposal or for data-only discussion. Do not silently infer Android runtime
behavior from host codec/session execution. The source-pair profile intentionally
offers no mixed-version compatibility range; independent SDK/API/guest/UI/bridge
versions and the eventual installed runtime fingerprint still need their own
published compatibility/deprecation contracts.

## Evidence and remaining gates

`python3 -B verification/android-copied-sdk-appearance-contract/collect.py` completed
with Python 3.14.8 and Git 2.56.0. It retained exact source bytes and checked five
named sealed packaging members plus the selected root decision binding. Its
eleven synthetic map vectors illustrate the proposed identity rule, including
API/packet/manifest changes while the descriptor hash stays equal. The vector
probe does not compile or execute those synthetic sources, run a production
admission gate, or re-execute codec semantics. All 65 named inputs were unchanged
during collection; that observation is not immutable isolation.

No product file was changed or product code imported/executed by this proposal;
no compiler, whole build, APK creation, process discovery, native instance,
capture or UI automation ran. No new dependency, commit, push or publication is
part of this lane. There was no scratch or owned background process to clean up.

Public V2 routing, installed capture/Activity lifecycle and environment integration,
the private API36 versus proposed product API28 support gap, supported resource/font
behavior, OS/accessibility/input/design matrices and physical-phone acceptance
remain pending. Computer use, capture and native simulator/emulator runtime tests
remain paused; phones remain disconnected. Separate-repository FieldLog consumption
of immutable published packages, native ABI/runtime qualification, signed
presentation/health, OTA/release/store/operational evidence and accountable GA review
also remain pending. Selecting or implementing this source admission contract
cannot close any of those gates by itself.
