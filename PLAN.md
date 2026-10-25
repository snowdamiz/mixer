# Execution index

The SolidJS Builds screen now shares the website’s exact identity and the existing release-screen shell. It shows per-platform build outcomes, attempts and source references, with expandable immutable inputs. Root accepts 32 repository tests, seven independent controls, 117 backend text-boundary comparisons and 14 actual browser states. Desktop and 320/375-pixel layouts, keyboard details/skip/select behavior, navigation and production preview exclusion pass. The initial text-boundary mismatch and 320-pixel preview-control overflow are corrected and preserved in evidence. Phoenix data/auth, real build workflows and full G22/GA qualification remain pending. See [the Builds checkpoint](docs/console-build-overview-checkpoint.md).

Checkpoint `50f70a79` passes Phoenix CI, including the disposable PostgreSQL host checks; all eight steps succeed and PostgreSQL/scratch cleanup is confirmed. Its Engine CI remains in progress. See `verification/github-ci-50f70a79-phoenix/receipt.json`.

Checkpoint `50f70a79` passes the Linux VM CI job after the test-only deadline fixture repair: 391 all-feature tests and 361 Swift-only tests pass in both Debug and Release. All 12 VM job steps succeed, including the previously skipped later checks. Services and Phoenix CI also pass; Swift CI is still running. The earlier `ccd8e4c3` three-test Linux setup failure remains preserved. See `verification/github-ci-50f70a79-vm/receipt.json` and `verification/github-ci-50f70a79-phoenix/receipt.json`.

The first hosted build-attempt lifecycle now has root acceptance as a pure Elixir component. Producer and root runs pass 21 tests; independent review passes the same 21 plus ten hostile controls. It preserves worker-completion uncertainty on cancellation/expiry, rejects stale scoped results, handles exact duplicate delivery and bounds infrastructure-only retries. Durable Phoenix/Ecto/Oban scheduling, real workers, artifact publication, signing, billing and full W12/GA remain pending. See [the lifecycle checkpoint](docs/hosted-build-lifecycle-checkpoint.md).

The private lifecycle test suite is now expanded from 23 to 49 identities and integrated without changing production engine bytes. All four Swift/all Debug/Release contexts pass (196 executions), six compiler-negative checks pass, and independent review passes 49 tests plus two controls over eight variants. Root verifies both packets and passes a fresh 49-test live replay at exact 132-file closure `64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de`. All owned build targets are removed. Every SL01-SL23 row remains partial; table mutation, the full reactor, public/signed/native entry, FieldLog and GA remain pending. See [the test checkpoint](docs/swift-reactor-lifecycle-remaining-checkpoint.md).

The keyboard full-case V3 harness now has root source/host acceptance: 69 producer methods, 45 independent methods and 24 import-alias controls pass. The review verifies all three earlier findings are repaired, including temporary-workspace cleanup after partial allocation. The generic runner compiles successfully once, and root verifies the restored source tree and complete product archive after preserving an initial recorder failure on four Xcode-generated empty directories. The post-build adapter is in preparation; native execution is not yet selected and all six app keyboard cases remain unrun. See [the independent review](docs/apple-toggle-keyboard-full-case-independent-review-v3.md) and `verification/apple-toggle-keyboard-full-case-root-review/v3-source/acceptance.json`.

Checkpoints `384e22ac` and `86ab91eb` pass all three Engine CI jobs, with all 38 steps successful and none skipped in each run. See `verification/github-ci-384e22ac-engine/receipt.json`, `verification/github-ci-86ab91eb-engine/receipt.json` and `verification/github-delivery-86ab91eb/delivery.json`.

Checkpoint `67d6d045` passes Console CI (typecheck, 17 tests and production build)
and all three Engine jobs, with all 38 steps successful. The earlier `c628863f`
Engine checkpoint also passes. See `verification/github-ci-67d6d045-console/receipt.json`,
`verification/github-ci-67d6d045-engine/receipt.json` and
`verification/github-ci-c628863f-engine/receipt.json`.

The builder repair at `2335207a` now passes all three Engine CI jobs: Swift, VM
and services, with no skipped steps. Its finite 16-MiB source-file cap preserves
the 64-MiB aggregate and all runtime budgets. The earlier 52 builder test
executions, fresh archive and three C consumers also pass. See
[the repair evidence](docs/capability-builder-source-bound-repair.md) and
`verification/github-ci-2335207a-engine/receipt.json`.
The subsequent source/diagnostic checkpoint `fdf59652` also passes all three
Engine CI jobs, with no skipped steps. See
`verification/github-ci-fdf59652-engine/receipt.json`.
Checkpoint `06147f0e` also passes all three Engine jobs, with all 38 returned
steps successful and none skipped. See `verification/github-ci-06147f0e-engine/receipt.json`.

The private Swift lifecycle V3 candidate now has root acceptance for its selected host matrix: all 30 rows pass, comprising 1,602 test executions and four compile checks. The four focused contexts pass 23 lifecycle tests each; Swift and all-feature libraries, Frozen regressions and both qualified Node oracle runs also pass. Root verifies all 978 sealed files and all 30 target cleanups. V2’s failed ticket assertion remains preserved; V3 changes its expectation to match retained decoded-cache ownership without changing engine limits. The exact three-file private implementation is now integrated: the full 132-file VM source closure matches the tested candidate, and 23 focused live tests plus Swift-only Clippy pass. Its fresh target is removed. The complete SL matrix, guest table mutation, real full reactor, native execution, FieldLog and GA remain pending. See
`verification/swift-reactor-lifecycle-runtime-v3/runtime-receipt.json` and
`verification/swift-reactor-lifecycle-runtime-v3-root-review/live-integration-acceptance.json` and
[the integration checkpoint](docs/swift-reactor-lifecycle-v3-integration.md).

V9 repairs the diagnostic harness commit boundary: after durable evidence publication, cleanup errors preserve the acknowledgement and live cursor while unresolved retirement blocks new work and setup credit. Producer checks pass 21 Session methods, 20 persistence methods covering 68 actual HTTP controls, 71 resolver checks and 16/35 transport checks. Independent and root review now accept the selected host persistence contract after 72 controls and 1,546 actual HTTP requests. The selected iOS 26.5 simulator setup diagnostic now passes its one official XCTest method, with complete durable settings evidence and matching offline replay. All five cleanup operations pass, and the owned simulator/workspace are absent. The expected diagnostic-only outer exit and duplicate attachment-export reporting failure are preserved; the six app keyboard cases remain unrun. The V7/V8 persistence failures and prior iOS 26.5 setup failure remain preserved. See [the setup diagnostic](docs/apple-toggle-keyboard-focus-v9-runtime.md) and
`verification/apple-toggle-keyboard-focus-v9-root-review/runtime-review.json`.

The V6 host ordering repair passes independent review: 269 existing Python
methods, ten fresh methods over 15 route/time boundaries and 16 + 35 reused
Swift host checks. It rejects the unchanged V5 stale-capture journal. All three
actual V6 destination captures follow their completed taps. The app, native
runner and bounds remain fixed; the subsequent switch setup failure above is
separate. See `verification/apple-toggle-keyboard-focus-v6-independent-review/review.json`.

The Linux resource prerequisite probe now confirms Elixir 1.20.4, OTP 29.1.1,
ERTS 17.1 and the pinned runtime image under the selected isolation. That image
has no C compiler, linker, binary-inspection tools or required system headers;
no helper/NIF compilation or resource row ran in that earlier probe. The owned
container and temporary inputs were removed. Both earlier pre-start failures
remain preserved. The later compiler qualification below supersedes the missing
compiler prerequisite; all 30 resource runtime rows remain pending. See
`verification/stripe-webhook-resource-ingress-root-review/linux-tool-payload-v3-review/receipt.json`.

The private Linux compiler prerequisite now has root acceptance. The C6 V4 attempt compiles the unchanged helper and NIF twice, retains four AArch64 products totaling 288,864 bytes, and passes both native byte comparisons plus exported hash, dependency and GNU-version checks. All 46 host controls pass; root verifies 118 execution bindings, 27 command outputs, actual isolation and successful container/snapshot cleanup. V4 changes only fixed tar product-export transport. The earlier image, archive-name and export failures remain preserved. This qualifies the reviewed /opt compiler invocation only. The resource controller’s /usr/bin/cc integration, helper execution, NIF loading, BEAM execution and all 30 resource runtime rows remain pending. See
`verification/stripe-webhook-resource-ingress-root-review/linux-compiler-assembly-review/receipt.json` and
[the compiler checkpoint](docs/stripe-resource-linux-compiler-checkpoint.md) and
`verification/stripe-webhook-resource-ingress-root-review/linux-compiler-qualification-v4-review/runtime-acceptance.json`.

Latest native checkpoint: the private iOS pan-commit carrier passes 43 XCTest
methods, 45 native input actions and 36 scoped callback components on iOS 26.5.
Root replays 1,286 verdict predicates and 324 touch-origin checks. All five cleanup
operations pass; the owned simulator and temporary workspace are absent. The
first failed run and four original plain-UIKit reference failures remain recorded.
Keyboard/focus, remaining lifecycle cases, compositor parity and live Apple
integration are pending. Android authored V2 toggle input remains integrated at
`a490761`; no GA or dogfood gate passes.
See [the native checkpoint](docs/apple-toggle-pan-commit-runtime-checkpoint.md).

The first SolidJS release-check view now matches the website’s exact Flick/logo assets, effective cream-and-orange palette and typography. Seventeen repository tests and six independent compiled-view tests pass, alongside strict application typechecking and production builds. Browser checks cover six reactive states, production preview exclusion, skip-link focus and a 375-pixel layout without overflow. This is a local display slice; Phoenix API/auth, full hosted-build workflows and Cloudflare deployment remain pending. No GA or dogfood gate passes. See
[the console view checkpoint](docs/console-release-check-view.md).

Implementation resumed at the user's request on October 24. The saved
[pause handoff](docs/implementation-pause-2026-10-24.md) remains historical context.
The private frame entry/return/cleanup slice and bounded hosted RS256 token
verifier have root host acceptance. The user has also resumed computer use,
screen capture and simulator/emulator runtime tests. The full product scope
and all GA gates remain open.

The complete specification is [mixer-product-plan.md](mixer-product-plan.md).
All W01–W18 packages, G01–G38 launch gates, and D0–D8 dogfood milestones remain
in scope. No internal slice substitutes for those completion requirements.

The October 24 hosted-stack decision fixes Elixir/OTP + Phoenix + Plug/Bandit
for the REST API and orchestration, Ecto/Postgrex + Oban on Neon PostgreSQL for
durable jobs, Cloudflare Containers for the API, Workers/R2/CDN for suitable
edge/delivery workloads, SolidJS + TypeScript + Vite + Solid Router for the
console on Workers Static Assets, and Stripe Billing/Checkout/Customer Portal.
See product-plan sections 13.2–13.5, 14, 17 and 31. Cloudflare Oban processor
liveness and Android build resources/isolation require qualification; macOS
builds and isolated signing retain necessary hosting exceptions. Use direct
Neon TLS connections initially, with bounded pools and production scale-to-zero
disabled; qualify Oban notifications, retries and recovery. Current Go services
remain reference/compatibility work pending an explicit Phoenix migration.
This documentation decision implements no hosted migration or deployment and
passes no gate. W11/W12/W14/W16 retain the new deliverables and pending checks;
see `verification/hosted-stack-plan-update-2026-10-24/receipt.json`.

