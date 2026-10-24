# Private Swift lifecycle first runtime failure

The first selected Swift Debug run executed the 23 exact authored lifecycle tests:
**21 passed, two failed, none ignored; exit 101. Runtime acceptance is false.**
The matrix stopped before Swift Release/all-feature runs and all broader regressions.
The source and assertions remain unchanged. No failed test was rerun.

Candidate closure: `0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f` (132 files).
The accepted accounting packet is unchanged; this packet records actual runtime failure.

SL09 fails before Initialize because its original zero lifetime execution-work budget
correctly rejects state construction. The actual first charge is 38,319,741; the
test helper unwraps the constructor error. Independent constructor arithmetic gives
38,319,823 total successful construction work. The proposed initializer-specific
edge sets that original lifetime budget and expects entry work attempt 38,319,824.
The exact constructor rejection and retained cleanup tail must also be tested.

SL13 observes cache work 4,196→4,206, violating its incorrect unchanged-work
assertion. Independent lookup, pin-record and resident-slot costs are 4 for the
outer warm call plus 6 for its nested warm callee. The full source-derived trace
is 605 after cache construction, 1,803 after init, 4,196 after call one, 4,206
after call two. These predictions derive from charge sites and literal bodies;
they are not substituted observed expectations. See the exact source-bound
`independent-source-traces.json` and `repair-proposal.md` in the runtime packet.

The proposed repair is unselected and unimplemented. It changes only future
isolated tests and requires fresh accounting for every changed unit body/carrier.
No engine, owner, public API, ceiling or ticket change is proposed.

All build/list/test outputs and exact executable bytes are retained. The owned
target was removed after empty holder and process-group checks: 28 files and
36,505,412 logical bytes. No native instance, live integration, Git or network
operation occurred. No full reactor target was read, hashed or run.

## Complete original authored/remaining coverage ledger

The following original ledger is preserved verbatim in `authored-coverage.json`
and the receipt. A passed test identity covers only its authored assertions in
this single Swift Debug configuration. **No full planned SL row is complete.**
SL09 remains family-level; SL12 guest table mutation remains unsupported/unrun.

