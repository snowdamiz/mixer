# Independent cache-state execution tooling preparation

This is a separate preparation after root accepted the immutable implementation
preaccess packet and selected the fresh producer. It changes neither the sealed
preaccess files nor their plan. No new producer source was opened. Candidate
access and actual execution remain pending a later exact root admission.

The authorized root receipts are implementation selection
`012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3`
and public-getter selection
`80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1`.
Their exact copies and the two immutable old library API references are retained
in `verification/swift-cache-state-independent-review/execution-preparation/inputs/`.
The old Rust is reference data only; it is not imported or compiled. The
preaccess seal remains
`1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c`.

## Prepared public caller

`public_driver.rs` opens three ordinary input Files and creates one new empty
exclusive output File. It checks regular files, distinct inode identities and
initial offsets, then calls only `analyze_fixture_cache_state_v1` with four safe
mutable File borrows. The surrounding runner owns and quiesces those files and
checks their exact before/after hashes. No public record, candidate, private
receipt, state seed, supplied acceptance boolean or raw descriptor is used.

The driver collects all32 cache-state words through the individually selected
getters. It uses exhaustive matches for every new boundary/reason and existing
framing/envelope enum; enum values are never inferred through casts, Debug output
or serialization. The new aggregate's four authority getters are collected
separately, and the four observation getters occupy their exact word positions.
Reserved getters are read explicitly. Unexpected authority or reserved values
are retained and rejected by the comparison layer rather than normalized away.

The closed numeric JSON protocol also retains every old framing/error field,
all sixteen envelope words, envelope metric authority, initial/final file
stamps, final offsets, output metadata and fresh named layouts. An outer Err
retains the exact five AnalyzerError words and has null framing/envelope/cache
observations and aggregate authority. Partial report bytes remain on disk as
failed evidence. Post-call diagnostic failure cannot replace the API Result.
`driver-schema.json` fixes every position and the separate Result partition.

## Admission-bound future execution

`future_runner.py` is closed until it receives the exact hash of a root-owned
admission receipt. `execution-admission-schema.json` is a deliberately unadmitted
template for that later receipt. Before any candidate path is read, the runner
checks its status, accepted preaccess/getter identities, source/member paths,
compiler identities and separate future review-output location. Invalid receipt
controls prove that no candidate file read happens before this gate.

After admission, the runner verifies every preparation and preaccess member,
the candidate seal and all candidate members. Candidate members are restricted
to the selected producer closure and its named document; source compilation
uses only explicitly admitted Rust members copied into a fresh owned directory.
Symlinks, duplicate paths, traversal, missing/changed source and inconsistent
totals refuse. The Rust compiler's binary hash and exact verbose identity are
checked. Compilation uses direct rustc calls, an explicit library crate and the
independent driver; no Cargo build script, producer model, copied old tests or
broad harness is imported or run.

Public execution selects only immutable basics, word mutations, stage
transitions or sequence variants. Each serial batch has at most64 cases. The
runner independently materializes raw wire/profile/context bytes without
importing any sealed Python oracle. All39 basic public inputs are copied byte
for byte, and CAP encoding is independently reproduced in tooling controls.
Private seeded/corruption cases are not in
the public case map. Expected full32 words stay immutable; a mismatch is retained
as a failure. The accepted ambiguity in overlapping predicate order requires
later source-bound disposition; this tool does not rewrite expected reasons or
promote a mismatch to a pass.

Each public result preserves the raw report and checks its49,152-byte size,
schema/version, complete reserved tail, framing diagnostics, synthetic echoes,
false authorities and fresh layout bounds. The raw report and old diagnostics
remain available for exact independent review. Report consistency checks are
not an independent original-result/ledger adapter or proof of source accounting.
All source/debit/move/caller/lifetime/cleanup obligations remain separate.

Fifteen frozen API probe sources include one borrowed-getter positive control
and fourteen negative controls for Copy/Clone, constructors, private records/
candidate/budget/progress/receipt, a words accessor, raw descriptors, an acceptance
boolean and old-API semantic activation. Rust diagnostic JSON must attribute
each rejection to the intended probe span and declared error category; an
unrelated compiler failure is not a pass. A successful positive control confirms
the crate and selected borrowed surface can be named. API-only mode compiles
these controls without semantic execution. Actual candidate probe compilation
is still pending admission.

## Explicitly unimplemented private seams

`private-review-plan.json` proposes narrow, separately admitted test-only access
for row/scalar/candidate snapshots, numeric seeds, budget/progress corruption,
fault controls and private receipt construction. It requests no public API
addition and reads no producer implementation. Exact seam names and legal
borrow arrangements must be coordinated after frozen source access.

Public actual-File evidence, private seeded controls, test-only fault overlays
and source-proof-only obligations require distinct manifests and receipts. A
private snapshot must bind actual scalar indices to the immutable logical
expectations and preserve every non-owned byte. Observer memory/work is not
product resource qualification. Fault instrumentation cannot add a fallible
callback or allocation after first commit/clear mutation, or hide a cleanup
bypass. An overlay outcome cannot prove its production reachability.

All256 in-place clear-word iterations and12 envelope restores, one sequential
Candidate owner, every cleanup/error exit and both-leaf disablement after an
unexpected commit/cleanup fault require actual source and caller proof. The
three partial-paid variants SS/SF00,01,10 remain contract exclusions with zero
runtime passes; actual private constructors and every return/move must prove
them unconstructible for returned aggregates. API rejection and stub behavior
cannot discharge this obligation. All fixed work, role and layout ceilings from
P01–P35 remain unchanged and unproved against missing source.

## Tooling controls and evidence boundary

The self-owned `protocol_stub.rs` exists only to compile and exercise the caller
protocol. It accepts five-byte control files, returns arbitrary distinct getter
values and writes a fixed arbitrary report pattern or partial output. It has no
MIXFIX01 parser, cache transitions, producer model, old-library execution or ABI
claim. Tests cover every enum ID, all getter positions, authority one-hot values,
nonzero reserved diagnostics, exact outer errors and partial bytes, malformed
protocol, file preconditions, rejected admission, independent wire encoding,
timeouts and output caps. Its intentionally invalid synthetic outcomes cannot
be mistaken for candidate semantic fixtures.

The driver/stub and fifteen API probe sources compile with actual local Rust
1.99.0 (`b940084d7`, Apple arm). Reviewer Python controls pass nine methods,
372 checks and35 self-owned stub executions per normal and optimized mode.
The first authoring attempt's duplicate synthetic directory label is preserved
with raw failures and source snapshots; it was corrected without changing a
sealed fixture. This compiler/tooling evidence does not replace the old
envelope's Rust1.98.1 qualification or qualify a new candidate/compiler matrix.

Every child command is serial, has a maximum60-second deadline and one MiB
output cap per stream. The runner retains exact argv/cwd/tool/source/output/
failure metadata, joins or kills only its owned process group, and removes only
the scratch directory it created after all children return. Timeout/cap controls
are deliberate tooling refusals, not candidate failures. Other projects and
native/capture/UI/simulator/emulator/phone processes are neither started nor
queried. No process discovery, producer access, root metadata, CI, git index,
commit or push change occurs in this lane.

This preparation records **zero candidate Rust semantic executions, zero
candidate public-File cases, zero private candidate controls and zero product
tests**. Root must admit an exact later candidate before source review or real
execution. Real profile/selection/original-result/ledger/crypto/custody adapters,
live VM/target, native/device/compiler/signing/store/customer/operations,
immutable published FieldLog and GA qualification remain pending.
