# Implementation status

Development resumed at the user's October 25 request to continue PLAN.md. The
[saved handoff](docs/implementation-pause-2026-10-25.md) remains historical evidence.
Browser SQL, nine-migration integration, transaction-local JIT and trusted
configuration text validation now pass scoped independent development review;
the first pushed Phoenix run executes 615 passing methods but fails discovery
warnings. The four-path classification repair passes eight isolated Mix checks;
its next CI run stops earlier in storage setup. That fixture repair now passes
24 PostgreSQL 16 methods. Pure runtime constructors pass 30 producer and 25
independent methods with root acceptance. Pushed `4b458d6b` passes all Phoenix
CI steps, including storage/migrations and the broader hosted suite (645 passed,
two existing skips).
Native runtime and capture remain paused.
All eighteen work packages remain in scope:
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
| Swift runtime | Decode-plan reuse is integrated under unchanged limits. Four complete host contexts pass 2,314 named executions with nine inherited ignores each; the fresh live private suite passes 340 with zero ignores. | One corrected full attribution diagnostic reproduces the Corpus 1 cache-work failure at 23,358,291 instructions. Valid measurements show 61,142 repeated decodes and 53.907% of the work budget spent rebuilding previously decoded functions. Final consuming usage is zero and owned scratch is removed. The isolated segmented-LRU candidate regresses to 8,746,437 instructions under the same limit and is rejected for integration. Final consuming usage is zero, owned scratch is removed, and the failed result passes independent audit. Corpus 2 remains unrun. |
| iOS shared UI | Private pan input has simulator evidence. V7 Settings passes; first Tab fails actual focus traversal. All five run-cleanup checks pass and the owned simulator is deleted. | The corrected frozen V7 diagnostic join and fresh app/runner builds are accepted. The V8 runtime packet passes 16 producer and nine independent host methods. The fresh V8 simulator run passes Settings but fails first Tab, with zero skips and all five cleanup checks passed. The result audit and source lifecycle diagnosis are accepted; a passive lifecycle observer passes 116 producer and 371 independent Foundation checks. The first generic build failed Swift 6 actor isolation; the minimal correction now passes a fresh app/runner build and independent review. Corrected V9 runtime preparation passes 16 producer and nine independent host methods; root accepts preparation, with no new native execution. Shared UI/public routing remains incomplete. |
| Android shared UI | Private style/coordinator/input slices have scoped API37 emulator evidence. The latest integrated component fixture passes all 45 cases and 239 assertions; the separate pointer matrix passes 429 assertions. | Complete shared visual/interaction parity, public routing, resources/OS support, TalkBack and final physical comparison. |
| Hosted builds | Durable storage/coordinator components and registry/audit slices have host evidence. The isolated entry composition passes 922 groups; the defensive context-admission correction passes 79. | The broader entry review remains incomplete. Live Engine/entry composition, real worker/clock/provider operations, authentication, quotas and deployed schedule qualification remain pending. |
| Console | SolidJS Builds, Releases and Workspace use the website logo, colors and fonts. All 112 console host tests/typecheck/build pass; cookie transport and protocol prerequisites have independent review. | Implement durable sessions/provider login and connect live build/release/onboarding/billing workflows; browser visual and customer gates remain pending. |
| Hosted release/billing | Protected artifact upload/read/audit now has actual Phoenix Endpoint and PostgreSQL evidence: eight methods and 47 HTTP requests pass, with 32 transport tests and 46 combined independent controls. The earlier storage composition passes 97 methods and seven-migration checks. | Connect live console/customer sessions, complete tenant trust/lifecycle writers, distributed admission, Go migration parity, durable inbox/Oban reconciliation and selected-provider qualification. Frozen authority/inspector and rejected transport lanes remain unaccepted. |

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

