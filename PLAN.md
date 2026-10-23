# Execution index

The complete specification is [mixer-product-plan.md](mixer-product-plan.md).
All W01–W18 packages, G01–G38 launch gates, and D0–D8 dogfood milestones remain
in scope. No internal slice substitutes for those completion requirements.

Track implementation in `work-graph.json`, evidence in `verification/`, and current
limitations in `STATUS.md`. Work proceeds through the dependency graph in sections
24–25. This repository begins with no inherited implementation.

Initial integration: independently authored Swift core/UI and native renderer;
bounded Rust Wasm interpreter; canonical signed update contracts; useful local CLI;
native FieldLog baseline. Later slices extend these same components through the
complete native/guest/hosted workflow. External qualification stays explicit.

## Ongoing delivery

The user authorized periodic commits and pushes to
[snowdamiz/mixer](https://github.com/snowdamiz/mixer) on October 22, 2026.
Commit coherent, validated implementation or evidence slices and push `main`
after meaningful checkpoints. The root integrator coordinates pushes; agents
commit only their owned paths. Preserve other in-progress lanes, never force-push,
and inspect remote/CI state after publication. Failed or unavailable checks stay
explicit in the status and receipts. This code-delivery authorization does not
authorize production deployments, store submissions or messages to customers.

Physical phones are disconnected until the user says otherwise. Continue source
implementation, host tests, cross-compilation and simulator validation. Preserve
completed device receipts and mark subsequent physical-device checks pending;
do not retry devices or request reconnection during this limitation.


## Capability execution integration

The separately reviewed host bridge is checkpoint641b844. Root has frozen the
additive capability-execution-v1, runtime-identity-v2, release-v3 and activation-v2
contracts for implementation; see
`verification/capability-authority-contract-freeze-2026-10-23.json`.
Static contract approval enables no release or guest effect. Old identity1,
release1/2, activation1, default VM routes and frozen guest wire bytes stay strict.

Explicit identity2 parsing/capture/embed and protocol3 Go/Swift verification now
have scoped owner, independent review and combined-source receipts. See
`verification/release-v3-root-review/receipt.json`; these metadata and signature
proofs do not authorize a guest session. Hosted CI at24a7437 also passes all three
jobs after the pinned-compiler bridge and fixture repairs.

Bounded full native validation, zero-page parity and typed failure classification
now have a reviewed candidate; see `verification/capability-validation-review/`.
The operation returns no transferable proof and construction still revalidates.
Installed material now has a separately reviewed package, exact native-preimage
helper and bounded immutable policy/root capture; see
`verification/capability-installed-root-review/receipt.json`. It creates no adapters
or execution authority. The next slice composes concrete adapter lifecycle with
private durable signed recovery after review of the updater ownership design.
Explicit v3 development routes and schema3 storage now pass full local races,
PostgreSQL faults and independent public review; actual TCP delivery also verifies
with the public Swift v3 API before/after reopen. See
`verification/release-v3-service-root-review/receipt.json`. Production deployment
and immutable distribution remain separate. Hosted CI ata81f54c passes all three
jobs, including the v3 service. Durable updater ownership is approved in
`docs/capability-durable-updater-api-design.md`. The metadata-only recovery SPI now
passes its frozen matrix and204 independent external checks; private durable I/O
passes23 host tests per mode,29 independent checks and iOS/Android compilation.
See `verification/release-v3-durable-spi-root-review/receipt.json` and
`verification/capability-durable-io/final-receipt.json`. Actual committed-health
provenance and signed execution remain the private updater's responsibility.
Concrete adapter lifecycle now passes32 tests per mode,15 derived ownership
probes, independent public/internal checks and eight linked consumers; see
`verification/capability-bridge-lifecycle-root-review/receipt.json`. Pure private
policy derivation passes30 host tests per mode and iOS/Android compilation; see
`verification/capability-execution-policy/final-receipt.json`. It revalidates whole
evidence and intersects installed/signed grants without creating adapters.
Hosted CI at3bdf5cd passes all three jobs for the preceding SPI/I/O checkpoint.
Counted recovery storage now passes41 debug/release tests,18 new TSan tests and24
independent probes after repairing both owner-retirement races. Root audited the
frozen foundation; see `verification/capability-durable-store-root-review/receipt.json`.
Hosted CI at4a413b4 passes all three jobs for the preceding lifecycle/policy slice.
Owned enable's worker cutoff now passes35 tests per host mode, repaired cross
consumer links and independent zero-native-enable/retirement checks. The fixed
attempt signal latch passes six cases per host mode and independent source review.
See `verification/capability-enable-deadline/receipt.json` and
`verification/capability-attempt-signals/final-receipt.json`. CI at08e5c2d exposed
one fixture type-check complexity issue; a byte-preserving split is confirmed by
all three hosted jobs atbf5021e. See `verification/github-ci-bf5021e/receipt.json`.
The latch now also permits generation-bound control wakes without consuming its
terminal notification; eight cases pass per host mode, plus XCTest typechecking.
See `verification/capability-attempt-signals/2026-10-23-control-wake-1/receipt.json`.
Private durable selection/effects/health transitions now pass79 debug/release
functions and25 new TSan functions on frozen bf5021e dependencies, plus official
iOS/Android module builds. Root reproduced and repaired cold retry of an
interrupted or failed never-healthy candidate; the identical three probes pass
in all three host modes. Closing can record failure without selecting a fallback.
See `verification/capability-recovery-transitions-root-review/receipt.json`.
Hosted CI at7365b85 passes all three jobs for the preceding control-wake checkpoint.
Concrete attempt ownership and the signed coordinator are the current lanes;
combined composition, actual UI health and published consumer qualification remain.
Keep the full product plan and physical/published-consumer/GA gates in scope.
