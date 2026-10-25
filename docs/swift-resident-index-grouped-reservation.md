# Grouped resident-index reservation candidate

The isolated candidate includes the existing 192-byte index vector in the cache
header reservation and removes its separate ticket. The header is admitted
before allocation and remains charged until after payload and caller storage
destruction. Lookup, initialization, limits and public interfaces are unchanged.
The [ownership contract](swift-resident-index-grouped-reservation-contract.md)
defines the required partial and consuming cleanup boundaries.

The selected 132-file source closure is
`3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f`.
It differs from the integrated baseline in two files: private cache ownership
and its accounting expectations. The clean diagnosis candidate receives only a
three-line formatting correction to its new `let-else`; the exact patch and
format check are retained. No live VM file has changed. Root verifies all 229
diagnosis members, 132 clean input files and 264 archived prototype files.

The diagnosis's actual finite runtime owner recovers one ticket: construction
uses 21 rather than 22, and 64 residents use 85 rather than 86. A real additional
reservation at 86 succeeds, and the next attempt at 87 still refuses. That probe
does not identify the owner from the previous failed full reactor run or predict
full-workload completion. The exact vector still requests 192 payload bytes and
charges all 192 initialization writes; the complete fixture uses four allocation
requests, 26,304 payload bytes and 832 construction work credits.

Fresh root regression testing passes; independent ownership review is sealing.
The selected all-feature Release library suite passes 404 tests with no ignored
tests. Debug cache, execution and lifecycle suites pass 29, 21 and 49 tests, and
the literal Frozen trace control passes. These are 504 test executions; scoped
formatting and private Swift Clippy also pass. The first root
driver incorrectly expected the earlier all-target count of 626 rather than the
selected library count and stopped after that successful command. Two later
lifecycle filters selected zero tests and were rejected by the driver; neither
qualifies lifecycle coverage. Their scripts, outputs, receipts and cleanup are
retained. The final successful filter is taken from the 49 actual lifecycle names
in the successful Release output and the sealed diagnosis command. No product bytes or
test assertions were changed to repair these invocation errors.

The [selection](../verification/swift-resident-index-grouped-reservation/selection.json)
binds source, baseline, contract, inputs and formatting. All recorded attempts
preserve command output and source/tool identities. Owned test targets are
removed after process-group and holder checks, including failed driver attempts.
Live integration requires independent acceptance. Full reactor execution, native
parity, signed/public use, published FieldLog, physical devices and GA remain
pending.
