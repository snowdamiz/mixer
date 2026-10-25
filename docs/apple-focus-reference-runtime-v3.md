# Apple reference-first runtime preparation v3

V3 is a **host-only repair** of the rejected v2 packet. It passes the retained
111 producer controls and all 25 focused repair controls. The exact historical
33-control reviewer is also replayed: **32 pass and one unchanged assertion
fails because its lower-level synthetic journal is correctly rejected**. This is
not a 33/33 acceptance claim. Independent v3 review, fresh root selection and
native execution remain pending.

The frozen v2 producer and independent review remain unchanged, including their
10 failed independent controls. The reviewed v2 handoff remains
`78ada9ff4aa3392e07f4fdf71a0eb563c67c8fde920388609372b09a771f3668`.
Its rejected review handoff remains
`cf24502cf1201e22848628bf1e5254bb708b529006eb707c632b051e46ebb2f1`,
and its final review receipt remains
`3f4303a03dbcc955d6b7156b3ecf4db7d1a4466bcf14cf1c956f8e287a9cd6af`.
V3 rehashes every frozen member before and after controls. It never replays the
v2 packet, its scratch, or the retired authored-first runtime.

## What the repair changes

The actual composed Bridge writes `bridge-summary.json`. Its unchanged Session
and TransactionStore write `0000-settings-NNNN.json`, journal-linked
`settings-NNNN-ax.txt` and `settings-NNNN-png.png`, and retained UUID transaction
attempt directories. V2 rejected these normal outputs. V3 validates their full
closed relationships before collecting the four application evidence roles.
There is no broad filename-prefix exemption.

The new auxiliary validator requires:

- A closed bridge summary with the selected case, integer generation, no
  failures, no retained capability, at most one verdict, and agreement with the
  retained application generation and after verdict. A summary cannot create
  an application observation or a returned-key result.
- Contiguous, strictly shaped Settings journals with the selected device identity
  and canonical Session generation. The exact unchanged Session replays every
  request in memory. Reconstructed records must match the complete saved values
  and types. Valid partial prefixes are auxiliary evidence only.
- Every completed AX/PNG upload reconstructed by that replay to match its
  referenced original payload bytes. No unreferenced Settings payload is allowed.
- Exactly one retained canonical UUID attempt per journal. Each attempt must have
  a closed successful commit outcome, no ancillary failures, explicitly resolved
  guard retirement, exactly the journal and payloads for that transaction, and
  the original staged-to-published hard-link and byte identity.
- Rejection of an unresolved transaction guard, missing/failed/uncertain attempt
  outcome, ancillary failure, redirected path, substituted payload, duplicate
  transaction ownership, unknown artifact, or foreign generation/action name.

The validator returns only the fixed `begin`, `before`, `after` and `witness`
application files. Settings journals, payloads, attempts and bridge summaries
never become authoritative application evidence. They cannot establish an input
count, replace official attachments, or turn a missing observation into success.
The existing root-selected driver, official-result traversal, unique methods and
attachments, immutable capture, strict oracle and diagnostic outcome branches
remain binding.

The metadata repair now requires an exact integer `commandGeneration == 2`.
Each native file signature must be a four-member list: positive integer inode,
nonnegative integer nanosecond mtime, positive integer original byte length no
larger than the unchanged 16 MB observation bound, and a 64-character lowercase
hexadecimal SHA256. Booleans, floats, malformed digests and extra/missing fields
reject. The digest describes the original file bytes; V3 does not invent a digest
by reserializing a decoded observation.

## Exact wall-time ordering

The original filesystem signatures and `begunWallNS` are Unix nanoseconds.
Official result/attachment timestamps are Unix seconds represented by JSON
numbers. The original decimal tokens are retained separately using Decimal and
converted to integer nanoseconds exactly. Root ISO timestamps use integer
calendar/microsecond arithmetic. Authoritative wall-time comparisons have no
intermediate binary-float multiplication.

A baseline file must be no older than its generation begin and no later than the
unique official premise timestamp. An after sample must be no older than the
baseline and no later than the unique official returned-witness timestamp. This
allows a genuinely changed after file to occur after the premise, and allows a
file to remain completely unchanged when the app does not publish a focus update.
The unchanged monotonic AX/key witness ordering and action budget are separate
and remain untouched; wall clocks are not compared to system uptime.

No discretionary rounding or clock allowance is added. An official decimal token
is the reported endpoint; information discarded by that producer cannot be
reconstructed. A filesystem mtime beyond it, including an unresolved difference
below the producer's displayed resolution, yields incomplete/invalid diagnostic
evidence with an unknown count. It does not prove a native defect. A timestamp
with fractional precision beyond whole nanoseconds also fails closed. Boundary
controls cover the exact endpoint and +1 ns, raw nine-digit decimals at a large
Unix epoch, excess precision, changed-after/witness order, and unchanged files.

## Actual production-path controls

The focused probes import the whole selected source composition, construct its
actual composed Bridge, and route requests through the actual Session and
TransactionStore. Subprocess launch and socket bind/connect are forbidden inside
each probe before composition import. Parent-process audit guards reject native
commands, process execution and sockets; only inspected Python composition probes
inside the v3 directory are allowed.

