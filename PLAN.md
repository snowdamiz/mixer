# Execution index

The complete specification is [mixer-product-plan.md](mixer-product-plan.md).
All W01–W18 packages, G01–G38 launch gates, and D0–D8 dogfood milestones remain
in scope. No internal slice substitutes for those completion requirements.

Section 8.3 requires the same shared app design on iOS and Android. Shared theme
values control layout, typography scale, colors, iconography, spacing and component
appearance; platform-specific app appearance requires an explicit declaration.
Native accessibility, navigation, text input and system-owned surfaces retain their
platform behavior. The existing adapters do not yet satisfy this appearance
contract. W03/W04/W05 must coordinate its shared schema and renderer changes;
W17/G06 require side-by-side physical reference-screen review. Those device checks
remain pending while phones are disconnected. See
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

Physical phones are disconnected until the user says otherwise. Continue source
implementation, host tests, cross-compilation and simulator validation. Preserve
completed device receipts and mark subsequent physical-device checks pending;
do not retry devices or request reconnection during this limitation.

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
V2 data implementation is under independent review. Native consumers, resource/bootstrap support,
signed V2 installation, interaction and physical design parity remain pending.

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

Hosted `7855754` passes all three jobs. Hosted `26943ac` passes VM/services but fails
Swift bridge TSan with session/native-exit publication race reports and an
HTTP native-exit fixture timeout. Investigation and separately validated repair
are in progress; see `verification/github-ci-26943ac/receipt.json`.

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
