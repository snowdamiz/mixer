# Independent Android default appearance packaging review

Status: independent preaccess baseline, awaiting the root's frozen proposal.
This baseline was written before reading either
`docs/android-default-appearance-packaging-proposal.md` or its verification packet.
It makes no judgment about that unread proposal and authorizes no implementation.

The [preaccess receipt](../verification/android-default-appearance-packaging-review/preaccess/receipt.json),
[selected source manifest](../verification/android-default-appearance-packaging-review/preaccess/source-manifest.json),
and [numbered excerpts](../verification/android-default-appearance-packaging-review/preaccess/source-excerpts.txt)
bind the observations below. The initial source revision is
`99d6384306ea17643b70c472f93b57418c674f86`. Its selected-source digest is recorded
in the manifest; this is a bounded source selection, not a clean whole-tree or
immutable build attestation. Other lanes' changes remain outside review ownership.

## Independently observed contracts

| Contract | Source observation and implication |
| --- | --- |
| Product design | Product plan §8.3 requires shared layout, hierarchy, content, colors, type scale, icons, spacing and component appearance by default. Platform-specific appearance requires explicit opt-in. Native input/navigation/accessibility and system-owned surfaces retain their native behavior. Packaging one descriptor is only a prerequisite toward that contract. |
| Canonical default | `sdk/Sources/MixerUI/AppearanceDefaultV2.swift:7–10` exposes `UIAppearanceDescriptorCodecV2.mixerDefaultV2()`. It decodes the SDK's existing measured shared default; no resource or font installation is implied. Reuse this API and `canonicalData(_:)`; do not parse Swift literals, copy the table into the CLI, invent a JSON fixture as authority, or introduce branding/theme changes. |
| Closed codec | `AppearanceDescriptorV2.swift:3–37` explicitly makes this a data codec with no native/provenance/release authority. Decode admits 1–65,536 bytes, validates the closed model and semantics, and requires exact canonical bytes. The canonical encoder also validates. A JSON parse or hash match alone is weaker. |
| Current CLI dependencies | `cli/Package.swift:8–12` links MixerBuild to MixerCore and MixerUpdates, without a direct MixerUI dependency. A CLI-linked codec path therefore needs an explicit package dependency change, not accidental transitive import reliance. |
| SDK selection | CLI `main.swift:81` honors `--sdk-path`, then `MIXER_SDK_PATH`, then the repository SDK. `ProjectGenerator.swift:22,31–39` currently checks `Package.swift`, copies the selected source snapshot, and hashes that copy. It does not assert that copied SDK equals the SDK used to compile the CLI. |
| Atomic generation | `ProjectGenerator.swift:25–27,64–65` creates an owned sibling staging directory, removes it on exit, and publishes the entire project by a final move. Descriptor/helper failure should throw inside this transaction. A second project-generation transaction framework is unnecessary. |
| Existing locks | The copied SDK is covered by `sdkDigest`; the explicit adapter/runtime/build-driver closure by `android.adapterDigest`. Swift `verifyLock` and direct Python build check both before their build path. Writing generated appearance bytes after calculating the adapter digest would invalidate that lock unless the digest is recomputed before publishing it. |
| Current exported closure | `AndroidProject.swift:32–49` exports fourteen Java files, including `AuthoredToggleInputV2.java`. The earlier source-only routing document's observed thirteen-file defect is historical after `99d6384`; its remaining packaging/lifecycle/platform gaps are still relevant source questions. |
| App resources | `AndroidProject.swift:104` and `android-build.py:218–219` reject nonempty app `Resources`. The new internal descriptor must not quietly enable arbitrary app resources or fonts. |
| Installed asset | `InstalledAppearanceV2.java:13,31–55` reads `MixerAppearanceV2/descriptor.json` through `AssetManager`, enforces the byte bound while streaming, decodes canonically, then rejects any resource declaration or bundled font in either platform theme. The corresponding APK ZIP entry must be exactly `assets/MixerAppearanceV2/descriptor.json`. |
| Existing APK construction | `android-build.py:284–292` links an APK then appends the owned staging closure and DEX. It does not yet add the appearance descriptor. Lines 306–324 hash every named ZIP entry and record SDK/adapter digests, but the dictionary of entry hashes alone would conceal duplicate ZIP names. Exact single-entry checking is needed for the new asset contract. |
| Public route | `MixerActivity.java:12–15` still uses legacy `exchange` → `UiPacket` → `NativeRenderer.apply`. Packaging must preserve this route. Private prepare/commit/abort exports and Java source inclusion do not activate V2. |
| Platform gap | The generated manifest and driver advertise minimum API28; `NativeEnvironmentV2.java:69–74` rejects API<36, and lines 125–128 reject nondefault weight/high contrast. Product §19.1 keeps Android API28+ a proposed baseline subject to qualification. Neither D8 min28 nor a packaged descriptor resolves this gap or selects a higher product minimum. |
| Subprocess limitation | `ProcessRunner.swift:14–35` combines stdout/stderr in a private spool, waits without a deadline, and only bounds the returned tail to 8MiB. This protects against pipe deadlock, not time or disk exhaustion. Do not treat it as a bounded, clean descriptor transport. |

