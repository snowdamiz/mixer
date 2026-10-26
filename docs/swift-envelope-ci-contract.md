# Proposed standalone fixture-envelope CI contract

This is a source and contract proposal. Root accepted the isolated host
fixture-envelope implementation in
`verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json`
(`38918f5916cd976965cd93c233606687bc78918c105aa9bcc91c02c2acda4ebf`).
That acceptance does not select a CI runner, a portable test layout, or product
integration. No runner or workflow is implemented by this proposal, and no
candidate, historical collector, compiler, native runtime, capture tool, or UI
automation was executed to prepare it. The binding product scope remains
`mixer-product-plan.md`.

The next selection should be a new, small, independently reviewed source pack
and host runner for the exact source below. Keep the existing accepted 44-method
framing check unchanged while this addition is qualified. Its replacement,
deduplication, or expansion requires a separate explicit selection.

| Selected original | SHA-256 |
| --- | --- |
| `verification/swift-envelope-absent-state-correction/proposal-1/src/analyzer.rs` | `1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b` |
| `verification/swift-envelope-absent-state-correction/proposal-1/src/envelope.rs` | `2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef` |
| Root absence selection | `ae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0` |
| Producer implementation seal, 120 members / 8,532,453 bytes | `1e45ae55b5a159fd2c384bfdbbc520467e467b391af9f6a1d655e8ab67f0012a` |
| Producer terminal receipt | `6f6b1c607237aaaf5a0df3ed880165752af7f221180de6ef176e8608833f7f79` |
| Independent final review seal, 220 members / 1,331,015 bytes | `84f93960a58b6f5fe04a3e1a95211e6c1e5b2bc38c58752e6703f83b3184d2f8` |

`verification/swift-envelope-ci-contract/selected-input-manifest.json` enumerates
the 60 original input files (7,957,311 bytes), byte lengths, hashes, roles, and proposed packed
destinations. They are the exact source pair, six unchanged producer/review test
sources, the corrected focused eight-control source, three selected425 oracle
data files, the model source as provenance, 17 captured stream/sidecar pairs,
nine external API probes, and four independently authored exact-source test
files. The manifest is an offline audit of those selected files; it does not
re-verify every member of the historical seals. Root's acceptance records its
separate 407-member verification. Both kinds of evidence retain their scope.

The proposed pack should contain those original bytes, the manifest, the two
deterministic test-only augmentations described in `proposed-layout.json`, the
fixed inventories, and the small selected acceptance/binding/terminal-receipt
records. Its final file inventory and tree digest must be pinned in the runner
and approved by root before implementation can pass. The proposal itself does
not create or publish that executable pack. No historical collector, historical
runner, unrelated archive, rejected source lineage, or build product belongs in
its executable closure. The Python finite model is retained and hashed as
provenance; it is not imported or evaluated by the proposed CI run.

The original host receipts bind 70 unchanged methods, eight focused methods,
21,714 fresh candidate comparisons against previously frozen selected425
expected bytes, and 32 complete host layouts. Run 1 retained one incorrect new
test expectation: `4*471` omitted setup's 534 debit. Run 2 corrected only that
expectation to `534+4*471`, passed the focused eight and API probes, and reused
run 1's unchanged-70 results. The source did not change. CI must execute its
entire selected closure freshly in one invocation; it may not substitute either
historical run's success for a current result. Model evaluation remains false
even when all 21,714 comparisons execute again.

The accepted independent terminal review adds 14 methods using byte-identical
selected source. Its two separate counter methods used a dispatch interposition
and are test-overlay evidence. This first proposal selects the full exact-source
14 in a separate binary. It retains the overlay binding as provenance and does
not execute the instrumented envelope or claim those two methods ran against
unmodified source. Independent coverage overlaps the producer matrices; method
counts are test inventory, not an additive count of product capabilities.

## Closed source and test layout

Compile `source/library/analyzer.rs` with its adjacent exact `envelope.rs` as
the public library. Neither file receives appended code. API probes link that
specific fresh library artifact with `--extern mixer_absence=...`.

The producer test root is the unchanged `independent_tests.rs` at
`source/producer/independent_tests.rs`. Its `inputs/envelope.rs` is another
byte-identical copy of the selected envelope. Its `inputs/framing.rs` is the
exact parent analyzer followed by one fixed relative `include!` for the
unchanged private-I/O test module. The envelope test module is the exact frozen
`envelope_tests.rs` prefix followed by one relative child-module declaration for
the corrected focused controls. All remaining test bodies are unchanged copies;
`selected_tests.rs` and the two oracle binaries preserve their relative paths.
These two complete derived files and their construction hashes are explicit in
`proposed-layout.json`. They are test-only inputs, not the unmodified library.

