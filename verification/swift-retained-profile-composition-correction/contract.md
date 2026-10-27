# Retained wrapper lifecycle and cleanup correction

This packet proposes an isolated host prototype correction for mandatory R01/R02.
It does not alter either frozen packet, canonical source, runtime limits, the
snapshot grammar, original typed runtime outcomes, MIXFIX01 or any authority
getter. Native/runtime/UI/capture and process inventories remain paused. Only
this folder is written; no prohibited hosted harness is read/imported/executed.

Inputs are the41-member preparation seal
`c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860`
and29-member independent review seal
`ce7f9d15730411060284df6659ed7d5c3278a7f3b543142cd31b8d3dfa2091c1`.
Each input includes only its declared members, seal.json and separately verified
exact76-byte self-seal sidecar. `input-custody.json` records closed verification.
The original source and independent witness copies in old/ are byte-identical.
In corrected/, only prototype.py changes; the producer26 methods, schema.py,
consumer.py and unchanged independent witness remain exact copies.

## Closed ownership state

Each wrapper and each successfully opened descriptor has a separate monotonically
assigned u64 generation. Overflow refuses before another open. Descriptor-table
numbers, path/inode/metadata equality and Python object equality never identify
continuing ownership. Numeric equality of saved handles is observational only.

The wrapper state machine is:

| State | Permitted operations | Transition |
| --- | --- | --- |
| new | admission only | opening after owner registration |
| opening | private bounded path opens/constructor checks; cleanup on failure | open on complete checks, or closing |
| open | checked descriptor borrow/read/seek/check/hash/composition/one child lease | closing when close is admitted |
| closing | consume each independent close capability once; record every outcome | closed or quarantined |
| closed | return the identical terminal cleanup report on repeated close | terminal; no I/O/handoff/reopen through this wrapper |
| quarantined | return the same uncertainty report via CleanupFailure on repeated close; observations only | terminal; no numeric close retry, I/O or adoption |

A live child lease prevents close from beginning. Close refuses child-live before
changing ownership. Once admitted, close sets closing **before the first syscall**
and discards operational path links. No wrapper access/check/hash/read/seek/lease/
compose/adopt can run in closing, closed or quarantined. Reentrant close during
closing refuses without a syscall. Repeated closed/quarantined close is idempotent
with respect to syscalls and generation/accounting changes; quarantined close
continues to disclose failure, never converts to healthy success.

Descriptor tokens transition owned -> closing -> closed or uncertain. The private
close helper validates owner generation, token identity and owned state, then
consumes the close capability by setting closing before calling os.close once.
Successful close removes the token from the active ledger. Any raised exception
leaves an uncertain token and immutable CloseFault retaining the exact original
exception, owner/token generation and saved number. A local close-boundary refusal
is also uncertainty, without a guessed numeric retry. The loop then attempts every
remaining independently owned token. No error from one descriptor abandons later
independent ancestors or owners.

The saved number inside CloseFault is data, not an operational handle. There is
no uncertainty-resolution/retry API. The uncertain owner and token remain in
OWNERS/TOKENS/UNCERTAIN_CLOSES. New modeled owner/open admission refuses while any
close uncertainty or nonterminal-child quarantine remains. This bounds retained
uncertainty without needing a platform-specific assertion that an ambiguous close
actually closed or stayed open. Real OS uncertainty needs a separate platform
policy before any more capable admission or retirement rule can be selected.

The source-level descriptor access object holds the actual owner/token identity.
Every conversion to an OS descriptor checks the wrapper is currently open, its
registered owner identity and every token generation/state still match, and its
OFD is not child-leased. IO.read/write accept this access object, not an integer.
readinto and seek perform the same gate; check/hash/retained composition gate
before using source/metadata/offset. A stale access object therefore cannot revive
when a newly opened same-path/same-inode wrapper naturally receives identical
descriptor numbers. The new wrapper's generation remains distinct and usable.

