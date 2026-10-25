# Swift decode-plan reuse integration

The reviewed private cache optimization is integrated. The four complete isolated
host contexts pass 2,314 named executions: Swift-only Debug/Release pass 519 each
and full-feature Debug/Release pass 638 each, with nine inherited ignores per
context. A fresh focused live Swift library run passes **340 tests, zero failures
and zero ignores**. This does not establish completion of the full Swift reactor.

The live 132-file source closure is
`16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd`.
Four files change from the previous live source: production `cache.rs` and three
test files. Production bytes exactly match the independently reviewed finite
candidate. The tests reflect measured allocation/work costs, enumerate all fifteen
integrated allocation failures, and preserve failure precedence, capacity and
consuming cleanup assertions. See the [full regression](swift-decode-plan-full-regression.md)
and [independent accounting review](swift-decode-plan-reuse-accounting-review.md).

The cache retains 512 bounded count-scan plans under its existing header
reservation. Identity must match the owned immutable body before counts can be
reused. Every decoded rebuild still parses and validates the complete body and
checks the resulting counts. Successful complete scans are the only publication
source; collisions replace entries without authorizing an identity mismatch.
The 16-MiB cache, 8-MiB entry, 64 residents/pins, 86 tickets, 64-million work credits,
256-MiB combined limit and existing deadlines remain unchanged.

The fixed cache reservation grows by 29,008 bytes, reducing resident payload
capacity. Constructor work rises from 832 to 4,928 credits. The reviewed synthetic
large-body repeated sweep uses 36.53% fewer credits; the tiny-body sweep uses
2.14% more. These are bounded synthetic work counts, not CPU measurements or a
prediction that the real workload will finish.

Root accepted all 560 regression files and five external bindings before live
mutation. The exact four-context source is retained. The integration derivative
only formats one new test, three blank-line boundaries and one diagnostic print.
Its complete patch is retained and the subsequent 340-test run uses the final
live bytes. Whole-project formatting still fails: all 156 remaining hunks in
17 files are byte-identical to the pre-candidate baseline after excluding path
and line shifts. No new formatting failure is hidden. The isolated Swift-only
Clippy check passes; two inherited test warnings remain recorded.

The fresh live test executable, commands, tools, source manifest, output and
cleanup are retained in [the integration receipt](../verification/swift-decode-plan-root-integration/receipt.json).
Owned process groups are absent, holders are empty, the scratch identity was
checked and the build target was removed. The isolated regression verifier
intentionally binds the former live tree; its recorded pre-integration pass is
historical evidence, not a claim that it can revalidate the changed checkout.

The previous full reactor still records a Corpus 1 CacheWork failure after a
successful Initialize; Corpus 2 was unrun. A new source-bound full-reactor packet
must be prepared and selected separately. Native/public/signed execution,
immutable published-package FieldLog consumption, final phones and GA remain
pending. No hosted provider, store or release authority follows from this slice.
