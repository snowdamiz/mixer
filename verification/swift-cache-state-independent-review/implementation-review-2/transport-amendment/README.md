# Proposed lossless transport amendment

This freezes reviewer-owned transport tooling and its data-consistency controls.
It authorizes **zero** further candidate executions. The old preaccess, runner,
oracles, initial review and correction-control result seal remain unchanged.
The current correction's 39 public cases, 15 API controls and 14 private guard
observations belong to the separate correction-control seal
`13b4e77974be545bb34274ddba68b6b3b159e8d2287390dcffff864373d136c5`.

`dedup_transport.py` imports only the already sealed reviewer materializer and
bounded harness. No producer model, harness or test is imported. Each selected
fixture entry is retained verbatim as canonical JSON, bound to the exact raw
sealed source-file hash and source index. All expected words, expected errors,
state references, field names and refusal-policy metadata remain intact. The
original private overlap policy file is retained byte-for-byte. Public runtime
comparison remains the unchanged sealed `compare_public`, with exact full32 and
inherited report/error/input assertions. No reason set is enlarged and no
terminal precedence is inferred from internal predicate order.

Input bytes are stored once per content digest and role. A case references its
stream/profile/context objects; object paths, sizes and SHA256 values are checked
against both retained bytes and the unchanged sealed materializer. This permits
exact reconstruction of every logical input, not merely a synthetic digest echo.
Each case opens three distinct ordinary input Files through the unchanged public
driver, with a new distinct output File. A shared profile is quiescent and opened
at offset zero in each separate process. Per-case before/after hashes, raw driver
stdout/stderr, exact exit/timeout/cap status, full32 expected and actual words,
inherited diagnoses, report bytes/hash and input-object references are retained.
Full profile bytes are not copied into every case folder.

The proposed `dedup_runner.py` rejects the existing public admission because it
lacks a new explicit `dedup_transport` authorization. A later root-owned receipt
must bind this transport seal, exact candidate/compiler/source map, exact kind,
start and count, and a new `implementation-review-2/bulk-*` directory. Only
`words`, `transitions` and `sequences` are executable in this proposed runner,
with 1–64 cases per batch. Tooling/input/candidate hashes are verified before
compilation; all calls use the old bounded executor with per-command 60-second
deadlines and one-MiB stdout/stderr caps. Commands run serially. Orchestration
must yield at most 60 seconds between progress observations, without a global
60-second kill over an entire batch. Returned owned library/driver products are
hashed then removed in `finally`, after their commands return. Sources, raw
failures and input objects are preserved. Existing API controls are not rerun or
counted as fresh evidence in a bulk batch.

`terminal-full32` can be packed and reconstructed as **private data only**. It
does not become a public File fixture. The proposed public runner has no terminal
execution mode. Outer Err entries retain null observations, and partial-paid
00/01/10 variants remain source-proof exclusions with zero runtime pass credit.
Actual private terminal/fault/layout execution requires its own frozen source
mapping, glue delta, expectations and root admission. The adjacent
`private-probe-plan.json` is explicitly unimplemented.

The retained control command ran under Python 3.14.8 with a 60-second deadline
and one-MiB stream caps. It passed 120 reviewer-owned assertions, including 14
expected refusals. The 64-word sample represents 164,470,784 logical input bytes
using 2,642,432 unique input bytes, including one profile object. Four transition,
four sequence and two basic data cases also round-trip, and 64 terminal entries
remain private data. Wrong expected words, wrong case input mapping, changed
source-case references, content flips, symlinks, escaping paths, false byte
counts, terminal-as-public classification and absent root transport admission
are rejected. All negative mutations were restored and exact retained bytes
revalidated. There were **zero candidate Rust executions and zero product
semantic tests** in these controls. Candidate compilation/execution through this
new orchestrator has not yet run.

`proposed-batches.json` proposes initial batches, rather than admitting them.
Source accounting, complete lexical lifetimes, every remaining private control,
full matrix acceptance, native/device/capture, real-source and release/GA gates
remain separate. A transport pass cannot establish any of those properties.
