# Source-order/range argument

This is a mathematical argument for the exact proposed source, not proof that
Rust compiles, a substitute for the independent reader, or runtime evidence.

Admission already proves arena length8,388,608 and configured1..64 resident and
pin limits before G2. The G2 read-only arena view consequently has1,048,576
eight-byte elements and empty remainder. Resident base/8 plus row*8+field, with
row0..63 and field0..7, is within the existing Resident64x64 region. Pin base/8
plus pin*6+field, with pin0..63 and field0..5, is within Pin64x48. The existing
short circuits prove entry<slots before token joins index a resident. Every
conversion remains little endian. The source never casts a sentinel as an
address. `checked_add` still refuses before changed semantic arena mutation.

G2's Candidate split at512 yields disjoint lengths512 and1536. Mutable timestamp
chunks have64 elements; timestamp writes use slot<64. Index stores use slot
and512+slot, so their ranges are0..63 and512..575 within the1536-byte view.
Both halves are initialized at all64 positions. A entries are ascending actual
slot values when eligible, else255. Narrowing uses only slot<64. All remaining
Candidate offsets and old scalar/row destinations are unchanged. Neither array
view owns payload or extends past its block.

At merge entry the same split gives immutable timestamp chunks64 and mutable
index bytes1536. src/dst are0/512 in opposite order. width takes1,2,4,8,16,32;
base is a multiple of2*width; end=base+2*width<=64. left starts base and is
incremented only after a left take; right starts mid and increments only after
a right take. Exhaustion tests precede every pair comparison. While both halves
are live, base<=left<mid<=right<end<=64. Both byte-index reads are in the active
source half, and each output writes the opposite half at dst+out<576. No source
element is overwritten while its pass can still read it. Six even swaps leave
the final run at physical Candidate offset512.

Within a comparison, A is read, then B. The B==255 short circuit precedes the
A!=255 guard. Only after both permit a timestamp read does zero-extension to
usize occur. Every non255 byte is a seeded0..63 value, preserved by scalar
assignment; timestamp bounds therefore hold. Timestamp A precedes timestamp B.
`<=` keeps the left record first on ties. Stable induction from ascending slot
seed order is exactly ordering by unsigned `(last_used,slot)` with all255 tails
after every eligible slot. A true u64::MAX timestamp remains valid data.

Each pass emits64 outputs. A merge of two width-sized halves uses at most
2*width-1 comparisons. Across32,16,8,4,2,1 blocks this gives32,48,56,60,62,63,
sum321. The bit-reversal-key model reaches this bound; this is an attainable
source-model maximum rather than a guessed runtime cost.

G5's A-byte index uses i<64. It tests255 before zero-extending to u64/usize.
The resident-byte read is the same field2 as C3. Checked subtraction, selected
mask, stop condition, first-empty initialization and replacement of destination
by every selected victim are preserved. Thus an existing empty slot does not
prevent the last selected victim from becoming the final destination. A255
tail stops selection exactly where an old ABSENT u64 tail did. No signed
comparison, sign extension, modulo conversion or synthetic timestamp occurs.

Every new view is scoped inside its probe, merge or prefix block. Shared arena
views end before later mutable arena code. Timestamp/index views end before
staging continuation or merge return. A normal refusal still returns to the
existing single caller cleanup. No new `?`, outer early return, allocation,
callback, native code, I/O or release-authority path is introduced. Exact C3
cleanup and the complete suffix are compared byte-for-byte by the source check.
