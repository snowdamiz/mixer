# Independent R03 followup

Recommendation: **accept this exact finite host read-completion correction.**
R03 is corrected without increasing the32-attempt or512-byte per-read limits.
The original C01 raw-stdio ownership/cleanup requirements remain satisfied by
fresh unchanged independent controls. No material new finding was observed.
This is a scoped host recommendation, not complete composition or product release
acceptance, and it does not resolve any real OS close ambiguity.

## Exact custody and source delta

Before candidate reads/imports, all201 declared regular members and757,707 bytes
verify against seal
`c79bd64dc0019c17f03b17df0a6bd5dc8879334d64fbf74f92507d75a5e81f54`.
Its actual schema declares no self-seal sidecar: the exact directory contains201
members plus seal.json. The first tool-only verification attempt incorrectly
assumed the prior76-byte sidecar convention, and its extra undeclared-sidecar
lookup raised FileNotFoundError after all201 members verified. Corrected exact
schema custody completed before any candidate source import. This reviewer
assumption is preserved in initial-custody-assumption.json, not called a packet
defect or hidden as a passing command.

The659-member original candidate seal
`01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2`
and340-member original independent seal
`af9f20a00000cdbac6f772e19088e0c9ce078530386cb62d41d693954b832040`
also verify exactly, including their declared76-byte sidecars and directory
coverage. That prior review is unchanged. Its original required failures and
preliminary test-expectation correction remain sealed as historical observations.

The copied old prototype is exactly
`54d8b967b996ff273039824fffa6042e9ca9ef383079ce1427aadf45f23114a1`;
the copied new prototype is exactly
`af8d04f4940bca83c341d72970ef088852e27919305cda7aa7d53396ea2d2ccf`.
An independent byte-level comparison verifies that the new source is precisely
the old source with this one line inserted before the read-attempt refusal:

    if remaining==0:return b"".join(parts)

independently-computed.patch records that exact delta. All other prototype bytes
are identical, as are old/new schema.py, consumer.py and test_preparation.py.
No producer prepare/freeze script was rerun. The exact original independent
boundary_case.py and mixed_child_case.py were copied without changing any test
body or oracle. Old-source replay uses an isolated path layout; the original
case bytes themselves remain identical. Every fresh command receipt records
its executed test-source and prototype-source digest plus raw stream hashes.

## Completed32nd reads now succeed without a33rd call

The original independent read chunks32 and interrupt31 cases are rerun unchanged
on old and new source. Both old commands retain exit1, raw failed success
assertions, Refusal("stdio-read-attempts", "stdio-access") and healthy cleanup.
Both new commands satisfy the same original required-success assertions:

- 32 real one-byte reads complete read(32) within32 calls and return the exact
  requested bytes;
- 31 controlled InterruptedError events followed by a real32-byte read on call32
  complete the request and return those exact bytes.

The new post-loop check recognizes a completed request. It performs no new read,
seek, close, allocation of an owner or admission change. The loop still performs
at most32 source-level os.read calls. Requested size still requires exact int in
0...512, so negative,513, bool and float requests refuse before any read.

All16 root boundary controls are copied byte-identically and freshly replayed
against each source. New source passes all16, including the512-byte maximum
completed through32 real16-byte reads, zero/one-byte reads,31-call completion,
EOF on call32 and short-data/EOF completion on31/32. The wrapper records actual
OS-read lengths and asserts that a33rd call is never attempted. The three old
full-completion schedules still retain their required failure dispositions;
their expected exit1 is command bookkeeping, not a passing behavior result.

Incomplete operations continue to fail closed. read(33) from one-byte chunks
stops after32 calls;32 EINTR events stop after32; read(512) with31 EINTR events
and only a short nonempty result on call32 refuses because it has neither filled
the request nor observed EOF. The correction does not accept those partial results
or spend a33rd call. EOF on32 after31 EINTR events correctly returns an empty
byte string. These distinctions preserve the original attempt and byte limits.

## Actual fixed-child and C01 cleanup requirements

