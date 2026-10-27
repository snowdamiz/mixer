# Actual bounded-call stop contract and unselected work

Work means a bound on source-level logical work, not CPU time, wall-clock time,
native syscall latency, allocator overhead, physical stack, or RSS. The original
ExecutionWork field, usage counter, narrowing-only ceiling, and no-refund rule
remain the only work authority. The original maximum ceiling is 1,000,000,000.

The frozen encoder has no stop callback. `borrow_snapshot_v2` and `into_cursor`
are fixed bounded calls, and `next_block` is one indivisible bounded call. Its
source can make at most 515 progress iterations, 513 metadata record-word visits,
and nine directory probes per iteration, while copying at most 4096 bytes.
`record_word` rebuilds and validates the whole up-to-five-word record for EACH
output word. The directory search repeats on each metadata progress iteration.
The original proposal's once-per-record `64N` explanation therefore does not
bind this component. No inherited P/R emission allowance is used here.

The actual new writer places immutable actual-control stop observations before
and after cursor acquisition/init, block clearing, every `next_block`, each
File metadata call, the stream-position call, each explicit `write`, block exit,
and final publication. Fixed nine-count shape comparison is bounded by adjacent
checks and precedes all File operations. A returned encoder error and a post-call
stop remain independently retained. IO plus post-stop retains the actual original
`std::io::Error`; it is never reconstructed from a Debug string. Successful native
bytes update checked acknowledged progress before returning a post-call stop.
There is no promise of interruption inside a record/word loop or native syscall.

The actual storage/work source does fixed same-owner/layout/category/combined/
ticket coverage and nonterminal storage preflight, then debits original planning
work before the nine actual count operations. The original proposed planning
constant 16384 is present as an UNSELECTED contract. Full planning/helper source
operation accounting still needs review. An admitted branch would predebit the
audited emission bound, atomically enlarge that exact existing Construction
ticket, privately capture its previous extent, and only then initialize actual
plan/transfer values. Reservation refusal does not change ledgers/first_failure.
Planning or emission already consumed is never refunded.

`proposed_emission_work_v1` deliberately returns typed `WorkAuditPending`. This
is a fail-closed preparation boundary, not a guessed debit coefficient. Consequently
this exact prepared source cannot reach new admitted writer execution, even if
somebody calls the private authentic entry before a later source release. The
source still contains the actual admitted ownership/storage/writer/cleanup body
so compiler and signature review can expose its contracts now.

Root has separately accepted the encoder-only action interface at
`../swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json`
SHA256 `757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351`:
fixed initialization 14224; one block `26+68I+39D+139W+Q`, bounded by 291214;
opaque getter 3; abort on first error with no failed-call retry, at most B
nonempty blocks and one terminal None. Those are encoder-only logical actions.
Writer/caller/shape/control/stop/finalizer source costs are separately pending.
The complete checked formula and maximum-envelope refusal must be released by
root before a later variant replaces the pending result.
No product limit, alternate work grant, deadline reset, cancellation clone as
stop authority, injected clock, callback, unused credit refund, or maximum-derived
grant is introduced. Complete phase/helper/foundation closure and genuine fault,
alias, all-eight outcome, work, stop and cleanup behavior receipts remain pending.
