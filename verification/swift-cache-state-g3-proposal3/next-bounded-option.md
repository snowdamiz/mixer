# Next source-only option: one mutable word view for the whole sort

Assess this option before changing the primary Candidate representation. Enter
`merge` with the existing `&mut [u8;2048]`, form exactly one safe
`as_chunks_mut::<8>()` view, retain its word slice through all six merge passes,
and end that borrow when `merge` returns. No second2,048-byte owner, allocation,
native-u64 alias, unsafe application code, dependency or public API is proposed.

The official [slice API](https://doc.rust-lang.org/std/primitive.slice.html#method.as_chunks_mut)
supports mutable array chunks plus a disjoint remainder. At length2,048 and N8,
the intended word view has256 elements and an empty remainder. A word-slice
[copy_within](https://doc.rust-lang.org/std/primitive.slice.html#method.copy_within)
can transfer one `[u8;8]` element. `official-api-assumptions.json` binds the exact
recorded compiler's platform source for the chunk methods; these API facts are
not compilation, borrow-checking or full callee-work qualification.

`whole-sort-next-option-sketch.txt` is an uncompiled source-only sketch. It changes
sort offsets from bytes512/1024 to words64/128 and changes G4 copy ranges from
eight bytes to one word. Every comparison still reads A then B; both ABSENT
guards precede timestamp A then B; `<=` preserves the stable left tie. Widths,
passes, output order and the existing test counter placements are retained.
The semantic intent is byte-for-byte identical movement and timestamp decoding.

The prospective bounds are concrete but still require proof. On each admitted
pass `src,dst` are64/128 in opposite order; `base` is a multiple of2*width;
`end<=64`; `left` and `right` advance only after taking an entry from their own
half. Selected index-word loads therefore lie within64..191, destinations within
64..191, and timestamp loads use eligible slot indices0..63 after MAX guards.
The source range length is one word and the destination length is one word.
These statements need an exact source/branch proof before implementation,
including range construction, all bounds checks and panic exclusion.

This structure removes repeated chunk tuple formation from G3 comparisons.
It does not remove the thin original receiver, mutable slice coercion, returned
two-slice tuple, pattern bindings, discard/reborrow places or the one-time chunk
callee work. Those complete source/received places and all field movements must
be assigned exactly once within the selected semantic caps. Replacing the
explored fragment's two `src/8 + side` calculations by `src + side` reduces only
two explicitly named arithmetic entries: its comparison-body lower core becomes
44 scalars plus four separate payload copies before omitted Index/reborrow and
other callee work. That partial number is not an eight-group upper bound.

G4 changes too: all mutable word receiver fields, Range endpoints and source/
received fields, destination argument, checked bounds, one eight-byte copy,
returned/received unit and loop/control transfers need a new disjoint map within
two groups per transfer. One-time view setup is not free, and credits cannot be
borrowed from G4 to cover G3 or from another semantic group. No particular budget
partition is selected by this note.

The exclusive word view prevents direct Candidate byte-helper use until it ends.
Within the sort, temporary shared Index borrows must end before each mutable
word-copy receiver. After the sort, the exclusive view and unused remainder
must end before prefix, staging, cleanup or envelope helpers borrow Candidate
bytes. The new fat references, tuple source/received places, scalar operands,
copy ranges and immediate caller must enter the complete place-lifetime/peak
ledger; the primary payload remains the single existing2,048-byte owner.

Root must select bounded source-only design/proof work before any product edit or
compiler/runtime execution. Required deliverable: exact whole-function source,
complete G3/G4/setup cost partition, every source/received/binding/drop place,
no-panic ranges, unchanged321-comparison/384-transfer bounds, and full affected
role-union proof under unchanged caps. If that cannot fit, report the precise
obstacle. A broader fallback is one word-typed primary Candidate with sequential
safe byte views; it would affect more helper/loan boundaries and is not selected.
