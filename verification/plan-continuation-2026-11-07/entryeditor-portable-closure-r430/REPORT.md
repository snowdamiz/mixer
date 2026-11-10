The source-boundary experiment preserves the real EntryEditor behavior but does
not close W07/W08 admission. The unchanged owned runner validates and executes
all 80,539 bodies in the 53,905,562-byte candidate. Fresh baseline native,
candidate native and candidate guest outputs are identical: all 600 stdout bytes,
SHA-256 `884715f3cfb467df09c51c02d49acab371e34b6cab870dbbeae68248ad0c7623`.
All app/runner stderr is empty. The diagnostic reports `GuestExit(0)`, success,
completed logical cleanup, zero combined reservations and zero live tickets.

The tested premise was that the shared feature's mandatory full Foundation
closure is irreducible. This materially different source split isolates
`Workspace.report` and `matchingProjects` unchanged in `FieldLogFormatting`;
portable models and MixerCore imports use FoundationEssentials on Wasm. A shared
scalar-based trimming helper replaces CharacterSet trimming in the real model
and EntryEditor. UUID, Date, Codable/JSON, validation, state/effects, save-intent
application/result, exact bytes, the transaction port and every original fixture
assertion remain. Generic `error.localizedDescription` behavior is unchanged in
both EntryEditor and the fixture; no invented generic-error fallback is used.
The fixture source itself is byte-identical to R327.

The actual linker map still retains **33,976,096 bytes** in
`lib_FoundationICU.a(icu_packaged_data.cpp.obj):(.rodata.icudt76_dat)`.
Compared with R356's equivalent stripped build, the new source boundary removes
only 6,274 module bytes and five bodies (80,544 → 80,539). Strict TableMemoryV3
still rejects the 4 MiB module ceiling. The fixed reactor still rejects
80,539 against 79,966 bodies. No runner, capability, validation, VM, CLI profile,
production/default ceiling or policy is changed.

The remaining exact source operation requiring the full Foundation module is
`(any Error).localizedDescription`, including the unchanged in-memory port's
catch in `EntryEditorFixture.swift` and EntryEditor's validation catches.
`candidate-why-extract.tsv` directly records the fixture extracting
`libFoundation.a(NSError.swift.obj)` for
`$ss5ErrorP10FoundationE20localizedDescriptionSSvg`; NSError then extracts
CFError and NSURLError members. Other recorded CoreFoundation members extract
ICU formatting/collation members. `extraction-direct-facts.json` preserves these
specific edges. The dataset's actual retention is established by the map.
The extraction log does not supply a complete fixture-to-data-symbol path, and
is not per-function liveness proof; no claim is made that NSError alone causes
every retained byte, or that Foundation can never be reduced by another SDK or
reviewed public contract. The decisive scoped result is that extracting the two
formatting methods and replacing CharacterSet trimming does not remove this
closure while the exact fixture/generic-error contract is preserved. Another
flags-only loop is not justified.

All eight original `Tests/FieldLogTests` files from the pinned complete app ZIP
are retained. Seven are byte-unchanged; `FieldLogTests.swift` receives only
`import FieldLogFormatting` for the moved methods. The complete host suite passes:
**62 Swift Testing tests**, including the added exhaustive comparison of all
**1,112,064 valid Unicode scalars** against Foundation trimming plus combining,
nonbreaking-space, zero-width-space, Japanese, emoji and CRLF examples. Existing
shared EntryEditor, storage, task/presentation and Apple-host tests all execute;
XCTest discovers zero tests, so no XCTest count is claimed. This includes the
original report/search/date/JSON and repository tests. Exhaustive guest scalar
parity is not separately established; the complete original Unicode fixture
matches on the guest. The trimming proposal is not adopted on this evidence.

The first host build failed because the Apple SDK does not expose the standalone
FoundationEssentials module. The one correction changes only the host copies'
four import lines to the Apple Foundation umbrella; source logic and generic
errors are unchanged. Both failed and corrected raw outputs remain. There was
one Wasm compiler build (18.37 seconds including driver), one failed host test
build (10.58 seconds), and one corrected host test build/run (47.69 seconds),
all under their 180-second command bounds; no second Wasm variant was needed.
A preparation script had an unmatched-parenthesis SyntaxError before execution;
it changed no file and was corrected before either compiler ran.

Public ownership was sent to root before dependent edits. The new extension
module owns `report` and `matchingProjects`; `Workspace.trimmedText` is a new
public helper. All matching call-site files in the exact 65-member app archive
are listed in `ownership.json`: WorkspaceRepository, FieldLogTests and the iOS
WorkspaceView receive the formatting import in the candidate. The host package
wires and tests the storage/test consumers. The full app manifests, generated
Android packages and Xcode project are **not migrated or built**; the iOS import
is a source proposal only. This is an unaccepted module-ownership change, with
no canonical adoption or public-contract acceptance. Given the negligible
closure reduction, the patch is diagnostic evidence, not an integration request.

Inputs: R327 `inputs.zip` SHA-256
`d5bbfd08c49976c2249261cc88f90825acca149e5307459a90f7917f423e5e8d`;
R344 complete app ZIP SHA-256
`603cee687fda819414157a7eda0957e072a6097bb74d31fce69a31e2b0adba10`.
The EntryEditor in both archives is byte-identical before the one trimming call
changes. Wasm uses Swift 6.3.3 and `swift-6.3.3-RELEASE_wasm`; host tests/native
use Apple Swift 6.4.2 on macOS 27.0.1 arm64. Host tests combine R327's pinned
MixerCore with copied current canonical MixerUI/MixerApple sources; exact file
hashes are recorded, so this is not a claim to test immutable public SDK21d591.
Root Git was not used and no current revision is asserted. Original source
archive identities and source hashes identify the experiment.

Host load was about 18 across 15 CPUs. One compiler build ran at a time with
three requested jobs, chosen for this measured contention; the corrected host
build also explicitly requests three Swift frontend threads. This is not a
universal CPU limit or a timing benchmark. SDK/toolchain inputs are existing
platform tools; no new general-purpose dependency was added.

Delivery: `portable-boundary.patch`, `source/`, `host-source/`, `app-reference/`,
`ownership.json`, `original-tests-preserved.json`, `source-manifest.json`,
`artifacts/`, `artifacts.json`, `comparison.json`, `receipt.json`, `commands.json`,
`COMMANDS.txt`, raw logs, extraction TSV, compressed official linker map and
`link-map-largest.json`. `python3 compare.py` rechecks the retained complete
output, module/native/runner hashes, exact sources and preserved test files;
it does not claim to rerun the executables. Exact compiler/runtime argv and
working directories are in command metadata.

All work is isolated under R430. No canonical write, root Git, remote mutation,
credential/provider/customer action, child, device, signing, held namespace or
historical process access occurred. Every launched direct command returned and
was reaped; OS descendant-group absence was not independently measured. Owned
build/cache inputs are retained for reproducibility rather than deleted, as
recorded in `cleanup.json`. No device was created, so device cleanup is not
applicable. Independent slice review and root reconciliation remain pending.
Owned-Wasm filesystem durability/process restart, debugger, platform UI, OTA,
immutable-package, release and GA qualification remain pending. The host storage
tests do not convert the in-memory owned guest port into filesystem evidence.
