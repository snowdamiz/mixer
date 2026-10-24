# Cold-start milestone CI repair

The hosted Swift job for `6bee9510ac31456464c1e3a20024fc93dddc5fa7` failed in
`testEarlyInstalledMilestonesWakeAutomaticHealthAndStartupAloneDoesNot` at the
actual busy admission guard in `CapabilityColdStartControl.swift:102`. Its
Installed capability material and exact native preimage step ran 119 tests with
one unexpected failure. It was a normal host test step, without ThreadSanitizer.
The VM and services jobs passed; later Android binding/generated-consumer steps
were skipped. The authoritative captured logs are
`verification/github-ci-6bee951/{receipt.json,jobs.json,swift-job.log}` for run
40060002619, job 120771241624.

## Cause and change

`CapabilityColdStartRuntime.reportMilestone` synchronously calls
`control.admit(.milestone)` before capturing work or entering the worker actor.
That boundary intentionally rejects an ordinary mutation, cancellation, or
`notificationBusy`. The automatic consumer sets `notificationBusy` through
`beginNotification`, keeps it across `await reconcileOwned`, and clears it on
return. Thus sequential public calls do not guarantee a free admission slot.
The existing API design explicitly requires busy rejection before capture:
`docs/capability-durable-updater-api-design.md`, “Proposed public façade.”

The old test directly reported `feature_started`, waited 1100 ms against a
one-second observation timer, and directly reported `first_screen`. Its calls
could meet the automatic consumer while it held admission. The log identifies
the busy guard, but does not prove which public report or exact scheduling
sequence occurred on the hosted machine.

The test now uses a private `reportInstalledMilestone` helper with an eight-second
monotonic deadline and a two-millisecond suspension between retries. It retries
only `UpdateError.code == "capability.runtime.busy"`; every other error propagates.
Both the reports-before-timer and second-report-after-timer cases use it. The
unknown installed milestone assertion now requires the actual
`capability.runtime.milestone` rejection after admission instead of accepting an
arbitrary error. No product source, runtime admission bound, interval, native
adapter, signing behavior, or public retry/queue contract changes.

Every existing startup, nil-health, eventual-health, candidate, timing, and close
assertion remains. The pre-timer case still requires nil health immediately after
both reports. A sufficiently delayed caller can miss that checkpoint; the helper
does not redefine it or increase the observation interval. Controlled verification
additionally observes the real timer unfired when the held feature report returns.

## Reproduction and evidence

Run `python3 verification/cold-start-milestone-ci-repair/run.py --name NAME` for
fresh Debug, Release, and ThreadSanitizer host builds. The driver freezes the
Swift/C/header/fixture bytes and the exact cached Swift Crypto source revision,
then builds the native archive from the pinned Git revision into its own scratch
directory. It never consumes an active lane's uncommitted Rust changes or an old
Swift module. Every command, selected environment value, tool version/hash,
source tree digest, native archive digest, log digest, and result is retained.
The archive is built with `--locked --offline --release --lib
--no-default-features --features experimental-capability-native`.

Production activation is compiled separately from derived activation in each
mode. The full unchanged repaired eight-test fixture runs against production
activation. Separate immutable derived sources add only observation/scheduling:

- Hold the real worker immediately after `beginNotification` returns true and
  before reconciliation; release it without changing its production conditions.
- Observe busy rejection inside the unchanged admission predicate and observe
  milestone effects only after the real store report returns.
- For the pre-timer case, issue the existing generation-checked control wake to
  the installed observation's real consumer. This is a notification hint, not
  a milestone or health result.
- Observe retries in the test helper without manufacturing errors or success.

The controlled original early test must fail on the real busy guard while a real
notification is held after the actual timer fires. The repaired early test must
retry at least three times, remain unreturned with no accepted report or health
while held, then report exactly `first_screen` and earn the original candidate's
health after release. The pre-timer case proves the analogous behavior for
`feature_started`, observes the real timer unfired at release, retains the
nil-health checkpoint after both reports, and promotes through the real timer
without additional public calls. Separate checks require exact invalid-ID and
closed error propagation and exercise the actual eight-second retry deadline
while notification admission remains held. Cleanup joins the real runtime.

`verification/cold-start-milestone-ci-repair/final-1/receipt.json` is the qualifying
receipt. Its source-only replay archive, manifests, exact derivation diffs, and
logs are retained alongside it. To replay those exact inputs, run:

```sh
python3 verification/cold-start-milestone-ci-repair/run.py \
  --name replay-1 \
  --source-archive verification/cold-start-milestone-ci-repair/final-1/source.tar.gz
python3 verification/cold-start-milestone-ci-repair/verify_saved.py --name final-1
```

The saved verifier checks source/archive/log hashes, exact source bindings,
production fixture test names/count, expected original failure, real before/after
timer observations, required successful checks, compiler instrumentation flags,
and the absence of ThreadSanitizer warnings. Candidate 1 preserves an initial
verification-driver failure caused by an unavailable implicit `rustc` executable;
the driver now supplies the actual compiler path. Candidate 2 is the successful
Debug preflight. Neither replaces the complete qualifying receipt.

The qualifying run passed Debug, Release, and ThreadSanitizer: 24 unchanged
fixture tests, 12 repaired controlled checks, and three expected original busy
failures. No ThreadSanitizer warning appeared. The strict saved verifier passed.
Tools were Apple Swift 6.4, Xcode 27.1 (27A9275), macOS 27.0.1, and Rust 1.99.0.
The source revision and native archive source revision were both
`6bee9510ac31456464c1e3a20024fc93dddc5fa7`; the exact working Swift test repair is
bound by the input manifest. The complete derived source tree digest is
`7a60223c6c7cd4f7360fb524c4bfb2ea7651f007e5233dd6988d6b6a33f2b8c0`, and the
fresh native archive digest is
`af0acddd9ce7cf510e55e8413b1df112860e868d877c5b4dcd08b3862aa6c69f`.

`verification/cold-start-milestone-ci-repair/cleanup.json` records the fresh
`lsof` absence checks and deletion of this lane's three completed scratch builds
(1,079,183,326 bytes). Source replay archives, manifests, derivation diffs,
commands, and logs remain; build trees and native/test binaries are excluded.

## Limits

These are headless macOS XCTest development receipts. Swift/C code is rebuilt
and instrumented for ThreadSanitizer; the Rust archive and Apple system frameworks
are outside its instrumentation. The native source revision is pinned separately
from active Rust lane edits, which need their own evidence. Controlled schedules
prove an allowed overlap, not the exact historical hosted interleaving. A future
hosted CI pass is a separate observation. Computer use, native UI, simulator,
emulator, and physical-device tests remain pending under the user's pause.
Published consumer, distribution signing, store, customer, operational, and GA
gates are not qualified by this repair.
