# Native capability ABI design review

This is a read-only design review of proposal commit
`3b1903ad209a8292219009851b839647d48499f7`, compared with the unchanged legacy
session/FFI/header and committed guest design `e8012c5a923397729974dab6b297eab2f6e7cf0b`.
No native capability C implementation is qualified. No production/proposal edits,
builds, device work or publication were performed by this lane.

The proposed LP64 structures are internally consistent with their listed fields
and existing C layout receipt. No concrete field-offset defect was found. Shared
sixteen-slot ownership, separate actual-exit accounting, retained closing handles,
legacy/capability route separation and destruction outside the registry lock are
the correct requirements. The following corrections should precede implementation.

## D1: Make reclamation publication explicit; quarantine must be monotonic

The legacy `SessionLease::drop` first drops its `Arc` outside the registry mutex,
then reacquires the registry to reclaim (`session.rs:168–179`).
`begin_reclaim` checks `Arc::strong_count == 1` under that mutex (`123–136`).
Adding independent atomic outstanding/quarantine loads under the registry does not
by itself document a coherent publication protocol for earlier ledger writes:
`Arc::strong_count` is a snapshot, not an acquire synchronization contract.

A simple correction is to serialize transient lease release with the registry:
while the registry still owns its `Live`/`Closing` reference, release the transient
reference under that mutex and evaluate reclamation there. That release cannot be
the final session destructor; final destruction remains outside the registry lock
in `Reclaiming`. This makes prior obligation/quarantine updates visible before any
other registry observer can see zero API leases. An explicit registry-owned active
API count or a separately proven atomic/fence protocol is another valid design.
Do not rely on a pre-lock mailbox-usage snapshot or independent atomics alone.

Keep `quarantined` as an irreversible failure latch after publication. Root's
initial follow-up sketch set it before take and cleared it after normal commit;
that could erase quarantine set concurrently by an invocation panic/poison path.
Use an armed **local** RAII guard: arm before a possibly dispatching operation,
set permanent quarantine on unfinished Drop, and merely disarm after full commit.
The transient session reference already protects the ordinary in-progress phase.

## D2: Retain a fixed ticket ledger and make take publication unwind-safe

C retains integers, not the Rust `DispatchLease`. Dropping a temporary ticket does
not acknowledge native exit. Store the actual owner-bound ticket in one fixed
`[Option<Entry>; 8]` ledger per capability session, with an acknowledged bit.
The registry count and ticket publication must commit before the transient API
lease ends and before successful C output is treated as published.

Root's proposed order `ledger -> mailbox`, with the registry acquiring neither,
is compatible with guest `instance -> mailbox` provided no path adds a reverse
edge. Obtain the transient session reference under the registry first, then release
the registry before ledger/mailbox work. Reclamation must never inspect a mailbox
or ledger while holding the registry mutex. A pending-take guard must conservatively
pin/quarantine the session if unwind occurs after mailbox dispatch but before exact
ledger/count/output commitment. No fallible allocation or uncontained callback may
sit between an issued ticket and its durable ownership accounting.

Only a successful Call creates an entry/count. None, too-small and Cancel do not.
A Cancel ticket is a control identity for an existing call; match it to the ledger
and drop that temporary Rust value without treating it as exit. A new Call in a
reused request slot may replace only an acknowledged old entry with a different
request generation. An unexpected unacknowledged replacement is a fail-closed
invariant violation, not permission to discard its ticket.

## D3: Acknowledged ledger entries are not authority for repeated acknowledgements

The mailbox can retain an acknowledged request while delivery is pending, then
release it on poll/close. `Mailbox::ack_exit` distinguishes AlreadyAcknowledged
while retained from StaleRequest after release. A ledger entry can outlive either
state. Always delegate the exact stored ticket to the mailbox, including repeated
ack; do not return kind2 simply because `Entry.acknowledged` is true.

Decrement the common outstanding count only on the first successful Rust ack and
never on AlreadyAcknowledged, stale, foreign, operation mismatch or poison. Keep
the transient API reference through that commit/reclamation boundary. Post and
deadline narrowing likewise consult mailbox state, rather than using a cached
acknowledged flag to bypass its retained-generation/consumption checks.

## D4: Close/cancel need the native owner path and late-registration handling

The e8012c5 design describes `CapabilityGuest::close(&mut self)` but does not list a
native-port close primitive. That is a design/integration omission, not a missing
current WIP primitive: spot inspection confirms the in-progress
`CapabilityPort::close(&self)` latches shared closed/cancellation state and calls
mailbox close without taking the instance lock. The independent frozen Rust review
must still qualify that implementation before C depends on it.