The first Phoenix foundation is implemented under `hosted/`: pinned framework
packages, explicit API/processor roles, direct verified-TLS database settings,
bounded pools/queues, liveness-only HTTP and Oban schema migration. Eight actual
host tests and packaged release startup rejection pass; identity, domain release
routes and selected-cloud qualification remain open. See
`docs/phoenix-foundation.md` and `verification/phoenix-foundation/candidate-5/receipt.json`.
The coordinated next identity/artifact seam is documented in
`docs/hosted-identity-contract.md`; its declaration tests are not authentication.
The hosted artifact CBOR encoder now matches the existing v3 manifest,
assignment, signature-preimage and grant-descriptor vectors. Eleven new tests,
35 full hosted tests, two Go vector tests and packaged release checks pass in
an isolated accepted-source snapshot. See `docs/hosted-artifact-cbor.md` and
`verification/hosted-artifact-cbor/acceptance.json`. This supplies encoding only;
signed artifact admission, authenticated routes, membership and persistence
remain pending. Commit `68910a1` now passes Linux hosted CI with the same 35
tests and release checks; root verifies all 32 committed hosted/fixture inputs
in `verification/github-ci-68910a1-phoenix/receipt.json`. The same checkpoint
also passes the Swift, VM and Go service engine jobs; terminal step observations
are retained in `verification/github-ci-68910a1-engine/receipt.json`.
Recent hosted CI at 4546513 and b15ff7a passes Swift, VM and Go service jobs,
resolving the prior milestone busy-admission revalidation. No GA gate is closed.

The configured key-owner and signed artifact-admission components now have
root acceptance after independent review and a composed 73-pass host run. The
artifact overlay is applied exactly; existing v3 bytes and signed authority
remain unchanged. At that component checkpoint, application wiring, authenticated HTTP and current
database membership remained pending; startup integration is recorded below. See `docs/hosted-identity-artifact-checkpoint.md`
and `verification/hosted-component-integration-root-review/acceptance.json`.
The `dd604eca` engine jobs all pass. Its Phoenix CI exposed a platform-specific
temporary directory in a test fixture. The portable fixture and isolated test
measurement outputs now pass root host/Linux review; production identity code
is unchanged. See `verification/hosted-tls-fixture-ci-root-review/acceptance.json`;
the exact pushed repair `b0629cf5` now passes Linux hosted CI with 73 tests,
one explicit namespace skip, release checks and eight run-local metrics. See
`verification/github-ci-b0629cf5-phoenix/receipt.json`. Its Swift, VM and Go
engine jobs also pass: `verification/github-ci-b0629cf5-engine/receipt.json`.
The actual Ecto/Postgrex transaction boundary has a selected
preimplementation seam after 24 disposable PostgreSQL cases; protected checkout
must use `queue: false` because the pinned driver's transaction deadline does
not bound queued checkout. See
`verification/hosted-transaction-context-root-review/selection.json`. Membership,
repository, audit/idempotency atomicity and HTTP integration remain unimplemented.
The narrow atomic SQL writer, fixed audit/state encodings and bounded local blob
fixture now have independent mechanics review, with seven mandatory correction
groups selected in `docs/hosted-atomic-storage-corrections.md`. The corrected
isolated specimen passes 73 cases and 269 retained bindings. Independent review
passes the original suite but preserves two failures among 83 adversarial cases:
valid PostgreSQL control-character display bytes disagree with the Elixir
formatter. Root selected a focused formatter correction; repository acceptance
and migration remain pending. See `docs/hosted-atomic-storage-correction-review.md`
and `docs/hosted-atomic-display-correction-contract.md`.
Configured identity startup is now integrated after the independently reproduced
endpoint newline defect was corrected. The corrected source passes 95 Linux
tests, 31 independent focused cases and 93 root host tests with two explicit
Linux-only skips; release and cleanup checks pass. See
`docs/hosted-identity-startup-checkpoint.md`. Authenticated HTTP and current
database authority remain pending. The isolated schema/resolver prerequisite
passes 128 cases, but independent review reproduced three catalog-completeness
gaps across five drift cases. Root selects trigger/constraint/index enforcement,
relation persistence and effective parameter privileges/defaults corrections in
`docs/hosted-authority-schema-corrections.md`; final contract acceptance is pending.
The startup checkpoint `4250e05a` now passes Linux hosted CI: 93 tests, two
explicit network-namespace skips, release checks and ten run-local metrics;
all 62 archived inputs match the pushed commit. Its Swift, VM and Go engine
jobs also pass.
The preceding Swift control checkpoint `e58e84ca` passes all three engine jobs.
See `verification/github-ci-4250e05a-phoenix/receipt.json`,
`verification/github-ci-4250e05a-engine/receipt.json` and
`verification/github-ci-e58e84ca-engine/receipt.json`.

The private Swift control candidate 2 now has root source/accounting preflight
acceptance after fresh independent MIR, eight layout configurations and unchanged
Frozen expansion checks. See
`verification/swift-control-invocation-root-review/candidate-2-acceptance.json`.
SC01–SC12 private behavior now has independent and root host acceptance, and the
exact overlay is integrated. Four-mode control/Frozen tests, seven independent
adversarial groups, full libraries and eight layouts pass; root also verifies
669 bindings and 52 integrated Release tests. See
`verification/swift-control-behavior-root-review/acceptance.json`. Memory helpers,
full dispatch, Ready and public invocation remain next required implementation.
Root now accepts the isolated Load/Store type, borrow and logical-accounting
prerequisite after 454 bindings, eight fresh independent library checks, sixteen
paired metadata layouts and 39 unchanged Frozen methods. All sixteen behavior
groups remain pending; a new isolated lane is implementing caller failure handling
and executing that matrix. The live VM is unchanged. See
`docs/swift-memory-helper-acceptance.md`.

Section 8.3 requires the same shared app design on iOS and Android. Shared theme
values control layout, typography scale, colors, iconography, spacing and component
appearance; platform-specific app appearance requires an explicit declaration.
Native accessibility, navigation, text input and system-owned surfaces retain their
platform behavior. The existing adapters do not yet satisfy this appearance
contract. W03/W04/W05 must coordinate its shared schema and renderer changes;
Simulator/emulator reference-screen review is sufficient for development
acceptance. W17/G06 physical reference-screen review moves to final acceptance
under the user's October 23 instruction. See
`verification/ui-design-parity-plan-update/receipt.json`.

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
and inspect remote/CI state after publication. Use an explicit owned-path allowlist
and Git's path-limited commit index; the shared index may contain another chat's
staged work. Inspect the resulting commit paths before pushing. Failed or unavailable checks stay
explicit in the status and receipts. This code-delivery authorization does not
authorize production deployments, store submissions or messages to customers.

The user accepts iOS simulator and Android emulator tests as sufficient for
development acceptance and advancing dependent work. Use them for native UI,
interaction, visual parity and runtime integration now. Physical phones are
disconnected; defer their validation matrix to final acceptance and correct any
differences then. Missing phone receipts do not block development slices.
Preserve completed receipts, record each actual environment, and keep final
hardware checks pending; do not retry phones or request reconnection. This changes
test sequencing, not the shared-design contract or untested external launch gates.
See `verification/simulator-development-policy/receipt.json`.

The user fixed the iOS baseline at **iOS 26.0**, covering iOS 26, iOS 27 and
subsequent releases. Package and generated/native build defaults use 26.0.
Nine package manifests, 19 CLI tests and an actual generated app cross-build pass;
both the app Info.plist and Mach-O declare 26.0. Evidence is retained in
`verification/ios26-baseline/candidate-1/receipt.json`.
The private appearance prototype still admits only its exercised
iOS 26.5 runtime; broader version qualification remains pending, and historical
iOS17 compile receipts are retained as historical evidence. See product-plan
section19.1.

The user resumed computer use and screen capture on October 24 and separately
confirmed resuming simulator/emulator runtime tests. Reuse existing test instances,
keep normally one active instance per native lane, and shut down disposable
instances after collecting evidence, including failed runs. Preserve unrelated
projects and keep physical-phone qualification deferred. Prior native checks
remain pending until actually rerun against their current source. See
`verification/native-testing-resume-2026-10-24/receipt.json`; the earlier
`verification/computer-use-pause-2026-10-24/receipt.json` remains historical evidence.

Current Android checkpoint: private style consumption, staged JNI ownership and
generated-app staging exports are implemented. Current source passes Java/DEX,
host JNI and generated Swift tests, plus an inspected unsigned arm64 API28 APK
build and deliberate missing-export rejection. Root evidence is in
`verification/android-native-appearance-v2/root-headless-acceptance.json` and
`verification/android-generated-v2-bridge/acceptance.json`. Fresh API37 candidate16
now qualifies the private Android Section/baseline repairs with 570 main, 120 first-
baseline, 120 last-baseline and 14 inset assertions plus five rejection installations.
See `verification/android-native-appearance-v2/candidate-16-root-review/acceptance.json`
and `docs/android-native-resume-2026-10-24.md`; the owned emulator is stopped.
Apple pressed-switch/native qualification is underway. Continue coordinator/runtime
implementation in parallel. Public application paths remain V1, and no GA or
dogfood gate is passed.

The Apple private consumer has scoped headless acceptance at
`verification/apple-native-v2-root-review/acceptance.json`: exact final snapped
placements are shared by detached validation and attachment, eight production
CoreGraphics math checks pass, and the iOS17 consumer/harness compiles. Current
native paint/input/RTL qualification remains pending. The ordinary Android
coordinator now has host/cross-build acceptance under
`verification/android-native-v2-coordinator-root-review/acceptance.json`:
133 scenarios/2,087 checks replay the SDK-produced class with test-only leaves.
Generated source export now passes snapshot/lock tests, tamper rejection and a
fresh unsigned arm64/API28 APK cross-build; root inspects its DEX/native exports
at `verification/android-coordinator-generated-export/root-acceptance.json`.
Joined native execution, public Activity opt-in and signed integration remain
pending.

The W08 control-helper extraction stopped at its accounting prerequisite:
the proposed fallible adapters add at least 1,176 bytes of named result-transfer
storage, exceeding the entire 512-byte scalar allowance by 664 bytes before
other roles. That rejected attempt preserved all 116 VM source files. Root retained the rejected
proposal and four isolated compiler probes at
`verification/swift-control-extraction/root-rejection.json`. A smaller private
literal macro has separate implementation authorization at
`verification/swift-control-macro-extraction/root-freeze.json` after exact compiler
expansion, unchanged layout/formula and privacy checks. That extraction now has
host implementation acceptance at
`verification/swift-control-macro-root-review/acceptance.json`: 795 matching
baseline/candidate control observations per four configurations, independent
review of 44 binaries, and root replay of eight public/private host tests.
The complete private active-frame entry/return/unwind ownership contract now has
root acceptance at `verification/swift-active-frame-contract-root-review/acceptance.json`.
The amended original-owner declarations pass 81 compiler/layout/privacy commands,
two independent fresh compilations, and sixteen root metadata replays. Entry,
return, retained multiple-pin cleanup and both owner barriers now have root host
acceptance at `verification/swift-active-frames-root-review/acceptance.json`: 904
producer executions, 682 independent candidate executions, 40 adversarial probes,
eight producer layouts and two independent fresh layouts. Root reviewed the
actual methods and verified 2,148 source/evidence bindings, including the exact
229-command reuse lineage. No historical candidate result substitutes for the
final frozen source. Broad Clippy retains its 26 baseline diagnostics.
Swift control invocation, dispatch, memory and host integration remain incomplete.

The separate Swift milestone CI test failure has a bounded test-only busy retry;
production admission and health behavior are unchanged. Debug/Release/TSan
qualification passes the eight-test fixture in each mode and controlled overlap,
error-propagation and deadline cases. Root source/evidence acceptance is recorded
at `verification/cold-start-milestone-ci-repair/root-acceptance.json`; hosted
revalidation remains pending. Completed contract and CI-repair compiler scratch
was removed after checking for open files, while preserving source archives and
qualifying evidence. No native testing was resumed.

W11/W16 configuration ownership repair: the release server snapshots caller-owned
tokens, trust roots and registered hosts before validation. Public v1/v2/v3 and
race regressions plus independent review pass; root source/evidence acceptance is
at `verification/release-config-ownership/root-acceptance.json`. This closes the
constructor alias defect while hosted identity, delivery and operational
qualification remain open.

