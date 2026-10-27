# Independent lifecycle-correction review

Disposition: **R01 and retained-wrapper R02 are corrected within the finite source
model; terminal stdio cleanup requires a further correction. Complete composition
acceptance is withheld.** Root explicitly classified the stdio finding below as
required within the selected composed prototype.

Input custody: all476 declared regular members plus only seal.json and the exact
76-byte self-seal sidecar verify against seal SHA-256
`57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1`.
No correction member was read or imported before successful custody. Root's
selection is copied verbatim in root-selection.json and hashed in input-custody.
The correction source tree independently recomputes to
`3b78a8a719ab18856919ca5c201a403ccfb6223cbd012e6c1a39c5c11d3cacd6`.

## Required C01: terminal stdio can disappear into healthy-zero accounting

`corrected/replay/prototype.py:483-490` retains the original terminal_streams
implementation. It registers two TemporaryFile descriptors, yields them, then
removes both from STDIO_FDS in finally **before** the surrounding stream contexts
close. It neither records uncertain stream cleanup nor aggregates its errors.
ownership_snapshot at125-127 derives healthy_zero from those now-empty ledgers.

The independent bounded child case stdio-close creates two actual temporary
streams. It injects an OSError before the second stream's actual close and raises
a separate original Refusal inside terminal_streams. fstat on the separately
captured test-owned stream proves it remains open at the observation. Nevertheless
STDIO_FDS is empty and ownership_snapshot reports healthy_zero=true, owners=0,
all token states=0, uncertain_close_records=0, stdio_contexts=0.

The propagated exception is the injected stdio OSError. The original Refusal
survives in Python's __context__ chain but is no longer the structured primary
failure required by the selected cleanup contract; no CleanupAggregate preserves
it as primary. This is neither loss of all exception history nor a claim about
an actual kernel ambiguity. It is a deterministic owned-stream fault schedule
that exposes false healthy-zero accounting and wrong primary-result semantics.

The exact unchanged-source witness is independent_case.py:stdio_close. Its raw
stdout records both stream/accounting and exception observations before asserting.
Its stderr preserves the required failed assertion. The test process exits1 and
the parent terminally reaps it; process containment is not healthy stream cleanup
or resolution of a real ambiguous close. The known open stream is intentionally
not retried or erased by the witness. No frozen input is changed.

Select a bounded stdio ownership/close protocol that retains uncertainty, consumes
each independent close capability at most once, still attempts every other owned
stream, preserves the exact original primary and every cleanup error, and keeps
healthy_zero=false while anything is unresolved. Saved numeric descriptor values
must remain observations, without authority over later reused descriptors. Review
actual Python stream-object ownership/destructor behavior when designing this
correction; a raw numeric quarantine alone must not silently authorize a later
stream destructor or duplicate close against reused numbers. A real OS ambiguity
retirement policy remains separately pending.

## Scoped positive review

The correction changes only prototype.py between variants. Both schema.py and
consumer.py, both producer26-method suites and all307 snapshot-leaf controls are
byte-identical. Both copied producer suites freshly pass all26 methods with no
failure/error/skip. Exact raw original R01/R02 witnesses are copied unchanged.

R01's lifecycle fix is source-consistent and passes an independent real retained
composition-entry control. A stale closed wrapper and fresh same-path/same-inode
wrapper naturally receive identical descriptor numbers but different owner
generations. Stale check/read/seek/metadata/lease/composition refuses before output
creation, repeated old close makes no new close call, and the fresh owner remains
usable. That control ends with true healthy-zero ownership.

Retained-wrapper R02 is corrected under the source model. Independent pre- and
post-syscall errors across separate positions still attempt all independent
handles once; exact injected exception identities survive. A pre-close known-open
descriptor and a post-close known-released number both remain uncertain/accounted
and block new owner admission. Repeated close returns the identical terminal
report without another numeric close. The test deliberately finishes with two
uncertain token records and healthy_zero=false.

Independent nested-frame controls preserve the exact original ValueError primary
alongside every cleanup failure, or retain the identical completed observation
when cleanup alone fails. An independent number-reuse control naturally obtains a
new test-owned descriptor with a quarantined saved number, then confirms repeated
old close invokes no syscall and leaves that fresh owner readable. The uncertainty
record remains present. New test-owned handles are retired only by their own
successful-open birth handles; old uncertain capabilities are never retried.

The code's open/closing/closed/quarantined gates, monotonic generations, token
identity, once-only close consumption and lease claim prevent the original stale
wrapper behavior within supported interfaces. CleanupFrame flattens retained
owner failures without discarding primary/completed observations. This remains
a closed Python model; arbitrary mutation of module-private dictionaries, direct
external syscalls, hostile children or coordinated filesystem rewriting are not
admitted by it. Source loops and record caps are finite; no actual Rust caller,
whole-Python heap, CPU, retry/time or runtime debit allowance is established.

## Raw R02 adaptation audit

All six exact old/new raw witnesses were freshly rerun in separate bounded host
children. Old source retains three original failures. Corrected R01 passes. Both
corrected raw R02 commands retain failure/error outcomes and are never relabeled
passes. The post-close witness observes zero actually open captured ancestors,
then its old numeric-retry finalizer receives EBADF and attempts forbidden mutable
accounting removal. The pre-close witness uses held.fd after close began; its new
generation-bound access correctly refuses. Its obsolete finalizer also attempts
mutable accounting removal. Both tearDown zero assertions conflict with the
selected requirement to retain unresolved uncertainty.

control-revisions.md discloses these changes accurately. The separate65-position
pre/post adaptation captures numeric test observations before close, keeps the
required assertions that every independent remaining handle is closed and every
known-pre-close open handle stays accounted, and removes unsafe retry/registry
erasure. It does not weaken the behavior into expected failure. Its subprocess
containment is correctly separate from healthy-zero or real-OS resolution.
Our independent multi-close and reused-number controls reproduce those required
behaviors without invoking the producer adaptation.

## Retained evidence and fresh commands

The offline retained audit verifies all150 command stream hashes and terminal
dispositions, all142 case results, five genuine healthy-zero cases,136 deliberate
uncertainty cases and one no-process nonterminal-child model. That is an audit of
retained142-case evidence, not142 fresh independent executions.

Fresh bounded commands: two producer suites, six exact raw old/new witnesses and
six independent child cases, each bounded by15 seconds and terminally reaped.
Independent results are **five passed, one required failure**. All raw streams,
exact argv/cwd, elapsed times and hashes are in command-receipts.json and logs/.
run_review.py's expected exit1 records the failing witness without declaring its
behavior passed. It is not a complete-composition success result.

Parent-owned scratch directories are empty after commands. Fault children retain
modeled uncertainty at terminal exit; the stdio witness exposes a false candidate
healthy-zero observation. Neither is reported as successful operational cleanup.
No owned process remains running after the bounded child waits. No OS/process
inventory was used to establish that claim.

Actual OS ambiguity resolution, Rust snapshot export/loader/build/session binding,
original typed result/all15 ledger joins, actual8192-byte context, complete Rust
layout/work/lifetime accounting, canonical integration/full target/new CI/compiler,
native/UI/capture/physical/FieldLog/published package/OTA/store/operations/GA remain
pending. No native/UI/capture process, inventory, prohibited hosted read/import/
execution, canonical edit, original packet mutation, commit, push or publication
occurred. Only this new review directory was written.
