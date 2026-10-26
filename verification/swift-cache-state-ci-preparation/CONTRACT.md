# Closed cache-state fixture CI candidate contract

Status: implementation preparation authorized by root selection
`6628509512df7fd4bd69a4f45e4a9374c0b1653079a49236d8a2a0f69e67b0c5`.
No canonical CI/workflow integration is selected by this packet.

Each invocation has a fixed 600-second active deadline, at most 60 seconds per
owned child process group, and a separate 60-second evidence-retention/cleanup
allowance. These bounds are never extended on failure. Execution is serial.
Every child runs in its own session; terminal exits, timeout/group termination,
raw stdout/stderr, tool identities, command arguments, and executed artifact
hashes are recorded. Cleanup addresses only owned groups and owned scratch.
No global process discovery, native runtime, UI, capture, physical device,
compiler installation, live VM, or target invocation is permitted.

The runner will accept only actual stable Rust 1.99.0 or 1.98.1 on
`aarch64-apple-darwin`, using edition 2021. A selected compiler must pass every
fresh check in the invocation. Other compilers fail closed. The source requires
slice::as_chunks (stable since Rust 1.88); the Unix File/MetadataExt implementation
also restricts this proposed qualification to a native Unix host. No unsupported
compiler fallback or target-layout extrapolation is allowed.

The closed pack contains exact selected three-file library bytes, its exact
producer tests/oracles and API probes, fixed historical framing vectors,
independent scalar-cursor controls, and expected method/API/layout/File-result
inventories. Parent analyzer and envelope bytes are byte exact. cache_state.rs
remains `f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`,
including historical comments. No caller-supplied manifest/hash map, pack path,
readiness override, test filter, budget, or expectation is accepted.

Per Debug and optimized mode, complete inventories cover 84 host, 108 producer,
and 98 inherited-independent methods; their normalized overlap is explicitly
122 distinct methods. Three selected producer private controls and seven
independently authored controls add ten distinct private methods (132 total).
The derivative for those controls appends only two fixed cfg(test) module
declarations to a scratch copy; production bytes remain unchanged. All methods
of that derivative are executed: its 84 embedded host methods plus ten added
controls, with no ignored, skipped, or filtered method credit. The fresh list
and execution inventory must match exactly, including filtered counts for the
explicit producer partitions. Producer Debug uses seventeen individually named
root methods plus the 91-method embedded group. This complete grouped coverage
does not pass or erase the original single-command 60-second timeout, and is
not a performance-equivalence claim. The original timeout remains historical
failed evidence.

Per mode, all 25 API dispositions must match, including two positive executions
and 23 negative primary diagnostic/code/source-byte/span obligations; all
23 complete accounting layouts and exact 29 public File cases (27 complete
32-value observations plus two outer errors) and two private poison File cases
are required. Exact input/report hashes and complete result first lines are
compared; mutable inode/timestamp observations are retained without pretending
they are immutable expected values. Private admitted/malformed states carry no
general public File reachability credit. The seven independent methods retain
their complete layout and finite-case output obligations.

Output must be fresh, nonsymlinked, owned, outside immutable prior packs, and
under this candidate's run directory. Before/after runner, interpreter, compiler
launcher, selected real compiler, pack, and source identities are checked.
Scratch sources and artifacts are hashed before deletion; errors/raw outputs
are retained, content is deduplicated by verified hashes, and interrupted cleanup
preserves recoverable scratch. This assumes a quiescent trusted checkout and
does not claim adversarial filesystem custody. Nothing grants semantic/full
replay, arbitrary public admission, runtime/ABI/stack/RSS, native, signing/store,
FieldLog immutable release, customer/operational, or GA qualification.

Existing framing/envelope CI packs, tests, and runners stay immutable. The proposed addition requires the full eleven-minute bounded allowance inside
a 30-minute job. Root observed current Swift core duration about 12m24s including
checkout and capability duration about 18m30s; these are separate job timings.
Root must review actual workflow placement before integration. A second compiler
is a separate invocation and cannot be silently added to that same allowance.