The private Android host binding is now accepted within its recorded host scope;
see `verification/android-binding-stage4-root-review/acceptance.json`. Root
verified 4,149 acceptance bindings after independent review of 3,182 files and
nine additional lifecycle replays. A fresh-source CI runner passes 39 ordinary
scenarios per Debug/Release/TSan, with 15 provenance/CI regressions per normal and
optimized Python. The full original dynamic matrix is still incomplete: S4-21
native event delivery and S4-29 optimized Release lifetime-counter injection are
pending. Hosted pinned Swift 6.2.4 now passes all 39 ordinary cases per mode;
root matched 579 Git-input/log hashes in the retained CI artifact. See
`verification/github-ci-61c5c8b/receipt.json`. That checkpoint failed the separate
VM lint check described below.
The separate JNI/Java ownership and verification design now has root acceptance;
see `docs/android-jni-stage5-seams.md` and
`verification/android-jni-stage5-root-review/acceptance.json`. Eleven declaration
and audit commands pass, with 81 exact input/artifact bindings. All 50 native,
visual and external implementation cases remain pending. Implementation proceeds
through the shared appearance foundation, closed native Swift backend, Java
signed subset, actual JNI, and native observation before signed-core composition.
Host receipts and declaration compilation grant no native authority.

The data-only SDK native packet encoder and shared validator frontier repair now
have root acceptance after independent replay; see
`verification/ui-native-packet-root-review/acceptance.json`. The exact candidate
passes 51 SDK tests per Debug/Release, 16 production-Java decoder assertions,
three public Swift/Java event round trips and official iOS/Android module builds.
The validator admits node count/depth before queuing children. The encoder emits
one identity record per node from the same immutable snapshot and measures all
escaped bytes before allocating the bounded output buffer. Both ordinary Android
engines now adopt it with transactional error preservation; nine tests per mode,
34 Java contract checks, two public consumers and an actual Android shared-library
build pass. See `verification/ui-native-packet-android/candidate-2/receipt.json`.
Native JNI/rendering and shared appearance remain separate.

The shared appearance foundation implementation now has independent and root
acceptance in `verification/ui-appearance-foundation-root-review/acceptance.json`:
closed raw values and canonical codec, one 1,906-byte default, and checked metrics.
All 66 SDK tests pass per Debug/Release; an independent 5,153-case corpus and
2,507,093 assertions pass per mode. iOS and official Android modules compile.
This qualifies pure data only. The private Java reader now passes independent review and root acceptance after
7,990 independent cases across Java and Swift; 89 exact bindings are checked in
`verification/android-appearance-descriptor-root-review/acceptance.json`. There is
no Java default theme table. Shared per-node style resolution now has independent
and root acceptance as pure data: all 86 SDK tests and 29,278 independent cases
with 350,077 assertions pass per Debug/Release. Root verifies 224 bindings in
`verification/ui-appearance-resolution-root-review/acceptance.json`. The plan
resolves all ten current kinds, inherited disabled state, explicit canvas paint,
logical RTL metrics and bounded text-scale floors. Native consumption remains
pending. Java resolution now has independent and root acceptance: 183 exact
bindings cover the producer and independent Swift/Java corpora, immutable graph
checks and direct environment bounds. See
`verification/android-appearance-resolution-root-review/acceptance.json`.
This is pure data; the provisional recipe still differs from the iOS reference. The unchanged Apple reference now has 24 measured captures and scoped root
acceptance in `verification/apple-appearance-measurement-root-review/acceptance.json`.
Root verifies 385 bindings and independently decodes every PNG using Apple ImageIO: all
16 historical and 12 Debug/Release comparisons match exactly. Per-role accessibility
profiles and contextual font probes now have separate scoped acceptance: 12
public semantic font tables agree between Debug and Release, and all 18 candidate
and nonperturbation PNGs are byte-identical to the existing reference. Root checks
571 bindings in `verification/apple-appearance-font-profile-root-review/acceptance.json`.
The proposed Android preference mapping is not accepted; unsupported accessibility
requests must not silently clamp. Shape and spacing measurements now have scoped root acceptance: 260 bindings,
12 parent PNGs identical byte for byte and independent curve-residual calculations.
See `verification/apple-appearance-shape-root-review/acceptance.json`. Authored
curve candidates remain distinct from native-exact shapes. The SDK now implements
the twelve coordinated text profiles and a nearest-anchor policy that rejects
unsupported sizes. All 89 SDK tests pass per Debug/Release; 72 public role metrics
match retained measurements, 3,502 selection outcomes pass per mode, and public
iOS/Android modules compile. See `verification/ui-shared-text-profiles/acceptance.json`.
The separate measuredShared2 V2 implementation contract is now frozen with
92 root bindings and13 executable design checks per normal/optimized mode.
The first implementation slice supplies closed group/switch geometry and bounded
density conversion. All94 SDK tests pass per Debug/Release;1,058 public outputs
per mode match the frozen contract, and iOS/officialAndroid modules compile.
See `verification/ui-measured-appearance-v2-root-review/acceptance.json` and
`verification/ui-appearance-geometry-v2/acceptance.json` (148 bindings). V1 remains
unchanged. The Swift V2 codec now passes106 SDK tests per mode and an independent
5,584-case corpus (973 accepted/4,611 rejected), with exact canonical roundtrips.
Public constructors and iOS/officialAndroid modules compile; see
`verification/ui-appearance-descriptor-v2-root-review/acceptance.json`. Android
V2 reader and geometry now have scoped root acceptance with 387 bindings.
Independent review executes 6,165 descriptors, 100,989 Java geometry cases
(100,976 representable Swift cases), parser/ownership checks and exact complete
65,535/65,536/65,537-byte boundaries across both JVM and Swift modes. No Java
default theme is maintained. See
`verification/android-appearance-v2-root-review/acceptance.json`.
The Swift V2 identity/recipe/style resolver now has root acceptance with 654
bindings, 127 SDK tests per Debug/Release and 133 independent cases per build.
The independent oracle detects all six deliberate semantic faults, including lost
disabled inheritance, profile collapse and alpha loss. See
`verification/ui-appearance-resolution-v2-root-review/acceptance.json`.
Android V2 resolution now has root acceptance with 2,143 bindings. Actual Swift
Debug/Release and JVM default/interpreted outputs agree across 185 cases;
independent review passes 6,279 assertions per JVM mode and detects eight
semantic mutants. All twelve Java application sources compile through D8
minimum API28. See `verification/android-v2-resolver-root-review/acceptance.json`.
Closed native drawing
primitives now have root acceptance with 195 bindings: actual macOS CoreGraphics
checks, 131 SDK tests per Debug/Release, iOS17 compilation and 5,610 Android
API37 emulator checks across 45 paths. See
`verification/native-appearance-paths-v2-root-review/acceptance.json`.
Full native consumers, resource/bootstrap support, signed V2
installation, interaction and physical design parity remain pending.
Hosted `df97e3f` and `82d520c` pass all three configured jobs; the latter also has
an isolated Java-to-DEX compile receipt in
`verification/android-appearance-v2-root-review/dex-compile/receipt.json`. These
precede the bridge repair and do not qualify its later publication change.

Eight unchanged iOS simulator screenshots are retained in
`verification/apple-appearance-reference/gallery.html`; root accepts the baseline
reference in `verification/apple-appearance-reference-root-review/acceptance.json`.
The provisional candidate recipe differs in navigation titles, section headers,
toggle color and grouped-list geometry. It is not accepted as a match to that
reference. Final shared native recipes must follow the iOS app design on both
platforms. Native styling/resource packaging/private signed capture and physical
side-by-side parity remain pending; Android defaults are not a substitute.

The private Swift cache candidate3 now has independent and root acceptance;
see `verification/swift-function-cache-root-review/acceptance.json` and
`docs/swift-cache-candidate3-acceptance.md`. Root verifies 823 exact bindings,
including separately reconstructed measurement-only test overlays. All 18 named
functions pass in Debug and Release. The missing assertions now cover 21 explicit
terminal latches and 315 repeated no-effect routes per mode, plus three actual
constructor owner-exhaustion failures with isolated counters and partial cleanup.
These synthetic latch tests do not establish natural executor failure origins.
Measured authored-value construction accounting rises by 96 to 57,224 bytes;
other phase bounds remain unchanged. Physical stack/RSS is outside that model.
The private compiling executor type/lifetime/layout prerequisite now has root
acceptance after a separately reviewed final foundation correction. Root checks
2,102 bindings in `verification/swift-executor-layout-root-review/acceptance.json`.
The additional 864-byte final allowance raises foundation admission to 17,368;
stored owner layouts and existing cache additional envelopes remain unchanged.
Six feature combinations pass in Debug/Release; all-features runs pass 350 tests
per mode with nine preexisting ignored tests. Actual executor algorithms and the
exact full-target runner still need separate acceptance. No full target is run.
All three hosted jobs at `01d8491` pass; see
`verification/github-ci-01d8491/receipt.json`. The packet checkpoint
`09dac10` and ordinary Android checkpoint `958998d` also pass all three jobs.
See `verification/github-ci-958998d/receipt.json`. Cache checkpoint `d814055` passes VM/services,
but its Swift bridge test failed to observe a timer tick after a fixed 35ms sleep.
A test-only bounded observed-tick wait now passes all48 bridge tests per Debug,
Release and SwiftTSan, plus old/fixed controlled real-queue probes in both modes.
See `verification/guest-ui-polling-ci-repair/acceptance.json` and `verification/github-ci-d814055/receipt.json`. The exact
hosted scheduling cause is not established. Hosted checkpoint `0f177ad` now
passes all three jobs, including the repaired bridge test; see
`verification/github-ci-0f177ad/receipt.json`. The separately accepted final
foundation allowance accounts those borrows and locals explicitly; historical
cache receipts remain bound to their original source.

The private Uninitialized constructor and zero-frame cleanup now have root
acceptance with 927 exact bindings. Its deferred failure tail retains original
authority through caller return storage. Independent review checks 615 typed
classes, 5,004 named positions and eight layout configurations. Fresh isolated
product builds pass 366 full host tests per Debug/Release, with nine ignored;
434 independent derived library/probe executions are separately scoped.
The production foundation is now 267,800 bytes, additional construction 1,062,312
and the same execution header 207,352, all logical reservations. Historical
candidate2 cwd, candidate3 Clippy and candidate4 shared-target contamination
failures remain preserved. Candidate4's 367-test claims are invalidated by the
fresh 366-test receipt. See `docs/swift-executor-construction-acceptance.md` and
`verification/swift-executor-construction-root-review/acceptance.json`.
Shared interpreter algorithms, active-frame unwind/growth and exact bounded
full-target execution remain next; no Ready reactor or GA gate is accepted.
The static execution seam now has a scoped type/borrow freeze with 149 root
bindings, fourteen binding/layout probes, two frozen-layout comparisons and
three compiler-rejected invalid borrow variants. All 41 frozen layout lines
match. See `docs/swift-shared-executor-algorithm-contract.md` and
`verification/swift-shared-executor-algorithm-contract/root-acceptance.json`.
Only the compiled subset is accepted; later adapter bodies and simultaneous
accounting remain pending. The first narrow primitive-dispatch extraction now
has root acceptance with 360 bindings. Selected numeric/library matrices, exact
454-record traces per span/all-feature profile, independent semantic/allocation
checks and 72 explicit Node oracle executions pass. Its largest typed window is
464 of the unchanged 512 scalar bytes; fixed reservation remains 2,912. Broader
Clippy still reports 26 identical baseline/candidate diagnostics. See
`verification/numeric-primitive-root-review/acceptance.json`. The complete numeric
owner algorithm and Swift-mode execution remain unimplemented.

Hosted `7855754` passes all three jobs. Hosted `26943ac` passes VM/services but fails
Swift bridge TSan with session/native-exit publication race reports and an
HTTP native-exit fixture timeout. The scoped repair now has 875 root bindings:
explicit locked session publication, real native-request preconditions and an
explicit construction-permit lifetime in the test. All 48 existing bridge tests
plus three independent controlled schedules pass per Debug/Release/TSan.
Hosted `b6a7972` now passes all three jobs, including all 48 bridge tests per
Debug/Release/TSan under pinned Swift 6.2.4, with no TSan warning; see
`verification/github-ci-b6a7972/receipt.json`. Exact historical timeout cause is
unproved; demonstrated expiry and optimized lifetime hazards remain separately
scoped. See `verification/github-ci-26943ac/receipt.json` and
`verification/bridge-publication-root-review/acceptance.json`.