OPEN_FDS is now a read-only observation view over known plus uncertain tokens.
Removing, discarding or clearing the view refuses. It never grants a close
capability, and it is not the sole healthy-zero check. ownership_snapshot separately
reports owner count, owned/closing/uncertain token counts, uncertain-close records,
child quarantines and stdio contexts. Healthy zero requires all of them empty.
Known post-syscall reporting faults remain uncertain even when the synthetic test
oracle knows the OS number was released. Ledger removal cannot invent cleanup.

This is a closed Python source model, not a sandbox against arbitrary mutation
of module internals, arbitrary C calls or direct numeric operations outside its
interfaces. Saved numbers are available as observations for the unchanged
witnesses. They have no operational authority within the corrected wrapper,
composer, cleanup or child-handoff protocol. Coordinated hostile filesystem or
external fd-table manipulation remains unsupported. No new product authority
is derived from these model objects.

## Child handoff and adoption lifecycle

A child lease checks all actual owners open/idle, distinct handles and current
generation ownership before leasing. It captures the closed pass_fds tuple while
those borrows are usable, then records itself as each owner's sole lease. The
pass_fds tuple is a private once-only launch capability, separate from saved-number
observations. claim_launch validates lease state, owner identity and current lease;
it consumes the handoff once before Popen. Reusing it after consumption or lease
exit, entering the same lease again, or minting a lease from a closed owner refuses.

The fixed child still privately adopts exactly its two inherited descriptors once.
The child/schema sources and closed argv/standard hashlib behavior are unchanged.
Parent read/seek/check/hash/close remains unavailable while the OFD is leased.
Terminal wait/reap releases the lease. Nonterminal modeled child state retains
both actual wrappers and leases; the original unreaped-child refusal and both
blocked owner-cleanup errors survive. No caller boolean releases a lease.

The existing trusted-child/script-path/writable-fd limitations remain. This is
not admission of an arbitrary executable, hostile consumer or genuine Rust owner.

## Preserve original failure and all cleanup results

CleanupReport freezes owner generation, terminal state, attempted/closed/uncertain
token generations and all original CloseFault objects. CleanupFailure is an
OSError subtype for direct close failure. It retains its exact report and every
original exception rather than replacing them with a generic success count.

CleanupFrame owns a bounded list of independent wrappers. It rejects duplicate
owner adoption. On exit it attempts every owner in reverse acquisition order,
collecting every error even after prior errors. CleanupAggregate retains:

- primary: the original composition/constructor exception object, unchanged;
- cleanup_errors: the ordered original cleanup failures/refusals across all owners;
- retained_result: a completed composition observation when computation succeeded
  before cleanup failed, separately from the cleanup failure.

Nested output/input cleanup frames flatten their cleanup lists while preserving
the first actual primary object and completed result. An exception from finally/
context cleanup cannot replace the original partial-write/constructor failure.
A successful hash/composition observation is also not dropped when subsequent
close reporting fails. It remains unavailable as a healthy admitted result.

The constructor catches its original admission/check failure, attempts all opened
handles, and attaches cleanup errors if present. It never returns a partly opened
owner as success. The composer preserves the same behavior across the separate
output owner and all input owners. Physical partial output/progress and original
input artifacts survive until the test's owned fixture deletion, as before.

Nothing here invokes a real Swift constructor or refunds an original runtime
ticket. The original eight-variant runtime result, cache/proof ownership, exact
prepare/complete guard, transport header and future exporter state remain the
unchanged predecessor proposal. Real Rust integration needs its own exact typed
Result/caller/lifetime/layout/work/cleanup accounting under unchanged limits.

## Bounded records and explicit source scope

