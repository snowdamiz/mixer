# Execution index

The binding scope is [mixer-product-plan.md](mixer-product-plan.md): all W01–W18
packages, G01–G38 launch gates and D0–D8 dogfood milestones remain required.
This index does not narrow or replace that specification. Use
[STATUS.md](STATUS.md) for the current checkpoint,
[work-graph.json](work-graph.json) for package dependencies and evidence, and
[gates/ga.json](gates/ga.json) for launch acceptance. Historical checkpoint text
is preserved byte for byte in [the prior index](PLAN.history-2026-10-25.md);
its older pending/selected statements do not override the current state.

## Resumed checkpoint

Implementation resumed at the user's October 25 request to continue this plan.
The [pause handoff](docs/implementation-pause-2026-10-25.md) preserves the delivered
browser-session security slice and backed-up SQL candidate. The corrected SQL,
configuration text admission and transaction-local JIT policy now pass independent
development review. Nine-migration integration passes. Pushed `7e434330` passes
615 Phoenix methods with two existing skips, but CI fails on unclassified
selected-fixture discovery warnings. The narrow configuration repair passes eight
actual isolated Mix checks. It is pushed as `4492bbc7`; Phoenix then stops in
storage fixture setup at an ordinary directory query timeout. The fixture repair
now passes 24 PostgreSQL 16 methods, including commit/error rollback setting
restoration. Pushed `4b458d6b` now passes every Phoenix CI step, including
storage/migration and broader hosted checks (645 passed, two existing skips).
Lifecycle, discovery and constructor Engine runs pass all three jobs.
The catalog prerequisite is pushed as `9d5c40ee`; selected storage/migrations pass,
but its broader job stops at Mix formatting before tests. The terminal-newline
correction passes the actual formatter and fresh 26-method PostgreSQL 17 and
20-method independent PostgreSQL 16 replays. Corrected `6baf9acc` Phoenix CI
passes every step and its Engine run passes all three jobs. The preceding
catalog Engine run also passes. SQL prerequisite `97d436b4` now passes both
Phoenix and Engine CI. Catalog V2 checkpoint `6b1dfd33` now passes Phoenix and all Engine jobs. Model checkpoint
`53672fc1` passes Engine CI.
Migration checkpoint `a6eaa8a5` passes selected storage/migrations but broader
Phoenix CI invalidates fifteen build-storage tests because their expected list
omitted migration 00008 (649 passed, two existing skips). The one-item fixture
correction passes projectless formatting. Corrected `eec94804` Phoenix CI now
passes every step, including 664 ordinary methods with two existing skips. Its
Engine workflow now passes all three jobs. The preceding `d1ca1656` Phoenix
run was cancelled and is not a pass. Engine runs for `a6eaa8a5` and `d1ca1656`
now pass all three jobs.
See [the integrated scope](docs/hosted-browser-session-integration.md).
Ordered-diagnostic design checkpoint `ab5442a5` now passes all three Engine jobs.
Preauth checkpoint `72340253` now passes every Phoenix CI step, including
664 ordinary methods with two existing skips. Its Engine workflow now passes all three jobs.
Begin-login checkpoint `273a1e48` passes every Phoenix CI step, including
664 ordinary methods with two existing skips. Its Engine workflow passes all three jobs.
Callback-contract and recorded Swift-prototype review checkpoint `6d98de42`
now passes all three Engine CI jobs.
Selected finite Swift completion checkpoint `68468f8f` now passes all three Engine jobs.
Callback candidate `5595f7b6` is on the isolated `codex/browser-callback-ci` validation
branch. Phoenix CI passes 95 selected PostgreSQL 16 methods and 664 ordinary methods
with two existing skips. Its archive omits two hidden source inputs; a narrow upload
repair `9f15b11f` now passes every Phoenix step. Root verifies all 65 selected source
inputs and 123 outputs across both retained artifacts; all three Engine jobs pass. The earlier candidate VM job
exceeded its 20-minute limit after a 13-minute-47-second checkout; three later checks
were skipped. Independent storage acceptance remains pending.
Corrected analyzer design checkpoint `13ce0c2e` passes all three Engine CI jobs.
Accepted fixture framing checkpoint `4af8b7e1` passes all three Engine CI jobs.
Fixture contract and framing CI checkpoint `2e4ca9a3` fails its new framing CI step
before Rust compilation: Homebrew shim resolution selected rustup-init. The
retained artifact is complete; the repaired checkpoint is recorded below.
VM and services pass; subsequent Swift checks were skipped.
Rustup dispatch repair `05c1ebf0` passes all three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40247799000).
Generated Android source-export repair `99d63843` passes all 40 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40252047362).
Default appearance packaging `55985881` passes all 40 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40256207023).
Copied SDK/source-pair compatibility `1f114d8f` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40263504027) passed all 3 jobs and 40 steps.
Android host lifecycle core `4e48ac1a` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40267720327) passed all 3 jobs and 40 steps. The new Java suite has local host evidence and is not wired into this existing workflow.
Android observer/source-profile repair `b45963c0` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40272428143) is queued.
Computer use, capture and native runtime tests remain paused.
The full plan remains incomplete; no GA gate is promoted.

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
   is withheld. A second count-plan-aware cold-insertion model passes 24 producer
   and 18 independent methods (292 oracle cases, 46,550 transitions). Its retained
   phase regressions and estimated costs prevent an inference of target benefit.
   The separate isolated Rust feasibility experiment is now rejected: three of
   six complete CacheWork traces regress, operation reservation grows by 20,472
   bytes and memory admission fails earlier. Two original policy observations
   remain failed. An independent 23-method offline audit confirms the recorded
   rejection; live integration and full-target retry are unselected. The bounded
   ordered cache-transition diagnostic design passes 25 producer and 16 independent
   finite model methods after seven design corrections. Root verifies 73 sealed
   members and unchanged 132-file VM closure. The isolated Rust prototype
   reproduces 340 pristine and 356 candidate methods. Independent review adds
   five writer and five hook controls, but finds three malformed CAP streams
   mislabeled valid and incomplete memory accounting. Root verifies 305 sealed
   members and accepts the recorded finite evidence only. A separate finite completion now passes 362 candidate methods, 21 custody controls
   and six independent controls. Root verifies 380 sealed members and accepts the
   six selected fixture paths with the independent 19-phase inventory: 16,186 of
   16,384 logical bytes. Inherited serializer and CODE-buffer limits remain open;
   full diagnostic/analyzer/target acceptance remains pending. The corrected analyzer design now
   passes 25 producer and 23 independent methods, including 35,694 policy cases
   and 165 closed transitions. Root verifies 279 sealed members and accepts the
   design only. The bounded safe-File-borrow framing foundation now passes 20
   producer and 24 independent host methods. Root verifies 894 sealed members
   and 845 unchanged upstream members, accepting this standalone fixture scope.
   Its reviewed logical inventory is 14,248 bytes within 41,984 reserved bytes;
   all limits remain unchanged. Framing observation grants no semantic prefix
   validity. The first macOS CI attempt stops before Rust compilation at
   rustup shim dispatch. Its narrow repair passes the unchanged 44-method closure
   and 16 focused controls locally. The repaired macOS CI now passes all 44
   methods under Rust 1.98.1; root verifies its 78-member artifact and exact
   source bindings. All three Engine CI jobs now pass.
   The corrected acquisition/lifecycle contract now passes 24 producer
   and 38 independent methods, including 5,390 oracle comparisons. Root verifies
   773 sealed members and both preserved archives, accepting this contract only.
   The separate fixture-envelope candidate is frozen after 64 host methods
   and 16,170 finite-model comparisons pass. Root verifies 796 sealed members.
   Independent review finds an undercounted prior-read loop and inconsistent
   private poison-latch gating; the candidate needs revision. Seven accounting
   probes and 33 corrected public fixtures pass; one of ten private fault controls
   fails. The 64-method independent replay times out and is not a pass. Combined
   steps, layouts, lifetimes and implementation acceptance remain pending.
   The second correction proposal passes independent accounting review: all 116
   operation rows, 108 transfer entries and error-finalization funding reconcile.
   Root selects leaf425/W24/B471/G112/T42/finish47/F42 under unchanged global caps.
   The public debit becomes 534*S_paid + 47*F_paid + 425*N_B; zero-call framing
   retains debit581 with no invented observation. The corrected-source producer now passes
   70 host methods, 21,714 fresh model/threshold comparisons and 32 layouts. Root
   verifies 306 sealed members and the 86-member source archive. Independent
   review passes 18 methods but fails the absent-state debit control; eight API
   rejection probes pass. The final 116-row accounting bounds remain supported,
   but combined acceptance is withheld. A separate source, guard-funding and
   caller-validation proposal passes 352 independent offline checks. Root selects
   the exact correction and explicit guard ownership under unchanged amounts;
   the host producer now passes 70 unchanged plus 8 focused methods, 21,714
   comparisons and 32 layouts. Root verifies 177 proposal/accounting/implementation
   members and 27 qualification command results. Independent review passes 14
   exact-source methods, two separate counter-overlay methods and API controls;
   the original ten absence debits are all zero. Root verifies 407 combined members
   and accepts this corrected fixture-only host implementation and its selected
   step/memory bounds. A portable CI runner passes the complete local closure, but
   independent review rejects ambiguous compiler identity and unrelated API spans.
   Both parser corrections pass 32 normal/optimized controls and a fresh complete
   host qualification. Independent correction review is running; actual
   Rust 1.98.1 CI qualification remain pending. See the
   [bounded acceptance](verification/swift-ordered-retention-analyzer-envelope-root-review/absence-implementation-acceptance.json) and
   [selected numeric contract](verification/swift-ordered-retention-analyzer-envelope-root-review/correction-numeric-contract-selection.json).
   Existing framing behavior, ABI and report remain fixed. Semantic replay, real adapters,
   CLI/custody and target execution remain pending. See
   [the contract review](docs/swift-ordered-retention-analyzer-fsm-contract-review.md),
   [the CI wiring](docs/swift-ordered-retention-analyzer-framing-ci.md) and
   [the framing foundation review](docs/swift-ordered-retention-analyzer-library-review.md). See
   [the analyzer design review](docs/swift-ordered-retention-analyzer-review.md),
   [the completion review](docs/swift-ordered-retention-diagnostic-completion-review.md),
   [the prototype review](docs/swift-ordered-retention-diagnostic-rust-review.md), [the design review](docs/swift-ordered-retention-diagnostic-design-review.md),
   [the rejection audit](docs/swift-count-plan-retention-candidate-review.md),
   [the reviewed finite result](docs/swift-retention-next-design-review.md),
   [the earlier unselected model](docs/swift-adaptive-retention-design.md),
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
   The generated-source repair now passes independent fresh CLI export of fourteen
   Java files, strict Java/D8 compilation and Debug/Release source-lock checks.
   Root verifies 303 sealed members and accepts this source-export scope. Default
   appearance packaging now has scoped independent acceptance: 50 independent
   vectors and two complete unsigned generated-app cross-builds pass, with exact
   canonical descriptor bytes and unchanged Java classes. Root verifies 617 sealed
   members. The corrected copied-SDK contract and explicit ASCII-only SDK-root
   naming amendment are selected for implementation after independent review.
   One compiled source-pair profile will enforce the common Swift preaccess gate,
   including Android-configured projects with a missing Android lock, and render
   the direct driver's build-only policy. Root verifies 544 contract/review members
   and all 42 source-profile files against the accepted commit. The implementation
   now has scoped independent acceptance: 31 CLI methods per Debug/Release and
   28 Python methods pass. Independent checks cover common/driver entrypoints,
   copied Swift/Java consumers and all 75 unchanged native build inputs. Root
   verifies 2,623 producer/review/preaccess members, 105 current source inputs and
   235 independent command results. The profile governs common Swift preaccess
   and the rendered driver's build policy. Public V2 remains unchanged. A pure
   Java lifecycle decision core outside the exported adapter map now passes
   22 producer host methods and 45,841 assertions, plus 33 independent methods,
   71 scenarios and 264,289 assertions. Root verifies 119 sealed members and
   46 current inputs and accepts this host decision scope. Android effect-runner
   wiring and API28 environment support remain separate prerequisites. The actual
   environment observer listener repair and explicit source-pair.2 migration now
   have scoped acceptance: 161 producer and 287 independent host cases, 22 fresh
   consumer/signature control families and identical independent Java/D8 outputs.
   Producer app-owned Swift/JNI cross-compilation is audited. Root verifies 2,877
   sealed members and 34 independent commands. Private owner effect integration
   is the next contract; public routing remains separate.
   Native runtime checks remain paused. See
   [the observer acceptance](docs/android-environment-observer-acceptance.md),
   [the selected contract](verification/android-copied-sdk-appearance-contract-root-review/implementation-selection.json),
   [the export review](docs/android-authored-toggle-generated-export-review.md) and
   [the packaging review](verification/android-default-appearance-packaging-implementation-review/final-review.md).
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
   Protected artifact metadata/storage, immutable v2 audit and principal-bound
   idempotency now compose through the internal customer facade. All 97 current
   selected host methods and seven-migration apply/rollback/reapply checks pass,
   with independent codec, staged-read, storage and facade reviews. Root accepts
   this local component slice; customer HTTP/console composition, tenant trust
   and lifecycle writers, and provider qualification remain pending. See
   [the integration scope](docs/hosted-customer-artifact-integration.md) and
   [the artifact contract](docs/hosted-customer-artifact-transaction-contract.md).
   Artifact checkpoint `6fff5ab9` is pushed to `origin/main`; its Phoenix and
   Engine CI both pass. Both workflows passed for prior checkpoint `9662eda1`
   with no skipped steps. A local prerequisite pass is not full hosted or
   customer workflow acceptance.
   Preserve accurate unavailable
   states until data/auth is connected. Keep the website branding throughout.
   The final brand audit corrected sidebar/footer text contrast with the existing
   muted token; all 32 console tests and the production build pass. Saved layout
   evidence remains historical, with no new browser/capture run during the pause.
   The next ordinary HTTP slice now passes local acceptance: 18 facade methods,
   25 combined independent facade methods, 32 transport methods, 46 combined
   independent transport methods and eight real Endpoint/PostgreSQL methods
   covering 47 HTTP requests. Counts overlap. Review repaired normalized raw-path
   aliases; source/output bindings and all owned resource cleanup pass. Live
   console sessions/data, tenant trust/lifecycle, provider deployment, distributed
   admission and full Go parity remain pending. See
   [the HTTP checkpoint](docs/hosted-customer-artifact-http-checkpoint.md).

   Customer workspace discovery passes local acceptance through the production
   Endpoint/default verifier/default Repo and actual console client. The branded
   `/workspace` route composes scoped selection and session fencing. The cookie
   adapter now shares the bounded reader with the bearer client and accepts no
   browser bearer or destination configuration. All 112 console host tests and
   build pass; the website logo, colors and typography remain matched. Mobile
   navigation now puts its three links below the logo; visual checks remain paused.
   Browser-auth configuration, PKCE, cookie, CSRF and callback primitives pass 39
   selected host methods. Independent review passes 15 transport plus 15 protocol
   methods. Counts overlap with existing suites. Selected protocol CI is wired.
   This is component acceptance: no live session is installed, no auth routes or
   provider exchange are enabled, and the entry remains unavailable. The durable
   SQL lifecycle now passes 23 selected methods on PostgreSQL 16.15 and 17.11,
   six separate correction-review methods, and nine-migration rollback/reapply.
   Review fixed NULL-scope admission and expiry after unique-key waits. Config
   text admission passes 26 producer and 32 combined review methods. Ordinary
   authorization's transaction-local JIT policy passes 86 selected methods and
   six independent controls under unchanged deadlines. Counts overlap. Next
   implement the runtime pool/key-custody/current-verifier/provider owner join,
   then the ordinary protected HTTP/console session workflow. The storage
   contract's 18 complete-lifecycle cases remain a broader requirement than
   these component tests. See [integration](docs/hosted-browser-session-integration.md).
   The [runtime contract](docs/hosted-browser-lifecycle-runtime-contract.md) now
   passes independent bounded review after startup/policy/verifier corrections.
   Pure custody/runtime configuration now passes 30 producer and 25 independent
   methods, with root source/output/cleanup acceptance. No startup or route wiring
   is enabled. Function/type catalog checks now pass 26 producer PostgreSQL 17 and 20
   independent PostgreSQL 16 methods, with root source/output/cleanup acceptance.
   Their named partial result alone cannot authorize readiness.
   Three new PG17 probes exposed extra standalone browser types and altered ACL
   grantors; both gaps are now repaired. Explicit V1/V2 selection passes 30 PG17
   and 19 independent PG16 methods, plus 10/12 respective compile-rejection
   controls. Original catalog 26/20 and SQL 39/38 regressions pass separately.
   Root accepts the partial function/type prerequisite and has selected inert
   migration 20261025000008. Ten-migration integration passes on PG17 and
   independent PG16. Six PG17 operator methods and eleven independent PG16
   adversity methods pass separately. Root accepts this inert migration slice;
   corrected broader Phoenix CI passes at `eec94804` as recorded above. See
   [migration review](docs/hosted-browser-activation-preparation-migration-review.md).
   The pure activation-preparation decoder now passes 19 producer methods,
   11 existing snapshot regressions and 29 independent methods, with root
   source/output/format acceptance. It proves shape only; the future owner must
   compare retained claims, current identity and configuration before use.
   The corrected relation contract passes 12 producer and 16 independent
   source checks, including both incoming principal foreign keys. Its 48 runtime
   cases remain pending. Both PG16/17 representation fixtures now pass 82
   semantic checks, with 23/24 actual mutation controls. Independent review
   passes 427 main, 96 mutation-effect and 14 freeze/source assertions; counts
   overlap. Root accepts representation evidence. The RelationCatalog candidate
   passes 233 PG16 and 234 PG17 methods, with 65/66 live mutation controls.
   Independent review passes 96 methods on each major, including fourteen
   denied mutations and two allowed naming equivalences. Root accepts only
   this partial prerequisite. The subsequent dedicated preauth composition now
   passes 30 PG17 producer and 20 independent PG16 component methods. Review
   repaired foreign-caller slot release and rejected projected pending attempts.
   Root verifies 118 producer seal entries, 358 review artifacts and selected
   source/dependency/output bindings. This accepts manually started fixed
   bootstrap/load and Vault roundtrips only; complete 44/40/18 matrices and
   Application/current-identity/provider/HTTP joins remain pending. The fixed
   begin-login component now passes 30 PG17 controls, 30 unchanged preauth
   regressions and 34 independent PG16 controls. Root verifies 103 producer and
   284 review seal entries, exact source/output bindings and cleanup. Review
   added final caller publication checks after authoritative permit release;
   revision-stable audit races roll back. This accepts private preauth URLs only.
   The callback contract now passes independent source review and fourteen
   executable contract-model methods; root verifies 154 sealed members. All 39
   runtime matrix acceptance remains pending. The typed callback storage candidate
   passes 35 callback, 30 preauth and 30 begin producer methods on PostgreSQL 17.
   The PostgreSQL 16 review stopped before database creation after two archive
   preparation failures and an automated safety interruption; its runtime checks
   remain pending and owned scratch is removed. Separate portable Linux CI passes all 95 selected methods on PostgreSQL 16
   and 664 ordinary methods with two existing skips. The uploaded selected packet
   omits two hidden source inputs. Corrected `9f15b11f` passes every Phoenix step,
   and root verifies all 65 sources and 123 outputs across its two retained artifacts.
   This CI result does not complete the interrupted independent review. Complete
   supervised ClaimOwner ownership, shared permit transfer and a retained wall
   handoff must precede publishing a claim handle. Provider
   and public-route composition remain pending. See [callback contract review](docs/hosted-browser-callback-claim-review.md),
   [begin-login review](docs/hosted-browser-begin-login-review.md),
   [preauth review](docs/hosted-browser-preauth-store-review.md) and
   [relation review](docs/hosted-browser-relation-catalog-review.md). The additive preparation SQL helper passes 39 PG17 and 38
   independent PG16 methods after rejecting unexpected new-object grants. Root
   accepts this SQL component and the separately reviewed inert migration; no
   activation-preparation caller or authentication readiness is enabled. The full
   forty-case owner runtime matrix remains incomplete. See
   [constructor review](docs/hosted-browser-runtime-constructor-review.md),
   [versioned catalog review](docs/hosted-browser-catalog-v2-review.md) and
   [fixture repair](docs/hosted-browser-storage-ci-fixture.md).

   The prior `1257cbf8` Phoenix CI fails the 121-project directory transaction
   deadline (608/609 methods pass, two skips). At pushed `7e434330`, the same
   large-customer case passes in 449.6 ms and all 615 executed Phoenix methods
   pass. The workflow still fails under warnings-as-errors because four selected
   fixture/spec files need explicit discovery classification; two existing tests
   remain skipped. The four-path discovery repair passes eight isolated Mix
   checks with strict unknown-file and compiler-warning controls. No time limit
   was raised and the old failure's exact slow
   phase was not measured.
   Earlier 9a2bf16b Engine CI passes all three jobs. Provider, deployment, browser,
   customer/FieldLog and GA requirements remain pending. See
   [the workspace checkpoint](docs/hosted-customer-workspace-checkpoint.md),
   [cookie transport](docs/console-cookie-workspace-transport.md),
   [protocol helpers](docs/hosted-browser-auth-protocol.md),
   [independent review](docs/browser-auth-prerequisite-review.md) and
   [durable session contract](docs/hosted-browser-session-storage-contract.md).

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

The latest user-supplied AGENTS override pauses computer use, screen capture and
native simulator/emulator runtime tests until further notice. Continue source,
host tests, cross-compilation, offline review and authorized delivery. The earlier
resumption receipt remains historical. No native instance was started for this
HTTP checkpoint. When resumed, preserve the bounded one-instance-per-lane and
cleanup rules, including unrelated projects' instances, data and processes.

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