The segmented-LRU retention candidate passes finite correctness/accounting review,
but its one original-harness full comparison regresses: CacheWork exhausts at
8,746,437 instructions, versus the current engine's 23,358,291, with all limits
unchanged. Root rejects it for integration. Validation and Initialize pass;
Corpus 1 fails and Corpus 2 is unrun. The original failure stays intact; final
consuming reservations, live counts and tickets are zero. Owned scratch and the
restored executable are removed (78,039,492 bytes); sealed preparation artifacts
are unchanged. The live VM is untouched and no rerun is selected. Independent
result audit confirms this rejection. See [the rejected candidate result](docs/swift-retention-runtime.md)
and [the audit](docs/swift-retention-runtime-review.md).

The second isolated retention candidate weights eviction by estimated rebuild
cost and age. It passes 49 finite cache methods but increases work in all six
fixed comparison traces; the phase-change case uses 31.717 times the baseline
work. Root rejects integration and does not select a full-target run. The pristine
baseline has 39 cache methods; three common comparison methods bring it to 42.
Both copies pass five generic unit and ten integration methods with matching
output. Independent audit verifies the raw results, source archives, preserved
intermediate failures and cleanup. Root verifies 94 retained bindings and the
unchanged 132-file live VM closure. Owned scratch removal reclaims 218,566,668
logical bytes. This is rejection evidence, not candidate correctness or full
workload acceptance. See [the review](docs/swift-cost-retention-candidate-review.md).

An adaptive recency/frequency proposal now has 17 passing model controls and
seven finite access sequences. It reduces model decodes on several traces but
increases phase-change misses and adds four credits to every resident hit.
Implementation selection is withheld; this is a model result, not a new VM
implementation or performance receipt. Root verifies all eight sealed members,
an exact model replay and the unchanged 132-file VM closure. See
[the proposal](docs/swift-adaptive-retention-design.md) and
[the root audit](verification/swift-adaptive-retention-root-review/acceptance.json).

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

The first pure customer permission policy passed 26 initial tests, but independent
review found an incomplete decision could be accepted without its policy callback.
The correction now passes 30 product tests and 23 independent probes, with
warnings-as-errors compilation. Root accepts this finite prerequisite. It requires server membership evidence and the exact
verified token scope for human artifact/audit actions.
The unavailable repository default prevents this prerequisite from becoming a public
authorization path. At that checkpoint, durable lookup, transaction/RLS/revocation
ordering and console integration remained pending. See [the policy](docs/hosted-customer-authorization.md) and
[the correction](docs/hosted-customer-authorization-correction.md) and
[the accepted review](docs/hosted-customer-authorization-correction-review.md).

The subsequent PostgreSQL adapter supplies current stored identity, credential,
membership and resource evidence to that pure policy. Twenty-five product tests
and seventeen independent probes pass on PostgreSQL 17.11. They cover scoped
FORCE RLS, six ordered revocation locks, tenant ancestry, bounded membership
reads, rollback, timeouts and restricted runtime roles. Independent review found
that predefined privileged roles were accepted; the correction rejects every
reachable reserved `pg_` role, including indirect membership. The exact shared
CI fixture helper and all five migrations pass focused apply, idempotence,
latest-two rollback and reapply checks after repairing migration policy
dependencies. The original failed attempts remain recorded and owned clusters
and scratch are removed.

This remains a read-only evidence prerequisite. It does not supply transaction-bound
domain authority, a fresh trusted-clock check immediately before an effect,
durable audit/idempotency or customer HTTP/console integration. The older pure Repository facade still
defaults to unavailable. The complete standard Phoenix CI suite, configured
with PostgreSQL 16 and including existing build-worker checks, passes at
checkpoint `d385adf3`. See
[the current scope](docs/hosted-customer-authorization-postgres-ci-integration.md)
and [the independent review](docs/hosted-customer-authorization-postgres-review.md).
Root acceptance verifies 656 retained bindings and 25 current inputs; see
[the acceptance receipt](verification/hosted-customer-authorization-postgres-root-acceptance/acceptance.json).