The next hosted checkpoint `61c5c8b` exposed a minimal-feature Clippy failure in
unused private descriptor fields after its tests passed. The descriptor-only
repair passes 202 tests per Debug/Release and four feature-combination Clippy
checks against clean `61c5c8b` source. See
`verification/swift-minimal-descriptor-ci-repair/receipt.json`; this is independent
of the cache candidate. All three `d6c41a0` hosted jobs now pass, including the
fresh Android host runner under Swift 6.2.4; see
`verification/github-ci-d6c41a0/receipt.json`.


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
Private concrete attempt ownership now passes six tests in each host mode, nine
derived lifecycle checks and independent retirement/last-owner-drop probes. The
outer slot remains held through setup/method return and actual bridge retirement;
cancelled waits do not release it. Root verified both evidence seals; see
`verification/capability-concrete-attempt-root-review/receipt.json`.
Hosted CI atf5d99d1 passes all three jobs for the preceding durable transitions.
The signed cold-start coordinator now passes the combined 95-function suite in
Debug, Release and TSan, public consumer/privacy checks and official iOS/Android
module builds. Root's identical four flow checks pass in all three host modes;
see `verification/capability-cold-start-runtime-root-review/receipt.json`.
Independent shutdown/health-write review found no actionable defect; two original
races pass in all three modes, including 144 concurrent close calls. Hosted CI at
36c5579 exposed three test-fixture expression limits in Swift 6.2.4; a test-only
split preserves both Wasm variants exactly and passes six local XCTest functions.
All three hosted jobs at ac2d2b6 now pass, including all 95 capability-activation
functions on the pinned compiler. Actual guest UI/event delivery, real UI
health and published consumer qualification remain separate.
The next integration design connects validated UI documents and bounded native
events to the signed guest. Parallel compiler investigation uses the retained
full-Swift corpus to identify its actual WASI calls and memory requirements;
the full Swift execution and artifact-size requirements remain open.
Root reviewed the compiler diagnostic sources and verified 37 retained path
bindings across ten commands; see `verification/swift-guest-next-root-review.json`.
The actual unchanged FieldLog model now also passes complete native/command/reactor
parity across two calls after one initialization. Root audited 99 retained path
bindings across 21 commands; see `verification/fieldlog-reactor-root-review.json`.
Its complete 18,976,211-byte gzip artifact exceeds the delivery budget and is
still rejected by the owned VM. The nondefault decoded-function cache now passes
its bounded allocation/pin/LRU/work matrix, independent debug/release probes, and
199 combined cache/native tests in each host mode. Root audited the exact
evidence in `verification/span-function-cache-root-review/receipt.json`. It has
no execution bridge and does not widen the existing VM limits.
The additive guest UI/event contract and separate native header are now frozen
after 55 independent static checks and C/C++ declaration/layout checks; see
`verification/guest-ui-contract-freeze-2026-10-23.json`. Implement its fixed
validator, bounded SDK exchange, bridge composites and signed native presentation
in that order. Contract review alone qualifies no UI execution or health.
Keep the full product plan and physical/published-consumer/GA gates in scope.

The additive native guest-UI validator now passes 79 combined native tests,
six focused tests, 49 default regressions and 16 public C checks per host mode.
An independent retained-Release public C probe passes 135 checks; root source
and evidence review is recorded in `verification/guest-ui-native-root-review.json`.
The installed-mode gate passes 12 scoped functions in Debug, Release and TSan,
including capability-only rejection before a full reservation pool or filesystem
access. Its receipt uses frozen pre-UI dependencies. The subsequent bounded
exchange, fixed bridge and signed Apple presentation checkpoint is described below.
All three hosted jobs passed for b02b76f and 51aafe8; receipts are retained.
No physical-device or UI health qualification is inferred from these checks.

Hosted run39948346991 at1adb25c passed VM/services but Swift stopped at the
old27-symbol archive inventory. The additive UI packager repair checks exactly
28 reviewed symbols and all three pinned headers; 24 policy tests pass in
normal and optimized Python. See verification/guest-ui-builder-ci-repair/receipt.json.
Hosted run39949617183 at32725fa now passes all three jobs; see
verification/github-ci-32725fa/receipt.json. The immutable native-only package
passes host C tests and iOS, simulator and Android C links with exactly28 symbols.

The bounded guest UI exchange, fixed native bridge, explicit signed Apple facade
and native presentation model now have a reviewed implementation checkpoint.
SDK Debug/Release42 and scoped TSan19 tests pass; independent review repaired
Unicode byte-identity substitution and unseen terminal-event consumption.
The packaged native-only archive passes the full48 bridge tests in each host
mode, including ordinary-trust local TLS rejection. The combined signed runtime
passes113 tests per Debug/Release/TSan mode. Actual signed event handling writes
app-private storage only after UI validation, distinguishes committed success
from permission denial, and retains uncertainty when a later wake frame fails.
Independent activation probes verify post-intent reopen diagnostics and a close
race while MainActor binding is delayed. Presentation tests cover final event
retirement and duplicate attachments;12 tests pass per Debug/Release and11 under
TSan, with the positive visible-window check explicitly pending.
Ordinary public imports cannot access the render host, inject events, construct
the presentation model, mutate its state or report a health milestone. The full
composed activation module builds for official iOS and Android targets; the
signed native screen facade is Apple-only. Root matched693 source/evidence/log/
dependency bindings in verification/guest-ui-integration-root-review.json.
Visible native display, an actual native button click, mobile app/lifecycle
qualification, Android signed UI integration, full Swift guest execution and the
delivery-size budget remain open. The first Mac display probes were occluded and
correctly produced no health receipt. This checkpoint grants no FieldLog or GA
acceptance. Phones remain disconnected. Hosted CI for this newer UI checkpoint
will be inspected after its push.

The signed Mac window flow now passes against the exact candidate4 runtime
binary. Root used native controls to start the signed guest, click Save sample,
inspect Saved sample, and close/verify storage. Revisions1->2->3, committed
health through the public recovery snapshot, exact stored bytes and joined
cleanup are recorded in verification/guest-ui-activation-window/receipt.json.
This supersedes the earlier occluded Mac probe limitation for this specific
flow; full Swift/FieldLog and mobile lifecycle qualification remain open.
Hosted run39952552065 at5a0367d passed services but exposed test-fixture
portability errors in GCC indentation and pinned Swift expression typechecking.
Its complete logs are retained in verification/github-ci-5a0367d; later Swift
steps were skipped, not passed. Byte-preserving fixture repairs now pass locally:167 exact outputs,42 C
checks,13 runtime UI tests and113 activation tests. The repair receipt is
verification/guest-ui-ci-repair/receipt.json. Pinned GCC/Swift confirmation
remains pending the next hosted run.

Hosted run39961877995 at35a9a36 passed VM/services, the48-test bridge matrix
and113 activation XCTests, then exposed a native SwiftUI graph teardown crash
in attachment publication. The repaired model separates published readiness
from synchronous attachment authority; the original-source regression observes
five unsafe publications and the repaired path observes none. Debug/Release
execute13 presentation tests with one positive-window skip each; TSan executes12,
and official mobile module compilation passes. Independent attachment probes
also pass. Evidence: verification/guest-ui-teardown-repair/receipt.json.
The pinned hosted recheck and current-repair visible native flow remain pending;
previous signed Mac evidence stays tied to its original runtime binary. No
physical/device, full Swift/size, published consumer or GA gate is closed.

Exact full-reactor diagnostics now cover all 79,832 defined bodies and preserve
the original command-artifact inventory. Six bodies exceed the current control
ceiling; the maximum is 379 including the function frame. Parameters plus locals
peak at181; scalar-arity operand-height inventory peaks at67 and is not complete
type validation. Root audited150 current source/tool/output/artifact bindings.
A mutable diagnostic executable binding was found and repaired by retaining the
tool before replaying the full trace; historical evidence is preserved. See
`verification/swift-reactor-diagnostics-root-review/audit.json`. The reference
executes initialization once and all11 corpus observations twice; owned full
Swift execution and the3MiB compressed-size gate remain unqualified.

The additive cache-backed Rust executor and standalone exact34 Preview1 adapter
now pass root combined Debug/Release checks:244 tests plus all9 explicit reference
checks per mode, focused Clippy and formatting. Independent review passes4
executor probes and6 WASI probes per mode (including1222 range/alias cases).
Review found and root fixed a no-owner constructor pin counter; failed evidence
is retained. See `verification/span-wasi-root-review/receipt.json`. CI includes
both features explicitly. WASI is not yet admitted/routed by the VM; frozen
profiles, native ABI, signing paths and release pins are unchanged. Full Swift
policy/validation/execution, total session accounting, mobile, immutable consumer
and GA qualification remain open.

Teardown repair 5a5b395 now passes all three hosted jobs, including pinned Swift
6.2.4 and generated consumer checks. A fresh source build at 92e93b2 also passes
the actual Mac public native flow: Start, Save sample, Saved sample, committed
health, exact stored bytes and joined Close. Root verified 208 frozen inputs, 54
artifacts and 33 build commands; see
`verification/guest-ui-teardown-window/root-flow-receipt.json`. The later
diagnostic checkpoint caaa005 passes Swift/services but exposes an intermittent
process-wide allocation-observer mismatch in a cache test; investigation is
active and its VM job remains failed. No failed run is relabeled a pass.

The Android C transport slice passes 26 owner cases and 9 independent cases in
each Debug/Release/ASan+UBSan/TSan mode, plus API 30 arm64 compile/link checks.
Root audited 66 bindings in `verification/android-transport-root-review.json`.
It counts a process baseline of two FDs, one Looper registration/reference and
16 static owner slots. Callback-return fencing is separate from actual consumer
join. Android binding remains incomplete: bounded fence-progress notification,
pre-bind presentation reservation, exact waiter publication, real main-Looper
and Swift Task join, JNI widgets and display/health integration are required.
These host checks do not qualify Android execution or any GA gate.


The allocator observer repair now isolates synchronous test ownership from harness
threads while preserving the original product assertions and fault ordinals.
Original observers deterministically fail under a background 900-byte allocation
and fault-ordinal interference; the repaired two tests pass Debug/Release with
and without that noise. Root audited the immutable e299f1a baseline plus exactly
three test files, 404 snapshot files and unchanged counts/peaks; see
`verification/allocator-observer-root-review/receipt.json`. The exact origin of
the earlier CI allocation remains unattributed and that failed run stays failed.
Hosted checkpoints 92e93b2 and e299f1a now pass all three jobs. Full Swift validator
work remains a separate uncommitted lane; physical phones stay disconnected.


The nondefault Swift reactor validator now type-checks every one of the immutable
53,777,114-byte target's 79,832 defined bodies under the exact 34-import policy.
It validates 6,505,659 instructions with a 54,827,522-byte internal reservation
peak; retained caller input raises the measured reservation overlap to
108,604,636 bytes. This is reservation accounting, not measured process RSS.
Root combined Debug/Release checks each pass 263 tests and nine explicit reference
checks; the older feature matrices also pass. Independent review verifies 147
adversarial cases, all 41 allocation/cancellation ordinals, eight proof-authority
compile failures and exact legacy observations/budget boundaries. Root audited
1,071 source and evidence bindings in
`verification/swift-reactor-root-review/receipt.json`. The opaque proof permits
no execution, serialization or conversion into existing release authority.
CI now explicitly includes the feature. Hosted checkpoint 8296296 passes all
three jobs, including observer background-noise regressions. Full Swift execution,
runtime/WASI composition, the compressed delivery budget, Android signed binding,
physical devices, immutable published consumers and all GA acceptance remain open.


