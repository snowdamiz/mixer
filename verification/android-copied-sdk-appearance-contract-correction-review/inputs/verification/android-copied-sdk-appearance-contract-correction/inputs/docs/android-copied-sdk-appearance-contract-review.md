# Independent review of Android copied-SDK appearance admission

The frozen proposal needs three contract revisions before root selects an
implementation. Its compiled source-pair direction is a suitable bounded
development step: one CLI-owned canonical default, exact reviewed Core/UI and
exported adapter sources, one rendered Python policy, and explicit local-source
limits. The current manifest boundary can admit an unreviewed Core/UI graph,
and the generation/build entrypoints need explicit ordering requirements. This
review selects no implementation and grants no ABI, public V2 or GA acceptance.

The reviewed proposal is SHA-256
`340bbf77a48b086f143746ca7f46eef2786a1064d5777f2d4b5b7adb3859de2e`;
its producer seal is
`e08abcacc8421eb2415daa259cf0f9d67a9e2fafa7a879f0b95f574866f62ffb`.
Before review, all 87 seal members, totaling 971,695 bytes, were verified and
copied into the [owned review inputs](../verification/android-copied-sdk-appearance-contract-review/inputs/).
The source revision is `99d6384306ea17643b70c472f93b57418c674f86`.
The independent [pin report](../verification/android-copied-sdk-appearance-contract-review/pin-report.json),
[host probe result](../verification/android-copied-sdk-appearance-contract-review/probe-result.json)
and [receipt](../verification/android-copied-sdk-appearance-contract-review/receipt.json)
define the evidence scope.

## Revisions required before selection

### R1 — Bind every SDK manifest SwiftPM can select (P1)

Proposal lines 65 and 81–108 pin `Package.swift` and complete Core/UI source
directories while preserving ordinary snapshot rules for everything outside
that projection. Frozen `ProjectGenerator.swift:31–39` copies all admitted
`SourceDigest.files`, and `Configuration.swift:89–104` has no ordinary-file
extension whitelist. An additional SDK-root version-specific manifest is copied
but falls outside the proposed 22-file compatibility map.

