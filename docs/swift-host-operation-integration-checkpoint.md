# Private imported-host operation integration

The independently reviewed imported-host operation is integrated into the live
owned VM. Its 128-file closure is
`7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329`.
All ten changed files match the reviewed candidate exactly; no normalization or
additional production change was applied.

The operation uses the original phase, argument/memory arenas, sealed import
descriptor, AccountedWasi, resource control and single fixed outcome slot.
It checks argument types and the caller floor, performs one original host debit,
preserves adapter faults and unsigned GuestExit, and reconciles arguments before
pushing an unsigned errno. Host effects survive later failures; failed live-count
reconciliation keeps the existing debt. The pinned wrapper executes one imported
Call prefix. It adds no complete dispatcher or defined/indirect call path.

Root verifies 1,910 producer/reviewer bindings and the complete source closure.
Fresh integration builds with the reviewed Rust/Cargo identity pass all 265
all-feature Release library tests, sixteen Frozen Release integration tests,
Swift-only Clippy with warnings denied, and changed-source whitespace checks.
The exact executed binaries, test lists, source archive, commands and outputs
are retained in the [root receipt](../verification/swift-host-operation-root-integration/acceptance.json).
All owned command groups and scratch are cleaned.

The [independent review](swift-host-operation-review.md) separately passes 302
test executions with deliberate overlap, fresh production/unit MIR and Frozen
expansion, sixteen retained layout replays and all 4,876 accounting positions.
The producer's 1,014 library, 64 additional host-probe and 64 Frozen executions
remain separately attributed. Both packets retain their failed harness attempts.
These are macOS host receipts, not native mobile qualification.

The original containing owners, 39 Frozen methods and prior memory/bulk/growth
accounting remain unchanged. Added reservations are 113,760 permanent bytes and
515,320 production / 1,040,136 unit active bytes. Zero-sized fields retain empty
intervals and supply no byte credit. These are logical named-object bounds, not
physical stack, allocator-overhead or RSS guarantees. The warmed allocation
observation covers one ArgsSizesGet interval; OS deadline checks are cooperative.

Completion fixtures use plain `prepare_frames`. A future combined dispatcher
must retain `complete_growth` while growth context, replacement storage or debt
exists. G08's cursorless cleanup diagnostic remains pending under its separately
selected repair contract. Full calls/dispatch/Swift, Ready/public invocation,
native joins, immutable published FieldLog from a separate repository, physical
phones, signing, store/customer/operational evidence and GA remain open.

Replay the immutable acceptance with:

```sh
python3 -B verification/swift-host-operation-root-integration/verify.py --live
```
