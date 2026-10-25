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
| Swift runtime | Decode-plan reuse is integrated under unchanged limits. Four complete host contexts pass 2,314 named executions with nine inherited ignores each; the fresh live private suite passes 340 with zero ignores. | One corrected full attribution diagnostic reproduces the Corpus 1 cache-work failure at 23,358,291 instructions. Valid measurements show 61,142 repeated decodes and 53.907% of the work budget spent rebuilding previously decoded functions. Final consuming usage is zero and owned scratch is removed. An isolated retention candidate passes finite tests but has mixed synthetic costs; independent review and exact-target preparation are underway. Corpus 2 remains unrun. |
| iOS shared UI | Private pan input has simulator evidence. V7 Settings passes; first Tab fails actual focus traversal. All five run-cleanup checks pass and the owned simulator is deleted. | The corrected frozen V7 diagnostic join and fresh app/runner builds are accepted. The V8 runtime packet passes 16 producer and nine independent host methods. The fresh V8 simulator run passes Settings but fails first Tab, with zero skips and all five cleanup checks passed. The result audit and source lifecycle diagnosis are accepted; a passive lifecycle observer passes 116 producer and 371 independent Foundation checks. The first generic build failed Swift 6 actor isolation; the minimal correction now passes a fresh app/runner build and independent review. Corrected V9 runtime preparation passes 16 producer and nine independent host methods; root accepts preparation, with no new native execution. Shared UI/public routing remains incomplete. |
| Android shared UI | Private style/coordinator/input slices have scoped API37 emulator evidence. The latest integrated component fixture passes all 45 cases and 239 assertions; the separate pointer matrix passes 429 assertions. | Complete shared visual/interaction parity, public routing, resources/OS support, TalkBack and final physical comparison. |
| Hosted builds | Durable storage/coordinator components and registry/audit slices have host evidence. The isolated entry composition passes 922 groups; the defensive context-admission correction passes 79. | The broader entry review remains incomplete. Live Engine/entry composition, real worker/clock/provider operations, authentication, quotas and deployed schedule qualification remain pending. |
| Console | SolidJS Builds/releases use the website logo, cream/orange palette and typography. Builds passes 32 repository tests, seven independent controls, 117 backend text comparisons and 14 browser states. | Connect ordinary Phoenix customer authorization and live data/workflows; complete onboarding, permissions, billing and other G22–G24 requirements. |
| Hosted release/billing | Phoenix identity/artifact, build persistence and private webhook components have separately scoped host receipts. | Complete accepted authority/domain/HTTP composition, durable inbox/Oban reconciliation, Neon/Cloudflare/Stripe qualification, backup/recovery and operational evidence. Frozen authority/inspector and rejected transport lanes remain unaccepted. |

The new single full Swift reactor attempt passes validation and Initialize, then
fails Corpus 1 at CacheWork 64,000,001 / 64,000,000 after 23,358,291 guest
instructions; the preceding attempt reached 15,753,076 instructions. Corpus 2
remains unrun. Root verified all 311 result members and final consuming cleanup:
all current reservations, live counts and tickets are zero, with no cleanup
invariant. Owned scratch is removed and the exact compressed binary is retained.
No work, memory,
ticket or time limit was raised, and no retry is selected. The integrated
optimization passes ordinary host regression but does not yet complete the full
workload. A bounded diagnosis establishes 11,828,480 planning credits (18.48%)
and locates the final failure inside rebuild decoding. The test-only attribution
observer passes four finite host tests, covering 409 work prefixes and 173
cancellation prefixes. Three independent tests pass and root accepts the observer
for diagnostic preparation. Fresh preparation passes five finite Rust executions
and fourteen host controls. Independent review found six malformed supplementary schema cases; the strict correction
now passes 38 host methods. One corrected full diagnostic reproduces the original
failure and instruction count. All five telemetry snapshots are valid: 61,627
completed decodes include 61,142 repeats across 485 distinct functions. Repeated
IR construction consumes 34,500,496 credits (53.907% of the unchanged work budget).
This points investigation toward retention; it does not prove a replacement policy
will finish the workload. The original Result and legacy false cleanup flag remain
visible separately from final zero consuming usage. Owned processes and scratch
are removed. The result passes independent audit and root acceptance for retained host
measurements only. See
[the independent audit](docs/swift-current-attribution-runtime-review.md),
[the measured result](docs/swift-current-attribution-runtime.md),
[the schema correction](docs/swift-attribution-schema-correction.md),
[the preparation review](docs/swift-current-attribution-preparation-review.md),
[the diagnosis](docs/swift-plan-cache-remaining-work-diagnosis.md),
[the selected packet](docs/swift-exact-reactor-after-plan-reuse.md),
[audited result](docs/swift-exact-reactor-after-plan-reuse-result.md)
and [integration](docs/swift-decode-plan-integration.md).