The previous implementation wrappers contain absolute paths on this Mac. They
are historical provenance, not portable runner inputs. The proposed relative
augmentation differs from those wrappers. It needs a new bounded host
qualification, including exact inventory and prefix/hash checks, before CI
selection. Creating a relative layout is not evidence that it already compiles.

The independent binary uses an exact source pair under
`source/independent/source/`, with four unchanged files under its sibling
`tests/`: `envelope_tests.rs`, `caller_cases.rs`, and the deliberately empty
fixture/correction modules. It needs only its owned `REVIEW_SCRATCH` environment
and no producer code or oracle import. This keeps its 14-method result separate
from the producer test-only parent augmentation.

Require the exact 78 producer names and exact 14 independent names in
`expected-methods.json` from both listing and executed output. Use one thread,
no filter, and require zero failed, ignored, measured, or filtered methods. A
successful empty listing, ignored test, substituted method, or successful
partial run fails. Record each binary, source closure, method inventory, and
fresh result independently. The historical 32 layout names/values are in
`expected-host-layouts.json`; future receipts must retain the raw fresh output
and a complete named mapping, including Metadata 144 and its Result 152.

## Runner identity, custody, and failure behavior

Use a narrow direct-`rustc`, Python-standard-library runner without Cargo,
network fetches, optional test/source/model overrides, caller-supplied compiler
flags, or arbitrary command execution. Copy only manifest members to a fresh,
owned output. Reject noncanonical relative paths, duplicate destinations,
symlink ancestors or members, nonregular files, traversal, `.git`, existing
outputs, and destinations inside either the immutable pack or historical
packets. Record the exclusive-create output marker and scratch device/inode;
local checks assume a quiescent trusted checkout and do not certify adversarial
filesystem custody.

Reuse the current framing runner's actual compiler-selection behavior: preserve
the original PATH/explicit `rustc` launcher, query it with `--print sysroot` in
the repository context and `RUSTUP_AUTO_INSTALL=0`, then invoke the selected
`sysroot/bin/rustc` directly. Record and hash launcher, resolved compiler, sysroot,
`rustc --version --verbose`, Python executable/version, git revision and tree
digest, OS, machine, compiler host, and the executed runner. Refuse a missing
toolchain rather than installing it. Validate a complete rustc identity; a
successful manager/installer version query does not identify the compiler.
The old shim failure is not a current defect in the framing runner.

Before running children, verify every pack file against the pinned closure and
the exact source pair against root acceptance. Copy and hash each original and
derived input; require the derived prefixes and fixed suffixes exactly. Hash
the selected pack, source snapshots, derived tests, runner, and compiler again
after execution, including failures. Changed inputs make the final result fail.
CI does not need to open, traverse, copy, or hash all historical seals' members.

All commands use argument arrays and fixed cwd/environment. Remove caller test
filters/options and Rust compiler injection variables; set only the named owned
scratch and selected historical fixture paths. Preserve exact argv, cwd,
environment overrides, start/end UTC, timeout, exit or spawn error, elapsed
time, raw stdout/stderr, and their hashes. Flush a failed receipt even when
selection, spawn, compile, listing, test, postflight, or cleanup fails.

Run one synchronous child group at a time. Bound version/listing commands to
15 seconds, each compiler invocation to 60 seconds, and each test binary to
120 seconds. Enforce an overall active-run deadline of eight minutes, then a
bounded 60-second retention/cleanup allowance; propose a ten-minute CI step
limit. On timeout or interruption, terminate only the owned process group and
wait for the direct child before cleanup. Prove the owned group has returned
using that group's identity, without querying unrelated processes or native
instances. Never use global process discovery or blanket kill commands.

Retain test-created input/report/failure bytes before deletion, including the
independent actual-File reports. Hash compiler products before removing them.
Cleanup must compare the exact scratch device/inode and marker, reject links or
special files, and remove only that owned tree after children return. Changed
ownership makes cleanup fail and leaves the tree for inspection. Preserve large
sparse failure fixtures losslessly with streaming compression and record both
compressed and original size/hash. An interrupted retention step must leave
the source scratch recoverable. No unrelated simulator, emulator, device,
capture service, process, or data is inspected or changed.

Runner qualification must cover no-optimization-bypass checks, malformed or
mutated pack/overlay, symlink/traversal/output refusal, explicit compiler and
rustup selection, fixed inventory, missing/failed compiler, partial logs,
negative diagnostic false positives, descendant timeout/reap, output retention,
independent reports, sparse compression, and changed scratch ownership. Simulate
these runner failure controls independently of product behavior. A failed
negative API probe must not become a passing runner result because the compiler,
dependency, fixture, or library was unavailable.

## Expected API refusals

