# Private Swift cache reset elimination checkpoint

The private Swift cache no longer clears its entire 512-slot control arena before
each decoder pass. Both passes already initialize every active record before
reading it. The initialized allocation, capacity check, explicit cancellation and
deadline checks, and charges for actual decoder work remain unchanged. This removes
1,024 real work credits per cold decode without changing runtime limits or the
legacy cache implementation.

Root accepted the producer's sealed candidate and integrated exactly three files:
the private cache, its tests, and two lifecycle tests' exact work expectations.
The resulting 132-file VM closure is
`b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11`.
The [root receipt](../verification/swift-cache-reset-elision-root-review/receipt.json)
records six fresh passing live tests, unchanged source during those tests, empty
owned process groups and removal of the disposable build target.

The producer's broader matrix passes default, compatibility and all-feature
Debug/Release tests, dirty-scratch decoding, finite exhaustion/cancellation,
failure precedence, allocation/cleanup, downstream compilation and frozen legacy
trace comparisons. Initial fixture/environment failures and bounded test
continuations remain recorded. Eight default and nine compatibility/all-feature
pre-existing ignored tests remain ignored. Global formatting still reports the
same 16 inherited files; the three changed files are formatted.

The earlier full reactor's cache-work exhaustion remains valid historical
evidence. A separate fresh diagnostic is being prepared with the unchanged full
Wasm target, harness, corpus and limits. No target completion, stdout parity,
native/signed package, published FieldLog consumption or GA pass follows from
this optimization alone. See the [candidate report](swift-cache-reset-elision.md)
and [selected contract](swift-cache-reset-elision-contract.md) for exact scope.