The subsequent transaction-owned facade now keeps authorization and local SQL
inside the same checked transaction. It binds the exact identity, action, target,
owner, connection, transaction and local settings; checks fresh time before
effects and finalization; and retains complete revision snapshots. Review fixed
a post-validation time gap and independently reproduced caught effect errors
that could commit prior writes. Corrected code rolls those writes back even
when the outer callback catches the error.

Eighteen product methods and twenty-one independent PostgreSQL methods pass.
The exact new CI fixture also passes all eighteen methods, and all six ordinary
migrations pass apply, idempotence, latest-three rollback and reapply. Root
verifies 424 retained files and 201 historical source copies; every owned test
cluster and scratch directory is removed. Full standard CI for that transaction
checkpoint passes at `9662eda1`. See [the review](docs/hosted-customer-authorized-transaction-review.md),
[the CI scope](verification/hosted-customer-authorized-transaction-ci/README.md)
and [root acceptance](verification/hosted-customer-authorized-transaction-root-acceptance/acceptance.json).

Protected artifact storage and staged metadata resolution, immutable v2 upload
audit, principal-bound retries and the internal customer application facade are
now accepted as local components. The corrected codec passes 39 producer and 49
combined independent methods; staged reads pass 63 producer/regression and 80
combined independent methods. Storage passes 19 producer and 22 independent
methods. The application facade passes 15 producer and 12 independent methods,
including actual commit failures that suppress upload receipts, private bytes and
audit results. Counts overlap and must not be added as distinct coverage.

The current-source combined CI fixture passes all 97 selected methods, and all
seven ordinary migrations pass apply, idempotence, latest-four rollback and
reapply. Root verifies 428 retained bindings and 45 current source bindings;
owned PostgreSQL instances and scratch are removed. At artifact checkpoint
`6fff5ab9`, the 132-file VM closure and 40 console bindings were unchanged. Earlier findings and failed attempts are
preserved, including the codec callback guard, SQL type and artifact/event
binding repairs, reserved-role matching and migration policy-drop ordering.
That storage checkpoint did not enable HTTP routes, deployment or live console data. The facade
uses one server-configured host/trust snapshot; tenant trust/lifecycle writers
and provider operations remain pending. See
[the integration scope](docs/hosted-customer-artifact-integration.md) and
[root acceptance](verification/hosted-customer-artifact-root-acceptance/attempt-2/acceptance.json).

The subsequent ordinary customer HTTP slice is accepted locally. Digest-bound
uploads pass 18 facade methods and 25 combined independent methods. Transport
passes 32 producer and 46 combined independent methods after review repaired
encoded/extra-slash route aliases. The actual production Endpoint, default bearer
verifier with synthetic TLS/JWKS, and restricted PostgreSQL transactions pass
eight methods and 47 real HTTP requests, with zero skips. Tests prove exact-byte
reads, authenticated HEAD with no wire body, revocation, tenant isolation,
idempotent retries and rollback after local writes. All owned listeners,
workers, PostgreSQL clusters and scratch are removed. Root verifies 244 retained
bindings and 56 current product inputs; console branding and VM sources are
unchanged. Counts overlap. Live console sessions/data, tenant trust/lifecycle,
distributed admission, provider deployment and full Go parity remain pending.
See [the HTTP checkpoint](docs/hosted-customer-artifact-http-checkpoint.md) and
[root acceptance](verification/hosted-customer-artifact-http-root-acceptance/attempt-2/acceptance.json).

## Customer workspace discovery and console composition

The authenticated workspace API and actual client are accepted locally through
production Endpoint/default verifier/default Repo. The console now routes
`/workspace` inside the website-branded shell and owns selection across routes.
Session changes synchronously hide stale rows and fence actions; pagination,
organization changes and disposal cancel obsolete work. All 100 console host
tests and the production build pass; 14 independent composition probes pass.
The four nested binding methods use the actual Solid reactive runtime and HTTP
client. Counts overlap. Review repaired an effect-order stale-state window and a
trailing-slash header mismatch. No browser/capture/native instance was started.

