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

Next implement explicit identity2 parsing/capture/embed, protocol3 Go/Swift
verification and cross-language vectors, plus bounded full native validation and
typed failure classification. Then bind exact captured material to concrete
adapters in a separate activation package and qualify durable signed recovery.
Explicit hosted v3 routes/storage and immutable external distribution follow.
Keep the full product plan and physical/published-consumer/GA gates in scope.
