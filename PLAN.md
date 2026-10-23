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
