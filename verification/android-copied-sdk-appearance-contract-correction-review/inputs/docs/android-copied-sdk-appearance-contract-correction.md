# Corrected Android copied-SDK appearance admission contract

This separate correction addresses R1–R3 in the admitted [independent review](android-copied-sdk-appearance-contract-review.md).
The [original proposal](android-copied-sdk-appearance-contract.md), its seal and
the review remain immutable. This document selects a corrected contract candidate
for another independent review; it selects no product implementation or public V2
routing. The canonical-default packaging slice is now independently accepted and
committed as `559858810e133640d52730972a6610e98442be6d`. Its six product files and
the 42 source-profile inputs still match the original proposal's frozen bytes.

Retain one compiled, internal `MixerBuild` source-pair profile, provisionally
`mixer.android-source-pair.1`, for exact first-party source identity. Retain the
22-file SDK map, 20-file exported adapter map, destination-label mapping and
default identity from the original proposal. Add closed manifest-namespace and
directory-inventory rules rather than changing those file bytes. The observed
SDK digest remains
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`;
the adapter digest remains
`05cd1c21b598d4b610ab19e10679982aabe618d62eb5784ef723777e1754c5fa`.
These observations do not become production constants without root selection.

The [correction packet](../verification/android-copied-sdk-appearance-contract-correction/receipt.json)
binds current source bytes to that accepted Git commit, rechecks the original and
admitted review seals, and retains the review's manifest-selection inputs/outputs.
The review observed SwiftPM choosing `Sources/UnreviewedUI` through an added
`Package@swift-6.4.swift` while the original SDK map stayed equal. That was a host
manifest evaluation, not an Android build. This correction does not rerun SwiftPM,
compile source, import product code or execute a native runtime.

## R1: close SDK-root manifest selection before copy or hash

Enumerate actual SDK-root directory entries without following entries. Reserve
the conservative **ASCII case-insensitive `Package` prefix**: the only permitted
entry in that namespace is exactly spelled `Package.swift`, an ordinary regular
file with its pinned length/hash. Reject every other matching name and every
type, without opening it: for example `Package@swift-6.4.swift`, other version
selectors, `package.swift`, `PACKAGE.SWIFT`, `Package.swift.bak` and
`Package.resolved`. Rejecting the latter harmless names is deliberate conservative
development policy; the currently pinned manifest has no external dependency.
A future SDK needing another manifest/lock entry requires a reviewed profile
change. Do not silently recognize or pin a selector chosen by the host compiler.

Apply the same namespace rule to the input SDK **before source copying or generic
hashing**, after the SDK root is explicitly resolved, and again to the actual
`Generated/MixerSDK` after copying. Apply it at every later Android project
admission, including the direct driver. Recomputed `sdkDigest` or local lock data
cannot authorize a new root selector. A version-specific selector is rejected by
its directory-entry name before symlink resolution, size reads or manifest
evaluation. The canonical manifest itself is stat/type/length checked before a
bounded read. No product path evaluates an unadmitted selected SDK to learn policy.

Compare actual entry spelling for `Sources`, `MixerCore`, `MixerUI` and each
required descendant directory/file. Derive the exact internal directory set from
the pinned paths, including no extra empty directories within either target.
Reject missing, renamed, case-aliased, hidden, skipped, unknown-extension,
credential-extension, symlink or nonregular entries in these target closures.
Constructing canonical labels after resolving a case-insensitive path is
insufficient. A relocated SDK root is permitted; the root's explicit resolution
does not permit symlink descendants. Sibling SDK targets outside Core/UI remain
outside this compatibility claim and retain whole-snapshot rules. Input adapter
files outside the explicit export are likewise outside the map; the generated
adapter must contain the exact selected exported source inventories.

The ordinary full `sdkDigest` still locks all copied files. The compatibility map
is not a complete public specification inventory: separately pin
`contracts/ui-v1.json` as qualification input to the consumer Swift → Java tests,
as the review requires. The current executable builder does not load that
specification, so it need not enter the 42-file executable source map. No arbitrary
app-owned manifest, plugin, package execution or external SDK product is qualified
by this exact first-party projection.

## R2: one Swift preflight before every Android source hash

Add one internal Swift admission implementation with one compiled expected
profile. Put its project-level invocation inside `ProjectBuild.verifyLock`, after
the existing configuration/lock decode identifies an Android lock, but **before
either `SourceDigest.tree` call and before `swift --version`**. Invoke it for
every Android lock even when the requested operation is host testing, iOS building
or export. Do not rely on reaching the Python driver later.

The common project preflight must first admit the existing appearance topology:
ordinary `Generated`, adapter, `app`, `assets` and `MixerAppearanceV2` directories;
the complete closed asset inventory; one ordinary, nonsymlink descriptor;
1–65,536 bytes. Check exact entry spelling as well as type. Then admit the SDK
root manifest namespace, required source ancestors/inventories/types and pinned
lengths. Only after those checks may bounded reads verify descriptor identity and
the source-pair maps. The descriptor must match the compiled expected length/hash,
as produced by the unchanged CLI-linked typed codec. None of these checks may
open an oversized regular required input through a generic source hasher first.

This corrects a precise current limitation. `SourceDigest.tree` reads regular
files through unbounded `Data(contentsOf:)`; its enumerator already filters
nonregular entries. The review does **not** show Swift opening a FIFO. The new
preflight rejects unexpected types/names and oversized regular inputs within the
required source/appearance boundary before hashing. It makes no blanket claim
about special files, oversized files or hostile code outside that boundary, nor
about lock/config reader hardening or concurrent same-user filesystem writers.

| Entrypoint | Required order |
| --- | --- |
| Android `ProjectGenerator.create` | Validate basic request; resolve input roots; admit input SDK manifest namespace, SDK closure and selected adapter closure before `SourceDigest.files` copying or `SourceDigest.tree`. Create owned staging and copy. Re-admit actual staged SDK before its generic digest. Snapshot the adapter with the existing CLI default producer and rendered driver; admit its actual source closure and appearance before snapshot's generic adapter digest. Only then run host Swift/tool inventory, write the lock and publish the final project. Failed creation removes owned staging and leaves the requested destination absent. |
| `ProjectBuild.verifyLock` | Existing config/lock decode and lock schema check → Android/profile presence checks if applicable → common project preflight → existing whole SDK/adapter locks → host compiler identity. A required Android context with no Android lock rejects before generic hashes/tools. Preserve the non-Android path for an iOS-only lock. |
| `ProjectBuild.run` | Forward Android-required context when `platform == android`; otherwise the presence of an Android lock still triggers the common gate. Existing dispatch can call `AndroidProject.build`, whose verification may safely repeat the same admission. No skip flag or alternate expected table. |
| Direct `AndroidProject.build` | Call the same `verifyLock` path with Android required, so a missing/legacy lock rejects before hashing; then current capability/resource checks and generated Python invocation. The method must remain safe when called directly, without `ProjectBuild.run`. |
| `ProjectBuild.export` | Its existing `verifyLock` call admits any Android source/asset inputs before generic reads/copy/output. Re-admit an Android export's actual copied SDK/adapter/appearance before the final destination tree digest, retaining existing cleanup on failure. Export grants no additional compatibility authority. |
| Rendered Python `build` | Decode the embedded profile at build entry; decode local lock/config only as needed → strict existing asset layout/type/size gate → SDK manifest namespace and required source inventories/types/lengths → bounded profile/default checks → existing full locks → output/tool/build work. Repeat applicable checks with current before/after source observations. |

Stat lengths before reading, bound reads to the pinned lengths and reject short
reads/growth. Keep typed CLI codec validation, asset inventory, lock, containment,
resource refusal and final archive byte checks. The source profiler adds an exact
reviewed-source observation; it does not give the Python layout layer semantic
codec or signed authority. Existing source observations remain local and mutable.

For the new contract, require an additive Android lock profile record from the
same compiled value, containing profile ID, both projection digests and descriptor
identity. A new CLI encountering an Android lock missing that record, declaring an
unknown profile or mismatching policy rejects as an actionable
`android.sdk-profile-required`/`android.sdk-profile-mismatch` before source hashes,
tools or export output. Explain that the project predates this source-pair contract
and requires explicit migration or a fresh project with the matching distribution.
Do not rewrite app-owned sources, repair locks, infer compatibility, auto-pin or
overwrite existing projects. Historical old CLIs/drivers remain historical local
development tools; they gain no V2 qualification. iOS-only locks keep their existing
SDK selection contract. An Android-containing project's host/iOS/export operation
also enforces this gate; this observable legacy restriction must be explicit in
root's eventual selection and release notes.

## R3: retain raw inspection; decode profile only during build

Choose root's minimal lazy-decoder option. Keep `buildDriver()` returning the raw
resource template and keep `inspectToolchain()` using that template's `inspect`
mode. Move the profile-hex decoding into a build-only admission function.
Raw-template import and `inspect` must not evaluate or require the profile at all.
They are tool inventory only and cannot report source compatibility. Creation
must still complete input/staged source/default admission before calling inspect,
as R2 specifies; the current earlier host `swift --version` must also move after
the relevant admission.

Use exactly one hex-profile string literal in one fixed template assignment,
with exactly one trusted marker inside that literal. The compiled Swift profile
renders the marker using hexadecimal UTF-8 `JSONFile.data(profile)`. Require one
marker before replacement and none afterward; the rendered driver contains one
profile literal and no second policy table/resource. The build-only function
decodes that literal, validates the closed profile shape and rejects a raw marker,
nonhex, malformed or unsupported data clearly as
`Android SDK source profile is not rendered or supported; recreate with the matching CLI.`
before reading app sources, creating output or running tools. Do not repeat the
marker text in a comparison elsewhere in the template; a decode failure can be
classified without creating a second marker occurrence.

This leaves raw inspect usable with the least wiring change. Passing a rendered
staged driver into inspection would also be feasible, but would change its
parameter/call path and is not needed for inventory that consumes no policy.
Do not implement both paths or introduce a second pre-rendered resource/helper.
The rendered driver remains in the complete adapter lock; its source-pair map
excludes generated driver bytes, preserving the existing absence of a digest cycle.

## Bounded ownership and acceptance evidence

One coordinated implementation lane can own a new internal
`AndroidSDKCompatibility.swift`, focused tests, `ProjectGenerator.swift` (including
`verifyLock`/run/export), `AndroidProject.swift`, the existing Python resource and
their test files. The accepted packaging sources must be coordinated first.
No SDK public API, Java/JNI/runtime, Activity, general `ProcessRunner` supervisor,
dependency, hosted authority or other active lane source needs modification.
The single committed compiled profile is authoritative. Development/release
consistency checks must also reject alternate manifests in the linked SDK root;
they must never refresh expected policy from a successful local build or mutable
bundle/selected SDK metadata. Profile changes require frozen candidate bytes,
bounded tests, coordinated review and root selection.

The implementation's executable evidence must cover:

1. Actual alternate-manifest regression using the reviewed fixture: show the
   unchanged 22-file map and retained SwiftPM redirection, then require both
   input and generated SDK admission to reject the selector before a copy/hash/
   compiler/tool sentinel. Cover every reserved-name case, alternate-manifest
   symlink/FIFO/directory/oversize, ancestor case aliases, nested symlinks, exact
   empty-directory inventory and the existing required-file size/type cases.
   Baseline relocation passes; iOS-only selection stays unchanged.
2. Debug/Release tests through common `verifyLock`, `ProjectBuild.run`, direct
   `AndroidProject.build` and export, plus the rendered driver. Recompute local
   whole locks independently and prove profile/asset refusal still precedes
   generic required-file reads, `swift --version`, tool inspection and output
   sentinels. Test missing/legacy/unknown Android profile records and failed
   staging/export cleanup. A mocked private helper alone cannot close entrypoint
   ordering.
3. Actual create → template render → raw inspect → final generated project wiring.
   Raw import/inspect remain usable; raw build clearly refuses; the created
   script has exactly one expected literal and no marker. Exercise its build
   admission with ordinary matching inputs and tool/output sentinels, then with
   profile/selector/asset drift. The actual raw inspect uses installed official
   tools in the normal create flow; a separately stubbed unit test is supplemental.
   Do not require another whole APK merely to test admission.
4. The original proposal/review's fresh copied-consumer Swift default, session and
   prepare/commit/abort tests and production pure Java wire/descriptor tests remain
   necessary. Include separately pinned `contracts/ui-v1.json` as qualification
   input, malformed/duplicate/unsupported schemas, successor/identity and full
   UInt64 cases, with actual source/class/output bindings and no repository SDK
   fallback. Run changed target/export compilation only when inputs justify it.

No implementation tests above ran for this correction. The new Python data probe
checks the conservative name predicate against retained manifest-selection data,
unchanged source maps against accepted Git, and one-marker/hex-data invariants.
It cannot prove future Swift entrypoint ordering, generated Python execution,
codec semantics, target ABI or actual create/inspect wiring. Those remain explicit
implementation acceptance requirements.

Source identity, even with closed manifest selection, establishes only a matched
reviewed first-party implementation within its observed tests. Editable generated
drivers/local locks remain unauthenticated; signed immutable CLI/SDK packaging,
build provenance and separate-repository FieldLog consumption remain separate.
Public V2, stable native ABI, installed capture/lifecycle, private API36 versus
product API28 support, resources/fonts, input/accessibility/design/OS matrices,
physical-phone acceptance, signed presentation/health, OTA/store/operations and
accountable GA review remain pending. Computer use, capture and native runtime
tests remain paused; phones remain disconnected. This lane starts no such process
and performs no discovery, compiler/build/APK, commit, push or publication.