The presentation reservation prerequisite now holds the outer slot through its
retained owner's actual destructor, independently of store and adapter retirement.
Once-only admission, all three held-destructor orderings, concurrent admission and
abandonment quarantine pass scoped Debug/Release/TSan checks and the reservation
XCTest against the complete current activation module. Root audited 410 bindings
in `verification/presentation-reservation/root-review.json`. The trusted final
caller must first join work and relinquish every other resource-owner alias.
The corrected Android binding contract is accepted for staged implementation in
`verification/android-binding-contract-acceptance.json`; it fixes direct UI-entry
counting, stable facade identity, exact final cleanup and single-owner joins.
Common lifetime integration, C facade/entry fences, Swift Android/JNI binding and
real display/health remain subsequent implementation and qualification work.
These prerequisites enable no Android signed UI mode or GA acceptance. Physical
phones remain disconnected; the next hosted checkpoint is pending.


Hosted f19cf9f passes VM/services but fails an existing HTTP cleanup assertion
under pinned Swift Thread Sanitizer; the exact failing ordering is unknown.
A deterministic probe proves the original assertion rejects legal expiry before
protocol start. The test-only repair observes start before advancing its deadline
and separately checks native invalidation before resume. Debug/Release52, TSan32,
20 repeated cleanup pairs and alternate Swift6.3.3 TSan32 pass; root audited267
bindings in `verification/http-cleanup-ci-repair/root-review.json`. Product HTTP
transport is unchanged and pinned Swift 6.2.4 revalidation remains pending CI.
Hosted401e16c also passes VM/services but Swift stops at the dependency guard:
its `wasm3` substring wrongly matches `wasm32` architecture names in the concurrent
website lockfile. The narrow guard correction reproduces all11 false positives,
passes seven regression tests and keeps prohibited runtime names rejected; see
`verification/dependency-architecture-ci-repair/receipt.json`. Original failed
runs and skipped later checks stay explicit. No physical/GA gate changed.


The private Android facade transport now adds 16 stable facade identities, counted
UI entries, callback/entry fences, terminal cleanup admission and bounded progress
notification. Owner checks pass 248 host case executions; independent review
passes 292 across Debug, Release, ASan/UBSan and TSan, with API30 arm64 compile/link
checks. Root audited 301 evidence bindings and ran 146 additional portable
Debug/Release checks; see `verification/android-facade-transport-root-review/receipt.json`.
The same host driver is now wired into Linux CI, whose first run is pending.
These checks use host Looper simulations. Actual Swift/JNI binding, consumer joins,
view cleanup, Android display/health and device qualification remain open. No
Android signed UI mode or GA gate is enabled by this private C prerequisite.


The private Swift runtime-control foundation now consumes the exact validated
proof, admits seven categories under one combined ceiling, and keeps cumulative
fuel/work/host limits, earliest deadlines and immutable failure diagnostics.
Storage drops precede refunds; an unclosed enlarged construction phase stays
charged. Independent adversarial probes cover 4,000 ledger operations, destructor
unwind and foreign proof cleanup. Root combined Debug/Release each pass 287 tests
plus nine explicit reference checks; 563 evidence bindings match in
`verification/swift-runtime-control-root-review/receipt.json`. Scoped lint passes;
the preserved broader lint attempt still has unrelated existing test warnings.
This foundation selects no execution route. Swift cache/executor/WASI composition
and the bounded target attempt remain subsequent work. No full reactor execution,
physical qualification, published consumer or GA acceptance is claimed.

Hosted22d048c now confirms the HTTP and dependency-guard repairs but fails a later
cold-start test whose directory-created signal precedes native queue admission.
A test-only ordering repair is under deterministic review. Hosted d6505ac then
fails a separate process-wide VM allocation observer by four calls and 900 bytes;
its exact source is unknown. Remaining observers of that form are being repaired.
The new Android host CI step was skipped by that earlier failure, not passed.
Original logs remain in `verification/github-ci-22d048c/` and
`verification/github-ci-d6505ac/`. No failed CI run or skipped gate is relabeled.


Common presentation lifetime integration now keeps its once-only obligation
through the actual Apple task join and final MainActor view retirement. Protected
setup, failed bind and close races preserve ownership; pending or quarantined
results cannot release capacity. Owner checks pass 14 XCTest and 13 model/hidden
window tests per Debug/Release/TSan, with one explicit visible-window skip.
Independent review passes 13 XCTest per mode plus API-authority negatives; the
portable unsupported branch passes 32 host cycles per mode. Root audited 1,163
bindings in `verification/common-presentation-lifetime-root-review/receipt.json`.
The cold-start CI test now accepts early capacity return only after both actual
tails finish while its native queue remains held. Deterministic original/repaired
pre-admission and queued cases pass their 15 expected outcomes across modes;
see `verification/cold-start-cleanup-ci-repair/final-1/receipt.json`. The original
hosted interleaving remains unproven. Apple receipts cover view retirement, not
destruction of publicly retainable model shells; Android binding remains pending.

Hosted020f909 passes all three engine jobs, including the new Android facade host
regression step. This is the prior Swift-control/C checkpoint, not a hosted pass
for these newer presentation or observer changes. Hosted d6505ac's Swift job also
finished successfully; its original VM failure remains retained. Physical phones,
actual Android signed binding/display, full Swift target execution, immutable
consumers and GA acceptance remain pending.


The three remaining VM allocation probes now use the reviewed pointer ledger
with thread-local size/fault/gate observations. All 69 original assertions and
17 measurement lines remain exact. Owner Debug/Release runs pass with and without
900-byte background noise; independent review passes 43 additional checks in
four combinations. CI now runs all five affected observer tests under noise;
those exact combined Debug/Release commands pass ten local test processes.
Root audited 546 bindings in
`verification/remaining-allocator-observers-root-review/receipt.json`.
Original observer replays reproduce the hosted four-call/900-byte tuple and
fault-ordinal interference; the actual hosted allocation origin is still unknown.
This changes test instrumentation only. Its hosted recheck, physical devices and
all specified external qualification remain separate. Presentation checkpoint
f19a18b has passed VM/services; its Swift job is still running at this observation.


Hosted f19a18b and b79ca53 both pass VM/services but stop Swift compilation at
the unannotated local NSView diagnostic helper. An explicit `@MainActor` fixes
that test-only helper. The actual retained model/hidden-window suite passes
13 tests with one visible-window skip per Debug/Release/TSan on Swift6.4. Root
audited 111 bindings in `verification/presentation-actor-ci-repair/root-review.json`.
The retained production module matches this committed checkpoint; concurrent
Android implementation is outside that qualification. Pinned Swift 6.2.4 rerun
is pending. Both failed hosted receipts remain preserved; no skipped gate,
physical device or GA check is relabeled as passed.


The private accounted WASI owner now charges its context, four buffers and
construction/cleanup scratch to the shared runtime ceiling. Actual WASI context
counters remain authoritative; cancellation, host admission and cleanup preserve
the first failure and its actual counters. Independent review reproduced a
cleanup-first diagnostic omission; the repaired Debug/Release probes now retain
that observation without refunding a foreign owner. Root combined Debug/Release
each pass 308 tests plus nine reference checks, scoped Clippy and full formatting.
Root audited 1,555 bindings in
`verification/swift-accounted-wasi-root-review/receipt.json`; the independent
review seals 953 checks, descriptor parity, allocation/cancellation ordinals,
privacy negatives and byte-identical old-route behavior. Earlier owner receipts
are historical and do not qualify the final cleanup repair. This private slice
creates no Swift execution route. Cache/executor composition, bounded full-target
execution, delivery size, physical devices, published consumers and GA remain open.


Private Swift execution descriptors now borrow the retained validated proof without
allocation or public authority. Observed control paths retain actual paired WASI
counters, validate both original proof tickets, and preserve legacy owner layouts.
Root combined Debug/Release each pass 318 tests plus nine reference checks, scoped
Clippy and full formatting. Independent review passes seven additional probes per
mode, 103 original library tests per mode, 37 legacy regressions and privacy checks.
Root audited 3,682 bindings in
`verification/swift-cache-prerequisites-root-review/receipt.json`.
The refined cache contract preserves rejected cleanup owners and keeps its same
header reservation through cleanup return. Root now authorizes bounded private
cache implementation in `verification/swift-cache-stage-acceptance.json`; its 18
named tests, concrete temporary-memory layouts, independent implementation review,
executor and bounded full-target runner remain pending. No cache execution or GA
qualification follows from this prerequisite checkpoint.

Hosted 8d809df and bd8a896 both pass all three VM/Swift/services jobs. This confirms
the pinned Swift 6.2.4 actor-helper repair and the accounted WASI checkpoint.
Historical failed runs remain retained. Android binding implementation/review is
ongoing; physical phones, immutable separately published FieldLog packages,
full-target performance/delivery-size and all specified external gates remain open.


The next executor prerequisite adds private instruction/fuel observation methods,
with original entry points delegating None. Actual paired WASI counters now remain
in the first failure at cancellation/deadline, fuel exhaustion and checked
instruction overflow. Eleven actual-context cases also verify unchanged charging
order and no-effect reentry. Isolated checkpoint4585220 plus these two source
files passes 319 tests and nine reference checks per Debug/Release, 72 minimal-
Swift library tests per mode, Clippy and formatting. Root binds 853 checks in
`verification/swift-instruction-observation/root-audit.json`; independent review
and executor acceptance remain pending. Active cache and Android edits are outside
this qualification. The preceding4585220 CI currently passes VM/services while
its Swift job is still running. No physical, target-execution or GA claim changes.


Independent review now accepts the private instruction/fuel observation delta at
`3a1bb5a`: the original eleven actual-context cases and three additional boundary
probes pass per Debug/Release. Root verifies 443 independent bindings and the
853 producer bindings in `verification/swift-instruction-observation/acceptance.json`.
Hosted `4585220` passes all three VM/Swift/services jobs. This does not qualify
active cache or Android changes. Cache layout measurements exposed a separate
shared-foundation observation allowance gap. The accepted correction now counts
six optional observations: five nested control arguments plus one caller copy.
Root audits 522 independent and 859 producer bindings; isolated Debug/Release
each pass320 tests plus9 reference checks and73 minimal-Swift library checks.
Independent admission and30 control tests per mode exercise deep faults after
actual WASI teardown;36 contract mutations fail closed. The revised cache v3
implementation freeze is `verification/swift-cache-stage-acceptance.json`, with
exact v2 history preserved. Actual cache implementation review, executor contract
refinement/implementation and composed temporary layouts remain pending.
Physical phones, full-target execution, immutable published consumers and all
external GA requirements remain open.


The refined private executor contract now has root acceptance of its algorithm,
authority, API intent and named accounting rules, after92 artifact/source
bindings and37 rejected contract mutations. Exact revision1 remains archived;
see `verification/swift-executor-stage-acceptance.json`. Actual cache acceptance
must precede a separately assigned compiling type/lifetime/layout prerequisite.
The full20 executor functions and75 assertions remain
pending, with no implementation assignment or full-target execution enabled.


Hosted `39199ae` now passes all three VM/Swift/services jobs; see
`verification/github-ci-39199ae/receipt.json`. A test-only deadline repair now
requires the selected allocation to be reached before counting its deadline
sample, with bounded retries for earlier real-clock expiry. Isolated Debug and
Release each preserve all56 allocation/failure/cancellation/deadline positions,
including deterministic retry and exhaustion coverage. Root audits417 source
and21 artifact bindings in `verification/swift-validation-deadline-repair/root-review.json`.
Targeted all-feature Clippy and formatting pass. The original timing failure and
the first run's pre-existing minimal-feature Clippy warning remain recorded.
Active cache and Android qualification, physical devices, full-target execution,
immutable published consumers and every specified GA acceptance remain pending.

Hosted `5988e4a` now passes all VM/Swift/services jobs, including the pure shared
appearance resolver. See `verification/github-ci-5988e4a/receipt.json`.

