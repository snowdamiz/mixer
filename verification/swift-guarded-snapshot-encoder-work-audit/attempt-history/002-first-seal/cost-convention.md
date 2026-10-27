# Primitive logical action convention

This is a documented source-level upper-bound convention for the proposed
ExecutionWork use, as required by the original design section 5. The existing
ExecutionWork counter does not prescribe a hardware instruction unit. No claim
is made that earlier unrelated execution charges use this decomposition.

An action is one of:

1. Fetch one scalar/enum/reference from a named source place (a constant-depth
   field path is one place), bind/store one scalar/reference, evaluate one scalar
   arithmetic/checked-arithmetic/comparison/conversion/endian operation, or make
   one branch/match decision. Literal values and already-bound local operands are
   free inputs. Boolean AND/OR are scalar operations. Dereferencing a loop's
   borrowed scalar is a fetch. Range containment is its two comparisons plus
   creation of the fixed range value.
   A checked-arithmetic primitive includes producing its overflow result;
   subsequent `is_some_and`, `ok_or`, `?` or explicitly written Some/Result
   operations are charged separately. A built-in Vec length/capacity query is
   one scalar fetch at its named place; it does not copy the Vec payload.
2. Inspect or construct one Option/Result carrier. `?` costs two (inspect plus
   extract/propagate). `map_err` costs three (inspect, possible alternate error,
   output carrier); `ok_or_else` costs two plus the error helper if selected.
   We add worst success and failure subpaths when convenient. Doing so is an
   upper bound even though those paths cannot both execute.
3. Enter and return from one repository function: two. Argument expressions are
   charged at the caller; local parameter names are free operands. Each aggregate
   construction writes its scalar/reference slots separately. Explicit by-value
   Copy of a multi-field source struct is a fetch and store per field; an Option
   scalar has at most tag and payload. Ownership moves do not imply byte copying;
   an explicit ownership field move is one slot store. Carrier propagation covers
   its error payload ownership move, not a newly allocated/error-string copy.
4. Initialize/transfer one explicit output byte: one. A bulk copy also has one
   length equality check, one slice construction per slice, and the scalar
   endpoint arithmetic written at the source. Fill/repeat-array zeroing charges
   every byte. A fixed u64 pack/unpack is one scalar endian operation. A validated
   fixed eight-byte load is one word read. This is a logical word operation,
   not eight loads or a claim about compiler lowering. Slice-to-array try_into
   additionally charges its length test and Result carrier; expect charges its
   carrier test. No unbounded library work is hidden in these fixed operations.
5. Each loop has two setup/termination actions. Each range iteration costs two
   (advance, bind item); an enumerate iteration costs three (advance, bind index,
   bind value). While-condition expressions are charged on each body entry, with
   final termination in setup/termination. The next_block while condition costs
   up to five actions on termination, so its fixed ledger explicitly uses five
   in place of the generic two. Iterator creation has no hidden scan.

All direct source helpers and transitive production getters/bridges appear in
the ledger. Standard-library primitives used here are scalar conversions,
Option/Result control, fixed-array/slice operations and iterator progression;
none invokes user code except named closures whose bodies are expanded. No
allocator, hashing, Wasm revalidation, I/O, native syscall, clock, cancellation,
stop callback or work mutation occurs in the encoder. A failed indexing panic
is outside the safe opaque-cursor invariant; legal fallible errors are included.

## Helper expansions

Locations below use immutable `host/encoder.rs` lines; that file is an exact byte
substring of `source/vm/src/experimental/swift.rs` beginning at line 732. The
packet verifies this. Bridge references name their actual source members.

| Helper | Credits | Expansion |
| --- | ---: | --- |
| field (46-52) | 8 | enter/return 2 + two casts + three fields + enum constructor |
| require (53-59) | 12 | enter/return 2 + decision + Err carrier + field 8; success smaller |
| word (60-62) | 7 | enter/return 2 + conversion + Result + map_err 3 |
| put (63-65) | 14 | enter/return 2 + endpoint add + slice + endian + copy test + 8 bytes |
| get (66-68) | 9 | enter/return 2 + endpoint add + slice + length test + Result + word read + expect test + endian |
| words(n) (69-73) | 4+20n | enter/return 2 + loop setup/termination 2; per item enumerate 3 + multiply/add 2 + dereference + put 14 |
| optional (74-79) | 6 | enter/return 2 + match + Some conversion + two array slots |
| type_id / wasi_id | 3 | enter/return 2 + exhaustive enum match |
| result_id (88-93) | 6 | enter/return 2 + match + type_id 3 |
| SpanCheck.check (100-109) | 24 | enter/return 2 + five source-place fetches + two casts + checked add + Option inspect + end comparison + require 12 |
| Buffer.len | 3 | enter/return 2 + Vec length scalar |
| Buffer.get | 6 | enter/return 2 + values place fetch + bounds compare + reference + Option |
| entry! plus binding (436-440) | 20 | metadata field fetch + Buffer.get 6 + ok_or_else 2 + field 8 + ? 2 + binding |
| Buffer inventory | 12 | enter/return 2 + length/capacity/size/category/charge 5 + tuple slots 5 |
| opaque scalar/slice getter | 3 | enter/return 2 + named-place fetch |

The 139-word ceiling uses the import arm, **not** a 139-action unexplained
margin: record common body 29 + import lookup 20 + two (argument field fetch +
SpanCheck 24 + ? 2)=54 + type-index check 21 + five field/conversion/slot triples
15 = 139. The 29 common actions are entry/return 2; metadata binding 2; source
length binding 3; SpanCheck three slots/binding 4; section match 1; output binding
1; final array get/copied/ok_or_else including field error 16. The type-index
check 21 is field/cast 2, signatures field/len 4, compare 1, require 12, ? 2.
Other complete record bounds are signature 90, parameter 58, function 108,
global 91, export 105, data/element 91. Unknown-section and bad-within errors are
smaller; the final bad-within error is already in the common 29.

All required expression branches and helper bodies are summed conservatively,
including late field errors, absent WASI, optional Some values and error
propagation, even when a single legal input cannot realize every term. No large
rounded multiplier or allocator/runtime speed assumption is used.