All63 independent required behavior cases from the original review are freshly
rerun against new source with their bodies/oracles byte-identical. All63 pass;
the original two R03 failures therefore become passes only through the prototype
change. This set includes all eight one/two-stream pre/post close schedules with
primary, completed observation or both; a KeyboardInterrupt close error; both
raw acquisition positions and captured-birth/prepare/unlink failure boundaries;
partial second acquisition combined with first-owner pre/post cleanup errors;
path and descriptor reuse; repeated close; and24 rounds collecting48 successful
old owners while fresh owners naturally hold the reused numbers.

The same controls still require every independent known close capability to be
consumed at most once, every other owner to be attempted after an error, and the
exact primary/completed-result/all-cleanup-error identities to survive. Access
after close begins refuses. Uncertain descriptor/name obligations remain in their
ledgers, keep healthy_zero false and block new retained/stdio admission. No saved
number retry or uncertainty erasure is permitted. Known pre/post syscall fates
are controlled test oracles; they never authorize real uncertainty retirement.

The actual unchanged fixed child terminally exits0 and is reaped using its owned
process reference. Its independent profile/body hashes join the observed report.
The byte/EOF distinction is also freshly verified at that actual helper boundary:
30 EINTR events, short report data on31 and EOF on32 return the exact child result;
31 EINTR events and only short report data on32 refuse within32 calls. Both paths
close parent stdio and retained owners to healthy zero after terminal child reap.
The latter refusal remains an intentional bounded refusal, not an R03 failure.

Additional actual child cases preserve the identical completed child-step tuple
through stdio cleanup faults, and preserve that tuple together with a later exact
primary. The byte-identical nested mixed-child case also combines stdout post-close,
stderr pre-close and retained pre-close faults. It retains all three exact cleanup
exception identities, the exact KeyError primary and identical completed child
observation; every independent retained descriptor is attempted once. Deliberate
uncertainty remains explicitly nonzero after fixture deletion and at process exit.
The result is a completed child-step observation, not completed whole-profile
post-consumer validation.

The exact26-method producer suite freshly passes without failure/error/skip and
includes all307 snapshot-leaf mutations. This source model still creates no owning
parent FileIO/BufferedRandom stdio object or closer finalizer; the one-line read
change does not touch the ownership/close code. The prior9 retained-owner,
65-descriptor-per-owner and2-stdio-owner logical bounds remain unchanged.

## Recorded evidence and limits

98 final fresh commands are retained:32 root boundary commands (16 per variant),
two exact original independent failures on old source,63 original independent
cases on new source, and one26-method producer suite. There are no unexpected
dispositions or timeouts. The five old required R03 failure executions remain
failed behavioral requirements, alongside passing new-source requirements.
The201-member candidate's90 retained command stream hashes/terminal dispositions,
16 new boundary results and57 stdio results (5 healthy zero,52 unresolved) are
also audited offline; those90 commands are not called independent fresh runs.

Each owned case subprocess is limited to20 seconds and terminally reaped. Actual
fixed-child success/error paths use source wait/kill/wait and are checked through
owned references. No process inventory is used. All owned scratch directories
are empty and removed after evidence collection. Process exit and directory
cleanup do not resolve an uncertain fd/name obligation. No real stuck OS child
or real OS-close ambiguity was created or qualified.

The unchanged142 retained-descriptor lifecycle-position cases are not freshly
rerun for this one-line read correction; their exact prior evidence remains in
the verified659-member packet. Fresh63 independent controls exercise the material
C01 cleanup contracts instead. Whole Python memory/RSS, arbitrary SDK/kernel
internals, fatal heap/asynchronous interruption, hostile direct private-module
mutation and adversarial filesystem/process rewriting remain outside this closed
quiescent-fixture model.

Actual Rust exporter/loader/build/session provenance, original typed result/all15
ledger joins, real8192-byte context, complete layout/work/lifetime accounting,
canonical integration/full target/new compiler or CI, native runtimes/devices,
simulators/emulators/UI/capture/physical matrix, immutable separate-repository
FieldLog packages, dogfood/OTA/store/operations/GA remain separately pending.
This lane uses no prohibited hosted catalog-inspector/authority-driver/
rejectedWorkerV2/broad harness read/import/execution, stopped Android startup
experiment, process inventory, canonical/index edit, commit, push or publication.
