# Root-bound layout probe v3: finite publication cutoff

This separate source/offline packet completes the remaining R02 publication
correction. No compiler, version query, child workload, product runtime, native
runtime, UI/capture, phone, network or global process inventory is authorized or
started by preparation. Root must release one exact frozen plan after independent
review before the one compiler-only command can run.

The original 173-member packet remains immutable, with seal SHA256
`c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9`.
The complete 16-member v2 packet remains immutable, with seal SHA256
`76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8`
and plan SHA256
`ac581da773865faf19b72eef8f2b12d3693b6e691ca910130f4e01f97e241c3d`.
The preaccess oracle and both frozen reviews remain unchanged. The original
v1/v2 commands were never executed. Their preparation results supply no actual
compiler diagnostic or numerical layout qualification.

## Finite signal observation

The runner completes or rejects all compiler work, owned child/group cleanup,
source/tool/output hashing, generated-build cleanup and diagnostic parsing before
calling `publication.publish`. It then sets one one-way
`publication_cutoff=True` flag before snapshotting pending handler observations.
The assignment is the logical boundary. Its reported monotonic reading occurs
after assignment and does not replace that boundary.

All four catchable handlers still record and return. A handler observation before
the flag assignment appends to the pre-cutoff pending list. Python executes these
handlers on the same main thread, so that handler completes before interrupted
main-thread code continues to the assignment/snapshot. Every pre-cutoff pending
record is therefore included in the frozen snapshot and rejects acceptance,
including a request after the last protected work checkpoint.

A handler observation after the assignment is outside the completed observation.
It updates only a bounded in-memory count and last classification, then returns.
It cannot append to or change the frozen pre-cutoff records or acceptance decision.
The receipt explicitly promises only the pre-cutoff evidence. No promise persists
every later signal, including a signal between assignment and snapshot or during
either publication write. The completed scope concerns handler observations, not
an unknowable physical arrival time before Python dispatches a handler.

After the cutoff, only finite evidence serialization/publication, signal handler
restoration and return occur. No compiler, child, source/tool hash, parse, product
work or owned-artifact cleanup occurs. The cutoff cannot be reopened or entered
during an active unretained launch. Existing v2 record-only launch handlers,
internal process-handle retention, protected work checks, strict JSON rejection,
unmodified inherited mask and unconditional owned cleanup are preserved.

## Observation precedes final receipt

`diagnostic-observation.json` is published before constructing and publishing an
accepted `receipt.json`. Both use bounded JSON serialization and a write-once
staging file, closed before atomic non-overwriting publication of the final name.
No accepted receipt can be published for an observation that failed publication.
An observation write exception yields a rejected receipt. A receipt write failure
can leave the already published observation, but no final accepted receipt from
that failed write. Staging members remain as local evidence and are never treated
as final receipt names. A failed command is not retried automatically.

The clock is checked before evidence, after observation publication, while
serializing/staging each runtime JSON file and immediately before its final-name
publication. A deadline failure refuses final accepted publication. Catchable
post-cutoff signals never interrupt the writer or reclassify the completed scope.

## Offline controls and unchanged execution proposal

All previous 42 synthetic/offline controls remain. Twenty-two fresh controls
exercise all four signal numbers immediately before cutoff, between assignment
and snapshot through the injected clock, during the observation write and during
the receipt write; observation/receipt writer failures; deadlines before evidence
and after observation; one-way cutoff and active-launch refusal. The real
publication state machine is called with fake clocks/writers. No actual signal
is sent, no subprocess is started and synthetic sizes are never stored as product
observations.

`correction-delta.patch` reconstructs the complete execution/control code delta
against v2. The unchanged diagnostic parser and strict JSON module remain pinned.
`prepare.py` checks both original/v2 sealed membership sets before creating this
new plan. `check.py` pins all nine v3 scripts, verifies the original 173 and v2 16
members, checks frozen preaccess seal members, replays the exact three source edits
and rehashes the toolchain and both source146 trees. `verify_and_seal.py` performs
custody checking, all 64 controls and custody rechecking in one Python process,
then freezes v3. Command, Python identity, tree identities and outputs are retained
in the preparation receipt and `commands/final-offline/` receipt.

Original146 remains
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`;
diagnostic146 remains
`2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e`.
The exact compiler argv, full environment, cwd, original two insertions and actual
closure expression replacement, 28 named queries and actual closure, expected
56 E0308 plus two E0512 diagnostics and fail-closed diagnostic/source binding are
unchanged from both prior plans. Exact byte/hash comparisons enforce these facts.

Root release permits one compiler invocation with no automatic retry, work by 44
seconds, owned cleanup by 49 seconds, posthash/parser/artifact handling by 53.5
seconds and evidence publication before 55 seconds. The exact argv still targets
the original transient `build/layout-proposal.rmeta`, absent before launch and
execution-owned only after root release. Sealed original/v2 source and evidence
remain immutable; all new runtime command outputs belong to v3. Exact PID/group
absence and child reaping must be confirmed before generated artifacts are
deleted. Ambiguous artifacts are retained. Intentional compiler exit 1 remains
diagnostic evidence only.

The proposed later command is the pinned Python tool with `-B`, this packet's
`run.py`, `--plan-sha256` containing the exact new plan digest, and
`--root-release-sha256` containing the later root release receipt digest. This
preparation does not create that release or start the compiler slot.

Actual diagnostic strategy behavior and all actual layouts remain unqualified.
Work/storage prices, backing capacities, simultaneous peaks, root/child and
forgotten-result funding, full ownership, canonical product integration,
FieldLog/OTA, paused native/device checks and every GA gate remain pending.
