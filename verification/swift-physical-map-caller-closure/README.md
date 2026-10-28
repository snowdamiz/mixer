# Caller and Closure saved-artifact mapping

Status: **incomplete**. Neither Caller nor the exact Closure at source 861:36
has a uniquely identified LLVM definition or assembly function in this capture.

The two exact accepted raw artifacts were indexed in full: 3,758 LLVM definitions,
145 declarations, 174,794 LLVM metadata records, and 3,758 complete assembly CFI
functions. `run_one_admitted_fixture_v1` has zero literal occurrences anywhere
in either artifact, including definitions, declarations, debug records, instruction
references, symbols, and comments. The one debug file record for
`initial_profile_v1.rs` has 50 directly attributed subprograms; none has source
line 853 or 861. This negative evidence does not establish a DCE, private-linkage,
renaming, or capture configuration cause.

Both original source and retained MIR anchors match the exact `target-frontier.json`
file/span pins. Their presence does not establish an actual native function.
The complete target anchor excerpts are retained as `caller-source.txt`,
`caller-retained_mir.txt`, `closure-source.txt`, and `closure-retained_mir.txt`.
Source spans are exactly the selected frontier anchor spans; the Closure source
excerpt is the exact expression rather than a complete containing function.

`mapping-report.json` is the machine-readable result. The LLVM and assembly
indexes identify every whole definition/function by byte/line span and whole
SHA-256 over the retained original artifact. Byte spans are zero-based and
half-open; line spans are one-based and inclusive. Assembly ranges explicitly
start at the function symbol label and end after `.cfi_endproc`; directives before
the symbol are excluded. These complete inventories contain no selected target
body, and there are no Caller→Dispatch or Closure→Body native edges to report.

`index-method.json` and `finalization-index-method.json` were written before
their corresponding raw-artifact access. Before/after pins match. The two distinct
raw inputs total 58,805,427 bytes, below the 64 MiB bound; derived files remain
below 8 MiB. Each inspection command had a 55-second alarm. No raw input was
changed or removed. `final-seal.json` freezes this folder's report, complete
indexes, excerpts, inspection methods, scripts, receipts, and input pins.

Only bounded Python standard-library inspection was run. No compiler, linker,
native product runtime, tests, model, external version tool, geometry verifier,
UI/capture, simulator/emulator, or physical-device process was invoked. No source,
flags, wrappers, reachability, product code, or global status metadata was changed.

Geometry, arena identities/offsets, return-slot aliases, frames/call peaks,
capacity, backing, destruction/unwind obligations, prices, and root funding remain
unknown. The map does not accept a certificate, physical peak, semantic frontier,
or GA gate. Root must independently review the merged four-target map and select
any future step. There is no authorized automatic retry or substitute capture.