The cookie workspace adapter now uses fixed same-origin routes and shares the
bounded transport with the existing bearer client. All 112 console host tests,
type checking and production build pass. Browser-auth configuration, PKCE,
cookie, CSRF and callback primitives pass 39 selected host methods; independent
review passes 15 transport plus 15 protocol methods with no findings. Counts
remain separate. Selected protocol CI is wired. The mobile navigation adjustment
places the three route links below the website logo; visual verification is paused.

These are local components. The production entry still has no authenticated
session adapter and renders unavailable. The typed encrypted vault, configuration digest and closed stored-record decoder
now pass scoped host tests and independent review. Their producer suites pass
25, 20 (including 14 existing Config methods), and 11 methods respectively;
independent review passes 16 vault/digest plus 11 decoder groups. The SQL
lifecycle now passes 23 selected methods on PostgreSQL 16.15 and 17.11 after
review repaired NULL-scope admission and expiry after unique-key waits. Six
separate correction-review methods pass. The inert migration and all nine
ordinary migrations pass apply/rollback/reapply with independent review.
Browser Config text admission passes 26 producer and 32 combined independent
methods without changing valid digest bytes. Transaction-local JIT passes 86
selected PostgreSQL 16 methods and six independent controls with unchanged
deadlines and verified connection-setting restoration. Counts overlap. See
[the integrated component scope](docs/hosted-browser-session-integration.md).
Provider exchange/ID-token validation, runtime owner, routes, ingress and actual
login remain unimplemented or unqualified. The original storage contract defines 18 required cases;
its case count is not interchangeable with the new candidate test count. No launch gate is promoted. See
[cookie transport](docs/console-cookie-workspace-transport.md),
[protocol](docs/hosted-browser-auth-protocol.md),
[independent review](docs/browser-auth-prerequisite-review.md),
[session storage contract](docs/hosted-browser-session-storage-contract.md) and
[composition acceptance](verification/console-workspace-composition/root-acceptance/receipt.json).

The [browser runtime contract](docs/hosted-browser-lifecycle-runtime-contract.md)
passes eight producer and twelve independent structural checks after correcting
startup binding, existing PUBLIC-policy expectations, same-process trust-change
limits and first-slice preauth behavior. This accepts the implementation contract
only. Pure custody/runtime configuration now passes 30 producer and 25 independent
methods, zero failures/skips/exclusions. Root audited 51 source/dependency and
33 output bindings and cleanup. Exact constructor checks preserve supplied TLS,
separate all four roles, derive the fixed two-connection pool and disclose no
secrets. This proves neither live startup provenance nor secure external custody.
The existing URI HTTPS registry read is narrowly documented; drift fails closed.
Function/type catalog checks now pass 26 producer methods on PostgreSQL 17.11
and 20 independent methods on PostgreSQL 16.15. Root audited 14 source, 803
dependency and 49 output bindings and cleanup; selected warnings-as-errors
compilation passes. Three new PG17 probes now reproduce extra standalone
browser-type admission and unchecked ACL grantor drift. Both-version repairs
and explicit version-2 admission are underway; prior checks did not cover those
gaps. This is only `:function_surface_verified`: tests explicitly
show that missing relation/policy/grant admission remains a separate requirement.
No consumer, pool, Store or readiness wiring exists. The pure activation
preparation decoder passes 19 producer methods, 11 existing snapshot regressions
and 29 independent methods. Root audited 13 source and 38 output bindings and
actual Mix formatting. Its exact six-field result proves shape; the future owner
must compare the retained claim, current identity and current configuration.
The corrected relation contract passes 12 producer and 16 independent source
checks, with both incoming principal foreign keys included. Root verified 62
input, four read-only context and 99 output bindings. All 48 relation runtime
cases and forty owner runtime cases remain pending. PG16/17 representation
fixtures each pass 82 semantic checks and 23/24 actual mutation controls.
Independent review passes 427 main, 96 effect and 14 freeze/source assertions
with overlapping coverage. Root accepts this representation evidence; production
RelationCatalog implementation has started. The additive preparation SQL helper passes 39 PG17
and 38 independent PG16 methods. Review found unexpected PUBLIC grants could
survive provisioning; initial and final exact new-object ACL checks now reject
them, including third-party/default grants and grant options. Root accepts this
component after auditing 22 source, 803 dependency and 62 output bindings. No
migration, combined version-2 admission, caller or readiness is enabled. See [catalog review](docs/hosted-browser-catalog-surface-review.md),
[contract review](docs/hosted-browser-lifecycle-runtime-contract-review.md) and
[constructor acceptance](verification/hosted-browser-runtime-constructor-review/root-acceptance.json).

