# Correction 3 lifetime selection

Root accepts the authored logical lifetime bound for frozen correction 3
`cache_state.rs` SHA-256
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
The selected proof combines the 36-member producer packet with the 25-member
independent review and its 18 supplementary schedules. The producer's original
claim of an exactly complete phase map remains unaccepted.

The independent correction retains `stage` through the final semantic reply,
raising that Control row from 576 to 584 bytes. It also retains seven projection
locals through the final return, raising that row from 240 to 275 bytes. The
supplement explicitly covers pin and fill loops, plan and reset loops, final
`None` transfers, early replies, common-stage operations and the actual caller's
post-reply snapshot. Named values remain live to their source scope ends.

| Added role | Reviewed maximum | Existing allowance |
| --- | ---: | ---: |
| Control | 1,201 | 1,280 |
| Wire | 152 | 256 |
| Setup | 160 | 256 |
| Report | 2,688 | 2,896 |

The inherited 24,656-byte bound plus the existing 4,688-byte allowances remains
29,344 bytes, within 41,984 reserved bytes. The 65,536-byte ceiling and all role
reservations remain unchanged. Unused reservation or ceiling capacity does not
fund an omitted value.

The complete public `Result` retains its 488-byte capacity on error paths.
Five prior 232-byte capacities grow to 488; five new observation capacities
and four additional error capacities produce the 2,688-byte Report increment.
Source, receiver, designated return and received values are counted separately;
fields within a complete aggregate are aliases rather than additional payloads.
Each of the sixteen anonymous 128-byte clear temporaries ends at its own
statement. Together with the live 24-byte paid value, each needs 152 Wire bytes.
All twelve restores occur afterward. No optimizer elision is assumed.

This accepts a finite source-level logical inventory, not a machine stack or
standard-library implementation bound. Predecessor proofs are inherited through
their exact accepted identities; they were not replayed in full. Root verified
all 61 producer/reviewer members and the retained independent normal and optimized
results. The independent checker reports 7,765 checks and 14 rejected mutation
controls in each mode; earlier checker failures remain retained.

Complete source-work accounting and independent implementation acceptance remain
open. Sorting proposals change source/layout and cannot inherit this selection
without a new lifetime review. Native, compiler-target, signed-package, store,
operational and published FieldLog qualification remain pending. No GA gate is
promoted.
