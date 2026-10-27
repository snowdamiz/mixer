# Selected-profile adoption evidence candidate

`source/vm` is the selected private implementation. The immutable loader and
independent review inputs are identified in `preparation/input-custody.json`;
root's exact implementation selection is retained as `selection.json`.
`CONTRACT.md` describes the implemented scope and limitations. `receipt.json`,
`accounting.json`, `source-manifest.json` and `seal.json` are produced after the
final matrix, evidence checks and owned cleanup.

The packet retains actual command arguments/environments, target/tool/source
identities, stdout/stderr, every initial failure, compiler-variant manifests,
full fresh build/session/source preimages, per-configuration layouts and the
literal migration. Earlier discovery inputs and failed attempts remain
historical evidence. They are not current authority or accepted layout tables.

The frozen packet's scripts must not be rerun in place. A reviewer should copy
the final source/harness into separately owned scratch, record changed runner
bytes and actual compile/session context, and preserve the frozen candidate.
The original loader and independent packets were read and verified; their
frozen orchestration was never rerun.

No canonical source or root metadata, commits, pushes, production publication,
native/mobile runtime, UI, capture or process inventories are part of this lane.
Independent review, root acceptance and the broader product gates remain
separate from successful host controls.