The [decoder review](docs/hosted-browser-activation-preparation-decoder-review.md)
and [relation contract review](docs/hosted-browser-relation-admission-contract-review.md)
record the accepted component scope and remaining owner/runtime work.

## Delivery and pending qualification

The corrected additive SQL component is pushed as `97d436b4`; all 780
committed paths and bytes were verified. Phoenix `40222180472` passes every
step; Engine `40222180507` remains running. No migration or caller is installed.

The decoder and corrected relation source contract are pushed as `0a6f110d`;
all 317 committed paths and bytes were verified. Phoenix `40221267196` passes
all workflow steps; Engine `40221267164` is still running. The preparation SQL
component is accepted locally after its ACL correction. See
[SQL review](docs/hosted-browser-activation-preparation-sql-review.md) and
[root acceptance](verification/hosted-browser-activation-preparation-acl-correction/root-acceptance.json).

The reviewed partial catalog prerequisite is pushed as `9d5c40ee`; 365 explicit
paths and remote main were verified. Phoenix `40219535335` passes selected
storage/migrations, then fails Mix formatting before broader tests: one extra
terminal newline in each new product module. Root corrected only terminal LF
bytes and reran the actual formatter, selected warnings-as-errors compile,
26 PostgreSQL 17 producer methods and 20 independent PostgreSQL 16 methods.
All pass, with cleanup. Corrected `6baf9acc` Phoenix `40220447677` passes
every step; Engine `40220447676` passes all three jobs. The preceding catalog Engine
`40219535273` passes all three jobs. See [correction](docs/hosted-browser-catalog-format-correction.md) and
[delivery](verification/github-delivery-browser-catalog/receipt.json).

The reviewed constructor slice and storage-fixture repair are pushed as
`4b458d6b`; all 490 explicit staged paths and remote main were verified. Phoenix
`40214597512` passes all workflow steps, including browser storage/migration
checks and the broader hosted suite: 645 methods pass and two existing methods
remain skipped. Engine `40214597602` passes all three jobs. The separate catalog source and
current decoder/relation lanes were excluded. See
[delivery](verification/github-delivery-browser-runtime-constructors/receipt.json).

The discovery repair and reviewed runtime contract are pushed as `4492bbc7`;
remote main matches. Phoenix `40212854925` failed in storage fixture setup: the
raw ordinary directory query reached its unchanged five-second statement limit,
so all 23 methods were invalid and migration/broader checks were not reached.
A local replay of the original fixture passes all 23 methods, so the precise CI
cause remains unproven. A paired plan exposes 455 JIT functions: 133.830 ms with
JIT versus 0.279 ms with transaction-local JIT disabled. The narrow raw-directory
fixture alignment now passes 24 PostgreSQL 16 methods with unchanged deadlines,
commit/SQL-error rollback restoration and owned-container cleanup. Root accepts
that fixture repair. Engine `40212854904` passes all three jobs. Constructor/catalog
implementations were excluded from that push. See
[fixture evidence](docs/hosted-browser-storage-ci-fixture.md) and
[delivery](verification/github-delivery-browser-discovery/receipt.json).

