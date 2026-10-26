# Phase/lifetime impact and explicit pending limits

All byte sizes here are logical64-bit source-field inventories. They are not
fresh compiler layouts, stack/RSS measurements, or an accepted full role union.
The existing Progress/Paid/loan/record/config/budget/reply/caller owners survive
their same C3 phases; the proposal does not erase them when a helper begins.

| Phase / source and received place | Logical source / received bytes | Birth, last use and overlap |
| --- | ---: | --- |
| Existing Candidate owner | 2048 / borrowed, no move | Original caller construction through original cleanup/final exit; unchanged |
| Existing arena owner | 8388608 / borrowed, no move | Same non-resizable exclusive borrow; unchanged |
| Outer decoded word array and leaf w borrow | Existing128 / borrowed8 | Original caller record128 remains live; `loan.record.words` is a thin borrowed array reference, not a new128-byte copy |
| Existing semantic call arguments / received parameters | b16+c8+loan8+p8+steps8 / same48 | Existing caller/source places remain through the leaf and original cleanup path; admission/reply ownership must still join G1/G7/G128 |
| Existing Progress, Paid and Loan |144,24,16 / existing locals | Caller controls, wire owner and record/config borrow remain live through the proposed helper phases |
| G2/G5 shared arena reborrow / as_chunks self | 16 /16 | Enter block through view helper return; original b16 remains live |
| G2 Candidate exclusive reborrow and byte unsizing | 8 then16 /16 | Enter G2 block; c8 remains live, no payload move |
| G2/G3 split return tuple / received tuple | 32 /32 | Platform split return through tuple destructuring; original receiver/borrow still exists |
| G2/G3 time_bytes and index_bytes bindings | 16+16 / corresponding tuple fields | Whole respective block; byte regions are disjoint |
| Chunk helper returned tuple / received tuple | 32 /32 | Return through caller destructuring; empty remainder is still received |
| Caller word view binding / remainder discard | 16 /16 and16 /0 | Word view lasts through block; discarded empty remainder ends at statement |
| G2 row fields occupied/function/bytes/pins/last_used | source8 each / binding8 each | Respective initializer through end resident iteration; last_used array return is separate |
| G2 entry/nonce fields | source8 each / binding8 each | Pin iteration; coexist with original probe accumulators |
| G2 timestamp to_le_bytes receiver and argument | source8 / received8 | Each assignment; no64-element temporary |
| G2 timestamp array return / RHS / destination | 8 /8 then8 / existing8 | RHS survives destination-index evaluation; both distinct movements counted |
| G2 eligibility u8 value / A destination | 1 / existing1 | Conditional value survives destination-index evaluation |
| G2/G5 base/limit/index locals | source8 each / binding8 each | At most resident_base,pin_base,resident_limit,pin_limit,slot,pin in G2; resident_base,i in G5; blocks do not overlap |
| G3 caller merge argument / received c | 8 /8 | Whole call; caller semantic c8 also remains live |
| G3/G4 src,dst,width,base,left,mid,end,right,out,old_src | source8 each / binding8 each | Existing same ten named scalar roles; old_src is pass-end only |
| G3 a,b byte values | source1 / binding1 each | Comparison until selection; old a/b u64 fields shrink |
| G3 timestamp argument arrays | existing8 / received8 each | Separate LE calls; left scalar result survives right call |
| G3 timestamp scalar results | return8 / received8 each | Until unsigned comparison; neither operand elided |
| G4 assigned byte RHS / destination | 1 / existing1 | RHS survives checked LHS evaluation; replaces old8-byte assigned value |
| take_left expression / binding | source1 / binding1 | Comparison or exhaustion arm through chosen-side branch, one actual binding |
| G5 slot_byte / slot | source1 / binding1 then source8 / binding8 |255 guard precedes zero-extension; both locals remain in loop scope |
| G5 bytes and next | source8 / binding8 each | LE and successful checked_sub through state update |
| G5 Option arithmetic source / received / payload | tag+8 / tag+8 /8 | Explicit checked_sub/match; inherited checked_add analogous in G2 |
| Safe view nested helper frames | each pointer8,length8,mid8,size8,align8,tag separately | Source/received argument, tuple and Option fields have exact scalar edges in ledger; each nested frame ends before its caller resumes |
| Every checked built-in index | pointer8,length8,index8,scaled8,address8,predicate1 | Per access; these metadata/value temporaries coexist with live caller arrays, operands and views |
| G3 merge unit source / received | 0 /0 | Real return and caller completion edges are charged |

Private helper frames can reuse a reserved phase slot only after its earlier
occupant has ended. Sequential G2, merge and G5 views cannot overlap. Within a
phase, actual receiver, returned/received tuple, wildcard remainder and caller
binding places must all remain in the independent layout audit. NLL ending a
borrow is not evidence a conceptual source/received value was optimized away.

The complete named-role envelope stays control8192, wire3072, report8192,
setup12288 and inherited roles; reserved sum41984, global65536. The prerequisite
proposed union29344 and control increment1280 are unchanged proposed ceilings.
No bytes are assigned to unused global margin or transferred between roles.
There is no new retained owning payload array or larger public Result/observation;
the8-byte conversion/assignment temporaries are explicitly inventoried above.
This packet supplies the affected source/received inventory; it does **not**
certify that the pre-existing unaccepted full C3 lifetime inventory plus these
views fits29344. An independent complete peak/role reconciliation and fresh
compiler layouts are required before implementation acceptance. This is a
specific remaining gate, not a claim that any candidate is impossible.

Pending qualification includes exact Rust borrow checking/compilation, full
G1/G6/G7/G128 caller ownership reconciliation, all whole-program transient
roles, old API/report compatibility, host behavior, native/runtime gates and
independent acceptance. G6's active other-lane ledger must be joined only after
its own completion. Nothing here accepts or modifies it.
