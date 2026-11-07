# Authored local places and the explicit unclosed helper boundary

Sizes below are 64-bit source-field inventories, not fresh measured complete
compiler layouts or a full role-union/peak proof. Source/received boundaries
remain distinct even where a value is Copy or a temporary has no named binding.
No standard-platform callee internals or inherited caller owner are declared
absent just because this exploration stops at G4.

| Place/value flow | Source / received size | Birth and last use |
| --- | ---: | --- |
| Existing primary Candidate bytes | 2048 / same borrowed owner | Existing caller through merge return; no new buffer. |
| Caller exclusive thin Candidate argument / c | 8 / 8 | Immediate call expression through merge body. |
| Exclusive thin reborrow for coercion | 8 / 8 | Chunk call entry only; distinct from c. |
| Coerced mutable byte slice / chunk self | 16 / 16 | Chunk call entry through its return; pointer+length fields. |
| Chunk returned tuple / caller tuple result | at least32 /32 | Actual `as_chunks_mut` return through destructuring. Two fat references; no payload. |
| Tuple chunks component / words binding | 16 /16 | Pattern binding through last word access and merge return. |
| Tuple remainder component / wildcard discard | 16 /0 | Empty disjoint remainder received then unbound; no future access. |
| src,dst,width | 8 each | Literal initializer source8 to each binding8; whole merge. |
| base | 8 | Literal initializer source8 to binding8; each pass until final base guard. |
| left,mid,end,right,out | 8 each | Expression initializer source8 to each binding8; one merge block. |
| old_src | 8 | src value source8 to binding8; pass-end three-move swap, then ends. |
| take_left expression result / binding | 1 /1 | Either exhaustion literal or comparison result through chosen-side branch. |
| A/B LE array argument | existing word8 / received array8 per call | Indexed source place through conversion completion; each call separately. |
| A/B conversion output / initializer | 8 /8 per call | Return through let initializer. |
| A/B initializer / named binding | 8 /8 per binding | Each let through guard/comparison completion. |
| Timestamp LE array argument | existing word8 / received array8 per call | Only after MAX guards; ends at conversion return. |
| Timestamp conversion output / comparison operand | 8 /8 each | Left operand remains while right is evaluated; then `<=`. |
| Intrinsic index operands | pointer8,length8,index8 components | Each individual element access only; no fabricated fat receiver argument or returned reference. |
| Index bound predicate / branch operand | bool1, no actual function receive | One checked access; no independent callee boundary. |
| Intrinsic indexed element place | locator, not a new owning array | Names part of existing Candidate; never another2048 owner. |
| G4 RHS array value | existing source word8 / abstract assigned value8 | After RHS read through LHS evaluation and assignment; no explicit named array local/function. |
| G4 destination place | existing destination word8 | LHS evaluation through assignment; disjoint from source half. |
| Scalar arithmetic / update store | result8 / destination8 | Each cursor update, base assignment, swap or width update; source result ends after store. |
| Unit values from assignments, updates and blocks | 0 /0 | Operation completion/statement discard; no synthetic helper call. |
| merge result / immediate caller receive | 0 /0 | Function normal return and caller completion, distinct control boundary. |

Each comparison-array argument remains a separate by-value input. The left
timestamp operand coexists with the right decode. Each RHS assigned array value
coexists with the LHS pointer/length/index/check computation. This packet does
not assume a compiler coalesces these conceptual places or puts them in a
register. It deliberately does not resolve the array movement grain to obtain
a bound: even the favorable one-copy flow fails G4.

The actual chunk helper boundary is unclosed, not given a numerical allowance.
Exact recorded-compiler source binds `as_chunks_mut`, `split_at_mut_unchecked`
and `as_chunks_unchecked_mut`. Source/received inner fat self parameters,
rounded-length initializer/binding, mid argument, inner split returned tuple,
multiple_of_n/remainder bindings, array_slice returned reference and binding,
outer tuple construction/return, pointer/length metadata, raw-parts helper
arguments/returns, and enabled precondition checks all still need an exact
complete cost/lifetime map. Nested platform pointer/raw-parts/check helpers are
not mapped to a vague <=16 bucket. Their normal/error places cannot be funded
by unused G1 credits, borrowed G4 credits, optimizer elision or a second owner.

No complete source upper, fresh layout, 29,344-byte union or global65,536-byte
acceptance is asserted. G4's qualified lower core already blocks this exact
design, so root directed freezing that obstacle rather than expanding the
platform helper audit or another redesign in this packet.
