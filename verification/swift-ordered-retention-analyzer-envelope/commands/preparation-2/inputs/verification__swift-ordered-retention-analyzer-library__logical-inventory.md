# Fixture framing library logical inventory

This inventory applies only to `src/analyzer.rs`, on the recorded 64-bit Unix
Rust toolchain, through the safe existing-File fixture entry. It is an authored
conservative named-role bound requiring independent source review. It is not
physical stack, TLS, allocator, kernel, stdlib-internal, optimizer-copy or RSS
qualification. Test encoders, scripted transports, runner paths and test vectors
are outside the library and do not inherit its bound.

The backing store is exactly one `Vec<u8>` allocation of 8,388,608 bytes.
`try_reserve_exact` runs once; failure or nonexact capacity refuses. Initialization
pushes exactly 1,048,576 eight-byte zeros within that capacity. No huge array,
unsafe access, secondary allocation, growing event collection, `String`, format,
serde, raw FD, CLI, source tree preparer or host acceptance object exists here.
The Vec header and every Result/owner move remain named transient roles.

The arena keeps all twelve reviewed regions and the 515,488-byte zero spare.
Only immutable FunctionRows receive profile identities. Resident/pin/plan/
recency/window/top sentinels are initialized; no semantic replay uses them.
Report bytes live in the existing arena report workspace, not a second 49-KiB
transient object. The candidate2048 reservation is unused and unavailable for
other storage. The fixed region borrows and input buffering retain no
per-record owner.

`inventory.py` names complete per-helper arguments, scalar/borrow/checked-Option
temporaries, complete return Result and caller receiving/move places. Its explicit
call-chain phases account for actual nesting rather than multiplying a largest
type size by an assumed helper count. `logical-inventory.json` is the executed
arithmetic result. Bounds deliberately count some mutually exclusive owner
moves together; the named-role union is an upper bound, not a claimed measured
simultaneous peak. All seven original reservations stay unchanged:

| Group | Reserved bytes | Complete roles |
| --- | ---: | --- |
| wire/decode | 3,072 | Stream header512 + footer512 + record128; profile header512 + row32; context header128 + single8; decoder raw512 + value8 + iterator24 + words slice16. The full conservative distinct-role union is2,392. |
| candidate | 2,048 | No candidate owner in this foundation; reserved for a later reviewed semantic implementation. |
| I/O | 4,096 | All `bounded_read`, EOF, `Reader::take/words/new`, three caller Readers and output-write transport argument/borrow/iterator/error/Result slots. No pipe, stdout or owned string. |
| Metadata/Results | 4,096 | Four caller-owned Files16; complete Metadata144 and `io::Result<Metadata>`152; Stamp72, `io::Result<Stamp>`80 and all produced/returned/wrapper/caller copies; initial and final stamps, output safety's a/b/c/d and full288-byte array; all position Results16. |
| paths/setup | 12,288 | No path owner. Three Vec/Arena header move slots, complete Arena Results, reserve function pointer and complete reserve Results/error; complete304-byte region iterator reserved336 plus region literal; all source numeric literal arrays/tuple iterators and initialization ranges. |
| control/helpers | 8,192 | Complete helper leases and every phase's live chain, including error construction, checked arena wrappers and Budget helpers. Stamp by-value length72+return is charged even in phases that do not call it. |
| report/error | 8,192 | Fixed header256, complete Outcome104 and public/core/caller/matched move slots, error32, complete `Result<bool,Error>`40 and unit Results40, loop/borrow/value/position slots. Full report body remains in arena. |

Reserved transient total is41,984 of65,536. The23,552-byte unassigned margin is
unused. No type, phase or role consumes that margin. The executed JSON records
the smaller conservative named-role upper and its maximum control phase; these
are scoped source inventory results, not substitute memory measurements.

Measured layouts include Error32, Outcome104, `Result<Outcome,Error>`104,
File4, `io::Result<File>`16, Metadata144, `io::Result<Metadata>`152, Stamp72,
`io::Result<Stamp>`80, `io::Result<usize>`16, `io::Error`8, Reader48, Budget56,
Fixture72, Framing80, `Result<(),Error>`40, reserve Result16, Region24,
region iterator304, `Result<Arena,Error>`40, `Result<Budget,Error>`64 and
`Result<Fixture,Error>`80. The executable layout method asserts the bound for
every layout used by the arithmetic. Generic wire decodes now write into
caller-owned fixed arrays and return a complete40-byte unit/error Result;
there is no512-byte decoded-return/caller copy chain.

The lifetime phases are explicit:

1. Public File borrows and the four complete caller File owners persist through
   core return. The library creates/adopts/duplicates/opens no File. `output_safety`
   obtains four local stamps, then a complete four-stamp array; local/array/return
   copies are all charged. Unknown identity, pairwise inode alias, nonregular,
   nonempty or nonzero-position output refuses before any write or allocation.
2. Allocation has one Vec header, reserve Result/error, produced Arena and
   returned/wrapper/caller Result slots. Initialization iterations and checked
   sentinel calls fit the setup/core leases; no row-sized all-functions array.
3. `observe_inputs` retains three initial Stamps plus its Fixture while context,
   profile and stream phases execute serially. Each phase has one Reader and the
   shared arena block. Context words leave their loop scope before its decoded
   header exists. Profile header and one row coexist; they leave scope before
   stream header/record/footer. Every decoder holds its own raw512, a word8 and
   iterator; all fixed arrays and argument borrows are charged.
4. Reader I/O Results are matched immediately. Their complete `io::Error` owner
   and fixed error return/receiving places are charged; no error text is retained.
   File metadata's complete Result and extracted Metadata are charged until the
   Stamp is formed and returned. Every stamp-wrapper return move is charged.
5. Stream framing holds header512 and either record128 or footer512. Record
   body/profile joins may nest arena wrappers; helper leases include all checked
   Option/Range/slice/LE copies and complete Results. No candidate/delta is
   published. Framing counters are separate from semantic accepted records.
6. A budget-limited walk drains bounded bytes with the same block and Reader;
   omitted records are never decoded. Footer checking does not supply missing
   semantic transitions. Initial stamps remain until final comparisons; they
   leave scope with `observe_inputs` before report serialization.
7. Report serialization retains Outcome104 plus its complete Result/return/move
   slots, fixed header256 and fixed error/enum/loop owners. The initial output
   Stamp, fresh prewrite Stamp and final Stamp are all counted. Output writes
   borrow arena bytes. All partial bytes remain caller-owned failed output on
   error; no new file name, retry, truncate or allocation is performed.
8. Returned Result and caller receiving places remain charged after inner
   decoder/metadata/input scopes close. Normal/error unwinding drops the one
   Arena allocation and returns the fixed outcome/error. Caller File ownership
   survives both paths. File/std/allocator internals remain explicitly excluded.

The complete inventory is a requirement of this finite path, not an available
real replay adapter or a memory claim for any future FSM, CLI, custody wrapper,
source preparer, target driver or full workload. Those additions require new
inventories and independent reviews under the unchanged ceilings.
