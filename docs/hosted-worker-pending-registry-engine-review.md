# Pending-registry Engine/Ledger independent review

Review status: **changes required**. Two fresh actual workerd/SQLite controls
reproduce defects in the frozen candidate. This review authorizes no integration,
entry wiring, deployment, provider enablement, publication or GA acceptance.

The reviewed packet is
`verification/hosted-worker-pending-registry-engine/receipt.json`, SHA-256
`71190f11b04f1693135d4539a6ed0c0c36bf0cf9dfa058550af28549b06f5c76`;
its integration patch is
`e728cf9f3ddf2b71d2791d37e8f914c74ec9c5a1f377798baf99a5488c9183f3`.
The producer runtime source digest is
`1481d1484c319e282fea6c9e61e3f21a149b323d6a7d3681bd3da0c5814db3c1`.
Every production source file in the independent review copy is byte-identical to
the frozen candidate. Only the excluded fixture and independent test runner add
controls. The review does not import the catalog-inspector, authority-driver or
rejected outbound transport lanes.

## Findings

**[P1] Validate and retain the trusted provider/platform binding.**
`candidate/src/engine.ts:70` checks the resource key and immutable digest, but
accepts an incompatible `resource.provider`. `matchesRow` in
`candidate/src/registry-context.ts:14` also omits the retained provider kind.
The fresh control supplies the fully valid canonical Android identity and
registration, an unchanged key/digest, and `resource.provider=external-macos`
while the trusted fixture provider returns `cloudflare-linux` from
`kind(android)`. The Engine creates the row with `provider_kind=external-macos`
and dispatches a launch using that identity. A later valid identity-only
`recoverKnown` call inspects the mismatched identity, returns `pending` at
version `7`, and leaves no fence. The fixture records one launch and one inspect.
The private API must reject the mismatch before initial row mutation, and
recovery must quarantine a retained resource incompatible with the trusted
provider's platform selection. Checking only the canonical pending identity does
not bind the separate provider resource. Preserve the existing resource rather
than silently replacing its identity during recovery.

**[P1] Recheck the independent fence after result verification.**
`candidate/src/engine.ts:361-365` checks the row version and `quarantined` flag
after `ObjectVerifier.verify` yields, but does not check `ledger.fenced()` or
revalidate the retained identity/receipt. The fresh control starts from an
authorized consumed claim, holds the verifier, then persists the separate
permanent quarantine fence without changing the row version or its flag. This
uses the same independent-fence restore semantics as the producer's existing
`fenceOnly` fixture. After releasing the verifier, `report` returns `accepted`,
stores `report_hash` and `pending_result_json`, and changes desired state to stop
while the permanent fence remains present. A fence already visible before
verification correctly rejects at the earlier check; the missing final check
allows this async interleaving. Recheck the permanent fence and full retained
resource/registration identity in the final transaction before result admission.
This does not prohibit enforcing an already committed stop under a fence.

Both counterexamples are preserved as explicitly labelled reproduced defects in
`verification/hosted-worker-pending-registry-engine-review/report.json`.
The control runner exits successfully when it reproduces those exact outcomes;
that exit is not a product pass. The receipt reports two product findings and
four passing positive controls, and keeps acceptance blocked.

## Focused verification

The reviewer read the complete new Engine, Ledger, schema and registry-context
modules against the pending-registry, stop/terminal and terminal-replay contracts.
The corrected registry dependency is pinned at
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`;
its separate component review remains outside this Engine review's authority.

Four additional actual workerd/SQLite controls passed:

- An independent fence inserted during the dispatch ACK wait prevents the
  provider launch while preserving the durable dispatch marker.
- A fence inserted while stop observation is pending permits the already owned
  cleanup action and prevents terminal admission; the row stays stop-pending.
- Effect and claim barriers starting at version `9007199254740993` retain exact
  integer comparison. The final claim version is `9007199254740999`, with its
  separate newest unacknowledged clock projection preserved.
- Schema-2 migration of a terminal operation preserves exact terminal bytes,
  phase, previous state version and clock floor. Explicit enrollment retains
  quarantine and does not issue a claim or launch.

The commands were `node .../candidate/build.mjs` and
`node .../candidate/test/review.mjs`, with exact paths, times, exits, tool versions,
source hashes and complete stdout/stderr in the review packet. Six independently
created SQLite storage environments were disposed and removed. Every observed
owned workerd PID was absent after disposal. This review performed no SIGKILL;
it reused the pinned process-identity ownership helper for observation/cleanup.

The producer's prior 32 groups and five SIGKILL controls are bound source
evidence, not reviewer reruns. The prior 71 controller groups and 20 process
controls were not rerun here. Root must review a separate repaired derivative
and complete the selected integration regressions. Public ingress/scheduled
wiring, deployed delivery, real provider/clock/signing, native/device execution,
dogfood release qualification, capacity/restore operations and GA acceptance
remain unverified by this packet. No live file, other lane, tracker or Git state
was changed by this review.
