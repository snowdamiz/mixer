# Grouped resident-index reservation integration

The private Swift cache now reserves its existing 192-byte index payload through
the cache header. This removes one persistent ticket while retaining all four
buffer allocations, metered initialization, index behavior and the 86-ticket
limit. Partial and successful cleanup destroy the payload before releasing its
header reservation. Only the private cache and its accounting tests changed.

The integrated 132-file closure is
`3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f`.
Root verifies all 179 candidate and 99 independent-review files plus their three
document bindings, then copies exactly the two accepted files. All 32 fresh live
checks pass: 29 private cache tests, both cumulative lifecycle budget controls
and the literal shared Frozen trace. Commands exit successfully with complete
output and no remaining owned process group. The owned target is removed after
an empty holder check.

The isolated candidate passes 504 regression executions, scoped formatting and
Clippy. Independent review passes 21 focused tests, including every one of 832
shorter constructor work budgets, 851 cancellation checkpoints, four actual
allocation failures, header refusal and deallocation ordering. The finite
original runtime owner uses 21 construction tickets and 85 tickets with 64
residents; a real reservation at 86 succeeds and an attempted 87 still refuses.
All consuming ownership reaches zero. The initial diagnostic and review test
expectation failures and root invocation errors remain preserved, with zero-test
commands explicitly excluded from accepted coverage.

The previous full reactor's failure remains authoritative. These finite results
do not identify its 87th requesting owner or predict full-workload completion.
A fresh original-harness diagnostic is being prepared separately against these
exact live bytes and unchanged limits. Full reactor, native parity, published
FieldLog, signing, physical devices, operational and GA acceptance remain open.

[Selection](../verification/swift-resident-index-grouped-reservation-root-integration/selection.json),
[live receipt](../verification/swift-resident-index-grouped-reservation-root-integration/receipt.json)
and [independent review](swift-resident-index-grouped-reservation-review.md)
retain the source, tool, test, output and cleanup evidence.
