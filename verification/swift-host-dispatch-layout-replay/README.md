# Fresh isolated host-contract layout replay

`receipt.json` seals the source/context-isolated replay.
`../../docs/swift-host-dispatch-layout-replay.md` explains its exact scope.

Run `python3 verification/swift-host-dispatch-layout-replay/verify.py` from the
repository to verify every sealed file, all exact archived source files,
per-command receipts, Cargo artifact selection, compressed executable hashes,
full unit test lists and parsed numeric layouts. The verifier runs no binary
and writes nothing. `--preseal` checks the artifacts before the final receipt
exists. No prior ambiguous executable output is used as source provenance.

`replay.py` is the reproducible recipe. Its session guard requires a new
evidence directory for another fresh replay. Each build uses an empty target
for one complete source digest/feature/profile/production-or-unit context.
`finish.py` seals all files, including every command receipt, and records
cleanup of only its two unique scratch directories after no-holder checks.

Sources are retained under `inputs/`, exact compressed executables and selected
Cargo JSON under `artifacts/`, raw complete build/list/run streams under
`commands/`, and complete context/parsed layout records under `contexts/` and
`layouts.json`. The initial runner artifact-kind selection attempt remains
historical. The frozen original contract packet is unchanged.

This packet executes metadata printing only. It authorizes no runtime host
operation and supplies no Ready, public invocation, native, release or GA pass.