The resumed slice is committed and pushed as `7e434330` to `origin/main`; remote
main matches. Phoenix `40211210237` fails after all 615 executed methods pass
(two existing skips): four selected fixture/spec files produce discovery warnings
under warnings-as-errors. The former 121-project deadline case passes in
449.6 ms. New browser storage and migration CI checks also pass. The narrow
four-path discovery repair passes eight actual Mix checks while retaining fatal
unknown-file/compiler warnings. Engine `40211210222` passes all three jobs. See
[delivery](verification/github-delivery-browser-lifecycle/delivery-receipt.json). Previous checkpoint `1257cbf8` Phoenix CI fails the
same first 121-project workspace read at its unchanged transaction deadline:
608/609 methods pass with two existing skips. Its exact output is preserved in
[the resume receipt](verification/implementation-resume-2026-10-25/receipt.json).
Local JIT measurements support the scoped correction but do not prove that CI
failure's cause. No new native, provider, deployment, FieldLog or GA evidence
is claimed.

Checkpoint `684bd524` is pushed to `origin/main`; remote main matches. It adds
reviewed cookie/protocol prerequisites, the mobile navigation adjustment and
retained CI timeout diagnostics. Console `40206420996` and Engine `40206420988` pass. Phoenix
`40206421015` fails the first workspace read's total transaction deadline
(566/567 methods passed, two existing skips); the separate protocol step passes. See
[delivery](verification/github-delivery-browser-auth-prerequisites/delivery-receipt.json)
and [current CI](verification/github-ci-684bd524/observation-4/receipt.json).
Root accepts the component slice with 112 console, 39 protocol and 30 independent
host methods; counts overlap. Live login and the prior Phoenix timeout remain
open, and no GA gate advances.

Checkpoint `f2aba240` is pushed to `origin/main`; remote main matches. It adds the
reviewed branded workspace route/session fencing and the CI fixture repairs.
Console CI `40204405241` passes. Phoenix CI `40204405232` fails one
121-project directory deadline test; the earlier migration and expiry repairs
pass. Query-plan diagnosis is in progress. Engine CI `40204405509` now passes all three jobs with no skips. See [delivery](verification/github-delivery-workspace-composition/delivery-receipt.json)
and [exact-push observation](verification/github-ci-f2aba240/observation-5/receipt.json).
Live login/session adapter and the broader qualification gates remain pending.

Workspace checkpoint `9a2bf16b` is pushed to `origin/main`; remote main matches.
It contains the reviewed workspace API/storage, website-branded selector, actual
console client, CI wiring and retained evidence. The local slice is accepted;
Console CI `40202578691` passes. Phoenix CI `40202578720` failed because five
fixtures expected seven migrations and the expiry-lock fixture missed its timing
window; the workspace HTTP/client join itself passed. Fixture repair passes 24 local workspace methods and eight-migration controls;
broader Linux fixture execution now confirms those repairs. Engine CI `40202578667` passes all three jobs. See
[fixture repair](docs/hosted-workspace-ci-fixture-repair.md). See [delivery](verification/github-delivery-customer-workspace/delivery-receipt.json)
and [the exact-push observation](verification/github-ci-9a2bf16b/observation-5/receipt.json).

Prior checkpoint `6ed7df4f` repairs the cold bearer pipeline compile order.
Phoenix CI `40199934265` and Engine CI `40199934237` both pass with no skips.
See [the completed observation](verification/github-ci-6ed7df4f/observation-3/receipt.json).

Prior checkpoint `c0334a99` was pushed to `origin/main` and remote main was verified.
It contains the reviewed customer HTTP routes, canonical path/digest binding,
ordinary CI fixture and retained local evidence. Phoenix CI `40197780896` failed
at cold router compilation; Engine CI `40197780881` passes with no skips. The
checkpoint therefore was not accepted as a complete exact-push verification.
The compile-order repair uses compiler-aware dependency checks and passes 64 scoped host tests, including a
regression that reproduced the original failure. See
[the repair](docs/hosted-bearer-cold-compile.md) and
[local evidence](verification/hosted-bearer-cold-compile/acceptance.json). See
[the delivery receipt](verification/github-delivery-customer-artifact-http/delivery-receipt.json)
and [CI observation](verification/github-ci-c0334a99/observation-5/receipt.json).

