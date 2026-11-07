# Independent G3 source and proposal review

Original four-ld source has a favorable70-scalar lower core plus four8-byte
payload copies. It cannot fit the selected64 scalar slots under that explicit
model. The binding contract does not formalize every primitive: this is a
conditional source-work finding, not a measured runtime overrun.

The admitted expression-macro proposal preserves single offset evaluation,
hygiene, short-circuit/read order and checked byte mapping. An ordinary block
adds no function return owner solely by having a tail expression. A/B outer
initializer temporaries and identifier bindings still need distinct edges.
Including those gives a conservative64-operation core with16/16/16/16 blocks.
Offsets are usize; the producer flow's u64 labels must be corrected. The captured
c shared indexing reborrow remains inside the named view primitive.

This is bounded design evidence, not a complete cost upper bound. In particular,
four expect message arguments still have no explicit owners. Charging one
scalar transfer each makes68 with this core. Range/view aggregation, every
other complete transfer and full lifetime assignment also need explicit closure.
A separately selected unwrap amendment could remove the message argument but
would still need exact source/proof review. No amendment is selected here.

`operation-table.json` and `path-and-boundary-table.json` bind the old comparison
and G3/G4 boundary. `proposal-disposition.json` freezes the exact conservative
partition, macro/block/temporary decisions, remaining edges and limitations.
`language-reference-basis.json` records official Rust specifications used for
semantic reasoning; they do not define debit atomization.

Reproduce static checks only:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/build_review.py
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/swift-cache-state-g3-independent-review/verify_review.py
```

Builder writes only this directory; rebuilding changes custody time/HEAD and
requires resealing. Verifier checks packet integrity and table arithmetic.
No active correction2 source, product/compiler/harness/model/native/device
execution or process inventory occurred. Old independent seal and all producer
bytes remain unchanged. Root owns repair selection and delivery. No complete
source-work, memory-role, implementation, release or GA acceptance is supplied.