Run the positive external probe first against the fresh unchanged library. Then
require each negative probe to return a normal nonzero compile status, produce
no executable, and emit its intended primary diagnostic at that probe's source
span. Parse compiler JSON diagnostics; retain raw bytes. Require the expected
code and target item/trait, and reject missing-library, incompatible-metadata,
missing-file, compiler crash, signal, or timeout outcomes. Additional unexpected
error codes require review; do not replace checks with “any failure is good.”

| Probe | Required code | Intended refusal |
| --- | --- | --- |
| `private-field.rs` | E0616 | private `envelope_debit` field |
| `no-clone.rs` | E0277 | observation does not implement Clone |
| `no-copy.rs` | E0277 | outcome does not implement Copy |
| `no-record-constructor.rs` | E0432 | no public `FixtureDecodedRecordV1` re-export |
| `no-word-or-boolean-entry.rs` | E0061 | safe entry takes four File borrows |
| `no-private-reply.rs` | E0432 | no public `FixtureEnvelopeReplyV1` re-export |
| `no-observation-constructor.rs` | E0451 | observation fields remain private |
| `no-raw-serializer.rs` | E0599 | no `to_bytes` authority serializer |

These are the selected producer probes. The independent review's differently
structured API probes and their E0603/E0425/E0599 diagnostics remain separate
historical evidence; this proposal does not silently substitute their diagnostic
codes or claim to rerun that second probe set.

## CI placement, delivery, and acceptance limits

After runner selection and local qualification, add the new envelope step and
its `always()` artifact upload beside the current framing check in the existing
`swift` job of `.github/workflows/verify.yml` (`macos-15`, current 30-minute job
limit). Keep its existing toolchain, native checks, and job topology. Do not add
a Linux matrix: accepted local evidence is Rust 1.99.0 on
`aarch64-apple-darwin`. A runner label does not prove that host triple or layout.
The first actual CI host must record its identity and pass the pinned layouts;
any other host/compiler combination remains unqualified until explicitly
selected with fresh evidence. These are official Rust compiler host results,
not Swift/Android/iOS compiler-target or device qualification, physical stack,
RSS, CPU, or measured operation-budget proof.

Use one source pack and serial host binaries. Selected oracle bytes total
7,687,680; all 60 original selected files total 7,957,311 bytes. The selected
fixture closure is small enough to retain without the
rejected archives. Historical producer command durations were approximately
50.8 seconds for framing44 and 3.6 seconds for envelope26 on this Mac; they are
capacity hints, not CI timing guarantees or performance qualification. Record
the new step's measured wall time and artifact sizes before considering any
timeout change to the existing job.

Upload the pack manifest and small provenance records, executed runner, source
and derived test snapshots, fixed oracle/fixture closure, command logs, receipt,
ownership, and retained test files under a new nonhidden output prefix. Keep
the 14-day retention pattern and an explicit upload allowlist; avoid wildcard
uploads of historical `verification/` trees. Root must deliver the exact narrow
pack and runner in a coherent commit before remote CI depends on them. A local
path/hash to a historical seal is an ancestry reference, not a remotely available
artifact. Include the needed executable bytes in that commit or an immutable
published pack verified against its selected digest. Missing bytes fail closed;
do not fetch or import the entire rejected lineage to fill gaps.

Retain all locally frozen original and rejected evidence. The acceptance receipt
and selected source/binding references explain provenance without claiming that
unpublished packets have been delivered. A future narrow pack can be verified
before and after a run entirely from its own pinned inventory. Any later
semantic replay, real source adapter, authority, engine/CLI/target integration,
or release request needs its own selected contract and evidence.

Every proposed receipt and output must keep `storedPrefixValidated=false`,
`fullReplayAccepted=false`, and `semanticMetricsValid=false`. Preserve parent
framing API/ABI/report prefix and all global limits. Preserve the selected public
debit `534*S_paid + 47*F_paid + 425*N_B`, single retained Candidate2048, one G112
reservation for at most one terminal unpaid path, W24 caller ownership, and no
main-paid425 refund. Poststate debit coherence is not a historical-budget,
arbitrary reply-shape, or authority validator; fabricated paid status1/reason1
remains outside canonical helper provenance. Private short-arena controls and
separate interposition controls do not establish a natural public File absence
fault, since public construction uses a full Arena.

Computer use, capture, UI and native simulator/emulator runtimes remain paused;
phones remain disconnected. Compiler-target/native/device/signing/store,
customer/operations, separate-repository immutable published-package FieldLog,
and accountable GA gates remain pending. No release or GA gate can be accepted
from the proposed host check alone. Root owns subsequent selection, integration,
metadata, commits, pushes, and actual remote CI inspection.
