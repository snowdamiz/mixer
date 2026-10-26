# Proposed private contract amendment; not selected

Amend only the prerequisite paragraph requiring A64x8 and B64x8. Candidate is
still one retained `[u8;2048]`, borrowed sequentially by the existing leaves.

| Physical Candidate bytes | Proposed meaning |
| --- | --- |
| 0..512 | Unchanged64 little-endian u64 timestamps |
| 512..576 | A:64 unsigned byte indices |
| 576..1024 | Former A-word padding: no semantic reads/writes by this proposal |
| 1024..1088 | B:64 unsigned byte indices |
| 1088..1536 | Former B-word padding: no semantic reads/writes by this proposal |
| 1536..1600 | Unchanged Resident64 staging |
| 1600..1648 | Unchanged Pin48 staging |
| 1648..1688 | Unchanged Plan40 staging |
| 1688..1944 | Unchanged32 scalar words |
| 1944..2048 | Unchanged reserved/zero source region |

An index is either0..63 or unsigned255 (`u8::MAX`). All64 A and all64 B bytes
are initialized during G2, including slots outside the configured resident
limit. Ineligible/out-of-configuration A entries are255. B is initialized255,
then each pass overwrites every one of its current64 output locations. Six
passes leave the final result in A. No truncation of a u64 ABSENT creates a
public value: only proven slot0..63 is narrowed to u8. After a255 test, G5
zero-extends the byte to u64 for mask/destination logic. The public ABSENT
remains u64::MAX everywhere else. Timestamps are never sentinels.

Padding may still contain the envelope's live bytes888..983 before the
semantic call. The proposal neither reads that padding nor assumes it is zero.
After every semantic return, the existing cleanup clears all2048 bytes and
restores exactly those96 envelope bytes from the same twelve arena cells. The
next envelope input, fault behavior, post-loan cleanup convergence, pre-loan
untouched-scratch paths and suppression of both leaves on poison are unchanged.

The G2/G5 immutable `arena_words` views are temporary metadata over the existing
arena. They change no field offsets or ownership. RESIDENT.base and PIN.base
are divisible by8; native-endian reads are not introduced: each payload is still
converted with `u64::from_le_bytes`. The G3 view similarly converts timestamp
arrays from little endian, with no alignment requirement beyond `[u8;8]`.
G2's simultaneous mutable timestamp/index views are disjoint at byte512. The
timestamp array return and its destination assignment are separately charged;
no temporary64-element owning timestamp/index array is constructed.

No numerical budget or role reservation changes. No spare space in a padding
region, role, semantic workgroup or global allowance is borrowed. This amendment
requires independent source review and root selection before implementation.
