# Correction proposal2 independent accounting review

Proposal2 resolves C1 and C2. **No new actionable finding was identified.** Its
bounded source-operation, transfer, funding and named-memory proposal is ready
for root's numeric-contract consideration. This review selects no debit,
qualifies no historical128/192 execution, and accepts no final implementation,
semantic replay, release, device or GA gate.

The admitted manifest is
`58b2fccf992baade1eee51dfdd9f5e3bd5c039cfa5b52a3a25fef8d97ff034e5`:
42 members/633,148 bytes, verified before/after. Exact owned copies and command,
Python version/tool hash, source-tree digest, contextual HEAD, raw outputs and
cleanup are in `commands/admission-1/`. The previous796-member producer,
64-member accounting review and69-member correction review are verified
unchanged:929 members total. No old packet or proposal is edited.

| Immutable input | SHA256 |
| --- | --- |
| Operation ledger | `8ba395af50cd827242ce121f60dade5ebd270956602454fbd7345cf8f89c0a0f` |
| Numeric proposal | `736947e71b0fcaf102ac2c64438730afbc6d2954ac082134066f73fae8211550` |
| Finalization funding table | `baec5fde93a784a20351e48f1200cb1d7378c0999f82aa4dd84e94aba897581d` |
| Unchanged envelope source | `e86ef43a99f99245c78308666f91f5147981859ca03fa3f97e62d46993667535` |
| Unchanged parent source | `1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b` |

## Findings resolved

C1 is resolved by a dedicated F05 subdivision13, raising outer wrapper-final
reservation from29 to42. That reservation occurs before output safety, arena
construction and input observation; it dominates every core `finalize` call.
Every returned input Err uses F05 for E01 classification plus E09/project/EH03
and E10 return. This includes initial/context/profile/header/setup failures,
finish-reservation failure, guard failure, later decode/framing failure and
drain/footer/EOF/final-metadata failure. If finish47 was already paid on such an
Err path, it remains unused without refund.

Input Ok requires successful walk setup and finish reservations. Complete
Ok(true) and limited Ok(false) therefore use finish47 for their finalizer;
F05 remains unused. No branch borrows the other branch's inactive credit. The
ownership distinction uses the existing input Result, with no added runtime
flag, field or storage owner. Outer failures that return before observation
never finalize and return no aggregate. Output/report failures retain their
separate outer-error transfers after the finalizer has its own prepaid owner.

C2 is resolved in all six affected rows: BR01, BS01, BP01, S01, S03 and F03
now use the complete40-byte unit/walk Results. AnalyzerError remains32. Each
corrected transfer still fits one fixed-copy group, so no copy-group delta is
required. Both source files exactly match proposal1's measured declarations;
the32 complete-layout facts and raw independent probe receipt/source/output
are verified byte-for-byte and reused. **No new Rust compile or runtime probe
was performed.** Historical behavior probes are not relabeled as new passes.

## Source operations, transfers and framing boundary

All116 rows independently reconcile scalar atoms, rounding, copy count,
bounded repetitions and linked/helper composition. Relative to proposal1,
only the six complete-type annotations changed and F05 was added. The
private-leaf425, guard112, wrapper24, setup-source329, setup-wrapper42 and
complete-finish47 source bounds are unchanged. F01–F04 remain29; F05 adds13.
The425 bound remains a conservative upper, not a minimum lower bound or proof
that every possible tighter implementation must exceed128.

All108 transfer-edge entries match their ledger row, copy width/count and
bounded repetition. Each actual16-byte handle transfer has one work-copy
edge. Coexisting complete source/destination places are counted for storage,
without inventing a second copy. Complete232-byte values are split128+104 for
work and retain their full232-byte source/destination storage roles. Candidate
initialization is one complete2048-byte source/destination transfer split into
sixteen bounded128-byte pieces; the pieces do not create sixteen owners.

Seven accepted framing22 call/statement mappings match exact source lines:
iteration extent, mandatory8,192 preflight, one generic Budget call, one
decoded128-byte backing/Reader call, offset calculation, field/profile join
and Framing coordinate. The accepted ce8f3013 source is an exact prefix of
the unchanged parent. All new typed accesses, progress/poison checks, wrapper,
setup, finalizer and aggregate transfers remain separately mapped. This reuses
the accepted framing boundary without broad re-proof or replay. The copied
crosswalk's proposal1 C1/C2 limitation text is historical; proposal2's active
funding/type corrections supersede those annotations.

The unrolled twelve reads/stages/commits and single length preflight retain
the previous source range/lifetime argument: one exclusive arena slice, one
retained Candidate2048 owner, payload888..983, fixed prior96/next96/word8,
no resize/allocation/I/O/callback or escaping reply borrow. No candidate
by-value wrapper, return, closure capture or per-record reinitialization appears.

## Memory and global arithmetic

The explicit leaf roles total936 within their existing1152-byte lease. New
walk roles total240 within256. Checked-word statement phases are184/160/184
within256, using complete slice/Option/Pair/Range values. Complete40-byte unit
Results, Progress144, Reply128, observation128 and aggregate/Result232 remain
included with caller/return/source/destination/move places.

Independent phase and group arithmetic yields:

| Named group | Bytes | Existing reservation |
| --- | ---: | ---: |
| Candidate | 2,048 | 2,048 |
| Control | 6,656 | 8,192 |
| I/O | 1,472 | 4,096 |
| Metadata | 2,400 | 4,096 |
| Report/error | 4,296 | 8,192 |
| Setup | 5,168 | 12,288 |
| Wire | 2,616 | 3,072 |
| **Total** | **24,656** | **41,984** |

The65,536 ceiling and23,552 unassigned margin are unchanged; no new role spends
that margin. These are complete named logical roles, not compiler stack,
optimizer-copy, allocator/OS/RSS or native-memory qualification.

The proposed combined charge is22+425+24=471 within mandatory8,192 preflight.
Setup42+534=576 is within65,536; actual setup bound329 fits534. New report
reservations47+112+42=201 plus unchanged fixed report bound6,245 total6,446
within3,000,000. Arena8,388,608, I/O263,584 and total step268,435,456 ceilings
remain fixed. Report49,152 plus future host8,192 stays57,344 within65,536.

The proposed public formula `534*S_paid + 47*F_paid + 425*N_B` is distinct
from outer wrapper F42. Verified cases include0,534,581,1,006 for one charged
record, and1,782,579,781 at the elementary4,194,304-record counter bound. That
counter bound is u64-safe and is not an achievable capacity claim. The stricter
full-reserve/preflight arithmetic upper559,256 is also only an upper bound,
not a guaranteed observed prefix, throughput promise or full-cap acceptance.

## Acceptance boundary and cleanup

`commands/audit-1/receipt.json` records the116-row,108-edge, eight input-result
funding-path, type-provenance, seven framing-call and memory/cap/formula checks.
The proposal's source bounds and C1/C2 corrections are supported for root
consideration. Root must separately select the amended contract and numeric
values, update the historical constants, and obtain accurate final-source
layout/behavior/budget/oracle evidence. Combined final-source qualification and
all semantic/product/GA claims remain pending.

Only owned Python bookkeeping ran. No producer/frozen runner, Rust compile,
old64 retry, runtime probe, native simulator/emulator, phone, UI/capture,
process/device discovery or forbidden hosted harness was used. Synchronous
bookkeeping children returned and were reaped. No executable or disposable
runtime scratch was created. Source copies, outputs, commands and all prior
failures remain preserved; unrelated HEAD/root metadata changes are contextual.
