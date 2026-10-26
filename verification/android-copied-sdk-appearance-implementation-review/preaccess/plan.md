# Independent implementation review: Android copied-SDK appearance admission

Status: **preaccess plan frozen; candidate implementation not accessed**. This
document records the controls selected before the implementation handoff. It is
not an implementation acceptance, a test pass, a native runtime receipt or a GA
gate. Root owns exact candidate admission and final acceptance.

## Baseline and review boundary

Root selected `implementation-selection.json` SHA-256
`cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917`.
The selected documents are the original contract, the correction SHA-256
`67e8bd12a618c606727315848c1a258cba59f4e112bfbdef8ab1be81db126857`, and the
independent correction review SHA-256
`801b275ebebc917022907de7f49307dfb985c225539f6fcba44643ea642378e7`, together
with root's explicit SDK-root ASCII, Android-required and lazy-policy amendments.

Before candidate access, the review copied these documents, the selected
observation and review/admission receipts, applicable instructions, and named
accepted Git inputs from `559858810e133640d52730972a6610e98442be6d` into its own
[preaccess packet](../verification/android-copied-sdk-appearance-implementation-review/preaccess/input-manifest.json).
The 42 accepted source inputs were independently checked against the selected
path/length/SHA-256 maps. Both projections were independently recomputed using
sorted `path + NUL + lowercase SHA-256 + LF` records. `contracts/ui-v1.json` is a
separate qualification input; it is not silently added to the executable 42-file
projection. Accepted CLI APIs and historical tests inform executable probes,
without reading the active implementation lane or its producer packet.