Independent iOS source review found two host-diagnostic completeness defects:
substituted original AX/app data and reordered callback references could be
labelled complete. The native verdict stays failed. A host-only correction now
binds exact immutable original packets and ordered callbacks. Independent review
passes 57 controls plus 38 producer methods, closing those two findings for frozen
V7 replay. Fresh app and runner builds pass with all 55 products newly built and
owned scratch removed. V8 runtime preparation and independent host review now
pass. The one selected V8 simulator attempt passes Settings but fails first Tab;
all five cleanup checks pass, and the owned instance and scratch are removed.
Root verified the result audit and its exact immutable raw packets. The new
diagnostics show focus leaving, briefly returning to, and leaving the same plain
UIKit reference. Source diagnosis identifies missing key-window/application/scene
state during the public-input interval. A passive observer passes 116 producer
and 371 independent Foundation checks. The original generic build exposed a Swift 6
actor-isolation error. The minimal correction now passes all eight generic build
commands and independent review, with 55 fresh products and owned scratch removed.
Corrected V9 runtime preparation passes 16 producer and nine independent host
methods, with 263 independently verified input bindings and root acceptance.
No new native attempt is selected.
The focus failure's cause remains unproven and native acceptance remains pending.
The candidate adds two helpers to the forty-member baseline and changes only its
app entry source; original oracle, input actions and transport limits remain fixed. See
[the correction review](docs/apple-focus-system-join-correction-review.md) and
[latest native result](docs/apple-focus-system-native-result.md).

The hosted entry review stopped on an automated safety check after 45 baseline
passes and 20 of 21 additional controls, which exposed the context-selection bug.
It was not retried. The isolated defensive correction passes 79 functional groups;
root verified its 114 artifacts and minimal source/compiled change. That does not
complete the interrupted broader review or select live integration. See
[the correction](docs/hosted-worker-entry-context-admission.md).

The ordinary Phoenix bearer identity Plug passes 47 targeted host tests, including
real RS256 verification, with build scratch removed. Independent review passes ten
groups after repairing malformed Content-Type parameters, empty subtypes and
duplicate response metadata. It grants identity only; no customer route, membership authorization,
login provider or console data connection is implemented by this slice. See
[the transport contract](docs/hosted-bearer-identity-transport.md).

The first pure customer permission policy now passes 26 host tests and warnings-as-errors
compilation. It requires both current server membership evidence and the exact
verified token scope for human artifact/audit actions. Independent review is active.
The unavailable repository default prevents this prerequisite from becoming a public
authorization path; durable lookup, transaction/RLS/revocation ordering and console
integration remain pending. See [the policy](docs/hosted-customer-authorization.md).

## Delivery and pending qualification

The branded Builds checkpoint is pushed in `ba9ad437`, with Console and Engine CI
passing. Latest pushed checkpoint `b375e55de` records the reviewed iOS compile
correction and runtime preparation, strict Swift telemetry correction and independently
audited full diagnostic failure. All 389 changed paths are pushed and remote main
matches; the active retention candidate is excluded. Engine CI `40182820548` is
running. See [the delivery receipt](verification/github-delivery-diagnostic-corrections/delivery-receipt.json).
The preceding `7b604864` adds the accepted bearer identity prerequisite, reviewed
source/host observers and then-unexecuted diagnostic preparation.
Phoenix CI `40179798794` passes its job and all eight steps without skips;
Engine CI `40179798720` passes all three jobs and all 38 steps without skips. See [the current CI receipt](verification/github-ci-7b604864/receipt.json). The preceding
`6b8aba35` records the full Swift failure, finite cache diagnosis, reviewed V8
execution and complete cleanup evidence; its Engine CI `40176959303` passes all
three jobs and all 38 steps without skips.
The preceding `6403eea9` checkpoint
integrates reviewed decode-plan reuse and fresh native builds; its Engine CI
`40174672304` passes all three jobs and all 38 steps without skips. See
[the terminal receipt](verification/github-ci-6403eea9-engine/terminal-receipt.json).
See [the latest terminal receipt](verification/github-ci-6b8aba35-engine/terminal-receipt.json).
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
