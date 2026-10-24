# Private pan-commit harness v2

The original sealed packet and entire runtime under
`verification/apple-toggle-pan-commit` remain byte-identical. Its native run
failed: 43 XCTest methods, 26 passed, 17 failed, exit 65; one interruption case
has no verdict. Cleanup passed all five resources and preserved baseline states.
`prior-packet-tree.json` binds every one of its 3,229 entries. This new packet is
a separate harness correction. It grants no retroactive pass.

The private app source closure, app archive, public XCTest runner sources,
compiled runner product tree, and runner archive are reused identically.
`immutable-reuse.json` binds the copied bytes and original build provenance.
No Swift compilation or native instance/device discovery occurs in preparation.
The suite remains 43 methods: 13 original native input actions, 16 interruption
actions, 16 final-pan callback actions, and one scoped 36-component direct result.
Original strict checks and their four plain-reference failures remain failed.

The new oracle validates the exact historical event prefix, sequence, time,
field types and semantic metadata while allowing a finite nonnegative display
scale and rectangle size before attachment. The actual baseline, final state,
every hook state, and every new tested event require a positive finite scale and
positive finite attached geometry. No touch admission, recognizer identity,
translation, time, counter, event order, trait, latest binding or semantic check
is relaxed. Zero, negative, boolean and nonfinite scales fail actual input states.

`offline-replay.json` reevaluates all 16 original failed pan captures using these
rules. Each satisfies the corrected predicates. This is labeled
`DIAGNOSTIC_ONLY`, preserves each original failed verdict, and sets native
acceptance and retroactive pass false. A fresh complete native run is required.

The new reader opens only the canonical fixed Documents observation path with
`O_NOFOLLOW`, checks regular-file type, one link, bounded size, payload and
schema, and rechecks descriptor/path inode, link count, ownership, mode, size,
modification time and change time before accepting bytes. Parent/path redirection,
symlinks, hardlinks, in-place mutation, malformed data and oversized input fail
closed. A demonstrably superseded or missing atomic snapshot is discarded and
reopened; an unlinked descriptor is never accepted. Every opened descriptor is
closed on every path.

Root explicitly selected a small dedicated-process Bridge subclass for deadline
propagation. `observe` passes one absolute effective deadline to the reader.
`wait` only sets/restores the earlier of the session deadline and its existing
operation deadline around the unchanged inherited wait loop. Direct observations
use the earlier of the session deadline and 50 milliseconds. Each reader call
has at most four attempts, no sleep, and no refreshed retry window. Existing
six-second waits and 600-second session limits remain in force. All request,
endpoint, command, capability, persistence, instance ownership and independent
cleanup logic is inherited unchanged. All parent files remain immutable.

Prepare and verify from the repository root:

```sh
python3 -B verification/apple-toggle-pan-commit-harness-v2/prepare_reuse.py
python3 -B verification/apple-toggle-pan-commit-harness-v2/offline_replay.py
python3 -B verification/apple-toggle-pan-commit-harness-v2/host_controls.py
python3 -B verification/apple-toggle-pan-commit-harness-v2/seal_packet.py
python3 -B verification/apple-toggle-pan-commit-harness-v2/run.py verify
```

The host suite has 37 methods: 13 oracle methods, including captured-history
regressions and 527 explicit negative oracle mutations, plus 24 reader/deadline
methods with real temporary-file race controls. Receipts retain exact commands,
interpreter, source digests, outputs and original build tool provenance.

After root independently reviews and selects the actual new seal, root owns the
fresh bounded runtime invocation:

```sh
python3 -B verification/apple-toggle-pan-commit-harness-v2/run.py run --scope interaction --reviewed-seal ACTUAL_REVIEWED_SHA256
```

Recovery uses `run.py cleanup --scope interaction` in this new packet, with the
same reviewed identity and inherited independent cleanup. No runtime attempt is
made during preparation. Before correcting any rejected sealed v2 attempt, use
its `reject_preparation.py 'Concrete reason'` to preserve its exact named bytes.
Do not edit or reseal the original failed packet. Phones remain disconnected;
physical VoiceOver, production adapter, full parity, external FieldLog dogfood,
store, customer, operational and GA qualifications remain pending.
