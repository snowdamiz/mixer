# Independent review of the frozen stdio ownership correction

Disposition: **C01's raw-descriptor ownership, cleanup and primary/result
preservation requirements pass within this finite host model. The candidate has
a separate required R03 read-completion defect. Complete selected stdio behavior
and complete composition acceptance remain withheld.**

## Custody and scope

Before input-source reads/imports, all659 candidate members,476 prior-correction
members and66 prior-independent members were checked for exact byte length and
SHA-256 against the supplied seals. Each directory has precisely its declared
members, seal.json and its exact76-byte self-seal metadata sidecar. Candidate seal
is `01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2`;
candidate source-tree digest independently recomputes to
`0f7e29d6c7224f2b390bfd586d7e5f4b35cb892624e064910e24a6f844636074`.
The root selection hash is
`43de06ff9abc96057c2e89aff5e842de81c8419eb92f1ea6a6db13f0486ab911`.

The exact source, contract, control-adaptation notes, command streams, tests and
prior independent findings were read. Only this new independent-review directory
was written. Old/new prototype, schema, consumer and producer-test sources plus
the previous independent witness were copied exactly into this directory before
execution. No producer one-shot preparation/freezing script was invoked.

## R03 required: completed32nd read is refused

In candidate `new/replay/corrected/replay/prototype.py:547-558`, RawStdio.read
checks `remaining == 0` only at the start of each iteration. If the32nd permitted
os.read supplies the final requested bytes, the loop ends before that check runs
again and raises Refusal("stdio-read-attempts", "stdio-access"). No33rd read is
needed to complete that request. Existing transfer() immediately recognizes the
analogous final acknowledged completion; the new stdio loop does not.

Two independent retained failing commands demonstrate this on an actual test-owned
regular raw descriptor. Both call read(32), within the512-byte limit:

- logs/054-read-chunks32.stdout records32 real os.read calls requesting
  32,31,...,1 bytes. The test boundary permits each real call to consume one byte
  from a64-byte known fixture. All32 requested bytes are consumed within32 calls,
  but the candidate raises stdio-read-attempts. The unchanged required-success
  assertion fails and stderr retains its traceback.
- logs/055-read-interrupt31.stdout records31 controlled InterruptedError events
  followed by a real32-byte os.read on call32. That call supplies the entire
  request; the same Refusal and required-success assertion failure result.

Neither failure is converted into a passing behavior assertion merely because
the runner records an expected exit1. Both commands' raw observations, failed
assertions and terminal cleanup are retained. Each finishes with healthy-zero
candidate accounting after the test owner's independent close and empty owned
scratch. This is an availability/attempt-boundary defect, distinct from the
previous false healthy-zero/primary-loss C01 defect. It does not establish an
actual kernel close ambiguity or an operational incident.

The correction must recognize request completion after the final allowed read
without a33rd syscall and without increasing32 attempts or512 bytes. Unsupported
or incomplete operations must continue to refuse. Root was notified as soon as
the failing behavior was independently observed; this lane edits no candidate.

## Fixed-child attempt distinction and corrected preliminary expectation

The unchanged actual fixed child emits fewer than512 bytes of stdout. For its
read(512),31 EINTR events followed by a nonempty short read on attempt32 have NOT
completed512 bytes or observed EOF. Refusing there is correct under the unchanged
32-call limit. The final logs/060-child-read-last control requires that refusal,
no33rd read, terminally reaped exit0 child and healthy parent cleanup; it passes.
With30 EINTR events, data on31 and EOF on32, logs/061-child-read-eof-last succeeds
and joins the exact real child result while keeping32 calls.

The preliminary run incorrectly required the former short-on32 schedule to
succeed. Its failed assertion was a test expectation error, not a third source
defect. preliminary/ retains all75 command streams, exact test versions and the
uncorrected historical summary; disposition-correction.json explicitly supersedes
that one label. Final source and77-command receipts implement the distinction.
The two real full-request-completion R03 failures remain required failures.

## C01 scoped positive ownership assessment

The replacement does not construct TemporaryFile, FileIO, BufferedRandom or an
IOBase owner for parent stdio. RawStdio contains raw descriptor/token data and
has no closer destructor or finalizer. Source review confirms the only stdio
numeric close is the explicit _stdio_close_syscall boundary. The registered
owner/token exist before the standard raw mkstemp primitive; the returned birth
descriptor and path are stored before a post-helper fault can escape. Its stated
scope excludes unreturned library internals, fatal heap/asynchronous interruption,
arbitrary hostile replacement libraries and external private-module mutation.

Independent cases exercise actual mkstemp failures before both first and second
births; faults after captured birth; prepare before/after; real unlink before/after;
and partial second-acquisition failure combined with a first-owner pre/post close
error. Each actual returned raw birth has exactly one close attempt. The exact
original primary survives; pending paths and exact cleanup exceptions survive
separately. Prior successfully acquired stdout is not lost when stderr acquisition
fails. Path failures retain an owner/name obligation even after the fd was really
closed; healthy_zero remains false and retained/stdio admission refuses.

