# Unselected G3 expression-inlining proposal

The current four-`ld` comparator has a producer-derived favorable core of
16 named scalar operations per load, four distinct8-byte array copies, and
six shared comparison/result scalar operations. That is70 scalars plus four
copies. It does not establish the selected eight-group bound. This is conditional
on the explicitly stated source-value-flow atomization; it is not a runtime
measurement or an unconditional numeric overrun under the binding contract.

The proposed change replaces only merge265–267 with a local expression macro.
Its body is the current ld149–155 expression plus a block-local `at`, so each
offset is evaluated exactly once. `ld` itself and every other caller remain
unchanged. No new runtime function, API, parameter, callback or dependency is
introduced. The macro expansion retains all range checks, first_chunk/expect,
from_le_bytes and the one dereferenced-array movement per load.

Inlining replaces the `at` parameter transfer with the local `at` transfer,
removes the complete `b` call-argument boundary, and removes the ld function
return→caller boundary. The conversion's returned scalar goes to the enclosing
caller expression instead. The favorable named map therefore becomes14 scalars
per expanded load,62 including the six shared predicates. Four explicit scalar
blocks contain14/16/16/16 operations, alongside the four separate array copies.
No optimizer elision is credited: the runtime call/return layer is absent in the
proposed source expression, just as a macro body creates no forwarding Result.

`operation-partition.json` lists every old/new operation and block assignment;
`value-and-lifetime-flow.json` names the complete returned/received values,
read order and borrow ends. Range/view/Option/reference flows use a favorable
primitive grammar which the binding passage does not itself formalize. That
choice requires independent review/root admission and is not silently accepted
here. Complete caller/memory-role accounting, all other G1–G7 work, ADMIN and
st/sq remain separate obligations. This proposal does not close them or select a
new product edit.

Both source fragments are text evidence only. The exact current24-copy candidate
SHA remains6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00.
No proposed fragment was copied into product source, compiled or tested. No
active independent G3 review or independent fixtures/oracles/glue were read.
Root must select the bounded change before implementation and fresh host/API/
layout qualification. Native, capture and process inventory remain paused.