This is an observed compiler-tool behavior, beyond the producer's eleven
synthetic map vectors. Using exact owned copies of all 22 frozen SDK files, the
review ran `swift package … dump-package` twice with host Apple Swift 6.4. The
baseline selected the original `MixerUI` target. A second copy added
`Package@swift-6.4.swift`, derived from the exact frozen manifest with only the
`MixerUI` target's path changed, and added `Sources/UnreviewedUI/Unreviewed.swift`.
SwiftPM selected `Sources/UnreviewedUI`. Every proposed profile member and its
digest remained equal:
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7`.
The raw manifest JSON, exact fixtures, command argv and stderr are retained under
[host-probe](../verification/android-copied-sdk-appearance-contract-review/host-probe/).
Only package manifests were evaluated; no app/module build or dependency
resolution was run. This proves host manifest selection, not an Android target
runtime outcome. The observed live SDK root currently has only `Package.swift`;
the finding concerns accepted alternate inputs.

Require a closed SDK-root manifest namespace before copy/hash and on the actual
staged/generated SDK. The smallest contract admits the ordinary, exactly named
`Package.swift` and rejects every version-specific manifest and path/case alias;
it need not hash unrelated tests or documentation. Alternatively, deliberately
pin every effective manifest and its transitive target graph for each supported
compiler. Requiring only the expected `Package.swift` bytes cannot establish
proposal line 87's claim that another SDK target/dependency rejects the profile.
Add an actual manifest-selection regression using the copied candidate, plus
preaccess refusal tests for alternate-manifest symlinks, special files and size
violations. The normal whole-SDK lock can be recomputed and is not the expected
compatibility authority.

### R2 — Put admission before Swift CLI source hashing (P2)

Proposal lines 140–148 and implementation test 2 require the **direct driver** to
admit required inventories before generic hashing, tools or output. The ordinary
`mixer build --platform android` path reaches generic hashing earlier:
`ProjectBuild.run` calls `verifyLock` at frozen `ProjectGenerator.swift:253–256`;
`verifyLock` hashes SDK and adapter at `:244–247` and invokes `swift --version` at
`:249`. `AndroidProject.build:118–124` calls `verifyLock` again before it reaches
the generated Python gate. Consequently, placing the new checks only in the
driver leaves the CLI path outside the proposed preaccess guarantee. An oversized
regular required input can be read by `SourceDigest.tree` through unbounded
`Data(contentsOf:)` first. Swift's enumerator filters nonregular entries, so this
review does not claim that its tree opens a FIFO.

Name the earliest admission point for each supported Android entrypoint:
creation, `ProjectBuild.run`/`AndroidProject.build`, and the direct generated
driver. Apply the exact inventory/type/length checks before any generic source
hasher can open required closure contents. Reuse one internal Swift admission
implementation; do not add another expected-profile table. Preserve the existing
strict asset preaccess gate in the appropriate order. Tests must exercise the
public Swift build path with recomputed local locks as well as the rendered
driver, and prove refusal before a tool sentinel or output path is touched.
This is a contract-ordering finding; no new admission implementation exists to
execute or accept in this review.

### R3 — Specify raw-template versus rendered-driver inspection (P2)

Proposal lines 129–138 correctly avoid a digest cycle by excluding the generated
driver from the compatibility projection and including its rendered bytes in
the full adapter digest. However, frozen `AndroidProject.snapshot:70–77` copies
the resource driver, then `ProjectGenerator.create:47` calls
`AndroidProject.inspectToolchain`. That method currently runs the **raw**
`Bundle.module` template returned by `buildDriver` (`AndroidProject.swift:94–102`).
An unconditional `json.loads(bytes.fromhex(marker))` at module scope in that raw
resource would fail before `inspect` can run.

Select and test a concrete path. Prefer passing the already-rendered staged
driver into tool inspection after source/default admission. A lazy profile
decoder used only by `build` is another bounded option if raw-template inspection
is intentionally retained. Require exactly one trusted marker, reject absent or
duplicate markers, require none in the exported script, and test complete
create → render → inspect wiring. Do not silently add a second pre-rendered policy
resource or executable helper to resolve this dependency.

## Source coverage and limitations

The independent data checks verified all 42 profile identities against both the
owned frozen source bytes and the frozen packaging `product-before.json`. They
recomputed both documented projection digests. This establishes the observed
candidate identities, rather than semantic compatibility of arbitrary sources.

| Boundary | Independent conclusion |
| --- | --- |
| Current SDK graph | Frozen `sdk/Package.swift:15,18` has `MixerUI → MixerCore`, no external package dependency, build plugin, source redirection or resources on those targets. Its conditional `MixerCapabilityIO` dependency belongs to the excluded `MixerCapabilities` target. Once R1 is fixed, the current transitive first-party Core/UI source closure is the proposed 21 Swift files plus manifest. |
| Conditional source | The exact 42-file projection contains no Swift conditional-compilation directives. That does not qualify Foundation, platform toolchains, future conditionals or Android runtime behavior. A changed manifest/source must reject until a new reviewed profile is selected; native target checks remain necessary for changed target inputs. |
| Adapter closure | The frozen snapshot selects fourteen Java files, JNI, both headers, one profile JSON and the two runtime Swift files; runtime destination labels are `Sources/MixerAndroidRuntime/...`. Those are the actual selected source identities. Generated runtime/app manifests, entrypoint and driver belong to the CLI/generated lock scope, so a profile match must not be described as proving the dependency graph of arbitrary edited app-owned manifests or hostile package code. |
| Wire/API behavior | `DocumentSession.swift:16–54` uses reconciliation, routing, document validation and native-packet encoding beyond default JSON. `UiPacket.java:16–25` separately enforces schema 1, full UInt64 identities and successor rules. `MixerActivity.java:12–15` still uses V1 exchange. No current profile/hash assertion executes or joins those semantics. The proposed copied-consumer Swift → Java tests are necessary before accepting the source-pair implementation. |
| Referenced schema | `android-profile-v1.json` names `contracts/ui-v1.json`; that specification is absent from the producer's 65 source inputs and is not loaded by the builder. This review separately pinned the current schema as supplementary context. It describes document, action, identity and raw-JSON limits with Android subset exceptions. Keep it as explicit qualification input for the bounded wire tests; do not call the 42-file executable projection a complete public-contract inventory. Its omission need not enlarge the runtime compatibility map because no current executable path reads it. |
| Source equality versus ABI | The private C header explicitly denies stable public ABI authority. Correct symbol names, source hashes, default equality and host session tests cannot prove target calling conventions, JNI exception behavior, lifetime/transaction semantics, OS rendering or lifecycle. The proposal preserves that limitation correctly. |

The strict enumerator must compare actual directory-entry spelling from the
resolved distribution root, including `Sources`, the two target roots and every
ancestor component. Constructing a canonical label from an already-resolved
case-insensitive path is insufficient. Derive the exact expected ordinary
directory set from the pinned file paths; reject extra empty directories,
unknown/hidden/excluded names, symlink components and nonregular files before
opening them. Check pinned sizes before bounded reads, then reject growth or
short reads. Include root/ancestor case variants, nested symlinks, FIFO,
directory-as-file, renamed files, `.build`, `.env`, `.txt` and excluded credential
extensions in tests. These refine the proposal's stated exact-path/type policy;
they introduce no claim against concurrent same-user writers or arbitrary
special files outside the admitted closure.

## Minimal implementation and acceptance contract

After the packaging implementation receives its separate independent review,
root can explicitly select the corrected development contract. Restricting new
Android `--sdk-path`/`MIXER_SDK_PATH` and adapter selections to relocated exact
matches is consistent with plan §§8.3 and 11.1's fail-closed compatibility
direction. It is an observable restriction and therefore needs root's explicit
selection as the proposal says. It is not the product's eventual independently
versioned SDK support or customer distribution policy (§19.3), and iOS-only
creation retains its existing selection contract.

One coordinated implementation lane is sufficient. Own the new internal
`AndroidSDKCompatibility.swift` and focused tests, `ProjectGenerator.swift`
(including the early build entrypoint), `AndroidProject.swift`, the existing
driver and their test files. Coordinate these files with the frozen packaging
lane first. No public SDK, Java/JNI/runtime, Activity, general process supervisor,
package dependency or hosted implementation needs modification. This review did
not edit or accept any of those files.

The executable acceptance contract should include:

1. Debug and Release source-profile consistency plus actual source/default
   admission. Accept identical relocation; reject changed API/default/encoder,
   effective manifests, dependencies, source/ancestor names, complete inventories,
   types and lengths. Validate inputs before copying and actual staged copies
   afterwards; failed creation must leave no requested destination or owned
   staging. Check iOS-only behavior explicitly.
2. Exercise both Swift CLI build entrypoints and the actual rendered direct
   script with independently recomputed local locks. Profile-covered drift must
   reject even with matching local lock hashes. Preserve asset preaccess,
   output containment, original source locks and final asset byte checks.
   Test marker failure cases and create/inspect wiring, including tool/output
   sentinels. Assert the recorded profile ID, SDK/adapter projections and default
   identity come from the same compiled value.
3. Use a fresh actual CLI-generated consumer. Execute its copied Core/UI
   default/canonical codec against the packaged descriptor and existing
   value-owned session/prepare/commit/abort behavior with the exported runtime
   and actual app entry. No repository SDK fallback or expected synthetic-source
   substitute can close this test.
4. Feed that consumer's produced packets and exact default asset into the
   exported production pure Java codecs under official host Java tools with
   empty accidental class/source paths. Include malformed/raw JSON, duplicate
   fields, unsupported formats/schemas/fields, stale revisions/identities and
   full UInt64 cases, with observable accept/reject results and complete source,
   class and output bindings. Host execution establishes only those operations.

Use the accepted packaging cross-build at its exact hashes; rerun changed
target/export inputs as needed. Another whole APK is unnecessary for this
contract review. Keep the one committed internal Swift profile authoritative;
observed JSON, selected SDK comments/metadata, local locks and bundle JSON must
never supply or refresh expected policy. Profile updates require a frozen
candidate, bounded API/wire tests, coordinated contract review and root selection.
They must not be auto-generated as part of ordinary build/test success.

The generated driver and local locks remain editable and unauthenticated.
`matched-reviewed-source-pair` is a local admission observation with a stated
scope. Signed immutable CLI/SDK distributions and provenance must eventually
bind the actual executable, resource template and profile, and FieldLog must
consume published packages from a separate repository. This review does not
establish that distribution path or any public compatibility range.

Computer use, capture, simulator/emulator runtime tests and physical-device runs
remain paused. No native instance or capture process was started or discovered.
The two host manifest evaluations completed, and their owned cache/scratch
directories were removed; the exact source fixtures and outputs remain. Public
V2 routing, installed capture and Activity/environment lifecycle, private API36
versus product API28 coverage, resources/fonts, accessibility/design/input/OS
matrices, target ABI semantics, signed presentation/health, OTA/store/operations,
immutable external consumption and accountable GA review remain pending.
