# Provisional candidate 2 root-leaf measurement

This snapshot is an independent measurement of evolving source, not acceptance of a frozen candidate. The source and all 420 actual VM inputs, the two test-only include changes, commands, outputs and tool versions are recorded in `measurement-receipt.json` and `provenance.json`. The captured cache source SHA-256 is `e0f2a6c66fe95a11e82b8bc7a944f0308e195ea47249cb769047bdda9f35070f`. Debug and Release agree.

| Inventory | Bytes | Alignment |
| --- | ---: | ---: |
| Preflight A / B | 1352 / 1664 | 8 / 8 |
| Setup / owner | 440 / 352 | 8 / 8 |
| Primitive / enlargement | 368 / 632 | 16 / 8 |
| Root leaf union | 1632 | 16 |
| Admission / owner branches | 1136 / 720 | 16 / 16 |
| Work-live / refund branches | 1632 / 1104 | 16 / 16 |
| Completion borrow inventory | 192 | 8 |
| Actual final cleanup return tuple | 40 | 8 |
| Whole control / proof / adopted classes | 1720 / 664 / 712 | 8 / 8 / 8 |

The candidate's named sums measure construction 57128, operation 80470, permanent cleanup 62096, header 62424 and unchanged foundation 16504 bytes. These are reservations for named Rust values, not physical storage aliases, stack instrumentation or RSS estimates. An inventory's alignment does not authorize reinterpreting a live foundation owner or borrowing its padding.

The final refund branch now explicitly includes refund checked-subtraction Options/patterns, category borrows, cleanup-fault arguments, get-or-insert receiver/return, fail/usage time values, record-cleanup borrows and the construction-phase narrowing calculation. The complete return tuple and complete caller borrows must remain in a different whole control class. The helper that consumed the large tail and caller storage must have returned before any header refund.

One simultaneous branch remains unclosed in this snapshot: `remove_live_with_wasi` underflow retains its own arguments, live-parts return, usage and checked subtraction while calling `cleanup_fault_with_wasi` and `get_or_insert`. Those latter fields exist only in the refund union member. Selecting that other union member cannot make the remove caller disappear. Adding all 88 fault/insert fields blindly to the maximum 1632-byte work/live group could round a 1720-byte sum to 1728 at alignment16; a separately measured actual remove-only branch avoids unnecessarily combining mutually exclusive work and add-live callers. This is a proof gap, not an observed behavioral defect or authorization for additional foundation bytes.

The final map also needs the `wasi.map(AccountedWasi::usage)` phases on each side of the header refund: map argument, AccountedWasi/Context receiver borrows, actual raw usage and Option transfer classes. The owner union branch contains those receiver fields and may be a whole-slot alternative while map frames run, because they return before refund or record-cleanup begins. The final frozen branch table must establish that relationship and all six optional-observation roles explicitly.

The original candidate 1 review receipt and its 85 bound artifacts remain unchanged. No guest execution, device access, publication, commit, composed executor or GA qualification occurred.