Prior console checkpoint `c4e1f571` is pushed to `origin/main`.
It contains the two reviewed console color corrections and updated delivery
evidence. Console CI `40195410847` and Engine CI `40195410870` both pass with no skipped steps.
Local console tests, TypeScript and production build already pass. See
[the delivery receipt](verification/github-delivery-console-contrast/delivery-receipt.json)
and [completed CI observation](verification/github-ci-c4e1f571/observation-5/receipt.json).

Artifact checkpoint `6fff5ab9` is pushed to `origin/main` and remote main was
verified. Its 2,198 changed paths contain the reviewed local customer artifact
composition, CI fixtures, seven-migration integration and retained producer/review
evidence. Phoenix CI `40195108526` and Engine CI `40195108524` both pass with
no skipped steps. See
[the delivery receipt](verification/github-delivery-customer-artifacts/delivery-receipt.json)
and [completed CI observation](verification/github-ci-6fff5ab9/observation-7/receipt.json).

The final console brand audit found two faint secondary text colors. Both now
use the website's existing muted token, increasing measured caption/footer
contrast from 4.05/3.39 to 5.25/5.38. All 32 existing tests, TypeScript and the
production build pass; logo bytes, palette, typography and layout remain intact.
This is a source/host verification supplement. Saved desktop/mobile images
predate the two color changes; no new browser or screen capture was performed.
See [the contrast receipt](verification/console-brand-contrast/receipt.json).

Prior checkpoint `9662eda1` is pushed to `origin/main`.
Its 506 changed paths include the reviewed transaction facade and rollback
correction, ordinary CI fixture/migration wiring, proposed artifact contract,
unselected adaptive retention model and current evidence indices. Phoenix CI
`40190910760` and Engine CI `40190910724` both passed for this exact revision:
one Phoenix job and three Engine jobs, with no skipped steps.
See [the delivery receipt](verification/github-delivery-authorized-transaction/delivery-receipt.json)
and [completed CI observation](verification/github-ci-9662eda1/observation-1/receipt.json).

Previous checkpoint `d385adf3` is pushed to `origin/main`.
Its 802 changed paths include the reviewed PostgreSQL lookup, scoped CI fixture
and migration repair, independently audited finite cache rejection, and accurate
evidence indices. Phoenix CI `40188545250` passes one job and eight steps;
Engine CI `40188545375` passes all three jobs and 38 steps. No steps are skipped.
See [the delivery receipt](verification/github-delivery-postgres-authorization/delivery-receipt.json)
and [terminal CI observation](verification/github-ci-d385adf3/observation-3/receipt.json).

Earlier checkpoint `cb56d4b9` is pushed to `origin/main`.
Its 621 changed paths include the reviewed pure customer permission policy,
callback-result correction and independently audited rejected retention experiment.
The live VM is unchanged. Phoenix CI `40185739942` passes its job and all eight
steps; Engine CI `40185739959` passes all three jobs and all 38 steps. Neither has
skipped steps. See [the CI receipt](verification/github-ci-cb56d4b9/observation-1/receipt.json)
and [the delivery receipt](verification/github-delivery-retention-authorization/delivery-receipt.json).

The branded Builds checkpoint is pushed in `ba9ad437`, with Console and Engine CI
passing. Prior checkpoint `b375e55de` records the reviewed iOS compile
correction and runtime preparation, strict Swift telemetry correction and independently
audited full diagnostic failure. All 389 changed paths are pushed and remote main
matches; the active retention candidate is excluded. Engine CI `40182820548`
passes all three jobs and all 38 steps without skips. See [the delivery receipt](verification/github-delivery-diagnostic-corrections/delivery-receipt.json).
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
paths are not complete parity. The latest user-supplied AGENTS override pauses
computer use, capture and native simulator/emulator tests. This HTTP slice starts
no native instances. Phones remain disconnected and their matrix is deferred to
final acceptance. When runtime tests resume, use one owned instance per lane,
clean up after every run and preserve unrelated projects.

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
