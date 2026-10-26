# Explicit primitive grammar for independent review

This is an authored-source grammar, not a compiler ABI or machine model. It
retains the preceding packet's required fixed-width LE conversion primitive.
Every intrinsic in the finite platform closure is disclosed below; none is an
arbitrary whole Range/view/call primitive.

One scalar event is one integer/pointer component transfer across an actual
argument, return, aggregate-field or binding edge; one integer arithmetic or
bitwise operation; one comparison; one conditional/short-circuit decision; one
scalar store; or one fixed-width scalar LE conversion. Reading an integer as an
operand of an operation is included in that operation. Distinct source/received
argument edges remain separate. Reading a pointer or length from metadata is
explicit. Normal unit return/caller control edges are charged, even though their
value has zero bytes. Literal operands inside arithmetic are included there;
an actual literal parameter/field initializer has its own transfer event.

Built-in usize indexing has six component events: pointer read, length read,
bounds comparison, normal branch, element-size scaling and address addition.
This keeps scaling even for size1. Byte reading to an abstract RHS value and
writing that value to the destination are separate scalars; a named byte local
adds its binding edge. A `[u8;8]` argument passed to `from_le_bytes` instead has
one separate8-byte copy group, then conversion and scalar return/binding edges.
No Index trait or returned-reference call is invented for built-in indexing.

Metadata aggregate movement is expanded field-by-field. Safe slice split/chunk
construction is expanded into its platform source's finite call graph: checked
and unchecked split, Option pair, as_chunks_unchecked, raw-parts constructors,
pointer addition, metadata extraction and UB precondition decisions. Each tuple
has four pointer/length fields, and each Option has explicit discriminator and
payload fields at every real movement. The only intrinsic leaves are metadata
extraction, raw pointer arithmetic/cast/metadata construction, exact integer
division, unchecked subtraction, fixed-width LE conversion, and one bounded
payload copy. Pointer alignment/non-null and allocation-size conditions are
expanded into casts, masks, arithmetic, comparisons and branches. There is no
fictional recursion into the compiler's implementation of an intrinsic.
Mutable and immutable split/chunk/raw-parts methods have the same pointer/length
field counts; G2 uses the mutable variant for Candidate and the immutable
variant for arena, G3 uses mutable split then immutable timestamp chunks, and
G5 uses immutable arena chunks. Their authority and aliasing are distinct even
where the numerical component trace is structurally identical. Checked_add's
overflow intrinsic, hint, unchecked arithmetic and Option edges, and checked_sub's
comparison, unchecked arithmetic and Option edges are expanded separately from
the surrounding loop arithmetic.

The finite one-time view trace charges both enabled successful UB-precondition
checks and the control deciding whether they are enabled. A disabled check can
only shorten it. Proven bounds exclude panic/UB failure bodies. Impossible
panic bodies are not part of the successful source path; no runtime assertion is
assumed optimized away. Safe built-in indexing still pays its check and branch.

G2 does not call `st`, a Range index, or `copy_from_slice`. It borrows mutable
timestamp chunks once. Each direct timestamp assignment charges the scalar
to_le_bytes receiver/received edges, conversion, normal return/caller control,
checked destination index components, array-return8 copy and destination8 copy.
The fixed copy primitive does not conceal its byte count. No return-value or
assignment movement is removed using an optimizer assumption.

Actual executed events are tagged by owned source site and occurrence. G2 owns
its probe/view/initialization/control stream. G3 owns merge caller/received
borrow, one-time timestamp/index views, pair comparison operations, and complete
merge return/receive. G4 owns all other merge control, exhaustion choice,
take_left binding and byte-output operations. G5 owns its prefix caller-local
initialization, arena view, reads, arithmetic, loop and feasibility expression.
G6 retains all unchanged delta staging/commit and cleanup work. Paid rejection
construction and complete semantic replies remain G7; zero-debit absorbing
guards remain G128. Neither is funded by the new stream.

Within each owner, scalar events are kept in execution order and partitioned
into numbered blocks of at most16. A block may straddle successive loop
iterations; it never straddles owners. Distinct payload movements each have a
separate copy group of8<=128 bytes. Group IDs include the owner and kind, so no
event or group can be assigned twice. Conservative component upper traces can
include mutually exclusive source arms, but actual trace IDs represent only
the executed arm. The packet checks both its static upper and dynamically
packed finite model traces. All accepted-qualification flags remain false.