## Default provenance must have one explicit guarantee

An installed descriptor needs an exact derivation and compatibility statement.
Three materially different claims should not be merged:

1. **CLI default packaging.** The emitted asset is the canonical existing default
   from the SDK linked into this CLI. The copied SDK is independently locked.
   Calling the linked API proves which default was emitted; it does not prove
   the selected `--sdk-path` SDK's default agrees or that the resulting generated
   application is compatible with that SDK. This can be a bounded data guarantee
   if the proposal says so explicitly and identifies the CLI/default provenance.
2. **Observed copied-SDK default packaging.** A small owned host helper calls
   `mixerDefaultV2()` and `canonicalData(_:)` against the already copied SDK, with
   a fixed entry point and controlled output. Validating those bytes with the
   CLI's codec establishes that this observed invocation produced acceptable
   canonical data. It can preserve source-distribution selection semantics
   without requiring the copied SDK's entire source tree to match the CLI's.
3. **SDK behavioral compatibility or trust.** Neither successful compilation nor
   equal helper/CLI output proves an arbitrary selected SDK has the same runtime
   behavior, always returns that default, is untampered, or is qualified. A
   package can emit the expected bytes while differing elsewhere or under other
   conditions. This stronger claim needs separately defined distribution trust
   and compatibility evidence; it is outside one-asset packaging.

Comparing copied-SDK helper output with CLI-linked default bytes is **necessary
only if the selected policy requires those two observed defaults to agree**. It
is sufficient to test that narrow byte-agreement predicate when both values were
derived through their APIs and checked without substitution. It is unnecessary
for the weaker claim that the asset contains the copied SDK's validated observed
default, and insufficient for arbitrary-SDK behavior or provenance. A proposal
that rejects differing defaults must call this a new, deliberate Android create
compatibility restriction and test its diagnostics; equality must not be sold as
SDK attestation. Keep iOS-only creation outside an Android-specific helper path.

The minimum selected data contract should require shared mode, the existing
default identity/recipe, an empty resource catalog and system-sans typography,
with exact policy details stated rather than inferred from a filename. A valid
but different custom/platform-specific descriptor is not automatically this
default. If byte equality with the linked default is selected, it already fixes
all these default values; avoid describing separate string checks as a substitute
for canonical API derivation and validation.

## Obligations for a minimal implementation proposal

| Area | Review obligation |
| --- | --- |
| Owned files | Enumerate generation/default helper, package dependency if needed, narrow Android driver change, focused tests and verification outputs. No renderer, Activity/JNI ABI, signing/update authority, application branding or unrelated hosted code changes belong to this slice. |
| Generated path | Choose one exact internal source path and state which existing digest covers it. Keeping it below the generated locked adapter is one small option; placing it outside both locked snapshots requires an explicit integrity mechanism. Do not use app `Resources` as a loophole. |
| Snapshot order | Derive from the selected source snapshot as claimed; put the final validated bytes in place before finalizing their covering digest. If any helper executes selected SDK code, check before/after snapshot identities and reject observed source mutation. State that this is local mutation detection, not hostile-code isolation. |
| Generation failure | Missing API, helper/build failure, incompatible/noncanonical/oversized/unsupported output, timeout, unexpected output, output path misuse or mutation must leave no destination project. Preserve a pre-existing destination and remove owned scratch/staging without deleting unrelated files. No stale/default fallback. |
| Helper ownership | If execution is chosen, define a fixed, owned host entry point/package, copied-SDK resolution, private scratch/output paths, exact compiler/tool identities, bounded elapsed time and output, and cleanup on failure. Keep machine bytes distinct from diagnostics (a bounded output file is an option). A narrow helper or runner overload can meet this; a broad unrelated ProcessRunner overhaul is not required. |
| Host trust | Building a supplied SDK runs its manifest/build code within the user's host trust boundary. A helper cannot promise sandboxing against a malicious same-user package. Scope any source/output guards accordingly. |
| Build admission | Swift CLI and direct driver must require the exact locked regular descriptor input, bounded length and selected data contract before creating, deleting or replacing build outputs. Input edit/remove/rename, symlink/redirect and unsupported resource/font cases fail closed. Existing SDK/adapter drift checks stay in force. |
| APK path and identity | Add only the fixed `assets/MixerAppearanceV2/descriptor.json` entry; never recursively copy arbitrary asset roots. Require the complete final APK `assets/` inventory to be exactly that singleton, with multiplicity one and exact byte/hash/length identity with the admitted locked file. Reject unexpected assets and duplicate ZIP names, not just a missing descriptor. Preserve rejection of unexpected signing/example content and existing source mutation checks. |
| Receipts | Record derivation policy, relevant source/SDK/adapter/default/helper identities, tool argv/versions, raw outputs, descriptor length/hash, final single APK-entry identity, source before/after observations and cleanup. Retain original SDK/adapter digests as well as any extra descriptor identity. |
| Scope language | The result is an unsigned local packaging prerequisite. It supplies bytes for private installed capture, without making the public Activity consume them or proving V2/native/OS/design behavior. Schema-1 UI packets need no invented appearance field for this step. |

