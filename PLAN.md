# Execution index

The binding scope is [mixer-product-plan.md](mixer-product-plan.md): all W01–W18
packages, G01–G38 launch gates and D0–D8 dogfood milestones remain required.
This index does not narrow or replace that specification. Use
[STATUS.md](STATUS.md) for the current checkpoint,
[work-graph.json](work-graph.json) for package dependencies and evidence, and
[gates/ga.json](gates/ga.json) for launch acceptance. Historical checkpoint text
is preserved byte for byte in [the prior index](PLAN.history-2026-10-25.md);
its older pending/selected statements do not override the current state.

## Current execution

1. **Owned Swift interpreter:** decode-plan reuse is reviewed and integrated.
   Four complete isolated host contexts pass 2,314 named executions; the fresh
   live private suite passes 340. Production limits remain fixed. The newly selected
   full attempt still reaches CacheWork exhaustion during Corpus 1 after
   23,358,291 guest instructions. The sealed result audit confirms all final
   reservations and live counts return to zero. A bounded remaining-work
   diagnosis now passes finite checks. The fixed-memory attribution observer
   passes four finite host tests and three independent tests. The strict supplementary classifier
   correction passes 38 host methods. One full attribution diagnostic reproduces
   the original failure; valid measurements attribute 53.907% of the fixed work
   budget to rebuilding previously decoded functions. A reviewed isolated segmented-LRU
   candidate regresses in one same-budget full comparison to 8,746,437 instructions
   and is rejected for integration. Final consuming usage is zero and owned products
   are removed. A second isolated cost/age candidate also regresses on all six
   finite work traces and is rejected before any full-target run. Its recorded
   rejection passes independent audit and all owned scratch is removed. Choose
   the next retention design from this evidence with exact work/memory accounting.
   An adaptive recency/frequency proposal passes 17 finite model controls but
   adds per-hit work and regresses phase-change misses; implementation selection
   is withheld. The live VM is unchanged and no new full retry is selected. See
   [the unselected model](docs/swift-adaptive-retention-design.md),
   [the finite rejection](docs/swift-cost-retention-candidate-review.md),
   [the rejected result](docs/swift-retention-runtime.md) and
   [the integration](docs/swift-decode-plan-integration.md).
2. **iOS shared UI:** the supplemental source and corrected frozen V7 host join
   pass independent review. Fresh generic simulator builds of both app and runner
   are accepted. A sealed host-only V8 runtime packet passes sixteen controls and
   passes nine independent review methods against those exact products. Root has
   completed one fresh V8 simulator run: Settings passes; first Tab fails. All
   five cleanup checks pass. The recorded-result audit and source lifecycle
   diagnosis are complete. A passive window/application/scene observer passes
   116 producer and 371 independent Foundation checks. The minimal UIKit notification
   Sendable correction passes a fresh generic app/runner build and independent
   review. Corrected V9 runtime preparation passes sixteen producer and nine
   independent host methods, with root acceptance. Native execution remains
   unselected and the original focus failure remains unresolved.
   The frozen V7 replay anchor cannot authorize a new supplemental join.
3. **Hosted builds:** preserve the isolated context-admission correction and its
   79 functional passes. The broader entry review stopped incomplete; the
   defensive source review does not replace it. Live Engine/entry integration,
   real provider/clock dependencies and deployed schedule remain pending.
4. **Android and cross-platform UI:** continue shared visual/interaction parity
   and public application routing from the accepted private emulator slices.
   Private native input acceptance is not complete public routing, TalkBack,
   compositor/resource coverage or final design parity.
5. **Hosted product and console:** continue ordinary customer authorization,
   durable domain/job integration, connected console workflows and provider
   qualification through the dependency graph. The new bearer identity Plug
   passes 47 targeted host tests and ten independent controls after review
   repairs. The pure human artifact/audit permission prerequisite now passes 30
   product tests and 23 independent probes after fixing incomplete callback-result
   acceptance. The durable PostgreSQL lookup now passes 25 product methods and
   17 independent probes, with scoped RLS, canonical revocation locks and strict
   runtime-role checks. Focused CI fixture wiring and all-five-migration
   apply/rollback/reapply checks pass after correcting rollback policy dependencies.
   The result remains pure policy evidence: protected domain/audit/idempotency
   transactions and customer routes remain pending. Full standard Phoenix CI
   and Engine CI pass for pushed checkpoint `d385adf3`; the Phoenix workflow
   uses its PostgreSQL 16 fixture. See
   [the current integration scope](docs/hosted-customer-authorization-postgres-ci-integration.md).
   The new transaction-owned authorization prerequisite now passes 18 product
   methods, 21 independent PostgreSQL probes and the equivalent CI fixture.
   Review repaired post-validation time checks and rescued effect errors that
   could commit prior SQL. All six migrations pass apply/rollback/reapply.
   Continue with protected artifact metadata/storage, immutable actor audit,
   principal-bound idempotency and customer HTTP composition; these remain
   unimplemented. See [the accepted transaction review](docs/hosted-customer-authorized-transaction-review.md)
   and [the proposed artifact contract](docs/hosted-customer-artifact-transaction-contract.md).
   Preserve accurate unavailable
   states until data/auth is connected. Keep the website branding throughout.