Modeled live owners<=9. Each owned path has<=64 components, including its leaf,
and<=65 descriptors including retained root. Live token records<=585; uncertain
records are a subset of these tokens. Close attempts<=65 per owner and<=585 per
composition cleanup, each attempted source-level numeric capability once. All
close errors may produce585 uncertain records. If that happens no new modeled
owner/open is admitted. Repeated terminal close adds no tokens, records or calls.
No global history of healthy closed tokens is accumulated; terminal wrapper-local
reports remain with those caller-owned wrappers. Arbitrary retained caller history
and arbitrary repeat callers are outside the bounded composition invocation.

Cleanup frames<=9 owner references, and failures are bounded by their owned token
inventory (a lease-blocked owner contributes one refusal rather than65 calls).
At most one original primary and one completed result are retained alongside
ordered cleanup errors. A generation counter is bounded by u64, refusing overflow.
The142 targeted cases include every actual maximal65-owned-position pre/post
fault,65 simultaneous uncertainties, nine-owner admission and duplicate-frame
refusal. The full585 simultaneous uncertainty branch is bounded by source
inventory; it is not claimed as an executed OS case.

The original block/I/O/hash extents and all runtime caps remain unchanged.
Ownership checks add source work and records; this does not inherit the accepted
451,173,376 abstraction as an allowance. No complete Python heap/RSS, actual
library/atomic retry/CPU/all-source-evaluation or elapsed-time bound is claimed.
Only explicit source loops, record counts and API attempts are bounded here.
Python, standard library, kernel and exception internals remain separate scopes.

## Exact controls and truthful cleanup disposition

Both exact26-method producer suites/307 leaf mutations replay unchanged. Three
exact independent R01/R02 witnesses replay in separate old-source processes and
retain their three actual required failures. They also replay byte-identically on
the correction. R01 passes. R02 raw replays expose their obsolete numeric finalizer
and, for the pre-close case, its use of a now-invalidated borrow. Those raw results
remain failures/errors; they are never relabeled passing. `control-revisions.md`
discloses the minimum observational/cleanup adaptation. The original behavioral
assertions remain required and execute in the targeted process-contained controls.

Targeted cases are142 finite host subprocesses:

- 130 cases: each of65 owned positions, pre-syscall or post-syscall reporting error;
- two cases: every one of65 positions faults, pre or post;
- stale same-fd reuse through actual retained entry, closing access, closing retained
 entry, once-only lease/adoption, constructor primary+cleanup, partial composition
 primary+cleanup, completed result+cleanup, nonterminal child model, post-report
 number reuse and owner/frame bounds.

Five cases finish true healthy zero.136 synthetic close-fault cases deliberately
finish with bounded uncertainty records and **healthy_zero=false**, even if the
test oracle knows every actual close happened. One no-process nonterminal model
finishes with two actual wrappers leased and records healthy_zero=false.
Each test then exits its owned host process; parent waits/reaps terminally. Test
directory cleanup and terminal process containment are recorded separately from
the modeled cleanup disposition. They never prove that a real ambiguous OS close
succeeded, refund a runtime owner or qualify operational quarantine persistence.

No synthetic uncertain number is automatically retried. A separate number-reuse
witness obtains new test-owner descriptors from actual successful os.open calls
until natural allocation reuses the known post-close number. The old quarantined
close makes zero new syscalls and leaves the fresh descriptor usable. Only those
new known test owners are closed by their new birth handles. The old uncertainty
record remains present, and new modeled Retained admission remains refused.

Raw streams, exact commands, source/tool/revision identity, original input seals,
source custody, generation/error observations and per-case cleanup are retained.
The seal declares its separately checked exact76-byte self-seal metadata; there
are no other unlisted files. No OS/process/native instance inventory is used.

Independent actual-source review may accept this exact bounded prototype
correction. Genuine Rust snapshot exporter/loader provenance/session/build
selection, original typed result/all15 ledger joins, actual8192 context, complete
measured memory/work accounting, canonical integration, full historical target,
native/physical/FieldLog/published package/OTA/store/operations/GA remain pending.
