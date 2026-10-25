# Pending registry engine correction

This immutable derivative corrects the two actual workerd/SQLite defects found
by the [independent engine review](../verification/hosted-worker-pending-registry-engine-review/receipt.json).
It preserves the original engine packet, reviewed source and receipts. Only the
isolated derivative's production `engine.ts` changes; Ledger, schema, wire,
private interface, identity helpers and corrected registry dependency remain
byte-identical. Root owns live integration and baseline entry regressions.

The source is
`verification/hosted-worker-pending-registry-engine-correction/candidate/`.
Its predecessor is the original candidate source digest
`1481d1484c319e282fea6c9e61e3f21a149b323d6a7d3681bd3da0c5814db3c1`.
The independent review receipt SHA-256 is
`3476e3e26845e4b3b21cf0208aac883908660fa5e3ae8c83392ec3859c824de0`.
The original defects remain counterexamples in that review, rather than being
rewritten as passes.

## Trusted provider binding

The earlier private command accepted a canonical Android pending identity with
an `external-macos` resource even though the trusted adapter selected
`cloudflare-linux`. It retained that provider, launched through it, and later
recovery inspected it without a fence.

The correction compares supplied `ResourceIdentity.provider` with
`Provider.kind(request.ref.platform)` before initial mutation. It independently
checks each retained row against the trusted platform mapping at command,
track, prepare/final dispatch, provider-observation acceptance, claim, report,
constructor/known recovery and explicit enrollment boundaries. A mismatched
existing row receives a permanent bounded quarantine fence. Its provider
identity is retained for evidence; no replacement, reconstruction or new
authority is inferred. Even an existing durable stop cannot dispatch through a
conflicting adapter. The normal committed-stop outage exception remains
available when its provider binding still matches.

## Report acceptance after awaits

The earlier report path checked the independent quarantine fence before
calling the object verifier, but its final transaction checked only row
version/flags. A fence inserted during verification could leave that version
unchanged and still admit a result plus desired-stop state.

The corrected path validates the retained full identity/receipt and snapshots
its exact request/authority, immutable binding, resource, retained registration,
consumed claim, effect identity and accepted clock history before the verifier
await. The final synchronous transaction independently rejects a permanent
fence, quarantine, provider mismatch, changed snapshot, changed version,
existing report/terminal/result, or changed desired state. It then preserves
the existing final qualified-clock and live-authority checks before accepting
the result atomically. A same-version restore-style change to the historical
clock floor cannot weaken this decision.

Acknowledged delivery versions and coalesced outbox bytes are excluded from the
authority snapshot. Their normal independent delivery may advance without a
state-version change, so a valid report remains admissible after an ACK-only
flush. No registration RPC, authority renewal, provider action or retry loop is
added to report verification. Public and private API signatures are unchanged.

## Observed evidence

`node verification/hosted-worker-pending-registry-engine-correction/candidate/check.mjs`
built the exact derivative and passed **54/54 actual workerd/SQLite groups**:
the original 32 assertions/inputs reran, and 22 new focused controls passed.
The runner reports these counts separately. The new controls cover rejection
of a mismatched first provider before row/effect creation; fencing of restored
provider mismatches on recovery, retained commands, enrollment and durable
stop; an independent fence during report verification; 14 exact-field race
mutations; final qualified expiry and newer-command rejection; and the positive
ACK-only delivery case.

The final run is
`verification/hosted-worker-pending-registry-engine-correction/runs/20261025T050031192Z`
with source digest
`ee330a270f6151dfff96ed561a8b654ca1cc753026d03583cea99aee4276d811`.
The earlier successful 53-group checkpoint is also retained. The final run
records complete build/test stdout/stderr EOF, exact commands and installed
tool versions, five exact-owned SIGKILL controls, 54 disposed owned storage
environments and absence of all observed owned workerd PIDs. Other projects'
processes were preserved. The provider/clock/fault helpers remain explicitly
excluded finite fixtures. Registry requests use the actual fixed DO binding
and SQLite component, without an in-memory registry.

The registry dependency is unchanged at
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`.
No audit module is imported or changed in this engine packet; root separately
owns the accepted corrected audit module
`8120ebd4786005b263264c1162fa5a6ed0a7a0347d235aa5b6c4e984b076e38d`.
No dependency or policy scope was widened.

The scoped `correction.patch`, production delta manifest and final receipt are
review artifacts relative to the original isolated candidate. They do not
apply the original Engine/Ledger integration to the live V2 controller. Root
must independently accept the correction, integrate, and verify its selected
entry/module mapping. The full live 71-group controller and 20-process-control
suites were not rerun in this isolated lane. Public/scheduled entry wiring,
qualified production time/providers, native/device tests, deployment and GA
acceptance remain outside this evidence. No live source, root tracker, Git
state, customer message or production setting was changed by this lane.
