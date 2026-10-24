# Audit decoder key-work correction

Root accepts the independent codec review's processing-bound finding as requiring
correction. The old decoder sorts every supplied key before checking the closed
schema. A map with the right number of unknown, long binary keys therefore does
work proportional to their common-prefix length. The inputs are already allocated;
this finding concerns decoder work, not an input-allocation or total-memory bound.

Preserve the frozen candidate and review. In a separate correction candidate,
replace each key enumeration/sort with the exact map cardinality followed by
membership checks for the fixed allowed keys. Equal cardinality plus presence of
every distinct required key proves the closed shape. Iterate only the sixteen
display or ten row constants. Keep all field bounds, CBOR, retained bytes, hashes,
row/edge semantics and artifact encoder behavior unchanged.

Replay the original eleven focused tests, the independent 107 coherent cases and
eight edges, plus full hosted regression/release checks. Add rejection cases for
oversized unknown keys and mixed key types at the exact map cardinality. Repeat
the independent finite timing probe against the corrected source; report actual
measurements without introducing a flaky timing threshold or claiming a universal
latency or BEAM memory bound. Record commands, source/dependency hashes and cleanup.

Independent correction review and root acceptance precede live integration. No
SQL migration, writer, current-authority, provider, native or GA gate is accepted
by this isolated pure component.
