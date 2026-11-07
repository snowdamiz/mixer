# Intended range, ordering and loan proof for the exact sketch

The only primary payload is the existing Candidate2048. A safe
`as_chunks_mut::<8>()` call at length2,048 is intended to yield256 word elements
and an empty remainder, without allocating or copying payload. The literal8 is
nonzero. This is a documented API assumption, not new compiler/borrow evidence.
All words retain `[u8;8]` type and all numeric interpretation remains LE.

Initial `src=64`, `dst=128`; each completed pass swaps the values using three
explicit scalar moves. Thus they are always opposite and each identifies one
disjoint64-word scratch half. Timestamp words0..63 are never destinations.
The six width values are1,2,4,8,16,32. Every pass covers64 outputs, so all passes
perform exactly384 transfers and the even number of swaps leaves the sorted
result in the original source half at words64..127, bytes512..1023.

For each width, base starts0 and advances by2*width to64. Thus each block has
`mid=base+width`, `end=base+2*width<=64`, and equal nonempty halves. Invariant:
`left in base..=mid`, `right in mid..=end`, and
`out-base=(left-base)+(right-mid)`. When `out<end`, both halves cannot be
exhausted. If `left==mid`, the right side is valid; otherwise if `right==end`,
the left side is valid; otherwise both sides can be compared. Increment only
the selected side and then out; this preserves the invariant until out=end.

Every source index is `src+selected_side` with selected_side<64, hence64..191.
Every destination is `dst+out` with out<64, hence64..191. Both lie below256.
Their byte ranges contain exactly eight bytes and the source/destination halves
are disjoint throughout a pass. Byte offsets are at most256*8; control/index
arithmetic is far below usize overflow on the64-bit host. This is an offset
bound, not a claim about the numerical base address of the existing allocation. The copy RHS is evaluated fully before the LHS; an RHS array value
survives only the LHS address evaluation, not another sort step.

Each actual comparison reads A then B from the selected index-word half.
`b==ABSENT` short circuits first. If B is eligible, `a!=ABSENT` is tested; only
if both indices are eligible are timestamp A then timestamp B read. Eligibility
seeding supplies only0..63 or ABSENT. Sorting moves those exact arrays without
creating new indices, so eligible timestamp indexes remain below64. A timestamp
equal to u64::MAX is valid data; only index-word MAX marks ineligibility.
The `<=` comparison selects left on equal timestamps. Initially eligible index
words appear in ascending slot order, so stable merges retain ascending slot
order for equal timestamps. ABSENT remains after eligible entries.

For width w, each of64/(2w) merges compares at most2w-1 times. The six pass
bounds are32,48,56,60,62,63; sum321. This counts comparisons including tail MAX
entries and is independent of timestamp values. Transfer count remains384.
No executable sort/model/fixture test is used to establish these source facts.

The exclusive word view lives for the whole merge. Each comparison's reads
finish and copy their array operands before a subsequent direct word mutation.
For assignment, the temporary shared source access ends after RHS evaluation;
the retained RHS value owns eight bytes and contains no borrow into Candidate.
LHS mutable access can then occur. The word view and empty remainder end on
merge return, before prefix/staging/cleanup/envelope helpers can borrow the
Candidate byte owner. No reference is returned. A fresh compiler check of this
exact sketch is deliberately pending; these are intended language-level loans.