Hosted `7c2baeb` passes VM/Swift/services, including all ordinary host scenarios.
The earlier `c687e69` run failed the TSan `fault-leave` test with an observation
deadline; its sparse log does not identify which wait timed out. A deterministic
C schedule reproduces a test precondition gap: admitting the next owner during
the earlier completion can coalesce its leave wake, leaving the injected write
unattempted. The test-only repair now has root acceptance with 1,157 bindings,
117 fresh Debug/Release/TSan scenario passes, six independent actual Swift/C
schedule proofs and three fixture replays. See
`verification/android-fault-leave-ci-root-review/acceptance.json`. Its hosted
checkpoint verification remains pending; the earlier failure stays recorded.
Constructor preflight remains under independent
review after missing whole-value accounting wrappers were found; no constructor
or full-target acceptance is claimed.

The internal V2 native consumer boundary is now accepted for implementation; see
`docs/native-appearance-v2-implementation-boundary.md`. The standalone UIKit field
probe passes 25 simulator stages. Root independently checks 731 pixels in 11
retained captures with Apple ImageIO; public reinstallation of the same managed
selection interaction enables separate caret/selection alpha. This accepts a
bounded iOS26.5 feasibility result; blinking, keyboard-driven IME and complete
native consumer behavior still require implementation/testing. Both concrete
native renderer lanes are active. `b858e91`, `2ca44e6` and `ca9f802` pass all three
hosted jobs. Physical-phone checks move to final acceptance under the user's
simulator-development policy; none of these slices closes a GA gate.

The ordinary Android engine now retains one value-owned candidate until explicit
commit/abort after native attachment. Its private SPI blocks legacy exchange
while pending; failed preparation, stale/foreign tokens, duplicate decisions and
session destruction preserve the documented state boundary. Independent source
review has no findings; all sixteen engine tests pass per Debug/Release/TSan and
the official Swift6.3.3 Android API28 library links. See
`verification/android-engine-v2-transactions/root-review/acceptance.json`.
The JNI/Activity/native-renderer join remains next; no ordinary V2 bootstrap or
signed presentation is enabled. Native renderer candidates now execute on their
dedicated simulator/emulator and are undergoing common-fixture visual review.
Initial nested interactive list rows reject before attachment as recorded in
`docs/native-appearance-v2-nested-row-limitation.md`. Hosted `25c5e03` passes all
three jobs. Hosted `8338fa0` and `a739aa6` also pass all three jobs.

Unused simulator cleanup is complete for this checkpoint: root shut down the two
older Mixer measurement/reference instances, and the Apple lane deleted its three
obsolete disposable instances. Only the current Mixer final test and an unrelated
active MeGPT iOS simulator remain booted. The current Android test emulator is
also retained until capture completes. One active instance per native lane and
post-run cleanup are now required in AGENTS.md. See
`verification/simulator-cleanup-2026-10-24/receipt.json`.

The private original-owner Swift value-operation slice now has independent and
root acceptance. Preparation, push/pop, admitted scalar/saturating numeric work,
trap reconciliation and zero-frame completion execute on the original accounted
owners. Root verifies 1,112 source/evidence bindings; independent review passes
48 selected product and 44 derived test executions, plus a separate metadata
replay. The corrected inventory has 227 fields and 561 typed positions; prior
accounting and collector failures remain retained. See
`verification/swift-value-operations-root-review/acceptance.json`.
These are selected host tests, not full Swift execution. Function entry/dispatch,
active-frame unwind, control flow, memory/growth and host integration remain next.
All GA and dogfood gates remain open. Hosted `8338fa0` and `a739aa6` now pass all
three configured VM/Swift/services jobs; their receipts are retained separately.

The ordinary Android checklist library now exposes the registry's private staged
C prepare/commit/abort decisions. Actual C clients pass 77 assertions per host
Debug/Release; C++ clients compile/link the same header, and official Swift 6.3.3
links the arm64 API28 exports. Root replays 79 captured source files, 20 command
logs and 7 native artifacts. The original NDK-discovery failure is preserved with
a completion receipt inspecting the unchanged binary using the bundled NDK r27d.
See `verification/android-engine-v2-c-bridge/acceptance.json`. JNI ownership,
generated application staging exports, native coordinator integration and final
hardware qualification remain pending; no public V2 opt-in or GA gate changes.

Hosted `1b3de6d` passes all three VM, Swift and services jobs; see
`verification/github-ci-1b3de6d/receipt.json`. This verifies the configured checks
for the value-operation checkpoint, with complete Swift execution still pending.

The pure hosted RS256 verifier now has root acceptance at
`verification/hosted-token-verifier-root-review/acceptance.json`: 16 scoped
producer tests, 23 independent real-signature adversarial tests, 24 full hosted
tests, production release build and missing-config boot rejection. The fixed
profile rejects duplicate JSON, unsupported headers/algorithms and invalid
keys/claims, while retaining no role or tenant authority. Configured active
trust ownership, bounded HTTPS key refresh/cache, provider interoperability and
authoritative membership/RLS/private artifact operations remain next. This is
a component acceptance; all hosted and GA completion gates remain open.

Linux hosted CI at `f18ea41` confirms the 24-test application suite and packaged
release checks; artifact/source verification is retained at
`verification/github-ci-f18ea41-phoenix/receipt.json`. This adds Linux host
evidence only; provider, membership, native and operational gates remain open.

Root accepts the isolated retained-display formatter correction after an exact
88-case replay and 94-case independent suite, both without skips or exclusions.
A separate oracle reconstructs 185 actual chain rows. Root verifies 625 review
and 1,509 reviewed input bindings; CR01 is resolved within the specimen. Complete
production AS05, catalog and repository integration remain pending. See
`docs/hosted-atomic-display-acceptance.md`.

The authority catalog correction now replays the original 128 cases and 43 review
controls, preserves five historical gap observations, and passes 67 new correction
cases. Root verifies 789 bindings; fresh independent review is running. Actual
Ecto/Postgrex authorization-driver implementation is also underway in isolation,
with no SQL signature changes or live migration. See
`docs/hosted-authority-catalog-correction.md` and
`docs/hosted-authority-driver-contract.md`.

Checkpoint `f044e6db` passes all three Swift, VM and Go service engine jobs.
See `verification/github-ci-f044e6db-engine/receipt.json`; no GA gate changes.

The catalog's independent review verifies 489 bindings and reproduces ACR01:
21 malformed raw metadata admissions across 126 boundary models. Ordinary
PostgreSQL changes remain detected in the tested scope; no ordinary-runtime
bypass was demonstrated. Root selected complete raw validation before lossy
normalization in `docs/hosted-authority-catalog-shape-direction.md`; correction
and fresh independent review remain pending.

The isolated Ecto/Postgrex authority driver passes 56 actual-driver cases and
711 source/evidence bindings. Fresh independent review is running. The isolated
hosted audit codec candidate preserves 185 captured PostgreSQL rows and passes
11 focused tests plus 104 full hosted tests with two explicit Linux-only skips;
its independent review is pending. See `docs/hosted-authority-driver.md` and
`docs/hosted-audit-codec-integration.md`. No live authority/domain migration,
HTTP or GA acceptance is claimed.


The isolated memory behavior candidate passes all 64 MM selections and 24
independent adversarial selections. Independent review reproduces existing
layouts and Frozen behavior but finds MR01: eight unit-only promoted-binding
positions are missing (64 named bytes). Root verifies 381 review and 1,451
producer bindings. An isolated accounting correction is underway; live VM
integration remains pending. See `docs/swift-memory-helper-behavior-review.md`
and `docs/swift-memory-promoted-accounting-direction.md`.

The audit decoder's independent review found unbounded work from sorting unknown
map keys. A two-line correction passes 12 focused tests, six retained review
tests covering 107 cases/eight edges, and 105 full hosted tests with two explicit
Linux-only skips, plus release checks. Root verifies 68 correction bindings;
fresh independent correction review is active. See
`docs/hosted-audit-key-bound-correction.md`.

The authority driver's independent review stopped after an automated safety
flag. Its preserved findings led to an isolated strict-context comparison and
fixed error-message correction: 56 original actual-driver cases, 128 unchanged
schema cases and 17 regression groups pass. All eight equal-value float context
copies reject before effects. Root verifies 303 correction bindings and 4,025
interrupted-review bindings; independent acceptance remains pending. See
`docs/hosted-authority-driver-correction.md`. The catalog shape correction and
review are also isolated, with final narrow domain corrections still pending.
No current-authority/domain migration, authenticated HTTP, provider, native,
physical-device or GA acceptance is inferred.

Checkpoint `e337ddd1` passes all three Swift, VM and Go service engine jobs.
See `verification/github-ci-e337ddd1-engine/receipt.json`; no GA gate changes.

The catalog shape review is frozen at 115 review/277 producer bindings. ACSR01
rejects a legal quoted asterisk role; ACSR02 admits impossible duplicate trigger
names after normalization. Both have selected isolated corrections; the latter
is model evidence, with no ordinary-runtime bypass demonstrated. See
`docs/hosted-catalog-wildcard-direction.md`. The preliminary review is retained.

The pure upload audit codec is now independently reviewed, root accepted and
integrated into `hosted/`. Root verifies 281 upstream and 17 integration bindings,
all 66 tested inputs, and 12 direct-checkout tests. The byte-identical full suite
passes 105 tests with two explicit Linux-only skips; release checks pass.
Independent review adds 546 key replacements and exact original/corrected byte
parity. See `docs/hosted-audit-codec-acceptance.md`. Current-authority/domain SQL,
authenticated HTTP, provider and GA qualification remain open.

Checkpoint `9f314ebb` is pushed. Its Phoenix/Linux CI passes 105 tests with two
explicit namespace skips and all release checks; all 66 archived inputs match
the commit. Engine CI subsequently passed all three jobs; see verification/github-ci-9f314ebb-engine/receipt.json. The memory promotion correction now
passes 563 bindings, 4,800 fields, 64 MM selections and 184 prior regressions.
The catalog domain correction passes 96 bindings, all selected model matrices
and five fresh targeted PostgreSQL cases. Both corrections are frozen under
fresh independent review. Live VM and catalog integration remain pending.


Private original-owner Load/Store is now independently reviewed, root accepted and integrated. MR01 resolves eight omitted unit promoted positions (64 bytes), retaining all 4,792 prior positions for 4,800 total. Root verifies 1,269 upstream and 22 integration bindings; fresh normalized-source Release runs pass 62 focused tests and 16 Frozen integration tests, plus Swift CI Clippy with warnings denied. Producer64 memory/184 prior selections and reviewer12 focused selections remain separately bound. Integrated123-file closure17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff. Full dispatch/Ready/public/native/FieldLog/GA and G08 absent-cursor diagnostics remain open. See `docs/swift-memory-integration-checkpoint.md`. The next isolated lane implements shared copy/fill/MemorySize; growth and later execution joins remain pending.

Pure audit codec is integrated and 9f314ebb Phoenix CI passes105 tests with2 explicit namespace skips, release checks and66 exact committed inputs. Catalog raw-domain correction now has independent and root prerequisite acceptance:96 producer/147 review bindings,245 root-bound inputs,133 additional model cases and5 fresh targeted PostgreSQL cases. ACSR01/02 resolved within isolated raw-domain contract; no actual ordinary-runtime bypass inferred. Actual hosted catalog inspector implementation is underway in isolation. Authority-driver independent review remains interrupted after automated safety flag; corrected driver acceptance remains pending. No combined authority/domain migration, authenticated HTTP, provider, native or GA acceptance. 9f314ebb engine CI now passes all three VM, Swift and services jobs. See `docs/hosted-catalog-acceptance.md`.


Checkpoint `615a05dc` now passes all three Swift, VM and services engine jobs. See `verification/github-ci-615a05dc-engine/receipt.json`; scoped live Load/Store regression acceptance only, with native and full product gates still open.


October 24 follow-on development slices:

The isolated copy/fill/MemorySize candidate is frozen at 125-file closure e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626. Producer evidence passes 312 selected tests across four configurations, 64 Frozen differential pairs, 16 paired layouts and 4,324 newly accounted fields while preserving all 4,800 prior memory rows. Root replay of the sealed producer packet and live baseline passes. Fresh independent source, behavior and accounting review is in progress; this candidate is not integrated. Growth, dispatcher, Ready/public execution, native and GA acceptance remain pending.

The ordinary Swift engine/JNI/private V2 coordinator/native renderer join now has a frozen headless APK build: 105 source inputs, 63 successful build commands, 177 retained compiled artifacts and 10 exact accepted renderer sources. Root headless-review-3 verifies artifact identity and removes its owned extraction after the holder check. Native assertions executed: zero. A separately bound runtime-runner extraction cleanup correction is underway before dispatch. Desktop UI access still awaits Mac unlock; public V1, shared cross-platform parity, physical and GA acceptance remain pending.

The isolated read-only catalog inspector uses separately held observer and restricted runtime repositories. Root selected an explicit versioned observer profile because restricted runtime cannot see 21 required settings: only the declared observer CONNECT ACL is added to the pinned original manifest, which remains immutable. Qualified fresh-session queries preserve nine-field semantics; asynchronous timed-out holder quarantine and backend retirement are distinguished from synchronous cleanup. Producer final sealing and independent implementation review remain pending. No live hosted integration, combined schema, HTTP authority, provider or GA acceptance.


Latest October 24 integration and runtime checkpoint:

Shared original-owner copy/fill/MemorySize is now independently reviewed, root accepted and integrated. The reviewed125-file closure e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626 differs from integrated96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d only by two explicitly bound blank-line whitespace removals. Root574upstream+23rootbindings pass; fresh normalized-source78focused/16Frozen Release tests, Swift CI Clippy and whitespace pass. Independent76fresh selections,4MIR,4layouts,39Frozenmethods/14owners; producer312selections/64Frozenpairs/16layouts remain separately attributed. All4800memory positions retained plus4324bulk positions. Owned scratch removed. Growth implementation is underway in isolation; full dispatch/Ready/public/native/GA and G08 remain open.

Ordinary Swift/JNI/private coordinator/native-renderer APK has root headless build acceptance:105inputs/63buildcommands/177compiledartifacts/10renderer matches. Separate runtime cleanup correction passes24host guards and184sealed bindings. Two actual API37 emulator attempts failed before boot with zero APK installations/native assertions; both owned processes/ports and172884977byte extractions cleaned. Read-only crash diagnosis underway before a changed experiment. Apple UI awaits Mac unlock; phones deferred; no publicV2, full native/design parity orGA acceptance.

Actual isolated Elixir/Ecto catalog inspector producer is frozen: root replay388bindings/1257model inputs/17PostgreSQL groups. Separate observer CONNECT profile and qualified session query remain explicit; original baseline immutable. Fresh independent review was interrupted by automated safety flag during an additional observer-privilege edge case. Root preserves117raw partial-review bindings and3cleaned attempts, without retry or final acceptance. Candidate/profile remain isolated and unaccepted. No combined schema/HTTP/provider/native/GA acceptance; earlier driver independent acceptance also remains pending.


Android boot diagnosis now localizes both failed coordinator attempts to netsim channel startup. A separate root-dispatched API37 arm64 boot-only probe passes with the sole launch delta -feature -WiFiPacketStream; its owned process group and ports are absent after cleanup. Root verifies 102 saved bindings and fifteen host guards. No APK or app assertion ran. A separately bound full runner adaptation is underway; the original APK, sources and assertions remain unchanged. Apple UI still awaits Mac unlock; physical phones and full product gates remain deferred. See `docs/android-emulator-boot-diagnosis.md` and `verification/android-coordinator-join-root-review/boot-probe-acceptance.json`.


Checkpoint `a1f78d1e` passes all three engine CI jobs (VM, Swift and services), with no skipped steps. See `verification/github-ci-a1f78d1e-engine/receipt.json`. The separately dispatched Android coordinator run boots and installs the exact frozen APK, then stops on check 27 after 26 passes: the fixture incorrectly requires `Switch.performClick()` to report an OnClickListener. Its original failure and cleanup are retained. A test-only correction preserves the actual reducer revision, checked state and identity assertions for a fresh native run; no app acceptance is claimed yet.


The corrected Android instrumentation build preserves production entry bytes and passes 36 fresh root host guards, but its first native attempt fails APK installation: resources.arsc was compressed during repacking. Root verifies 35 retained runtime files and independently confirms stored-to-deflated metadata drift with identical resource bytes. Zero app assertions ran; the owned emulator group, ports and 177-file extraction were cleaned. A separate APK-only packaging correction and pre-install storage/alignment validator are underway. Earlier 26 native passes and fixture failure remain historical evidence, not completed join acceptance. See `verification/android-coordinator-join-root-review/click-fixture-runtime-1-review.json`.


The private Swift memory.grow slice is independently reviewed and integrated. Root verifies 798 upstream bindings and 31 integration files; the raw reviewed closure is preserved and the integrated 127-file closure a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b differs only by one removed trailing ASCII space. Fresh normalized-source checks pass 98 focused all-feature Release tests, 16 Frozen Release tests and Swift-only Clippy. Independent review passes 20 exact-source growth tests, 14 adversarial selections, four fresh MIR inventories, sixteen raw layout audits and four representative layout executions. All 10,356 growth, 4,800 memory and 4,324 bulk positions remain accounted; 39 Frozen methods and sixteen checked owner declarations are unchanged. Owned command groups and scratch are cleaned. This accepts private host development only; G08 absent-cursor diagnostics, full dispatch/Ready/public/native/FieldLog/physical/GA remain pending. See `docs/swift-memory-growth-integration-checkpoint.md`.


The private host-import contract has root compiler/layout prerequisite acceptance: 557 root bindings, 14 original source archives, 16 fresh isolated layout contexts, retained exact executables and eight full unit lists. Historical shared-target outputs supply numeric proposals only. An isolated implementation lane is rebasing and remeasuring on accepted growth before qualifying H01–H16 actual imported-host behavior. No host import runtime acceptance is claimed. See `docs/swift-host-dispatch-contract-acceptance.md`.


The ordinary Swift/JNI/private coordinator/native-renderer join now has root acceptance for its bounded API37 arm64 development subset: all eight operations and 64 native checks pass. Root verifies 56 runtime artifacts/60 bindings and independently decodes seven packets, confirming reducer revisions, checked/text state, retained identity, environment byte equality and fresh relaunch. All 88 native/SDK inputs, including test inputs, match the checkout; production artifacts are unchanged. The corrected APK passes storage/alignment/signature checks and 44 fresh runner guards. Owned PID/group 31099, ports and 177-file extraction are cleaned; the unrelated emulator/service remain running. Actual pointer gestures, full IME/accessibility/lifecycle, shared appearance parity, public V2/signed transport, physical phones and GA remain pending. See `docs/android-coordinator-join-acceptance.md`.


The bounded Android pointer contract now has root acceptance for isolated fixture implementation: 20 tap/hold/drag/cancel/scroll and disabled/current/retired actions, at most 320 injected MotionEvents, passive Activity delivery observations and exact committed revision/state/identity oracles. Direct internal callback counts remain unobserved. Root rechecks 49 sealed contract files, 35 current sources, 60 predecessor bindings and all 88 native/SDK inputs (including test inputs). The new fixture lane preserves production bytes; no gesture run or new native acceptance is claimed. See `docs/android-native-input-matrix-contract.md` and `verification/android-native-input-root-review/contract-acceptance.json`.


Checkpoint `c1175f7a` passes all three terminal engine CI jobs (Swift, VM and services), with no skipped steps. See `verification/github-ci-c1175f7a-engine/receipt.json`. That run predates the newly integrated growth source; its next pushed revision requires a separate CI result.


The obsolete successful Android coordinator build scratch is now removed after verifying all 177 qualified artifacts against its retained archive and checking zero open holders: 347 generated files, 376,186,557 bytes, plus one internal Swift release symlink. The initial conservative symlink rejection remains recorded; no deletion occurred in that attempt. The failed original candidate-1 scratch remains preserved. No emulator or unrelated project process was changed. See `verification/android-obsolete-build-cleanup/attempt-2/receipt.json`.


The G08 cleanup-attribution audit reproduces an actual pinned Load at Invocation/function 34/offset 1713 returning a cursorless Cleanup underflow. Five existing tests and three isolated probes pass; root verifies 45 sealed files and 837 bound inputs. The selected repair adds a contextual original-control removal entry only for active pop/numeric/control/finish routes, preserving the legacy removal body, cleanup paths and immutable first failure. Sixteen repair groups remain pending; source integration is serialized after the host-operation slice and must be rebased/requalified. No diagnostic implementation or G08 pass is claimed. See `docs/swift-cleanup-diagnostic-contract.md` and `verification/swift-cleanup-diagnostic-root-review/selection.json`.

The integrated private memory-growth checkpoint `d4909e27` now passes all three terminal engine CI jobs (Swift, VM and services), with no skipped steps. See `verification/github-ci-d4909e27-engine/receipt.json`. The subsequent host-operation, cleanup diagnostic and pointer-fixture candidates remain outside that CI scope.

The first Stripe signature component now passes 22 isolated host tests, seven independent Python HMAC vectors, four disposable crypto-failure probes and one bounded comparison-schedule probe. Exact candidate/source/tool/output evidence is sealed; independent review and live hosted integration are pending. This verifies unchanged signed bytes and freshness only. Raw-body HTTP capture, endpoint ownership, durable inbox/atomic Oban enqueue, provider test-mode deliveries, reconciliation, usage and G23 remain open. See `docs/stripe-webhook-signature-evidence.md` and `verification/stripe-webhook-signature/receipt.json`.

The private Android pointer candidate4 passes independent build/DEX/packaging checks, but its oracle review reproduces five invalid acceptances involving obscured flags, pressure, MOVE history, missing actual MOVE samples and timing. Root retains both sealed packets and holds native dispatch for isolated candidate5 repair; no pointer runtime was attempted or accepted. See `verification/android-pointer-fixture-root-review/selection.json`.

Root accepted and integrated the bounded Stripe signature component after independent review: 2,352 adversarial cases plus late crypto-failure checks pass, and the exact composed hosted source passes 127 tests with two existing Linux-only skips on macOS. Production release build/configuration rejection/test-export checks pass; private PostgreSQL, command groups and scratch are cleaned. Three tested files are applied with 337 evidence bindings and 69 source inputs matched. See `docs/stripe-webhook-signature-integration.md` and `verification/stripe-webhook-signature-integration/acceptance.json`. Raw-body HTTP admission, endpoint ownership, durable inbox/Oban, real provider reconciliation and G23 remain open; exact-head Linux CI follows delivery.

Pushed signature checkpoint `11133e60` passes its terminal Phoenix/Linux CI run. The downloaded receipt and source archive match all 69 integrated inputs and digest exactly; 127 tests and release checks pass, with two existing isolated-network-namespace tests explicitly skipped because that separate fixture is not enabled. See `verification/github-ci-11133e60-phoenix/receipt.json`. Engine CI is still in progress; broader billing/G23 remains open.


Latest isolated follow-on work: Private host-operation candidate is frozen at 128-file closure 7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329. Producer 1,014 library, 64 host-probe and 64 Frozen executions pass; root replays 1,671 sealed evidence files, 285 commands, 91 artifacts and sixteen layout contexts. Independent review is active; live integration remains pending. Owned 14.85 GB logical scratch is removed. G08 diagnostic repair remains serialized after integration.

Root selects normal Bandit HTTP/1.1 and HTTP/2 framing for an isolated raw-body capture component. Nine dependency API probes replay with 49 root bindings and 69 exact hosted inputs. Capture implementation and real localhost wire/fake-adapter matrix are underway; endpoint transport privacy/cancellation, ingress, public admission, durable inbox/Oban, provider reconciliation and G23 remain pending.

