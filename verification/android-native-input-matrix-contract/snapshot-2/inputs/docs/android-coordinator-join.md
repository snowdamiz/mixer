# Private ordinary Android coordinator join

The [candidate-2 build](../verification/android-coordinator-join/candidate-2/receipt.json)
contains a real private APK joining the unchanged ordinary `ChecklistEngine` and
`AndroidSessionRegistry`, the actual C JNI bridge, `NativeBridge`, production
`NativeCoordinatorV2`, and concrete native renderer. Its Java source is compiled
against SDK37, its Swift code is cross-compiled with the installed Swift6.3.3
Android SDK, and its JNI is linked with NDK r27d Clang. No host Android, JNI,
renderer or engine leaf substitutes enter this APK.

The APK is **built; native runtime tests are NOT RUN**. The Mac was locked and
root had not dispatched native execution. No emulator, simulator, physical target,
UI automation or screen capture was started or queried by this work. The
[runtime status](../verification/android-coordinator-join/runtime-status.json)
records zero executed native assertions. The previous pause is historical; the
current limitation here is the pending explicit root dispatch after unlock.

The [headless identity check](../verification/android-coordinator-join/headless-review-2/receipt.json)
verified 105 frozen inputs, 63 successful build commands and 177 retained compiled
artifacts. All ten renderer sources match root's accepted candidate16. The exact
production coordinator class bytes are compiled separately against real platform
declarations, then included in the joined DEX with the verification harness.
The checker compares source/command seals, native libraries and DEX inside the
APK, its installed-descriptor bytes, and the disposable debug certificate identity.
This verifies packaging and identities, not execution on Android. The corrected
checker removes its temporary extraction in `finally` after checking that no
process holds it open, and records cleanup explicitly. Its 177-file extraction
was removed. The original review's
[checker bytes](../verification/android-coordinator-join/headless-review-1/verify.original.py)
and receipt/outcome are preserved; its unused extraction was separately checked
for open holders and removed with an
[independent cleanup receipt](../verification/android-coordinator-join/headless-review-1/extraction-cleanup.json).
Four [controlled host cleanup cases](../verification/android-coordinator-join/headless-cleanup-tests/receipt.json)
also pass: success, an operation failure followed by `finally` cleanup, refusal
while a file is held open, and refusal of a substituted symlink. Every owned
test extraction was removed after its safety conditions were restored.

| Identity | SHA-256 |
| --- | --- |
| APK | `396466de00b4b905c664632e711a5dcda151f85af1a4f9e47c6ff1b68e5c276c` |
| Frozen source closure | `ec2acb7c78862d899a4722d8f2c11d90d47c2cc4726af00976d392536fb85b30` |
| Installed descriptor | `1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3` |
| Disposable debug certificate | `bdd5da6ec07e37c44f3d973868e8a1a1ed5ceff97a7e312a5fb72704b3167b09` |

The [retained archive](../verification/android-coordinator-join/candidate-2/built-artifacts.tar.gz)
contains the APK, production/harness classes, DEX and complete native dependency
closure. Each ELF is AArch64 and its load segments meet 16KiB alignment; zipalign
checks native APK alignment. The disposable local debug key is deleted, its random
password is supplied through the command environment, and neither is archived.
No production credentials are used. The exact compiler/tool versions, hashes,
commands, outputs, source revision and source tree digest are in the build receipt.

The separate application ID is `dev.mixer.android.coordinatorjoin`; its manifest
declares only the verification Activity and Instrumentation. The public
`MixerActivity`, its V1 bootstrap, and signed transport are unchanged. The private
APK minimum is API36 and the intended executed environment is the accepted API37
arm64 emulator. The Swift SDK triple's API28 component is a compiler/link target,
not API28 runtime support. Even a later API37 pass will not qualify API36 or other
OS, font/resource or device environments.

The bounded eight-operation fixture is compiled into the APK and installed as an
asset. The native instrumentation requires API37/arm64, density3, a 1206×2622
pixel root, default native font scale/profile, and the exact packaged descriptor
hash. Native capture validation remains authoritative and unsupported captures
fail closed. These are prepared assertions, each **NOT RUN**:

