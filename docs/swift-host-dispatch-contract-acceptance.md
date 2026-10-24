# Private host-import contract checkpoint

Root selects the original-owner host-import contract and accepts its compiler
feasibility and fresh layout prerequisites. The methods are uncalled. No host
operation, runtime accounting, full interpreter loop or public invocation is
accepted here. See the [root receipt](../verification/swift-host-dispatch-root-review/acceptance.json),
[contract](swift-host-dispatch-contract.md) and [fresh replay](swift-host-dispatch-layout-replay.md).

The proposal borrows actual argument and memory owners, ends cache/signature views
before dispatch, preserves the fixed frame outcome slot, and uses the actual WASI
adapter. The pinned imported-call witness preserves instruction, fuel, work, PC
and cursor effects once. Successful errno cleanup uses the original value arena;
post-effect failures preserve actual host effects and unresolved cleanup debt.
The implementation still needs every H01–H16 runtime case.

Root verified 14 original source archives and independently bound all 50 original
command receipts. The earlier producer seal excluded every `receipt.json`
basename; the root preflight now explicitly binds each command receipt. Earlier
metadata outputs reused Cargo targets across source variants without exact binary
identity, so they remain historical numeric proposals.

Fresh replay resolves layout provenance with 16 separate source/configuration/
context targets, retained exact executables and Cargo artifact JSON, eight full
unit test lists, and 44 bound commands. All 4,768 measured positions, original
owner layouts, and prior memory/bulk totals agree. The replay seal binds all 297
files, including command receipts. Root reran its offline verifier and inspected
the verifier's source, exact executable selection and layout comparisons.

The baseline is the 125-file integrated bulk-memory closure
`96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d`.
This proposal predates memory growth. After independently reviewed growth is
integrated, rebase and remeasure the host-import implementation before accepting
runtime behavior. The original VM source remains unchanged by this contract.
State/Combined limits remain 128/256 MiB and the ticket limit remains 86.

H01–H16, full Swift execution, the complete dispatcher, Ready/public invocation,
native integration, separate-repository published FieldLog, physical testing and
GA remain pending. G08's absent-cursor diagnostic is unchanged. Both replay
scratch directories and the original contract scratch were removed after empty
open-holder checks; no native instances were started.
