# Proposed layout and complete affected-place inventory

Candidate remains one retained2048-byte owner. The proposed u8 layout has64
LE-u64 timestamps at0..512, A64 byte indices at512..576 and B64 byte indices at
1024..1088. Former A/B word padding is not used as new storage. Staging stays
Resident1536..1600, Pin1600..1648, Plan1648..1688, scalar words1688..1944,
reserved1944..2048. Envelope bytes888..983 may remain live in old padding before
the semantic call; this proposal neither reads them nor assumes they are zero.
The selected16 anonymous128-byte cleanup copies clear all2048 bytes and restore
the same12 scalar words unchanged after every admitted semantic return.

Each input/output is0..63 or255. u16 cached index256 denotes an exhausted run;
the chosen head is proved different from256 before narrowing to an output byte.
When the right head is255/tail or256/exhausted, a nonexhausted left head wins;
when the right head is eligible, only an eligible left head with timestamp<=
right can win. Stable left preference preserves original ascending slot ties.
Timestamps are read only for eligible head indices. u64::MAX remains a valid
timestamp. No invented timestamp establishes eligibility or exhaustion.

The following sizes are logical64-bit component inventories. No compiler was
run, and the88-byte cursor layout remains a proposed repr(C) layout requiring
fresh measurement. All actual source and received places are retained here;
NLL ending a borrow does not erase source/received work.

| Place | Bytes and phase |
| --- | --- |
| Existing Candidate owner |2048 throughout original walker; never copied/passed by value |
| Existing arena Vec/data |24 owner plus8,388,608 payload; same original caller lifetime |
| Original wire record |128 remains caller-owned through semantic call; word array is borrowed |
| Existing Progress/Paid/Loan |144/24/16; remain live through merge, output and original cleanup |
| Existing semantic/walker/caller borrows |record/config/arena/candidate/budget, caller arena pointer8 and original leaf parameters remain named; not erased by helper entry |
| Existing semantic locals/prior staging |original delta flags, total/count/found/first-empty/first-pin/pin counts plus staging/scalars retain their original scopes |
| merge received c and caller c place |8 each; four caller-only source/received/call/continuation edges stay selected G6 |
| Candidate split receiver |exclusive array reborrow8, unsized slice source16 and received16 during view setup |
| split returned/received tuple |32 each, then time_bytes16 and indices16 bindings; disjoint regions |
| timestamp chunk returned/received tuple |32 each; timestamps16 and discarded remainder16; exact outer closure remains pending |
| Pass source range |Range source16 and received16, Index receiver/source/received fat slices16 each, returned/received source slice16 each; source binding16 lasts through last emit |
| CachedMergeCursor constructor source |88 proposed: indices16,timestamps16, four usize32, two u16 values4, alignment4, two u64 values16 |
| CachedMergeCursor received local s |88 distinct from constructor source during complete move; retains its referenced source/timestamps through array construction |
| Initial fields |explicit receiver/source component or literal for every cursor field; no hidden Pair/Head owner |
| load_heads source/received cursor refs |8 each during each of63 calls; reborrow ends before the following emit |
| emit source/received cursor refs |8 each during each of384 calls; entry/return paid once per call |
| Head source Index places |field-address pointer8, Index receiver data8/len8/index8, predicate1, scaled8,address8, returned reference8, caller received reference8, byte source1 and index local1 |
| Eligible timestamp Index/LE places |same metadata/reference places with actual array8 source and received argument8, scalar result8 and destination cached u64 field8 |
| take_left |condition operands/source bool1, received/binding bool1; explicit G3 decision path |
| saved out |field value u16 source2, cast source/received u8 result1, local out1, designated return1 and caller array-element received1 |
| Cursor arithmetic/bounds |each usize operand/source8, result8, field address8, bool1; active helper scope, not a new retained array |
| Output constructor source |64, built by64 explicit scalar helper results; no destination IndexMut |
| Received output binding |64 distinct actual place during complete array64 move; source+received payload128 |
| Output copy source metadata |array address8/reborrow8, source slice source16 and copy received16 |
| Output destination |Range source/received16 each, view returned/received16 each, copy receiver16; actual payload destination is existing Candidate64 |
| Cleanup anonymous source |128 only after merge/output blocks end; selected literal anonymous source, never a new2048 owner |
| G2/G5 changed view/loop/Option places |disclosed in the source and inherited unselected idea inventory; full fresh component/role reconciliation pending after this failing initial gate |
| Reply/received/outer Result and caller places |remain in original G7/control/report scopes; not omitted because merge returned unit |

The new array64 source+received128 may be proposed inside the existing added
wire256 role through phase separation from cleanup's anonymous128 source; these
two phases do not overlap. This does not grant the complete wire role fit:
original record/Paid/caller owners and every metadata place must still join the
whole inventory. Cursor source88+received88 are proposed control places, not
bytes silently taken from wire or unused global margin. The complete role union
29344, control addition1280, wire256, setup256, report2896, reserved41984 and
global65536 are unchanged and remain unproved for this failed source. The
independent C3 lifetime lane is separate and is not used as a future premise.