| Row | Original authored subcases | Remaining planned cases/limitations | This run |
| --- | --- | --- | --- |
| SL01 | Duplicate/preinit with pending cancellation; exact state/counter/reservation snapshots and allocator refusal; corrupt Terminal marker for both requests. | Expired-deadline misuse combinations and direct per-control-method call instrumentation. | passed; full row pending |
| SL02 | Seven missing original reservation tickets and missing WASI/cache/State; actual failure, Terminal, no bound/guest/host debit, ownership restored. | Foreign-owner variants, nonempty arenas/pins/preparation, admission cancellation and restore fault variants; absent-control remains documented inherited expect precondition. | passed; full row pending |
| SL03 | Actual initializer global and stdout effect exactly once; two corpus calls then duplicate refusal. | Duplicate refusal before corpus calls also represented by SL01. | passed; full row pending |
| SL04 | Actual unit hooks force missing/CallerContinues/scalar/stored error/outer error; valid void control. | Runtime execution pending. | passed; full row pending |
| SL05 | Actual post-result value debit forces original inner Retained with bound live; no Ready. | Every separate frame/control/pin/cache/entry/nested-restore/live-debt/unfinished-bound adversarial variant. | passed; full row pending |
| SL06 | Actual page-sized admitted replacement/ticket retained with exact phase/context/storage; explicit original release/drain/completion; owner remains Terminal. | Committed old-ticket refund debt, occupied preparation and growth live disagreement variants. | passed; full row pending |
| SL07 | Actual original outer-restore hook yields inner RestoreRejected without reply or Ready; actual restore retry during cleanup. | Other inner Retained and outer Retained are scoped by SL05/SL06, all runtime pending. | passed; full row pending |
| SL08 | Unreachable, division, memory traps; proc_exit0/7/high unsigned; default denied random errno. | Indirect traps, typed WASI terminal failures and each denied grant variant. | passed; full row pending |
| SL09 | Zero fuel/work/frame/value/control/host dimensions and precise typed failure families. | All exact/one-below dimensions; cache/pin/page/State/Combined overlap exhaustion combinations. | failed; full row pending |
| SL10 | Final-check cancellation/deadline, immutable deadline and initialization cursor. | Cache/decode/nested/growth/WASI checkpoint placement variants and earliest WASI deadline. | passed; full row pending |
| SL11 | Actual trap first diagnostic remains authoritative across repeated Terminal markers and actual cleanup observation. | All cursor-stage combinations and later cleanup/refund/restore cause preservation. | passed; full row pending |
| SL12 | Actual memory/global mutations across init+two calls; repeated actual indirect table reads; table identity/content preservation; strict unsupported reference/table fragment rejection. | Guest table mutation unsupported by selected engine and explicitly unrun; real corpus local Workspace is not persistent-state evidence. Product scope unchanged. | passed; full row pending |
| SL13 | Independent hand-authored instruction traces (init6; each corpus12), cache-hit work accumulation, unchanged deadline and ticket count. | Exact execution/WASI/host/work/category/combined peaks and broader cache hit/miss traces. | failed; full row pending |
| SL14 | Same 4-fuel lifetime: init1 + call1(2) + call2 partial1 then exact exhaustion. | Execution/cache/WASI/host work and between-phase absolute deadline variants. | passed; full row pending |
| SL15 | Captured stdout init and cumulative stderr suffixes call1/call2; real output preserved before trap. | Later-call logging exhaustion and parser/receipt buffers (separate runner). | passed; full row pending |
| SL16 | Zero/nonzero/extreme valid i32; missing/CallerContinues/void shape failure; valid scalar followed by actual failed restore. | Runtime execution pending. | passed; full row pending |
| SL17 | Actual OS secure randomness grant and default-denied stdout; same WASI counters. Strict fixture includes all34 descriptors. | Real clocks, all34 behavior cases, partial errno/range/reentry and denied path/preopen/socket variants. | passed; full row pending |
| SL18 | Three real nested calls then trap; zero live frame/value/control/pin debt and no added instruction/work during cleanup. | Retained nested pins/failed entry/growth-debt and all exhaustion/interruption cleanup permutations. | passed; full row pending |
| SL19 | Actual combined frame envelope exact and one byte below; rejection before admitted phase. | Permanent/header/bootstrap constructor exact/one-below and State-only admission boundary variants. | passed; full row pending |
| SL20 | Warm actual lifecycle wrapper under first-allocation refusal measures zero allocations/attempts. | Cold cache/growth allocation deltas and each reached fallible allocation ordinal. | passed; full row pending |
| SL21 | Actual positive formula presence,86 tickets,128MiB State/256MiB Combined and restored frame bound. Exact full-body/compiler/layout coverage is separately bound in accounting evidence. | Accounting review and every runtime assertion pending. | passed; full row pending |
| SL22 | Strict complete validator rejects unsupported reference body and corrupt module; closed preinit target refusal. | Fresh negative compile compositions and complete public API/ABI audit; prior compiler packet retains original exact borrow rejections. | passed; full row pending |
| SL23 | Actual existing prepare/run/complete Preserve caller leaves successful initializer Uninitialized. | Full-library/default/span/Frozen runtime regressions and production Clippy/formatting; compile/list is not their execution. | passed; full row pending |

Frozen/full library/default/span regressions, the other three focused contexts,
remaining failure/budget/checkpoint/WASI variants and full original product
scope remain pending. Physical phones stay disconnected and deferred to final
acceptance. FieldLog still requires immutable packages from a separate repository.
No D3, G07/G08, dogfood, store, customer/operations or GA gate is accepted.

Read-only replay:

```sh
python3 -B verification/swift-reactor-lifecycle-runtime/verify.py --live
```

The replay reads retained evidence only. It does not rerun tests or compile code.
