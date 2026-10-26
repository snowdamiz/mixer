# Independent review of corrected Android source-pair admission

Recommend that root select the frozen corrected contract **with the explicit
SDK-root ASCII amendment below**. The correction addresses the earlier common
Swift preflight and raw-template inspection findings. Its ASCII-only prefix
predicate still misses a filesystem alias on this Mac; the amendment closes that
observed gap without requiring a Unicode normalization algorithm. This is a
contract recommendation, not implementation selection or acceptance.

The corrected proposal is SHA-256
`67e8bd12a618c606727315848c1a258cba59f4e112bfbdef8ab1be81db126857`;
its producer seal is
`08841ed0fd50b5ee0f42b98dbcd5a8751d36ca4712ce0792f929ee933ee3fbdb`.
Before review, all 140 members, totaling 752,291 bytes, were verified and copied
into this review's separate owned inputs. The [pin report](../verification/android-copied-sdk-appearance-contract-correction-review/pin-report.json)
records source revision `559858810e133640d52730972a6610e98442be6d`.
The original proposal and earlier 156-member review remain unchanged.

## Required root selection amendment

Select this paragraph together with corrected-contract R1, rather than modifying
either frozen producer or prior review:

> At every Android SDK admission, enumerate actual SDK-root entry names without
> following entries. Before selector classification, copying, generic hashing or
> any normalization/case transformation, reject every entry name containing a
> non-ASCII code point/byte. For the remaining ASCII names, reserve the existing
> ASCII case-insensitive `Package` prefix and admit only the exactly spelled
> ordinary regular `Package.swift` with its pinned size/hash. Apply this to the
> selected input SDK, actual staged/generated SDK, common Swift project preflight,
> rendered Python build preflight, and linked-SDK consistency checks. Do not infer
> policy from a compiler-selected manifest or normalize a disallowed name into an
> allowed name. Root names are inspected before following or opening those entries.

This deliberately rejects **all** Unicode SDK-root names, including unrelated
documentation or directory names. It is a conservative restriction for this exact
first-party development distribution. It does not impose a new recursive ASCII
rule on excluded inner target/documentation trees, change the existing exact
required-source directory inventory, or establish a general Unicode filesystem
security policy. Identically relocated compatible distributions remain supported.
Root must explicitly select this observable restriction together with the
correction's new/legacy Android project restrictions.

## Independently reproduced remaining R1 gap

Corrected-contract lines 32–50 classify SDK-root names using only an ASCII
case-insensitive `Package` prefix. An enumerated Unicode name can avoid that
predicate while an ordinary ASCII manifest lookup selects the same file on the
host filesystem.

The [independent probe](../verification/android-copied-sdk-appearance-contract-correction-review/filesystem-probe.json)
created separate inert regular-file fixtures, enumerated their actual names and
compared `lstat` device/inode pairs through ordinary lookup paths. It never
invoked Swift, SwiftPM, product code, a native runtime or UI/capture tools.

| Actual enumerated entry | Ordinary lookup | Observed identity | ASCII prefix rule | Amended rule |
| --- | --- | --- | --- | --- |
| `Pac\u212aage@swift-6.4.swift` | `Package@swift-6.4.swift` | Same device/inode | Admits | Rejects |
| `Pac\u212aage.swift` | `Package.swift` | Same device/inode | Admits | Rejects |
| `caf\u00e9.txt` | Decomposed equivalent | Same device/inode | Admits | Rejects deliberately |
| `Package@swift-6.4.swift` | Same spelling | Same device/inode | Rejects | Rejects |
| `Package.swift` | Same spelling | Same device/inode | Admits | Admits |
| `README.md` | Same spelling | Same device/inode | Admits | Admits |

The table uses literal Unicode escape notation for clarity. The Kelvin sign is
U+212A; exact created/enumerated strings and code points are retained in JSON.
ASCII-only folding leaves that character unchanged. The broad root ASCII check
rejects it before the namespace predicate. Different filesystems may resolve
these aliases differently; refusal remains deliberate and portable. This probe
establishes a filesystem lookup fact, not a fresh SwiftPM selection or future
admission implementation result. The earlier sealed host SwiftPM manifest
redirection evidence remains the separate compiler-tool observation.

