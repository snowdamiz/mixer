# Private Swift memory prerequisite acceptance

Root accepts the isolated Load/Store type, borrow and logical-accounting
prerequisite. The [producer contract](swift-memory-helper-contract.md) and
[independent review](swift-memory-helper-contract-review.md) bind this decision.
The live VM remains the accepted control implementation. Memory behavior and
integration are pending.

The exact candidate closure is
`b0922009f9fbb9b2b1091ec4b62607cff456288e8d044217481c31bfe826596c`.
Root verified all 319 producer and 129 review bindings, inspected the shared
range/load/store bodies, Swift floor/type and slot guards, actual pinned caller,
post-pop debt and original completion boundaries, and confirmed the live 121-file
baseline still matches the accepted control closure. The independent reviewer
freshly compiled eight library combinations and sixteen paired metadata layouts,
reproduced all 39 Frozen methods and all 4,688 positive accounting fields. Its
compiler/source evidence is independent of the producer's inventory parser.

The original owners, 128MiB State and 256MiB Combined limits, 86-ticket authority
and 2,912-byte Frozen reservation remain unchanged. Proposed production memory
active/permanent additions are 618,896/121,856 bytes; unit active addition is
1,153,832 bytes. These are conservative named-object bounds, not measured RSS or
compiler-stack bounds. No opcode was executed for this prerequisite.

The next isolated implementation must execute every MM01–MM16 group in Swift-only
and all-feature Debug/Release under the frozen finite fixture limits. Complete
the actual one-step pinned caller's failure handling: early active, cache-view,
missing instruction, charging and checked-PC errors must stop execution through
the existing terminal/drain and fixed-result-slot rules. An outer successful
publication must never be mistaken for an inner successful operation. Preserve
occupied results and first failure, inspect the actual stored outcome before
another fetch, and exercise original drain/completion with retained pins and debt.
No replacement owner, mock cache authority or duplicated load/store algorithm is
permitted. Any correction or test hook that changes concrete source/types must
regenerate affected positive accounting, actual layouts and Frozen expansion.

The new lane may add bounded test-only hooks and original fixtures in its own
packet. It must preserve every frozen input and current live source, retain all
failed attempts, exercise previous frame/control/value regressions, and obtain
fresh independent behavior review and root acceptance before integration.
Copy/fill/size/growth, full dispatch, Ready/public invocation, native joins,
published FieldLog, physical phones and GA gates remain pending. Existing Cleanup
diagnostics with absent source location are preserved truthfully; G08 stays open.

The decision and commands are in
`verification/swift-memory-helper-root-review/acceptance.json`. Run the companion
`verify.py` to check the frozen evidence; `--live-baseline` additionally requires
that the current live VM still matches this prerequisite's control baseline.