The valid AX/PNG probe uses actual Session observe/chunk requests and linked
publications. The full path replays all 276 retained Settings requests through
those production methods, yielding 13 journal-linked payloads. It then uses the
real Bridge begin/ready/resume/reset/baseline methods, with explicit synthetic
app acknowledgments, to create the before-premise baseline. The same inventory
accepts the complete Settings history and exactly the two `before`/`begin` roles.
No key method is called. A separate pure false-premise classification remains
synthetic zero-input evidence; it grants no native provenance.

Failure probes exercise actual production guard-retirement and outcome-reporting
failures, plus malformed journal, summary failure, payload corruption/symlink,
foreign device/generation/action, unrecognized Settings names, missing or malformed
attempt outcomes and unreferenced staged artifacts. These reject even when the
lower-level persistence protocol has already committed an ACK.

The [actual-composition outcomes](../verification/apple-focus-reference-runtime-v3/host-attempt-4/actual-composition-outcomes.json)
record the legitimate and adversarial inventories. All probes are synthetic host
work, including file payloads and app acknowledgments. They are not screenshots,
keyboard delivery or physical-device evidence.

## Retained controls and the historical fixture distinction

The v2 producer's 111 test contracts run against v3. Their declared adaptations
are isolated to the v3 namespace, the added auxiliary module in the source
manifest, and the fake-tool helper's use of the real retained
`Bridge.persist_summary` writer. The exact adaptation is retained as
`producer-test-adaptation.patch`; no old test file is modified. The oracle,
fixed identifiers, strict verdict, input-count branches, duplicate/foreign joins,
process-group/EOF rules and all broad false-credit assertions remain unchanged.

All 33 original reviewer control bodies, mutation lambdas and assertions are
extracted unchanged from source
`84f7d1c5dbe0cbe17d60c34675de1c3d17107c17964062ea74ebdf5982a195db`
and run in v3-owned scope. Their exact source hashes and results are retained in
[historical-review-results.json](../verification/apple-focus-reference-runtime-v3/host-attempt-4/historical-review-results.json).
All nine metadata failures now reject. Bridge construction and Session start
also pass its inventory probe.

That original probe's third stage calls TransactionStore directly with
`{'record': 'host-only-independent-synthetic-payload-publication'}`. The store
can publish it, but it is not a valid Session journal and lacks its required
receipt, sequence and generation metadata. V3 correctly rejects it. The original
probe still asserts that every stage must be accepted, so its one failed
assertion is preserved explicitly. V3 does not whitelist the marker or weaken
journal validation. Separate named controls prove valid actual Session-driven
AX/PNG acceptance and malformed lower-level journal rejection.

## Frozen source, evidence and cleanup

The same 39-source derivative is reused:
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`.
The exact compiled product archive remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`,
with 55-member tree
`e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`.
No generic or Swift compile is rerun. The reviewed v2 classifier and unchanged
observer V2, original oracle, bridge, Session, TransactionStore and compiled
app/runner bytes are reused exactly. The source-only packet adds the auxiliary
validator; its selected closure contains 31 files.

The final host command is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v3/verify_host.py --attempt 4
```

The receipt records Python 3.14.8, the actual host uname, exact source/input/tool
and output hashes, command/probe programs and cleanup. The compilation revision
label `ba9ad4372f94463ba4d363cdfd76dd565c96413f` remains inherited; exact frozen
hashes define this preparation, with no Git query. Current pinned tool files are
read and hashed without invoking native binaries. All host source/product copies,
transaction probes and temporary directories are absent after collection. Every
frozen v2 producer/review member and original failure input remains unchanged.

Attempt 1 preserves replay-harness errors caused by a missing imported alias.
Attempt 2 preserves two overly late expected-rejection assertions: actual
retirement/reporting failure was already rejected at the Session-start observation.
Only those harness assertions were corrected. Attempt 3 passed the then-current
repair. Attempt 4 binds the final source, exact native-call decimal path and
explicit handoff counts. All failed attempts remain preserved. No attempt used
a simulator, device, compiler, UI/capture, native command or service.

The frozen handoff can be checked with file/hash operations only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v3/freeze.py verify
```

## Separate v3 selection

Only after independent review may root dispatch this new packet using its exact
reviewed packet SHA256 and a separately created fresh root selection plus the
selection's out-of-band SHA256. The v3 root schema is
`mixer.apple-focus-reference-root-selection.3`; owned names begin
`MixerFocusReferenceV3-`, and output directories begin `native-run-v3-` followed
by a fresh run UUID. V2 selections and output folders cannot be adopted.

All other closed root fields retain their meaning: exact source/product and
packet digests, selection UTC at most five minutes old, one exact owned simulator,
actual complete device/frontend baseline from before creation, and pinned
`/Applications/Xcode_26.6.app/Contents/Developer`. The driver reuses the
root-selected instance, creates no simulator, registers all five cleanup actions,
and preserves result evidence while retiring verified owned scratch.

No native dispatch is performed by preparation. `runPassed`, complete-case,
cursor, keyboard, carrier and GA credit remain false. Original authored-first
failure, full keyboard/comparator coverage, immutable published FieldLog use,
signing, store, operational and accountable-reviewer gates remain open. Physical
phones stay disconnected and deferred. The hosted authority/catalog lane was
not read, imported or executed.
