# Dispatch and Body saved-artifact mapping: INCOMPLETE

The exact accepted artifact pair contains no uniquely identifiable actual LLVM
definition or assembly function for either selected target. There are zero literal
occurrences of `dispatch_v1`, `run_prepaid_admitted_fixture_v1`,
`AdmittedFixtureOutcomeV1`, `ReservationV1`, or `PrepaidOwnedV1` anywhere in either
file. No Dispatcher instantiation, Body linkage identity, source/debug linkage
chain, whole native function span/hash, or native call edge can be supplied.

`index-candidates.json` records complete input coverage, 3,758 LLVM definitions
with matching closing braces, and 3,758 assembly CFI function starts and ends.
`llvm-target-metadata-hits.json` contains only an `initial_profile_v1.rs` DIFile
mention; file metadata is not a function definition. The separate Caller/Closure
lane also reported no identifiable Caller/Closure native definition or edges.
This observation does not establish the cause of codegen omission. Private
reachability or dead-code elimination is a possible explanation, not a proven
fact or a basis for changing the capture.

The Dispatcher source is pinned at `host_account_v1.rs` lines 133–141; Body at
`initial_profile_v1.rs` lines 863–883. The original source and retained MIR slices
are copied in full with file and span hashes in the index. The Dispatcher MIR is
the generic template and is explicitly not proof of an actual admitted
monomorphization. The accepted source146 tree identity is retained as upstream
custody; this lane rehashes the two exact source anchor files and the retained MIR,
without claiming a fresh verification of all 146 files.

Method: `inspect_saved.py` uses Python standard-library byte/text inspection only.
It verifies the root-selected capture acceptance/frontier and independent terminal
seal pins, reads both saved artifacts fully, hashes disk bytes before inspection,
indexes every LLVM `define` through its complete closing brace, checks identifier
hits across all bytes (including declarations, globals, metadata and assembly),
and hashes both disk files again afterward. Candidate function extraction would
retain a complete definition with byte/line spans and whole SHA-256; neither target
has a candidate. The only retained compiler-output excerpts are explicit module
context prefixes in the index and the matching DIFile line. The empty structural
excerpt and candidate lists are absence evidence, not truncated functions.

Run command:

```text
python3 verification/swift-physical-map-dispatch-body/inspect_saved.py > verification/swift-physical-map-dispatch-body/inspection.stdout 2> verification/swift-physical-map-dispatch-body/inspection.stderr
```

The command enforces a 50-second internal alarm within the selected 55-second
command bound. The selected pair totals 58,805,427 unique raw bytes under the
64 MiB bound; rehash passes inspect the same preserved pair. Derived outputs remain
under 8 MiB. The final index records the current repository revision and Python
version; no compiler, compiler-version probe, linker, native binary, model, test,
UI automation, simulator/emulator, or geometry verifier was invoked in this lane.
An early metadata inventory command returned an explicitly truncated broad Git
status; it contained no compiler function inspection. Later repository output is
scoped to this new lane. No raw compiler artifact was modified or removed.

All requested native facts, numeric region geometry, aliases, capacity, prices,
backings, call peaks, cleanup/destruction, actual geometry-verifier input,
certificate/physical-peak acceptance, product acceptance and GA qualification
remain pending. This report authorizes no capture retry, source/flag/wrapper or
reachability change, fallback symbol, publication, credential change, or native
runtime work. The existing local custody, UnitA, computer-use, native-runtime and
device holds remain. Root independently reviews the merged four-target map and
selects any future work.
