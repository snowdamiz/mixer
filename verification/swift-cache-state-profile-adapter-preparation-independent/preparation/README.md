# Next Swift cache-state integration prerequisite

Proposed next slice: a crate-private adapter that derives the fixed 80,000 profile
rows from an actual `ValidatedSwiftReactor`, plus a bounded row-body File writer.
Exercise it against the real validator and the exact accepted closed fixture
consumer. This packet is preparation for independent review and root selection;
it contains no implementation, new retention model, target attempt or cap change.

The accepted scalar-cursor component already checks successful synthetic cache
transitions. Repeating that finite state work would not close the next dependency.
The missing link is the origin of each immutable function row: the accepted
consumer parses `MIXPRF01` but obtains its configuration from `MIXFIX01` and treats
digest slots as opaque echoes. A caller-authored row remains synthetic even when
its fields satisfy all parser checks.

The current sealed validator has the same source hash as the validator in the
accepted 132-member completion closure. Its existing crate-private
`execution_function(absolute)` returns the actual absolute function index,
validated type index, absolute source offset and body borrow. Imported functions
return `None`. This is sufficient to derive rows without decoding Wasm again,
learning identities from events, exposing constructors, or recovering offsets by
pointer subtraction. The live cache/control sources do not have the old
instrumented closure's hashes; that difference prevents a claim that a new
canonical runtime is already qualified.

Read `proposed-contract.md` for the concrete boundary and ownership,
`test-plan.md` for executable actual-source acceptance, and `source-review.md` for
observed seams and limitations. `input-manifest.json` identifies exact consulted
bytes; `offline-checks.json` records this packet's limited checks. Source snapshots
are evidence only and were never imported, compiled or executed in preparation.

The root remains controller. This lane changed only this directory and performed
no Git mutation, source implementation, workflow edit, root metadata edit,
compiler invocation, old harness invocation, native test, UI/capture operation or
process inventory. Actual Actions/Rust 1.98.1 qualification of the accepted
closedpack remains root-owned and pending in the reviewed input snapshots. No
GA or development implementation gate is promoted by this preparation.

This packet is frozen by `seal.json` and `seal.sha256`. A reviewer should verify
the seal rather than rerunning `prepare.py`, because root-owned context may move.