Adding a file below an adapter digest is sufficient for unchanged-lock edit,
remove and rename detection. It is not evidence that a user who intentionally
rewrites every local lock selected a qualified SDK or obtained signed authority.
Canonical/semantic admission remains useful so malformed data cannot be accepted
merely by matching an intentionally updated local hash. This distinction should
be covered in tests and claims without expanding the slice into a signing system.

## Evidence required after a proposal is frozen

These are future verification obligations; none has run in this review.

- Focused Debug/Release generation and lock tests should use the actual API,
  including fresh create from a relocated selected SDK, deterministic canonical
  output, iOS-only creation behavior, default disagreement under the selected
  policy, missing API and failure cleanup. Add timeout/noise/oversized output
  coverage if an executing helper is part of the implementation.
- Both CLI and direct driver should reject independently edited, removed and
  renamed descriptor inputs before touching output sentinels. Verify canonical
  and semantic rejection separately from digest drift by constructing an
  intentionally relocked malformed/unsupported fixture. Preserve rejection of
  arbitrary app resources, unused resource catalog entries and bundled fonts.
- A fresh built CLI should create a fresh Android project from the documented
  selected SDK and build its actual unsigned APK with official cross tools.
  Inspect the final ZIP independently: complete singleton asset inventory,
  fixed name, multiplicity one, exact bytes, bounded length and hash match.
  Retain class/DEX/native/lock receipts
  as appropriate to changed inputs; no repository/precompiled source leakage.
- Failure controls should exercise missing/malformed/duplicate APK asset and
  admitted-file drift during packaging where the implementation can encounter
  them. Host-only helpers may test ZIP checks without a full native rebuild.
- Do not claim native `InstalledAppearanceV2.capture`, V2 publication,
  lifecycle/environment refresh, API28–35 support, interaction/accessibility,
  resource/font support, design parity, phone matrix, external immutable
  FieldLog consumption, signed presentation/health, store release or GA passes.

Computer use, native simulator/emulator runtime tests, screen capture and UI
automation remain paused. Phones remain disconnected. This review starts no
native or capture processes and performs no process/device discovery. It reads
no frozen hosted inspector/authority/WorkerV2/broad hosted harness and no
Patch/Skip implementation artifacts. No product/compiler tests, dependency
installation, commits, pushes or root status/gate edits occurred in this lane.

## Questions reserved for the frozen proposal

1. Which of the three provenance claims is selected, and what precisely happens
   with a valid independently supplied SDK whose default differs from the CLI's?
2. Which fixed internal path covers the descriptor, and when is its covering
   digest finalized relative to generation and any executing helper?
3. How are canonical/default/no-resource/system-font constraints enforced at
   creation and at direct-driver admission without duplicating a theme table?
4. If a helper executes, what owns it, bounds its time/output and cleans its
   scratch space while retaining a useful failure diagnostic?
5. How is the final aligned APK checked for exactly one fixed asset with the
   admitted bytes, including duplicate-name and malformed/relocked negatives?
6. Are all acceptance claims limited to this data/packaging prerequisite, with
   public V2 routing, API36/private gaps and final product evidence still pending?
