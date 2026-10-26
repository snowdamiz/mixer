# Android source-pair.5 canonical inventory reconciliation

Status: bounded source audit and legacy appearance host compile passed. This packet
proposes policy; root selects the amendment and integration implementation.

The mismatch is an inventory-contract omission, not an extra new product source.
The current canonical Java directory has **20** files: the **17** Java subjects in
profile.4, two older appearance sources, and the named instrumentation probe.
Applying the accepted sixteen-source editor candidate replaces three profile.4
subjects and adds NativeEditorConnectionV2, producing **18** profile.5 Java
products and **21** files in the full canonical directory. Keep the profile map
at 22 SDK / 24 adapter entries; the two appearance sources and probe never enter
that product map or projection.

The exact legacy files are:

| Canonical-only name | Bytes | SHA256 |
| --- | ---: | --- |
| AppearanceDescriptorV1.java | 15,759 | `0b3afc54df5a8943d873c5ea3941d3843f233bf48ac9354b0ff1250d6017d009` |
| AppearanceResolutionV1.java | 16,316 | `c3737cbd05d71fb13cd4e105a212b67c946c4ebc9fbf020ba2e9bf5ceccf2934` |
| AdapterInstrumentation.java (separate probe) | 4,209 | `40e0d4643870aeee1c8ad5575aca89c1a026d7f243fe455c7920edde8fa1868c` |

Both legacy appearance sources have real retained control consumers. The
DescriptorTests compile invokes AppearanceDescriptorV1.decode; ResolutionTests
invokes that decoder and AppearanceResolutionV1.prepare; DescriptorV2Tests invokes
the V1 decoder to preserve cross-version rejection and the retained V1 golden
positive. A fresh explicit nine-source host compile passed with actual Homebrew
JDK27, `--release 17 -Xlint:all -Werror -proc:none`, empty classpath/sourcepath.
All 108 emitted classes are hashed. Saved javap output proves those exact call
references. The classes were removed after hashing; exact copied inputs remain.
The controls were compiled, not executed against their fixture/oracle corpus.

These two appearance sources are separate from the protocol's **five V1 renderer
compile baselines**. The frozen roster assigns all five to NativeRenderer.children:
removeViewAt, addView, setMarginEnd and both setLayoutParams branches.
NativeOwnerV2ConcreteHostTests:581-591 retains V1 apply/reuse, button/toggle/field
events, hierarchy replacement and explicit callback/BCI coverage for those five.
The protocol requires their fresh preservation separately. This audit does not
rerun or newly qualify those behavior rows.

Current `AndroidSDKCompatibility.swift:348-359` admits input mapped product paths
and closes the engine runtime directory, but closes app/src only for exported
input=false trees. Thus profile.4 canonical admission historically tolerates all
unmapped Java siblings, including the two appearance sources and instrumentation.
Neither their names, sizes nor hashes are pinned by that existing Swift input
policy. The root's frozen amendment names only AdapterInstrumentation as an
exception, so it omits the existing legacy pair when proposing a closed inventory.
The probe's canonical bytes match its frozen protocol source copy exactly.

`AndroidProject.snapshot:34-45` exports exclusively the compiled adapter_files
map. It omits both legacy appearance sources and the probe. The exact exported
Java-name assertion at AndroidProjectTests:28-36 lists the existing seventeen
products. The generated Python driver closes exported app/src against the map
before its Java discovery/compile. Canonical native/android/build.py:35 instead
globs the entire canonical source tree and therefore includes the old appearance
sources and probe in its separate local checklist build. Do not delete canonical
files to repair an export-admission inventory: that would discard real legacy
control source and conflate the two source closures.

The product-only copied adapter form is also intentional:
AndroidSDKCompatibilityTests:231-245 copies only profile.adapter_files and calls
admitInput successfully before its negative mutation. Requiring the legacy pair
in every input would regress that accepted input form. Proposed policy therefore
makes each of the three explicitly named, hash-pinned canonical-only extras
independently optional; see proposed-amendment.md. The optional set does not
permit any other sibling or relax exported inventory.

The frozen integration protocol seal, root inventory amendment, accepted candidate
seal and root acceptance hashes match the supplied identities. All sixteen
accepted source member identities were checked. The proposal's old unaccepted
source hashes/digest were not substituted for the accepted candidate. The current
profile4 canonical subjects and the accepted16 differ exactly in
NativeAppearanceViewsV2, NativeCoordinatorV2 and NativeRenderer, plus the new
NativeEditorConnectionV2. The audited source map is rechecked unchanged at the end
of audit.py; its context revision is 62db9518c0c108cb44b81455c9be239df4ee00db.

No canonical code, metadata, lock, Git/network state, simulator/device, UI/capture
or other lane was changed. No process inventory was taken. Fresh actual Swift/
Python enforcement, generated consumers, complete selected host A/B, current
callback/descriptor/BCI mapping and SDK/D8 cross-qualification remain root work.
Native/physical/runtime, public V2, release/OTA and GA remain pending. Initial
javap flag and missing explicit GeometryV2 compile-dependency preparation failures
are retained separately; the corrected final compile passed.
