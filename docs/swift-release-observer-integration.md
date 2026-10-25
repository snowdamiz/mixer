# Swift test observer integration

The default test observer no longer records ordinary frame releases into its
64-entry fault-injection array. Its three-line zero-mask guard leaves enabled
fault injection and the original bound unchanged. Both the module and its call
sites remain under `cfg(test)`; production runtime bytes and budgets do not change.

Root checked the frozen repair's 366 members, the complete live 132-file baseline,
the exact single-file diff and the existing release-order assertions before
copying the reviewed test file. The integrated source closure is
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`.

The isolated repair passes 1,516 test executions across Swift-only/all-feature
Debug/Release, four ordinary production checks and four expected production
compile failures proving the test module is absent. Root additionally passes
three freshly compiled live tests using actual owners, frame entry/completion,
cache pins and retained cleanup: 130 ordinary releases, the enabled bit-63 fault,
and a reset followed by 130 ordinary releases. Owned process groups and scratch
are absent after the run. The earlier serial timeout and incomplete collector
receipt remain explicit in the original repair packet.

The [source review](../verification/swift-release-observer-root-review/source-review.json)
and [live receipt](../verification/swift-release-observer-root-review/receipt.json)
record this test-only acceptance. The separate [exact full FieldLog run](swift-exact-reactor-after-observer.md)
now initializes successfully, then stops at the unchanged cache-work limit in
the first corpus. The original failure remains immutable. Full corpus parity,
table mutation, the complete SL matrix,
public/signed/native execution, published FieldLog dogfood and GA remain pending.
