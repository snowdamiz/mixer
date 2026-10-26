# Android default appearance packaging

This development slice implements the [root-selected narrow contract](../verification/android-default-appearance-packaging-root-review/implementation-selection.json)
from the independently reviewed frozen proposal. Producer evidence is retained in
[the implementation packet](../verification/android-default-appearance-packaging/).
Independent acceptance remains pending until a separate reviewer checks that packet.

`MixerBuild` explicitly links the existing first-party `MixerUI` product.
`AndroidProject.snapshot` calls one internal producer, which obtains
`UIAppearanceDescriptorCodecV2.mixerDefaultV2()`, calls the existing canonical
encoder once, decodes the resulting bytes with the actual typed codec and requires
shared mode, an empty resource catalog and system sans typography. It writes those
exact bytes to `app/assets/MixerAppearanceV2/descriptor.json` before computing the
adapter digest. No copied theme table, fixture, source scraper, Python codec or
additional emitter supplies the product descriptor. iOS-only creation does not
call this producer. No general-purpose dependency was added.

The generated driver checks the complete internal asset layout before any general
source hash can open its contents, before output creation/cleanup and before tool
inspection or compilation. `Generated`, the adapter, `app`, `assets` and
`MixerAppearanceV2` must be ordinary directories. The complete asset inventory must
contain the one expected descriptor and its one containing directory, including
names that the general source digest omits. The descriptor must be a regular file
without symlink redirection and contain 1–65,536 bytes. Both existing SDK/adapter
locks and app-resource refusal remain enforced. A FIFO, socket, directory,
symlink, hidden extra, renamed file or size violation fails before asset hashing.

Before packaging, the driver repeats the asset admission, checks exact admitted
bytes and the adapter lock, then passes only that assets directory through the
official AAPT2 `-A` option. After zipalign, it rejects duplicate ZIP names before
constructing the content hash dictionary. The complete final `assets/` inventory
must be exactly `assets/MixerAppearanceV2/descriptor.json`, once, with exact admitted
bytes. The receipt records its path, length, SHA-256 and packaging-only scope,
together with the existing source/tool/APK identities and commands. The existing
source before/after checks are retained.

The direct driver's validation establishes layout, type, size, local lock identity
and exact final archive bytes. It does not execute Swift/Java codec semantics. A
user can replace bounded descriptor bytes and recompute the unauthenticated local
lock; that does not become a canonical default, authentic package or signed
authority. The tests deliberately admit bounded nonsemantic bytes at the direct
layout layer to preserve this distinction. The checks observe local state and
repeat it; they do not provide race-free isolation from concurrent writers or
arbitrary package build code.

The source/bytecode export remains the accepted fourteen production Java sources,
the existing reusable Swift/JNI closure and the public V1 Activity. Packaging data
does not cause the Activity to read or install it. The separately copied
`--sdk-path` selection remains source-locked. Its default/API/ABI and published
distribution compatibility remain explicit prerequisites before public V2. A
fresh verification consumer may observe its selected SDK's codec/default equality;
that observation is not a compatibility policy for arbitrary SDK selections.

The collector uses dedicated bounded child process groups for host commands and
cross-compilation, preserves command outputs and failures, and removes only its
owned scratch after its children return and owned groups are gone. It runs the
focused CLI tests in Debug and Release and all `cli/build-tests`, creates a fresh
project through the actual built CLI, invokes its actual generated driver for the
complete Swift/JNI/Java/D8/AAPT2/zipalign build and inspects the final APK. It decodes
the extracted final bytes with the existing pure production Java codec and a host
Swift probe built from the fresh consumer's actual copied production
MixerCore/MixerUI sources. Product manifests before/after collection and retained
generated sources/classes bind the evidence. The packet records the concrete
observed outcome; this document does not promote a gate by itself.

The initial Python test attempt encountered the host AF_UNIX path-length limit;
the test now uses a short owned temporary path. The initial Swift test attempt
found a missing `try` in a new assertion; the test computes the throwing expected
value explicitly. Both failed outputs remain in the packet.

The final [run-2 receipt](../verification/android-default-appearance-packaging/run-2/receipt.json)
records six focused Swift test functions in each configuration (including six
Java drift cases and four descriptor drift cases), all 20 Python test methods and
the complete fresh unsigned build. The extracted descriptor contains 9,587 bytes,
SHA-256 `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3`.
The 28,028,802-byte APK has SHA-256
`740e8af341e371697b82d415b37b719078aee8859eb57c1fe8d258cdd319114b`.
Both production codecs accepted the final bytes; the observed selected copied
SDK default was equal. All fourteen exported Java source files and 160 compiled
classes match the retained accepted export evidence. The complete 241-file
first-party source manifest was unchanged during collection, and every owned
command group was gone before scratch removal. The first collector run also
completed its unsigned build, then failed because its historical class-archive
parser expected a leading directory before `classes/`; that collector defect,
its exact code, output, APK and cleanup receipt remain retained as run-1.

Computer use, capture and native simulator/emulator runtime checks remain paused;
phones remain disconnected. No discovery, native runtime, UI automation, install,
signing or publication is part of this slice. Installed V2 capture and lifecycle,
supported OS coverage (including the current private API36 versus product API28
gap), shared/platform-specific/custom appearances, resources/fonts, accessibility,
native interaction, design parity and physical-phone acceptance remain pending.
External FieldLog consumption of immutable published packages, signed installed
presentation/health, OTA/store/operational/release and GA qualification also remain
pending.
