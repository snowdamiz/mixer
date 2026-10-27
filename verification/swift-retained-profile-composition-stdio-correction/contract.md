# C01 explicit terminal stdio ownership correction

This is a new bounded host prototype/contract packet. It changes no frozen packet,
canonical source, runtime limit, Rust binding, typed original runtime outcome,
real context or authority getter. UI/native/runtime/capture/process inventories
remain paused. No commit, push, publication or prohibited hosted import occurs.

Root selected C01 in the exact retained selection
`43de06ff9abc96057c2e89aff5e842de81c8419eb92f1ea6a6db13f0486ab911`.
Inputs are the476-member correction seal
`57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1`
and66-member independent seal
`108faabdd9e9fdb0037f0fd59863a9782073effaea956753d0c76fed7698b6d3`.
Their exact closed members and76-byte self-seal metadata verify before copying.
Only the new replay prototype changes. Schema.py, consumer.py, producer26 methods,
the previous142-case source and six independent case bodies remain exact copies.

## Resource representation and destructor safety

The prior TerminalStreams used owning TemporaryFile/BufferedRandom objects whose
context close happened after bookkeeping was erased. The replacement creates no
owning Python stream object. RawStdio is an ordinary data owner containing a raw
descriptor token, generations, state and reports; it is not IOBase, FileIO,
BufferedRandom or a temporary-file closer. Neither RawStdio nor TerminalStreams
has __del__, weakref.finalize, or an automatic fd-closing context hidden in it.
The only stdio numeric close call is the explicit once-only close boundary.

The standard mkstemp primitive returns a raw fd and name. Before calling it,
preallocate and register the actual owner and descriptor token in acquiring state.
The token initially has no number and grants no close/read/seek authority. The
private acquisition helper writes the returned birth number into that registered
token and the returned path into the owner immediately, before later registration,
prepare hooks or return to the orchestrator. A post-helper reporting fault therefore
cannot hide the successful birth behind an empty owner. No token/FileIO allocation
or general callback is needed between the returned birth and its storage.

Only a successful primitive return transfers an owned raw resource to this model.
A test exception before that primitive acquires no descriptor. Unreturned library
internals, fatal Python allocation/asynchronous failures, arbitrary injected
replacement SDK implementations and whole-process resources remain outside the
qualified source model, as in the retained-wrapper predecessor. No complete Python
heap/RSS or arbitrary-library/kernel resource claim is made.

The private prepare step checks the new fd is a regular empty file, then unlinks
its exclusive temporary name before child use. A bounded pathname obligation is
registered before prepare and removed only after successful unlink. On pre/post
unlink reporting error, the name obligation remains explicitly accounted even
if the test oracle knows unlink occurred. It is never blindly retried. A prepare
failure cannot hide the fd: cleanup attempts its known close capability once.
An unresolved name keeps its owner quarantined after a successful fd close.
Directory cleanup by the contained test process never erases that model record.

No file-object destructor can later replay an uncertain number: there is no such
file object, and the model's integers/data tokens have no closer finalizer.
Quarantined owners stay referenced by the ledgers; successful owners are removed
without growing global successful history. Tests naturally reuse released numbers,
repeat terminal close and force gc.collect. Fresh owners remain usable and no old
close syscall occurs. The healthy test also proves the old ordinary owner objects
were actually collected while fresh owners held the reused numbers.

## Lifecycle and explicit cleanup

RawStdio states are new -> opening -> open -> closing -> closed/quarantined.
The descriptor token is acquiring without a number, owned after the birth is
captured, closing before the sole explicit close call, then closed or uncertain.
Unsupported state/generation/owner/token access refuses. fileno/read/seek require
the currently registered open owner and owned token. They refuse once close begins.
Private acquisition and prepare helpers likewise refuse stale ownership.

fileno returns a number only from a valid open owner for the fixed child's launch.
Saved numbers are observations, not authority for cleanup/retry. Arbitrary direct
external syscalls or private-module mutation remain outside this closed Python
model. This is not a security sandbox or a public runtime capability API.

Closing consumes the capability before calling _stdio_close_syscall once. Every
exception preserves the exact original exception in a CloseFault tagged stdio and
leaves its token/owner/uncertainty record present. No errno, injected pre/post fact
or matching fstat is used to guess real OS resolution. Repeated quarantined close
reports the identical CleanupReport without another syscall; repeated successful
close returns that same report. Closed/quarantined owners cannot revive after
number reuse. A failed path retirement has its own stdio-path failure record and
does not pretend that a successfully closed fd is still known open.

TerminalStreams owns its two acquisitions through the existing bounded CleanupFrame.
If the second acquisition fails, the first owner is still present and is cleaned.
If either close fails, the other independent close is still attempted once.
Constructor/prepare failures clean the resource born in that constructor and
preserve the first error. The frame then cleans prior acquisitions independently.
No automatic context nesting can replace the structured original primary.