| Operation | Actual executable assertion scope |
| --- | --- |
| JNI | Real session creation; defensive candidate copies; observed busy, stale, closed and rejected-input statuses; abort/idempotence; one-use commit; ordinary Swift reducer state after commit. No invented engine status. |
| Initial | Actual AssetManager descriptor and attached Activity environment; ordinary Swift checklist packet through the production coordinator into native views. |
| Toggle | Actual `Switch.performClick` callback through coordinator/JNI/Swift; one document revision increase; surviving native control agrees with committed state. |
| Text | Actual native `InputConnection.commitText` and ordinary reducer acknowledgement of the editor buffer. No system keyboard/composition workflow claim. |
| Environment only | Exact retained packet object/bytes; an actual pending registry candidate survives refresh; no extra prepare token is allocated; native capture invalidation closes forwarding, refresh reopens it; actual software `View.draw` canvas probe. |
| Attachment fault | Existing concrete renderer fault seam triggers a real attachment failure; production coordinator retires native and Swift owners and leaves forwarding closed. |
| Lifecycle | Real Activity destruction and relaunch; destruction of a live harness-owned coordinator closes the actual Swift session and native owner; a new Activity gets a fresh session. No persistence/process-death claim. |
| Rejection | Actual malformed ordinary input rejected by Swift; production coordinator/session/renderer retire and subsequent operations reject. |

The harness records every actual scalar status, check outcome, native environment,
ordinary packet bytes and SHA-256 provenance in app-private files. A runtime runner
exports them and verifies the installed APK hash. This bounded integration matrix
does not replace the existing headless coordinator fault matrix or qualify the full
native fault/IME/lifecycle suite, system keyboard interactions, hardware paint,
accessibility workflows, arbitrary app behavior or cross-platform design parity.

Headless build and review commands, using fresh evidence names, are:

```sh
python3 -B verification/android-coordinator-join/build.py --attempt candidate-3
python3 -B verification/android-coordinator-join/verify.py --build candidate-3 --attempt headless-review-3
```

The final collector and runner are frozen in candidate2. Four headless safety
tests passed: exact owned PID/port/AVD identity; archive traversal/link/membership
rejection; exact emulator-environment rejection; and timed-out child/grandchild
process-group cleanup. Every build command runs in a newly owned process group;
timeouts and unexpectedly retained descendants are cleaned within that group and
fail the attempt. These tests start ordinary controlled host processes only.

Before native dispatch, the frozen runtime runner still needs equivalent
temporary-extraction cleanup on success and failure. Static inspection found that
its `finally` handles the owned emulator but retains its extracted `.build`.
The [pending finding](../verification/android-coordinator-join/runtime-runner-cleanup-inspection.json)
records the exact unchanged runner hash and required correction. It has not been
run. After that correction and explicit root runtime dispatch, its invocation is:

```sh
python3 -B verification/android-coordinator-join/run.py --build candidate-2 --attempt runtime-1 --execute-native
```

It refuses occupied ports5586/5587 and an existing reserved-port instance. It
verifies the pinned AVD metadata, booted API37/arm64 image fingerprint and owned
child PID/port/AVD before installing or stopping anything. It creates at most one
read-only/no-snapshot instance of the existing `megpt-parity-api37` AVD, applies
the viewport only there, and addresses only `emulator-5586`; it never enumerates
physical targets. Its existing emulator `finally` cleanup stops only its owned
instance, rechecks exact
identity before PID fallback signals, collects any descendants confined to its
new group, and records process/port cleanup on failures as well as passes. Other
projects' emulators and data are preserved. No command above was used to start
native runtime during this slice.

[Candidate1](../verification/android-coordinator-join/candidate-1/receipt.json)
is a retained failed attempt: Swift, JNI, Java, DEX and APK signing had succeeded,
but the receipt parser expected the older apksigner certificate label. SDK37 emits
`V3.0 Signer`. Candidate2 fixes that parser and strengthens command-group cleanup.
The first disposable key was also deleted. Its echoed debug-password text was
removed from the log and frozen collector with original/redacted hashes recorded
in [redactions.json](../verification/android-coordinator-join/candidate-1/redactions.json);
the original source hash remains in its source lock. That attempt is not a pass.

Native acceptance, the complete native matrix, physical final acceptance,
side-by-side iOS/Android review, public V2 integration, signed authority,
immutable published FieldLog qualification, stores, customers, operations and GA
remain pending. Root must review observed native results before accepting a
runtime development slice.