For all eight one/two-stream pre/post close schedules, with original primary,
completed observation or both, close order is stderr then stdout, each once.
Each other independent stream is attempted after an error. Exact primary,
completed-result and every cleanup exception identity is checked, including a
KeyboardInterrupt at the close boundary and SystemExit during partial-acquisition
cleanup. Access through closed/closing/quarantined owners refuses. Repeated bundle
cleanup preserves the same terminal aggregate; repeated owner cleanup retains
the same terminal report without a new syscall.

The direct stderr-preclose plus primary schedule reproduces C01's material
obligations with the replacement's actual close boundary: the separately captured
known-owned stderr descriptor is really open by fstat, stdout is really closed,
the original ValueError is the identical aggregate primary, the exact injected
cleanup exception survives, and unresolved ownership blocks healthy zero and new
admission. Controlled pre/post oracle knowledge is never used to clear a ledger.

Independent reuse cases naturally assign a post-close uncertain saved number to
a fresh independently opened resource. Repeated old cleanup and gc.collect invoke
no old close and the new birth remains readable. Separate path-reuse controls
keep the unresolved path ledger while replacing only the contained fixture's
directory entry: a pre-unlink fixture is renamed aside, never subjected to a
numeric retry or candidate unlink retry. Candidate repeated cleanup/GC cannot
delete the replacement. Fresh handles are closed only under their own successful
open births. Fixture deletion later does not erase model uncertainty.

A24-round healthy control repeatedly closes old owners, naturally reuses their
numbers, collects48 old owner objects and proves fresh owners remain usable with
zero delayed close calls. Accounting returns to healthy zero after every round;
the global ledgers do not accumulate successful-history records. The source caps
remain2 stdio owners/tokens and2 name obligations, separate from the retained
9-owner/65-descriptor-per-owner bounds. These are logical/source bounds, not a
Python heap/RSS reservation or real VM charge qualification.

Actual bounded fixed-child controls join independent hashes of known profile/body
bytes, observe terminal child wait/reap and close both parent stdio owners. Cleanup
faults preserve the identical completed child-step tuple; a later primary plus
that same tuple both survive. The supplemental real-child nested-frame case adds
a known retained pre-close failure alongside stdout post-close and stderr pre-close
faults. It preserves all three exact cleanup exception identities, the exact
KeyError primary and identical completed child observation; every independent
retained descriptor is attempted once, and uncertainty remains explicitly nonzero.
The completed child-step tuple is not a completed whole-profile post-check result.

## Raw C01 adaptation and unchanged requirements

The byte-identical previous independent stdio-close witness freshly reruns on
both copied variants. Old source still produces a known-open stream while
healthy_zero=true and replaces the structured original primary with the cleanup
OSError; its required assertion fails. New source creates no TemporaryFile stream,
so the old hook is unused and the witness fails on streams[1] with IndexError.
That mechanism mismatch is explicitly not a new-source behavior pass. The
independent raw-boundary schedules above test the same material obligations
without relying on the obsolete stream factory.

Both exact26-method producer suites freshly pass with no failure/error/skip,
including307 snapshot-leaf mutations each. Five previous independent positive
cases freshly pass on both source variants. The retained audit checks all213
producer command stream hashes/terminal dispositions,142 prior lifecycle cases
and57 added stdio cases (5 healthy zero,52 honestly unresolved). This is an offline
audit of those cases, not142 or57 newly independent executions.

Final recorded executions are77 commands. They include63 new independent cases:
61 behavior passes and2 required R03 failures. The other14 are the two producer
suites and12 exact previous independent invocations (10 positives, one retained
old C01 required failure, one new raw mechanism mismatch). Preliminary75 commands
are preserved separately and excluded from this final77 count. An initial direct
tool probe of R03 was rerun with retained final streams and is also excluded.
Each final/preliminary case subprocess is bounded to20 seconds and terminally
reaped by its owned Popen reference; no timeout occurred. Actual nested fixed
children are reaped by source wait/kill/wait paths and checked through owned
references. No process inventory was used. All owned scratch directories are
empty. Contained process exit/fixture deletion is never called uncertainty
retirement or healthy cleanup for the deliberate fault cases.

## Limits

No actual OS ambiguity is resolved; saved numbers grant no retry authority.
No real stuck OS child is created. The source's closed fixture scope remains;
host tests do not establish an adversarial filesystem/process sandbox, arbitrary
SDK exception safety, fatal Python allocation/asynchronous interruption safety,
or complete Python memory/CPU/retry/time accounting.

Actual Rust exporter/loader/build/session provenance, original typed result and
all15 ledger joins, real8192-byte context, complete layout/work/lifetime accounting,
canonical integration/full target/new compiler or CI, devices/native runtimes,
simulators/emulators/UI/capture/physical matrix, separate-repository immutable
FieldLog packages, dogfood/OTA/store/operations/GA all remain separately pending.
No forbidden hosted catalog-inspector/authority-driver/rejectedWorkerV2/broad
harness read/import/execution, unrelated stopped Android startup experiment,
canonical/index edit, commit, push or publication occurred in this lane.
