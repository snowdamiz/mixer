# CapabilityHost deadline correctness finding

**Confirmed:** `CapabilityHost.complete()` can select and deliver success after the configured host timeout if its detached watchdog has not run its deadline handler. The host currently records no monotonic cutoff. The watchdog starts a relative `Task.sleep` when that task is scheduled, and `complete()` checks ownership/liveness but does not check time. Normal asynchronous scheduling can therefore make a late worker result win the first-terminal race.

The installed exit lease addresses a different obligation. `complete()` retains the slot when `exitLease` exists; `CapabilityExitLease` joins adapter cleanup with invocation return before the observer schedules slot release. That retention does not make a late success a valid timely result. The concrete HTTP adapter has its own private monotonic clock, but a shorter host default is still a separate authority; storage has no equivalent host-budget check inside its result path.

## Narrow proposed fix, not applied

`proposed-fix.patch` is a reviewable Host-only candidate kept outside the SDK:

1. Add an optional `ContinuousClock.Instant` cutoff to each slot. Compute it from the effective timeout after policy approval and before launching work. HTTP uses `min(request timeout, host default)`; storage uses the host default.
2. Immediately before invoking the adapter, reject an already-expired worker with `deadlineExceeded`. When no adapter was invoked, explicitly call the optional installed `lease.adapterExited()` under `#if !os(WASI)`; the existing worker `returned()` defer supplies the other half of the exit join.
3. Sleep the watchdog until that captured absolute cutoff. Check the stored cutoff before handling a watchdog notification.
4. Inside `complete()`, select `deadlineExceeded` when the monotonic cutoff has passed; otherwise use the worker outcome. Preserve the existing first-terminal guard, installed exit-lease retention, and legacy release branch.
5. Clear the cutoff when releasing the slot.

The pre-invoke check rejects worker admission already known to be late. Suspension can still occur after that check and before I/O; this does not prove absence of all side effects after a deadline. The cutoff is a logical completion-selection boundary. This does not promise that callback execution, cancellation, native effects, or OS resource teardown happens by an exact real-time instant. No rollback guarantee is added. Adapter deadline propagation and platform qualification remain separate work.

## Original test and exact experiment scope

Eleven existing source inputs were captured read-only under ignored `.build/capability-deadline-review/original` and hashed in `source-manifest.sha256`. Only a small direct compiler harness was built: the original JSON guard module, original native lock helper, and eight selected capability source files. No package-wide build, device, network endpoint, SDK/generator/identity edit, push, or deployment was used. The operation is a permitted get of an absent key in a temporary installed `AppPrivateKeyValueStore`.

The unchanged Host control uses the existing internal installed-adapter `afterInvocation` seam to hold worker return. For the reproduction, `test-only-watchdog.patch` adds exactly one scheduling gate immediately before the watchdog's existing relative sleep in a captured Host copy. This models withheld watchdog execution; it is **not an unmodified public late-success reproduction**. The real codec, grant policy, installed storage adapter and native exit lease remain in the test.

Observed runs on macOS arm64 / Apple Swift 6.4:

| Case | Host timeout | First terminal | Observed delivery |
| --- | --- | --- | --- |
| Unchanged Host, normal watchdog control | 25 ms | `deadlineExceeded` | 27.454 ms |
| Captured Host, watchdog held by test gate | 25 ms | **success** | 107.151083 ms |
| Derived fix candidate, watchdog held | 25 ms | `deadlineExceeded` | 107.856583 ms |
| Derived fix candidate, timely result | 500 ms | success | 0.969208 ms; remained sole terminal after an expired-deadline handler call |
| Derived fix candidate, worker admission and watchdog held | 25 ms | `deadlineExceeded` | 101.439625 ms; zero adapter invocations and storage key remained absent |

These observed times are host-test observations, not performance guarantees. The ordering/cutoff assertions in the programs are the correctness checks.

The candidate experiment has additional isolated instrumentation, separated in `candidate-test-only.patch`: it holds the worker **after `complete()` returns but before `invocationReturned()`** and exposes a same-file test-only forwarding method for the existing deadline handler. The late completion failure, timely success and delayed-admission failure all retain the single slot with zero exit callbacks while that worker gate is held. The delayed-admission PUT records zero adapter invocations, leaves the storage key absent and still completes one exit observation after return; this exercises the explicit no-adapter exit compensation. Releasing it produces exactly one exit callback and permits generation 2. The later deadline notification cannot replace the earlier terminal result. This tests the exit-join branch and prevents a deadline repair from freeing capacity with terminal delivery.

`verify.py` reconstructs/runs the original control and delayed-watchdog reproduction. `check_candidate.py` uses the same frozen inputs and compiles/runs the three derived candidate cases. No production patch is applied by either script. Each receipt records exact commands, source and output hashes, tools, and scope. Two initial harness-only Swift 6 isolation compile failures are preserved with their original test sources, diagnostics and receipts; the final probes corrected helper actor annotations/await placement and passed.

## Limits before production work

The candidate was compiled and exercised only on this macOS arm64 toolchain. ContinuousClock/Foundation availability and behavior still require the actual WASI cross-build and the project's other supported compiler/platform gates before adopting the change. Physical devices stayed disconnected. This is not native HTTP endpoint testing, native cancellation timeliness, scheduler fairness, guest/import/activation qualification, immutable package dogfood, or release/GA authorization. Production source bytes were checked unchanged after the probes.

The immutable captured Host SHA-256 and the proposed fixed Host SHA-256 are recorded separately in `receipt.json`. Root may apply the production-only patch after the codec source freeze; that later coordinated production change does not alter the captured review base or make this lane a production editor.