Native cancel/close must use that owner path outside the registry and instance
mutexes. Merely setting the legacy common cancellation bit leaves the mailbox able
to drain queued calls when no guest invocation is running. Calling `guest.close`
through the instance mutex would instead break nonwaiting cancel/close behavior.
Keep the transient lease until owner close finishes; poison retains unresolved
capacity. Specify terminal-live repeat-cancel semantics separately from closed
handle access. A trapped/cancelled wrapper must not keep take/post admission open.

A take admitted before close can return a Call after close has already cancelled
the Swift task mapping. The bridge must invalidate/latch its activation generation
before cancellation, serialize dispatch registration against close, and recheck
that generation before I/O. A late call gets an immediate no-I/O exit acknowledgement;
it cannot escape cancellation merely because it was absent from the earlier map.

## D5: Preflight the report itself before any output write

The existing `ffi::boundary` writes its report unconditionally after its body
(`ffi.rs:106–127`). That is valid under the old caller contract forbidding overlap,
but cannot implement the new stronger promise to reject overlap without mutation.

New entry points need complete checked-address/range preflight before creating
borrowed slices or writing report, handle, message, result, did-invoke or payload.
Include the report range in all pairwise input/output and output/output checks.
If the report is null, numerically invalid or overlaps any other range, return3
without writing it or any other output. Only after valid disjoint output storage
is established may ordinary semantic errors write a report/default outputs.

Check `size_t` caps, `isize::MAX`, pointer-plus-length overflow, checked value-count
multiplication, full fixed-structure storage, and full buffer capacity. Empty ranges
remain empty (null only where the zero-length contract permits); struct alignment
is unrestricted using unaligned reads/writes. Do not construct aligned Rust
references to arbitrary C storage or read pure output size/version bytes before
initialization. Numeric checks still cannot validate dangling native pointers.

## D6: Freeze the remaining C details before consumers

Publish exact prototypes and a per-function result/status/error matrix. In
particular define post-after-early-ack, deadline narrowing after terminal/ack,
allocation failure, busy, poisoned state, live-terminal versus closed handle, and
zero remaining-time results. Result kind0 in initialized error output is not an
accepted operation unless the outer report succeeded.

State take capacity0..524288, post length1..524288, reservation bytes1..8388608,
startup/export name bounds/UTF-8, checked value-array count/encoding, and the exact
`uint32_t` 0/1 did-invoke output/default. New structures require Rust `repr(C)`
size/alignment/offset tests in addition to the already compiled C assertions.
Do not use Rust enum/usize layouts as native wire layouts.

The independent validator must use the same full private import/body/startup/wake
validation as create, without instantiating memory or exporting a privileged
Module. The committed guest design exposes only read-only memory; new C write
requires a private checked wrapper operation without leaking its Instance/Module.
Keep errors and unsupported combinations fail-closed.

## D7: Preserve old entry points and state the limits of raw-token foreign checks

One common registry must count reservations, both live variants, closing work,
quarantine and destructors; creating a second pool is insufficient. Check the
expected variant in every old/new handle entry point, including cancel and close,
before side effects. Leave legacy profiles, headers/layouts, floating-value bit
encodings, terminal/busy/error rules and one-shot validation routes unchanged.
Run all old public C/session tests against the combined-feature archive, plus
mixed sixteen-slot admission and cross-family rejection matrices.

The C tuple `(session handle, raw request token, operation)` names a request in
that handle's context. Equal token bits legitimately exist in separate sessions.
If native code substitutes another valid handle that has its own matching tuple,
C cannot detect the caller's original intent. Route only through that session's
stored owner-bound ticket; never rebuild a ticket from guest bits. Scope foreign-
identity claims/tests accordingly. Stronger mixed-tuple rejection would require a
separate native ticket identity, absent from the current signatures; no such API
change is proposed by this review.

## Required follow-up proof

Use barriers/injected unwind to cover take before/after close, ticket/count/output
commit, simultaneous invocation quarantine, last ack during reclamation, stale ack
after poll/close, acknowledged replacement, unacknowledged replacement rejection,
blocked destruction, poison and the mixed global ceiling. Test every overlapping
report/output/input pair with unchanged sentinels, plus unaligned/overflow/zero/full
ranges. Run actual public C consumers and old ABI regressions only after a frozen
Rust guest implementation is independently reviewed. None of those execution gates
is passed by this design-only review.