The selected SDK and adapter digests are respectively
`4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7` and
`05cd1c21b598d4b610ab19e10679982aabe618d62eb5784ef723777e1754c5fa`.
The default must be the CLI-linked typed producer's canonical 9,587 bytes,
SHA-256 `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
No baseline script updates expected product policy from a successful test.

Review ownership is this new document and
`verification/android-copied-sdk-appearance-implementation-review/**` only.
No product files, root metadata, frozen hosted/catalog/authority/WorkerV2 inputs,
broader hosted harness, commits or pushes belong to this lane.

## Controls fixed before candidate access

| ID | Independent control and acceptance observation |
| --- | --- |
| P01 | Verify root's exact handoff bytes, seal membership and candidate source identities before executing any candidate. Copy admitted inputs into this review's owned packet. Check candidate closure against accepted Git and root's allowed file set. Record all source changes and untested effects. Never run a producer harness as a substitute for independent controls. |
| P02 | Inspect one compiled internal expected profile: exactly 22 SDK and 20 adapter path/length/hash identities, selected default and wire diagnostics. No override, mutable file/lock/bundle refresh, wildcard, source introspection or second policy authority. Linked-SDK consistency includes actual root-name enumeration and the same ASCII rule. |
| P03 | Actual CLI Android create from an identical relocated accepted distribution must succeed using installed official raw `inspect` and host compiler inventory. Bind the generated driver, actual SDK/adapter/default bytes and additive lock record. Create an iOS-only ordinary selection independently and verify its historical SDK selection behavior remains usable. |
| P04 | SDK input and generated SDK: reject `Package@swift-6.4.swift`, `package.swift`, `PACKAGE.SWIFT`, `Package.swift.bak`, `Package.resolved`, both `Pac\u212aage.swift` and `Pac\u212aage@swift-6.4.swift`, unrelated `caf\u00e9.txt`, and an unrelated Unicode root directory. Enumerate and retain actual names/code points. Every non-ASCII root entry is rejected before any transformation, selector classification, following/copy/hash. Preserve the sealed SwiftPM redirection observation; do not evaluate the malicious package. Ordinary root relocation passes. |
| P05 | Within the required SDK and exported adapter closures: exact spelling of `Sources`, `MixerCore`, `MixerUI` and descendants; missing/renamed/case-aliased source, extra ordinary/hidden/`.build`/`.env`/credential-extension/unknown-extension file, extra empty directory, nested symlink, wrong ancestor type, directory/FIFO substituted for required file, short/long file, same-length changed content. Test source inventory against pinned paths, including derived directory set, rather than `SourceDigest` filtering. Input adapter extras outside its explicit export remain outside the selected map; generated selected target/source inventories remain exact. |
| P06 | The canonical manifest and required files reject wrong type/length before bounded reads, and reads detect short data/growth. Reserved selector variants of directory, symlink, FIFO and oversize type refuse by enumerated name before following/opening. Use bounded inert fixtures with process deadlines; never demand a giant allocation to demonstrate ordering. |
| P07 | Appearance topology remains first in common project admission after necessary config/lock/schema/profile recognition: ordinary exact `Generated`, adapter, `app`, `assets`, `MixerAppearanceV2`; closed asset inventory; ordinary nonsymlink descriptor in 1–65,536 bytes; then selected identity. Exercise layout/symlink/extra/empty/oversize/altered bytes before generic source hashes, compiler, tools and output. Preserve typed CLI default roundtrip and resource/system-sans restrictions. |
| P08 | Android is required by requested Android operation OR configuration `targets` containing `android` OR Android lock. Independently mutate each dimension; cover missing Android lock, legacy missing profile, unknown profile and each mismatching identity. An Android-configured project whose lock was removed must refuse during host/iOS/export too. An Android lock on iOS-only config must still gate. Preserve a genuinely iOS-only lock's existing path. |
| P09 | Execute Debug and Release common `verifyLock`, `ProjectBuild.run` for host test/host build/iOS/Android dispatch, direct `AndroidProject.build`, and export. Probe public APIs directly in an owned host harness where the CLI cannot expose the exact entrypoint. Require actionable profile/compatibility errors, no tool sentinel and no build/export output. Private predicate tests alone do not satisfy this row. |
| P10 | Create order: request validation/root resolution → input SDK/adapter admission → owned staging/copy → actual staged SDK admission → snapshot with typed default/rendered driver → actual adapter/appearance admission → full local hashes → host/tool inventory → lock/publication. Inspect staged/source code and exercise invalid input, late failure and absent final destination/staging cleanup; positive actual create binds the produced artifacts. |
| P11 | Export: common admission before any source copy/output; admit the actual copied export SDK/adapter/appearance before final generic tree digest. Exercise source refusal, positive export and failed-copy or post-copy failure cleanup. Race-free hostile mutation is outside scope; any mutation seam used to reach a deterministic late failure is supplemental and must be identified. |
| P12 | One raw trusted marker inside one profile-hex literal. Actual snapshot replaces exactly once using hex of `JSONFile.data(compiledProfile)`; no marker remains. Missing/duplicate marker generation refuses. Raw import and actual installed-official-tool `inspect` succeed without profile decode; raw `build` refuses before source/tool/output. Malformed/nonhex/missing/unsupported/extra policy shape refuses on build. Generated driver policy equals the compiled source, without a second maintained expected table. |
| P13 | Actual CLI-created rendered Python driver: positive admission reaches a bounded tool/output sentinel only after all admission and local locks. Recompute SDK/adapter locks independently after SDK/default/adapter drift, alternate/Kelvin/Unicode entries and missing/legacy/unknown profile mutations; refuse against compiled policy despite matching mutable local locks. Check no output/tool sentinel for negative cases. Repeat applicable source checks around build. |
| P14 | Fresh actual CLI-created consumer uses only copied SDK Core/UI and exported runtime/app entry. Compile/run a host executable/test target with no repository SDK fallback. Canonical default encoding and typed decode/re-encode must equal the packaged asset. Exercise initial session/render, successful dispatch, stale/wrong identity/generation/event/schema, reducer/document failure rollback, successor revision, prepare/commit/abort/token lifetime and malformed/duplicate/unsupported input. Include exact full UInt64 identities/revisions above 2^53 and at UInt64.max, with the defined exhaustion behavior. Bind actual Swift sources, command, output packets and descriptor bytes. |
| P15 | Compile production pure Java `Json`, `UiPacket` and `AppearanceDescriptorV2` dependencies from the created consumer. Empty accidental source/class paths; explicit owned source list and class directory. Feed actual P14 Swift-produced packets and exact descriptor. Assert schema/successor/identity coverage and full UInt64 parsing, and rejection of wrong document/packet/appearance format, recipe, unknown/duplicate fields, malformed JSON, missing/duplicate/extra identities, unsupported values and stale inputs as supported by the actual codec contract. Bind source/class/output SHA-256 separately and pin `contracts/ui-v1.json`; no handwritten JSON positive stands in for the Swift producer. |
| P16 | Preserve accepted asset/source locks, output containment, unsupported resource/capability refusal, codec and final archive byte checks. Independently execute focused host regressions from the admitted candidate; inspect accepted-to-candidate behavior changes. Reuse exact accepted native target compilation when native SDK/Java/JNI/runtime/profile inputs are unchanged; rerun changed target compilation only when warranted. No redundant whole APK is planned for unchanged native inputs. |

## Independent oracle, ordering evidence and execution hygiene

Expected source/default identities come from the selected frozen contracts and
accepted Git, not from the candidate's compatibility helpers. Whole local locks
will be recomputed with an independently written Python `hashlib` implementation
of the historical snapshot recipe and explicitly recorded exclusions. Fixture
inventories and expected errors are selected above before candidate access.
Compatibility helpers may be invoked for coverage but cannot supply their own
expected outcomes.

For actual entrypoint ordering, combine the structured compatibility/profile
error with filesystem observations (absent requested destination/staging/export
and build output), bounded PATH tool sentinels (`swift`, Python/tool inventory),
and an ordinary unreadable required/generic-read sentinel where the current host
enforces permission refusal. Compute its independent lock before removing read
permission, then restore permissions during cleanup. A self-check must establish
that the generic reader actually trips that sentinel on this host; otherwise
record that observation as unavailable and use source-order inspection plus other
observable controls. FIFO fixtures are type controls, not evidence that historical
Swift hashing opened FIFOs. Error wording alone does not establish bounded reads
or race freedom. No implementation-only mocked predicate can establish create,
common entrypoint or driver ordering.

Host commands execute with explicit argv, cwd, source tree digest, tool version,
bounded timeout/output and an owned subprocess group. On timeout preserve partial
stdout/stderr, terminate/reap owned descendants, and record failure before retry.
Use one copied consumer and bounded host builds; compile Debug/Release once per
admitted tree unless changed input or a concrete failure warrants another run.
Keep failures and supplemental attempts in the packet. Remove only owned scratch
after evidence collection and retain cleanup receipts. No process discovery,
simulator/emulator, phone, UI, capture or native runtime is authorized.

## Current result and next admission

Preaccess preparation copied and hash-checked accepted data only. Python and Git
metadata versions and bounded command stdout/stderr are retained. One optional
historical test path did not exist at the accepted Git revision; that failed read
and the corrected preparation are preserved. No compiler, candidate product,
producer harness, copied consumer or Java codec has executed in this phase.

The immutable copy of this plan and baseline manifest will be sealed before
root's exact implementation handoff. Candidate review/execution begins only after
root admits that handoff. Every executable row P03–P16 is currently **pending**;
P01/P02 are not implementation passes until a candidate is admitted and reviewed.

Exact source matching establishes the reviewed development source pair within
the executed test scope. Local drivers/locks remain mutable and unauthenticated.
Public V2, stable native ABI, installed lifecycle/capture/rendering, API28 versus
API36 support, resource/font/design/input/accessibility/OS matrices, physical-phone
acceptance, signed/immutable distribution, separate-repository FieldLog dogfood,
OTA/store/operational and accountable GA gates remain pending.
