# Implementation status

Development is in progress. All eighteen work packages remain in scope:
sixteen are in progress and two are marked ready. No launch gate is verified;
[gates/ga.json](gates/ga.json) records eight running and thirty planned gates.
These gate counts are not an estimate of implementation percentage.
[The product plan](mixer-product-plan.md) remains the completion contract.

The repository contains independently authored Swift SDK/native adapters, a Rust
interpreter, signed update/verification components, a CLI, local reference
services, Phoenix components, the branded website/console and a separate FieldLog
repository. Accepted component slices do not establish the complete native,
hosted, store, customer or operational product.

## Current work and evidence

| Area | Verified scope | Next required work |
| --- | --- | --- |
| Swift runtime | Decode-plan reuse is integrated under unchanged limits. Four complete host contexts pass 2,314 named executions with nine inherited ignores each; the fresh live private suite passes 340 with zero ignores. | Prepare and review one source-bound full-reactor attempt, then separately select execution. Full-workload completion remains unverified. |
| iOS shared UI | Private pan input has simulator evidence. V7 Settings passes; first Tab fails actual focus traversal. All five run-cleanup checks pass and the owned simulator is deleted. | The corrected frozen V7 diagnostic join and fresh app/runner builds are accepted. A host-only V8 runtime packet is in preparation; independent review precedes native focus diagnosis and remaining shared UI/public routing. |
| Android shared UI | Private style/coordinator/input slices have scoped API37 emulator evidence. The latest integrated component fixture passes all 45 cases and 239 assertions; the separate pointer matrix passes 429 assertions. | Complete shared visual/interaction parity, public routing, resources/OS support, TalkBack and final physical comparison. |
| Hosted builds | Durable storage/coordinator components and registry/audit slices have host evidence. The isolated entry composition passes 922 groups; the defensive context-admission correction passes 79. | The broader entry review remains incomplete. Live Engine/entry composition, real worker/clock/provider operations, authentication, quotas and deployed schedule qualification remain pending. |
| Console | SolidJS Builds/releases use the website logo, cream/orange palette and typography. Builds passes 32 repository tests, seven independent controls, 117 backend text comparisons and 14 browser states. | Connect ordinary Phoenix customer authorization and live data/workflows; complete onboarding, permissions, billing and other G22–G24 requirements. |
| Hosted release/billing | Phoenix identity/artifact, build persistence and private webhook components have separately scoped host receipts. | Complete accepted authority/domain/HTTP composition, durable inbox/Oban reconciliation, Neon/Cloudflare/Stripe qualification, backup/recovery and operational evidence. Frozen authority/inspector and rejected transport lanes remain unaccepted. |

The previous unchanged full Swift reactor attempt passed validation and
Initialize, then failed Corpus 1 at CacheWork 64,000,001 / 64,000,000. Corpus 2
was unrun. Final consuming cleanup reached zero. The integrated decode-plan
optimization has full ordinary host regression and focused live evidence; it does
not yet establish a successful full workload. No work/memory/ticket limit is raised. See [the full result](verification/swift-exact-reactor-after-grouped-index/result.md),
[finite review](docs/swift-decode-plan-reuse-accounting-review.md) and
[integration](docs/swift-decode-plan-integration.md).

Independent iOS source review found two host-diagnostic completeness defects:
substituted original AX/app data and reordered callback references could be
labelled complete. The native verdict stays failed. A host-only correction now
binds exact immutable original packets and ordered callbacks. Independent review
passes 57 controls plus 38 producer methods, closing those two findings for frozen
V7 replay. Fresh app and runner builds pass with all 55 products newly built and
owned scratch removed. Host-only runtime preparation is underway; future runtime
ingestion and native acceptance remain pending. The forty-member Swift archive, original
oracle, input actions and transport limits remain fixed. See
[the correction review](docs/apple-focus-system-join-correction-review.md) and
[original native result](docs/apple-settings-fixed-chunk-native-result.md).

The hosted entry review stopped on an automated safety check after 45 baseline
passes and 20 of 21 additional controls, which exposed the context-selection bug.
It was not retried. The isolated defensive correction passes 79 functional groups;
root verified its 114 artifacts and minimal source/compiled change. That does not
complete the interrupted broader review or select live integration. See
[the correction](docs/hosted-worker-entry-context-admission.md).

## Delivery and pending qualification

The branded Builds checkpoint is pushed in `ba9ad437`, with Console and Engine CI
passing. Latest pushed checkpoint `9102ad3e` preserves finite diagnostics and
review boundaries. Its Engine CI run `40171963809` passes all three jobs and all
38 steps without skips; see
[the terminal receipt](verification/github-ci-9102ad3e-engine/terminal-receipt.json).
No native/provider/GA acceptance follows from host CI.

The supported iOS baseline is 26.0, targeting iOS 26, 27 and onward. Current
private appearance evidence is narrower and records iOS 26.5. Section 8.3's
identical shared app design remains required on Android; platform-default public
paths are not complete parity. Computer use and simulator/emulator tests are
resumed. Phones remain disconnected, and their matrix is deferred to final
acceptance. Normally one owned instance per native lane is allowed, with cleanup
after every run and preservation of unrelated projects.

Still required before completion: full public native/guest integration and OS
matrix; immutable published-package FieldLog consumption; signed clean-worker
builds; ready-for-testing distribution on both stores; connected customer console,
authorization and billing workflows; selected-cloud deployment, restore/failover,
security/operations and all specified accountable launch reviews. No implementation
slice replaces those requirements. See [PLAN.md](PLAN.md) for current execution
and [work-graph.json](work-graph.json) for every package's retained evidence.

Historical status text is preserved byte for byte in
[STATUS.history-2026-10-25.md](STATUS.history-2026-10-25.md). It records earlier
failures, intermediate selections and superseded pending states; consult the
current index and the source-bound receipts for present decisions.
