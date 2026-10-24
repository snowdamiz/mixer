# Contextual cleanup diagnostic integration

The private Swift reactor now attributes active live-count underflow to the
current instruction, resource, requested removal and available count. Cleanup
without an active instruction retains its original cursorless diagnostic.
The first failure and its captured state remain immutable through later cleanup.

All twelve changed files match the independently reviewed candidate exactly.
The 128-file integrated source closure is
`1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c`.
Root verifies 2,010 upstream bindings, then passes fresh all-feature Release
library tests (282), Frozen Release integration tests (16), Swift-only production
Clippy with warnings denied, and changed-source whitespace checks. Executed
binaries, test lists, source archives, tool identities and all fourteen command
outputs are retained in the [root receipt](../verification/swift-cleanup-diagnostic-root-integration/acceptance.json).
All owned command groups and 166,955,154 bytes of scratch are cleaned.

Independent review separately passes 1,068 library, 68 selected diagnostic,
64 Frozen and six adversarial test executions. Its compiler evidence covers
5,516 positive positions, sixteen metadata contexts, eight layout pairs,
24 unchanged legacy MIR bodies and 39 unchanged Frozen methods. The producer
retains its separate tests and all rejected harness attempts. These counts
overlap intentionally and are not a unique-test total.

Five active removal sites use the contextual entry; nine legacy cleanup sites
retain the original entry. The repair adds no owner, field, ticket, work/fuel
debit, public route or debt mechanism. Host effects survive later failures and
the existing debt remains sticky. Added logical reservations are 11,168
permanent bytes and 493,272 production / 1,036,112 unit active bytes. They do
not establish physical stack, allocator overhead or RSS bounds.

This accepts a private macOS host development slice. A Wasm offset is not an
original Swift source location. Full calls and dispatch, initializer/Ready/public
invocation, source maps and readable Swift stacks, native joins, immutable
published FieldLog consumption, final physical-phone testing and G08/GA remain
pending. Simulator/emulator testing is authorized; none was needed for this
host-only change.

Replay the accepted source and evidence with:

```sh
python3 -B verification/swift-cleanup-diagnostic-root-integration/verify.py --live
```