The frozen hosted catalog-inspector/authority-driver lanes and rejected outbound
Worker transport V2 lane remain isolated and unaccepted. Do not read, import,
execute or retry those frozen lanes. An interrupted review is not a pass.
Continue other authorized product work without treating that boundary as a
whole-project pause.

## Product decisions and verification

The iOS minimum is **26.0**, with support intended for iOS 26, 27 and onward.
Record the actual SDK/runtime tested; the private appearance prototype's current
26.5 evidence does not establish broader version qualification. Historical iOS17
compile receipts remain historical. See
[the baseline receipt](verification/ios26-baseline/candidate-1/receipt.json).

Section 8.3 requires the same shared app design on iOS and Android: layout,
hierarchy, colors, typography scale, icons, spacing and component appearance.
Platform-specific app styling requires explicit opt-in. Accessibility,
navigation, text input and system-owned surfaces remain native. Public paths
still need the shared design; existing platform defaults do not satisfy it.
See [the design decision](verification/ui-design-parity-plan-update/receipt.json).

The hosted stack remains Elixir/OTP + Phoenix + Plug/Bandit, Ecto/Postgrex and
Oban on Neon PostgreSQL; Cloudflare Containers for the API, Workers Static Assets
for the SolidJS/TypeScript/Vite/Solid Router console, and Workers/R2/CDN for
suitable edge/delivery workloads. Stripe supplies Billing, Checkout and Customer
Portal. Node is build tooling. Licensed macOS workers and isolated signing retain
necessary hosting exceptions; Android container resources/isolation and Oban
stop/wake/recovery require qualification. Start with direct verified-TLS Neon
connections, bounded pools and production scale-to-zero disabled. Protected Ecto
checkout uses `queue: false` under its selected transaction contract. Existing
Go/local PostgreSQL work is reference/compatibility evidence pending explicit
Phoenix migration. See [the stack decision](verification/hosted-stack-plan-update-2026-10-24/receipt.json).

Implement all product engine code independently. No Patch/Skip implementations,
generated source, tests, fixtures or dependencies. Record general-purpose
libraries in THIRD_PARTY.yml. Existing signed/wire contracts remain strict;
unsupported instructions, capabilities, UI operations or security contracts fail
closed. Static inspection alone never authorizes an OTA release. Keep signing
keys out of source/build workers and use standard cryptography.

Each slice needs executable tests with exact source/tool/command/output scope.
Skipped native, compiler, signing, store, customer or operational gates remain
pending. FieldLog must consume immutable published packages from its separate
repository. Local-checkout debugging is not dogfood release qualification.
Never promote a GA gate without its specified evidence and accountable reviewer.

## Ongoing delivery and resource ownership

The user authorized periodic coherent commits and non-force pushes to
[snowdamiz/mixer](https://github.com/snowdamiz/mixer) `origin/main`. Root coordinates
delivery, uses explicit path allowlists, preserves other staged/unfinished work,
checks resulting commit paths and inspects CI after each push. This authorization
does not include production deployment, store submission, customer messages,
destructive migrations or credential changes.

The plan requests parallel agents using fresh context, `gpt-6.1-sol`, `xhigh`,
and bounded file ownership. Coordinate contracts before dependent changes; do
not edit another active lane's files or claim to change the controlling model.

Computer use, screen capture and simulator/emulator tests are resumed. Normally
use one active owned instance per native lane; reuse it, retire an obsolete owned
instance before replacement, and shut down disposable instances after evidence,
including failed runs. Preserve other projects' instances, data and processes.
See [the resumption receipt](verification/native-testing-resume-2026-10-24/receipt.json).

Phones remain disconnected. Do not query/retry phones or request reconnection.
The user accepts simulator/emulator tests for development slices and advancing
dependent work. Run the physical matrix at final acceptance and correct any
hardware differences then. Preserve actual environments and keep final hardware
checks pending. See [the development policy](verification/simulator-development-policy/receipt.json).

## Complete package index

The acceptance/dependency details for every row remain in the product plan and
work graph. `ready` means available work, not completed acceptance.

| Package | Workstream | Current state |
| --- | --- | --- |
| W01 | Product and contracts | in_progress |
| W02 | Toolchain and local build | in_progress |
| W03 | Core Swift model | in_progress |
| W04 | iOS UI adapter | in_progress |
| W05 | Android UI adapter | in_progress |
| W06 | Capability generator | in_progress |
| W07 | Guest compilation | in_progress |
| W08 | Owned interpreter | in_progress |
| W09 | First-party integrations | in_progress |
| W10 | Device updater | in_progress |
| W11 | Release backend | in_progress |
| W12 | Build/signing service | in_progress |
| W13 | Store distribution | ready |
| W14 | Console and commercial | in_progress |
| W15 | Debug/import/export | in_progress |
| W16 | Security and reliability | in_progress |
| W17 | FieldLog delivery | in_progress |
| W18 | External qualification and launch | ready |
