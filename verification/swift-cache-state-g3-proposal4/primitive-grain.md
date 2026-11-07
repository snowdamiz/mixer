# Disclosed primitive and value grain

The cost requirement is bound to
`docs/swift-semantic-adapter-prerequisite.md:244–286`: at most16 named scalar
operations/group, each distinct fixed copy at most128 bytes/group, complete
arguments/returns/caller moves counted exactly once, unchanged group ceilings,
and no optimizer elision. This packet supplies a component model and a qualified
obstacle rather than declaring that passage a complete machine instruction set.

One scalar entry is one pointer/length/integer component read or transfer, one
integer arithmetic operation, one predicate, one conditional decision, or one
scalar binding/store. Array payload movement is a distinct copy group. Constant
operands inside an operation do not invent a callee argument; actual literals
passed to a function would require that argument edge. Scalar initializer to
binding and arithmetic to updated cursor storage are named separately. All
values remain present in the place inventory even if their representation has
zero bytes or they have no destructor.

For built-in slice indexing this model names the data-pointer read, length
read, bounds predicate, normal branch, index scaling by element size and address
addition. Pointer and length remain distinct words. The favorable sensitivity
combines the last two into one indexed-address operation, giving five scalars.
This interpretation is disclosed rather than selected merely because a number
fits. More detailed checks/transfers can add work; they cannot close this map.

The [Rust indexing reference](https://doc.rust-lang.org/reference/expressions/array-expr.html#array-and-slice-indexing-expressions)
distinguishes built-in array/slice indexing from trait-based indexing for other
types. Here `words` dereferences to `[[u8;8]]`, indexed by `usize`. Therefore no
fictional Index/IndexMut trait wrapper, received slice argument, Option, returned
array reference or Range is charged. The built-in result is an element place.
Component metadata reads and checks are still counted. This distinction is
about the language operation, not an inference that inlining deletes a call.

The four explicit `from_le_bytes` arguments each receive one complete array8
copied from an element place. A fixed-width LE conversion is the required
conversion primitive. Its scalar output to caller and the actual A/B binding
edges are separate. The comparison map does not recursively reinterpret the
platform conversion's internal implementation as additional authored functions;
it labels that leaf assumption and does not claim a machine instruction bound.
The one-time `as_chunks_mut` helper has a more complex tuple/borrow boundary and
is not silently placed in that conversion primitive or declared free.

The [assignment reference](https://doc.rust-lang.org/reference/expressions/operator-expr.html#assignment-expressions)
specifies RHS-before-LHS evaluation and assignment to a place. Direct assignment
has no explicit array binding, helper array argument or array-return function.
It is thus a candidate for one source-element-to-destination copy, with an
abstract RHS value surviving LHS evaluation. This packet does not settle whether
the accounting must name a second independent RHS-value-to-destination movement.
It grants one copy for the lower bound; charging two only increases the failure.
No source/received RHS value is omitted from the lifetime inventory, and no
optimizer is invoked to claim its disappearance.

Assignment and compound-update results are unit0. Their places are recorded;
normal completion belongs to the named copy/store operation. They are not
extra standard-library control returns. The actual merge call's source/received
unit result and the chunk helper's complete source/received tuple are separate
unclosed outer edges, not hidden in a payload copy.