Require future executable fixtures for both Kelvin-sign names through Android
creation, common Swift `verifyLock` and the generated direct driver. Test selected
and already-generated SDKs; independently recompute local whole-tree locks and
prove refusal before required-source copying/hash/tool/output sentinels. If a
test filesystem does not reproduce the lookup alias, it must still verify the
explicit rejection policy and report the alias observation accurately. Also
test unrelated Unicode root entries and ordinary ASCII relocation. A synthetic
name predicate alone cannot close these gates.

## Assessment of corrected R2 and R3

Corrected R2 places one compiled Swift admission implementation inside common
`ProjectBuild.verifyLock`, before either `SourceDigest.tree` and before
`swift --version`. Its entrypoint table explicitly covers run, direct Android
build and export, the copied export, creation input/staging, and generated Python
build. It adds missing/unknown/mismatching Android profile refusal and preserves
iOS-only locks. It also includes the appearance topology and bounded identity
read before generic hashing. This addresses the previous ordering finding at the
contract level. Regular-file oversize checks remain important; the earlier
review did not demonstrate Swift hashing a FIFO.

Implement “Android-containing project / required Android context” consistently:
an explicitly requested Android operation, configured `targets` containing
`android`, **or** an Android lock requires the common gate. Presence of the
optional lock alone must not determine whether the project is Android. In
particular, removing an Android lock from an Android-configured project must not
route host test, iOS build or export into the iOS-only hash path. This follows the
correction's existing missing-lock and Android-containing-project requirements
(lines 102 and 114–126); include it explicitly in the entrypoint tests. Ordinary
user source/config edits remain mutable local inputs, not signed authority.

Corrected R3 chooses one coherent minimal path: raw resource import and `inspect`
do not decode the profile, while `build` lazily decodes and validates the one
hex-profile literal. The compiled Swift value renders exactly one marker into
that literal, and the driver remains in the full adapter lock outside the
source-pair projection. This preserves raw tool inspection and avoids both a
second expected-policy table and a digest cycle. Creation's host/tool inspection
moves after source/default admission. Require the proposed actual create → render
→ raw inspect → final generated project execution, raw build refusal, marker
failures and rendered build sentinels. No implementation of that wiring was run
or accepted by this review.

## Source binding, ownership and remaining acceptance

Independent read-only Git batch checks verified all 51 retained source files
against accepted commit `559858810e133640d52730972a6610e98442be6d`, not just the
producer's assertion. All 42 source-profile files also equal the earlier review's
owned frozen copies. The recomputed SDK and adapter projection digests remain
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7` and
`05cd1c21b598d4b610ab19e10679982aabe618d62eb5784ef723777e1754c5fa`.
The separately pinned `contracts/ui-v1.json` is now qualification input without
pretending it is loaded by the executable builder. The [offline verification](../verification/android-copied-sdk-appearance-contract-correction-review/offline-verification.json)
retains the Git blob bindings and confirms the original 87-member proposal,
156-member review and 140-member correction seals still match every member.

One coordinated implementation lane retains the correction's ownership:
`AndroidSDKCompatibility.swift`, focused tests, `ProjectGenerator.swift`
(`verifyLock`/run/export/create), `AndroidProject.swift`, the existing Python
driver and their tests. Coordinate accepted packaging files before mutation.
No public SDK API, Java/JNI/runtime, Activity, process supervisor, hosted code or
dependency change is needed. Keep the expected policy in one committed internal
Swift value; neither mutable JSON/locks nor bundle/selected-SDK metadata may
refresh it. The root ASCII amendment is part of that policy and its rendered
projection, not a separately maintained allowlist.

Implementation acceptance still requires the correction's Debug/Release
entrypoint, exact inventory/type/size, legacy-profile, export/staging cleanup and
actual rendering/inspection tests, including the filesystem alias fixtures above.
It also requires the original fresh copied-consumer Swift default/session/
prepare/commit/abort tests and production pure Java wire/descriptor tests with
actual source/class/output bindings, full UInt64 and rejection cases, and no
repository SDK fallback. Source identity or a data predicate cannot substitute
for those executable checks. No whole build/APK was needed for this review.

The review's inert filesystem scratch was removed. No compiler, native instance,
process discovery, UI/capture, product/producer harness execution, product edit,
commit, push or publication occurred. Computer use and native runtime checks
remain paused. Root selection can authorize the bounded implementation; it does
not establish native ABI compatibility, public V2, installed lifecycle/rendering,
resource/font/OS/accessibility/design/input matrices, signed presentation/health,
immutable CLI/SDK authenticity, separate-repository FieldLog consumption,
physical-phone acceptance, OTA/store/operational or accountable GA gates.
