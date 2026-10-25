# Private Swift resident index integration

Root accepts and integrates the independently reviewed six-file candidate as a
development slice. The live 132-file closure is
`02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d`.
All 570 producer and 79 independent-review members verify. The earlier baseline,
all producer failures and invalid stale-build evidence remain preserved.

The private Swift cache uses 128 bucket heads and 64 links in an exactly admitted
192-byte index. Full chain validation, charged atomic mutation, strict LRU,
pin/nonce rules and zero consuming cleanup remain enforced. Shared FrozenMode
retains its literal lookup trace. No production limit or dependency changes.

The producer passes 626 all-feature Release tests with nine inherited ignores.
Independent review passes cache 29, execution 21, lifecycle 49 and shared-cache
five tests, plus six new Debug/six Release/two baseline controls. Its separate
8,192-operation model matches the baseline, and constructor and multi-victim
failure boundaries preserve coherent state and consume cleanup to zero.

Fresh root compilation from the actual live files passes 32 tests: all 29 private
cache tests, two lifecycle budget tests and the literal FrozenMode trace test.
All four commands complete with both streams closed, no timeout or signal and no
surviving owned process group. Source hashes remain unchanged. The fresh target
directory is removed after a recursive holder check finds no open files.

The finite 256-hit fixture uses 2,048 versus 8,832 credits; this is not CPU timing
or a full-reactor pass. Fixed cache accounting increases from 88,536 to 89,376
bytes, and foundation accounting increases by 384 bytes within existing limits.
Unfavorable collision and single-resident cases remain explicitly measured in
the [independent review](swift-cache-resident-index-review.md).

The [selection](../verification/swift-cache-resident-index-root-integration/selection.json)
and [live receipt](../verification/swift-cache-resident-index-root-integration/receipt.json)
bind exact source, tools, executable hashes and output. A fresh unchanged full
reactor diagnostic is being prepared separately; execution has not been selected.
Native parity, physical phones, signed/public use, published FieldLog consumption,
performance qualification and all final acceptance gates remain pending.