Android pointer candidate5 is frozen with 42 host tests and byte-exact fresh private Java/DEX replay. Root verifies 284 repaired host bindings plus unchanged 507 producer/42 prior-review bindings. Independent oracle review remains active; no pointer native run or acceptance. Apple UI remains unavailable because the Mac is locked; no instance started by the latest check.


Checkpoint `11133e60` now passes all three terminal engine CI jobs (Swift, VM and services), with all 38 steps successful and none skipped. See `verification/github-ci-11133e60-engine/receipt.json`. Its newer isolated host-operation, pointer-oracle repair and raw-body capture candidates are outside that CI scope.


Independent Android pointer candidate5 review confirms F06/F07: Activity delivery was not matched to its synchronous worker interval, and impossible UP/CANCEL history could replace all MOVE deliveries. Five synthetic false acceptances are retained; these are oracle findings, not observed Android defects. Root verifies 1,121 producer/review bindings and selects an oracle/runner-only correction on the identical APK and gesture schedule. All 42 prior tests and source/archive/signature/alignment checks pass; no pointer runtime is authorized yet. See docs/android-pointer-oracle-repair-review.md and verification/android-pointer-oracle-root-review/correction-selection.json.


Private imported-host operation is independently reviewed, root accepted and integrated byte-exactly at 128-file closure7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329. Root verifies1910 upstream/30 integration bindings; fresh265all-feature Release library tests,16Frozen Release tests, Swift Clippy and whitespace pass. Independent302executions,62fresh MIR bodies,16layout replays,4876positions and39unchanged Frozen methods remain scoped host evidence. Root scratch161551623bytes removed. G08 contextual diagnostic repair now proceeds on this baseline, including the new active host removal; full calls/dispatch/Ready/public/native/FieldLog/physical/GA remain open. See docs/swift-host-operation-integration-checkpoint.md.


Latest Android native result:

The unchanged candidate-5 APK now has an actual API37 arm64 pointer attempt after the timing/history oracle passed 55 host tests and 12 independent root controls. P01 tap and P02 hold each commit one revision. P03 rightward drag receives all ten events including UP, but remains off at revision3; 52 assertions pass and one fails, so the full20-action matrix is not accepted. Root verifies61 runtime files/43command outputs/7exports/14synchronous deliveries. Owned emulator group, ports and172952201-byte extraction are cleaned; unrelated emulator preserved. Read-only diagnosis precedes any changed experiment. See docs/android-pointer-native-checkpoint.md and verification/android-pointer-native-root-review/receipt.json.

Latest private Stripe capture candidate:

Root-selected normal HTTP1.1/HTTP2 raw-body capture candidate is sealed in isolation: root replays273 producer files, nine attempts and dependency/source pins. Final14 component tests and13 wire groups cover105 localhost clients (70H1/35h2c), with measured verifier calls and all responses non2xx. Independent implementation review is active; no live integration or public admission. Actual slow h2 rejects after5564ms; telemetry/log exposure and absent hard cancellation remain endpoint requirements. TLS/ALPN/ingress, durable inbox/Oban, provider reconciliation and G23 remain pending.


Latest private Stripe integration:

Private raw-body capture is independently reviewed, root accepted and integrated at71-input closure ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc. Fresh full hosted suite passes142tests with2existing namespace-fixture skips; production release build, expected missing-config rejection and capture test-clock/adapter exclusions pass. Root verifies433 upstream/composition bindings and117 integration files. Independent38groups/360subcases/110clients/31actual traced verifier calls remain scoped evidence. Three tested files applied; only module normalization is a final blank line. PostgreSQL, owned groups and63766343-byte root scratch cleaned. No public route/acknowledgment/provider/DB admission; endpoint privacy/hard cancellation, TLS/ALPN/ingress, inbox/Oban, provider reconciliation and G23 remain pending. See docs/stripe-raw-body-integration.md.

Latest Android diagnosis:

Root verifies the sealed offline P03 diagnosis:20owned files and177 read-only inputs. The actual UP was delivered and its after-send snapshot remains off at revision3. The final settled assertion fails but its snapshot was not exported. Official pinned AOSP arithmetic supports an authored-versus-carrier drag-range mismatch, with actual platform-private cause unobserved. Root is coordinating an authored-geometry input repair; the unchanged pointer fixture remains the regression contract. No new runtime or full pointer acceptance. See docs/android-pointer-native-diagnosis.md.


Checkpoint `2e1931b4` passes all three terminal engine CI jobs (Swift, VM and services), with all 38 steps successful and none skipped. See `verification/github-ci-2e1931b4-engine/receipt.json`. This qualifies the pushed private host-operation host/cross-build slice; subsequent raw-body integration and diagnostic/input repairs remain outside that run.


Root selected the authored-toggle input contract after 16 proposed-policy host tests and 44 input bindings. The root receipt binds 69 actual packet files and records the producer seal membership omission without mutating it. Isolated product implementation is in progress using shared drawing/drag geometry, original admission and ordinary listener ownership, with cancellation on lifecycle/binding/gate changes. The original 20-action native fixture remains immutable. Independent build/source review and a new emulator run remain pending; the prior P03 drag failure is not accepted. See `docs/android-authored-toggle-input-contract.md` and `verification/android-authored-toggle-root-review/selection.json`.

Checkpoint 8c634c49 passes exact-source Linux hosted CI: 142 tests pass, two network-namespace fixture tests remain explicitly skipped, and packaged release checks pass. All 71 archived source inputs match the integrated capture closure ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc. Root selects the dedicated private transport role, complete configured-sink boundary, whole-connection disposal, 16-connection envelope and fixed stage/outer deadlines after 150 sealed contract files and 228 root bindings. Isolated implementation is in progress. Public admission, resource ceilings, trailer policy, deployed ingress, provider/account/inbox and G23 remain pending. See `verification/github-ci-8c634c49-phoenix/receipt.json`, `docs/stripe-webhook-transport-direction.md` and `verification/stripe-webhook-transport-root-review/selection.json`.


The contextual cleanup diagnostic repair is independently reviewed, root accepted
and integrated without normalization at 128-file source closure
1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c.
Root verifies 2,010 upstream bindings and 31 integration files; fresh 282
all-feature Release library tests, sixteen Frozen Release tests, Swift Clippy
and whitespace checks pass. Active live-count failures now retain the current
instruction/resource/count; legacy cleanup remains cursorless and the first
failure remains immutable. Owned command groups and 166,955,154 bytes of scratch
are cleaned. Defined/indirect calls and the full dispatcher contract are next.
Original-source diagnostics, Ready/public invocation, native/FieldLog/physical
and G08/GA remain pending. See `docs/swift-cleanup-diagnostic-integration-checkpoint.md`.


The authored Android candidate now passes all 429 assertions in the original
20-action API37 arm64 pointer matrix, including all three P03 drag repetitions.
Root verifies 124 worker/Activity deliveries, 573 observations, 73 exports and
107 command outputs; owned emulator/groups/ports and 172,984,646 scratch bytes
are cleaned. Separate supplement runtime-3 crashed before exporting results;
zero component assertions are accepted, its cause is unobserved and all owned
resources are cleaned. A fixture-only reporting/diagnostic repair is underway.
Live production integration, preview/key/AX and broader authority/parity checks
remain pending. See `docs/android-authored-toggle-native-checkpoint.md`.

Pushed diagnostic checkpoint 2fb0db99 passes all three terminal engine jobs and
38 steps, with none skipped. Root selects the coherent defined/indirect calls
plus complete private dispatcher contract after 139 bindings, eight fresh
compiler contexts and four expected borrow rejections. CD01-CD24 runtime and
complete positive accounting remain pending; the uncalled compiler witness is
not execution or reservation evidence. See `docs/swift-calls-dispatch-contract.md`
and `verification/swift-calls-dispatch-root-review/selection.json`.

The native toggle diagnostic checkpoint is recorded in
`docs/native-toggle-diagnostics-checkpoint.md`: Apple partial simulator results
and the Android component scroll failure are preserved separately from the
accepted Android pointer matrix. All owned test instances are cleaned. The
private webhook transport is now integrated at72-input closure
789b7de9b46ef2ce65ad83a4c916dde9a513a8eaa68dfc073e4c65ec97e2ee93;
see `docs/stripe-webhook-transport-integration.md`. It remains inactive and passes
no public billing or GA gate. Checkpoint2f715b10 is pushed; VM and service CI jobs
pass while Swift CI is still running at this observation.

The permanent webhook transport tests and packaged release exclusions are now
integrated at73-input closure
1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997.
The isolated full host suite passes149tests with2namespacefixtures skipped;
production modules remain unchanged and inactive. See
`docs/stripe-webhook-transport-regressions.md`. Checkpoint09ee31ff passes the
preceding142-test Linux hosted suite and release checks; checkpoint2f715b10
passes all three engine jobs and38steps without skips. These CI receipts retain
their exact earlier source scope.

The fresh Android diagnostic delivered all9originalevents to the Activity and
actual child, but observed no positive content extent, interception or CANCEL.
Requested6000-pixel layout height measured532inside2622viewport. Root retains
the failed original assertion, trace and cleanup in
`verification/android-toggle-scroll-runtime-root-review/runtime-review.json`.
A fixture-only measured-extent correction precedes the unchanged45-case rerun;
no product input change or full component acceptance follows from this diagnosis.

The private Swift calls/dispatch candidate at source closure ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70 now has independent and root logical-accounting acceptance: 89,124 roles, 1,032 exact finite positions, eight compiler contexts and sixteen layouts. All 39 Frozen methods, the 2,912-byte Frozen bound, original owners and ceilings are preserved. Runtime preflight found three original fixture sums missing the new calls component. The separate V7 candidate at source closure 78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237 contains only those three expectation additions over V5; all eight implementation files remain unchanged. Fresh compiler evidence, root replay and final independent accounting review pass with all selected runtime MIR bodies unchanged. The sealed 27-command private runtime matrix now passes with 1,378 test executions, all 63 source/compiler and Node prelaunch checks, final Node pins and cleanup. Root accepted it, integrated eleven changed files and passed a fresh 342-test live-path check with the qualified tool environment. The first live check had one runner-PATH failure and remains preserved. Final integrated closure 3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3 differs from V7 only by removing spaces on seven otherwise-empty lines after the successful runtime checks; the exact formatting normalization is recorded and git diff --check passes. See verification/swift-calls-dispatch-root-review/sealed-v7/runtime-review.json and live-v7-integration-retry. Prior checkpoint 9a9c0e00 passes all three Engine CI jobs. No native, full Swift readiness, FieldLog, OTA or GA gate is closed by this development slice.
See `docs/swift-dispatch-accounting-checkpoint.md`.

The private iOS pan-commit carrier now passes a fresh iOS 26.5 simulator run:43 XCTest methods,45 native input actions and36 scoped direct callback components. Root replays1286 verdict predicates and324 native touch-origin predicates; zero bridge failures, all5cleanup operations pass, owned simulator/workspace absent. The first26pass/17fail run and four original plain-UIKit reference failures remain recorded. App/runner bytes are unchanged; the new harness corrects startup-history validation and atomic observation reads. Keyboard/focus, remaining lifecycle retirements, compositor parity, live Apple integration, physical final matrix, FieldLog and GA remain pending.
See `verification/apple-toggle-pan-commit-root-review/failed-runtime-review.json`.


The private Linux resource harness V5 now has independent and root source/host-method acceptance with no open findings. All 82 producer controls and eight independent controls pass. V4 repaired child-PID-namespace lifetime tracking and immutable retry history; V5 additionally preserves each successful descriptor observation before a later read error, deadline or proved exit. Final physical-zero proof stays separate from historical positive counts. All prior packets and unchanged C/NIF/role/signal bytes remain preserved. Separate compiler prerequisite V4 now passes four native compilations and exported repeat equality; no helper/NIF/BEAM execution or resource runtime row has run. Controller integration and all 30 runtime rows remain pending. See docs/stripe-resource-harness-v5-source-checkpoint.md and verification/stripe-webhook-resource-ingress-root-review/v5-source-acceptance/receipt.json. No production transport, provider or GA acceptance.
