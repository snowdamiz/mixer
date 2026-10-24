# Private Swift lifecycle V2 runtime failure

The first repaired Swift Debug run executed 23 exact authored lifecycle tests:
**22 passed, one failed, none ignored; exit101. Runtime acceptance remains false.**
The matrix stopped before other feature/profile contexts and all broader regressions.
No failed test was rerun. Source remains exactly `0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56`.

SL09’s selected constructor cleanup, lifetime work boundary and exact diagnostic
assertions passed in this context. SL13’s independent605/1803/4196/4206 cache
trace and warm+4/+6, hits+2, unchanged misses/decodes/evictions/resident bytes and
second==first ticket checks passed. An inherited second==initialized ticket
comparison then failed24vs22. Its later deadline/explicit-retire code was not reached.

The source independently admits one retained Cache ticket per decoded entry.
Initialize decodes35; first corpus decodes62and36; second corpus hits both.
Pin release retains residents and their tickets. The correct relative ticket
deltas are+1,+2,+0, with live cache entries0/1/3/3. The next SL13-only repair
proposal is unselected/unimplemented; no engine or accounting change is proposed.

## Source and compiler proof retained

Only SL09/SL13 test bodies differ from the original candidate. All other131files,
imports/helpers/hooks/21testbodies and production lifecycle/growth/accounting/Frozen
source are exact. Four fresh unit compiler contexts and39Frozen expanded methods
passed before runtime. Root accepted the precisely bound allocation/hygiene maps;
full macro expansion chains were not queried or claimed.

Root found and corrected a position-proof dictionary collision. The original
276-file freeze is unchanged. Its12-file occurrence supplement preserves all2744
raw occurrences,11760unit-role joins and1296zero-byte function-item-role joins.
The former108omitted constant occurrences, all original failed proof checks and
full before/after bodies/types/layouts remain retained. No numeric credit was added.

All five compiler targets, metadata scratch and the failed runtime target were
removed after empty-holder/process-group checks. The runtime target contained28
files and36,480,293logical bytes. Complete outputs, tools and executable bytes
are retained. No Node oracle, full real reactor or native/device run occurred.

## Entire original authored and remaining coverage ledger

This table preserves the original ledger verbatim. Passed identities cover only
their authored assertions in this single Swift Debug context; no full planned SL
row is complete. SL12 guest table mutation stays unsupported/unimplemented/unrun.

| Row | Original authored subcases | Original remaining gaps | V2 result |
| --- | --- | --- | --- | --- |
| SL01 | Duplicate/preinit with pending cancellation; exact state/counter/reservation snapshots and allocator refusal; corrupt Terminal marker for both requests. | Expired-deadline misuse combinations and direct per-control-method call instrumentation. | passed; full row pending |
| SL02 | Seven missing original reservation tickets and missing WASI/cache/State; actual failure, Terminal, no bound/guest/host debit, ownership restored. | Foreign-owner variants, nonempty arenas/pins/preparation, admission cancellation and restore fault variants; absent-control remains documented inherited expect precondition. | passed; full row pending |
| SL03 | Actual initializer global and stdout effect exactly once; two corpus calls then duplicate refusal. | Duplicate refusal before corpus calls also represented by SL01. | passed; full row pending |
| SL04 | Actual unit hooks force missing/CallerContinues/scalar/stored error/outer error; valid void control. | Runtime execution pending. | passed; full row pending |
| SL05 | Actual post-result value debit forces original inner Retained with bound live; no Ready. | Every separate frame/control/pin/cache/entry/nested-restore/live-debt/unfinished-bound adversarial variant. | passed; full row pending |
| SL06 | Actual page-sized admitted replacement/ticket retained with exact phase/context/storage; explicit original release/drain/completion; owner remains Terminal. | Committed old-ticket refund debt, occupied preparation and growth live disagreement variants. | passed; full row pending |
| SL07 | Actual original outer-restore hook yields inner RestoreRejected without reply or Ready; actual restore retry during cleanup. | Other inner Retained and outer Retained are scoped by SL05/SL06, all runtime pending. | passed; full row pending |
| SL08 | Unreachable, division, memory traps; proc_exit0/7/high unsigned; default denied random errno. | Indirect traps, typed WASI terminal failures and each denied grant variant. | passed; full row pending |
| SL09 | Zero fuel/work/frame/value/control/host dimensions and precise typed failure families. | All exact/one-below dimensions; cache/pin/page/State/Combined overlap exhaustion combinations. | passed; full row pending |
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

The other three focused contexts, Frozen/full-library/default/span runtime
regressions, remaining checkpoint/budget/WASI/failure variants, physical phones
and immutable separate-repository FieldLog release remain pending. No live
integration, full53MBtarget read/hash/run, native, Git, network or shared-tracker
operation occurred. No D3/G07/G08/dogfood/store/customer/operational/GA gate passes.

Read-only replay:

```sh
python3 -B verification/swift-reactor-lifecycle-runtime-v2/verify_failure.py
```