The bundle's completed method records the actual pending observation before
cleanup. CleanupAggregate retains the identical original primary and/or completed
result, plus every stdio/path/retained-owner cleanup error. The child_consume helper
now records its actual tuple before leaving the stdio frame and returns only after
healthy cleanup. If cleanup fails, that tuple survives as a completed **child-step**
observation; it does not invent the unrun later whole-profile post-checks or a
successful admitted complete composition. A separate control retains both an
existing completed observation and a later original primary simultaneously.

The actual fixed child, closed argv, exact pass_fds, terminal wait/reap and retained
body/profile leases are unchanged. Parent stdio fd cleanup is independent from the
child's inherited descriptor table: closing a parent log fd does not retire an
unreaped child. Nonterminal-child quarantine still preserves the original pending
process and profile/body owners, so healthy_zero remains false. No parent stdio
read/report is accepted before terminal child wait. A real stuck OS child is not
created or qualified by this packet.

## Accounting and bounded quarantine

STDIO_OWNERS, STDIO_TOKENS and STDIO_UNCERTAIN_CLOSES hold at most two generations
each. STDIO_PATHS holds at most two bounded name observations. STDIO_FDS is a
read-only numeric observation view; it cannot be cleared to manufacture health.
ownership_snapshot reports owners, acquiring/owned/closing/uncertain stdio tokens,
stdio close uncertainty and name obligations independently of retained owners,
retained close uncertainty, child quarantines and stdio numeric count. Healthy zero
requires every ledger empty, including an unresolved path with no live fd token.

New retained/open/stdio admission refuses any unresolved stdio close or pathname
obligation, as well as prior retained/child quarantine. Existing independently
owned cleanup remains allowed so an error never abandons the other stream or
retained ancestor. There is no operational uncertainty-resolution/retry API.
Terminal bundle cleanup is idempotent and reports its original terminal error.

At most nine retained owners/585 retained fd tokens plus two stdio owners/tokens
are live in this finite composition:587 visible owned descriptors, with at most
two additional pathname records. Stdio closes add at most two explicit close
attempts per invocation. Stdio close/path errors add at most four failure records
beside the retained frame's bounded inventory. These are logical record/source
call bounds, not a runtime reservation, total memory measurement or allowance.

Each parent log read accepts at most512 bytes and32 explicit read attempts,
including Interrupted; both reads request at most32,768 cumulative bytes and
acknowledge at most1,024. Seeking is the closed offset0 operation. Standard-library
tempfile/subprocess internals and actual CPU/retry/time/Python heap remain excluded.
The existing row/profile/preimage limits and the prior451,173,376 abstraction keep
their original scopes. No cap, VM debit or deadline is enlarged or newly qualified.

All fault cases are contained host subprocesses. The model deliberately retains
unknown close/name obligations at exit; parent terminal wait/reap and owned fixture
directory deletion are reported separately from healthy cleanup. Known synthetic
pre/post syscall fates do not establish a real ambiguity retirement policy. A new
test-owner number is closed only by its actual successful-open birth handle,
never by replaying an old uncertainty record.

## Executable requirements and unchanged raw C01

Both exact26-method producer suites and307 leaf mutations replay. The previous142
cases replay unchanged against the new prototype. Five independent positive cases
replay on old and new source. The literal old C01 witness is retained in both
variants and rerun byte-identically: old source still fails its required behavior;
on new source its TemporaryFile.__exit__ fault hook is unused and the witness
itself fails indexing its empty stream list. That mechanism mismatch is explicitly
not a behavior pass. The original review's raw C01 streams are also retained.

control-adaptations.md maps the replacement fault mechanism to the same obligations.
The57 added cases include both acquisition positions before/after captured birth,
before/after prepare and unlink, first-owner close faults after partial second
acquisition, both close positions pre/post, all four two-stream combinations,
original primary/completed-result/both preservation, repeated close, natural reuse,
destructor absence/GC, and four actual terminal-child stdio/retained-error joins.
The stderr-pre-close plus original-primary case retains the original C01 behavior
assertions: a separately captured known-owned fd is actually open, healthy_zero
is false, and the identical original Refusal is the structured aggregate primary.

Five stdio cases finish healthy zero;52 deliberately retain bounded uncertainty or
path obligations. All57 behavior cases pass. Raw primary/cleanup traces, completed
observations, exact source/tool/stdlib module hash, commands and per-case cleanup
are retained. No unresolved case is relabeled healthy because its child exits.

Independent review may accept this exact host correction only. Real Rust exporter/
loader/build/session provenance, original typed result/all15 ledger joins, real8192
context, full layout/work/lifetime accounting, canonical integration/full target,
new compiler/CI/native/physical/FieldLog/published package/OTA/store/operations/GA
remain separately pending. No production authority is selected.
