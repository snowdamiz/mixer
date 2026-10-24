# Ordinary Android coordinator runtime status

Latest root result: **eight operations and 64 native checks pass** on the owned
API37 arm64 emulator. The final test instance and extraction are cleaned. Read
[the current acceptance](android-coordinator-join-acceptance.md) for exact scope.
The failed attempts below remain preserved as historical evidence.

The unchanged frozen ordinary Swift/JNI/private V2 coordinator/renderer APK builds
and passes root artifact checks. Its separately bound runtime-runner correction
passes 24 host cleanup/identity guards and root replay of 184 sealed host files.

Root attempted actual headless API37 execution twice. Both emulator instances
exited before boot, with QEMU hanging-thread diagnostics and targeted ADB offline.
Neither attempt installed the APK or executed native assertions. Both failed
receipts remain failures; no native acceptance follows from the successful build.

Each attempt verified its exact owned PID/AVD/port profile, used read-only and
no-snapshot mode, and preserved the unrelated running emulator. The owned process
groups were absent at cleanup, ports 5586/5587 were free, and all 177 extracted
artifacts (172,884,977 bytes per attempt) were removed after empty holder checks.
The retained command logs, source identities and cleanup results are bound by
`verification/android-coordinator-join-root-review/runtime-attempts-status.json`.

The read-only crash diagnosis locates both hangs in virtual Wi-Fi netsim channel
startup. A root-dispatched boot-only experiment now passes with the sole launch
delta `-feature -WiFiPacketStream`; the owned group and ports were cleaned up.
Root verifies 102 saved evidence bindings and fifteen host guards. See
`docs/android-emulator-boot-diagnosis.md` and
`verification/android-coordinator-join-root-review/boot-probe-acceptance.json`.
This experiment installed no APK and ran no app assertions. A separately bound
full runner adaptation preserves the frozen build and assertions while adopting
the fallback and exact installed headless executable identity checks.

Root has now dispatched that full runner after replaying all 32 host guards and
verifying 1,116 sealed packet files. The emulator booted and installed the exact
frozen APK. Twenty-six native checks passed; check 27 stopped the run because
the fixture required `Switch.performClick()` to return true. Android defines
that Boolean as whether an assigned `OnClickListener` was invoked. This native
switch uses `OnCheckedChangeListener`; the later reducer revision, checked-state
and identity assertions were never reached. The failure is retained at
`verification/android-coordinator-wifi-runner/runtime-1/receipt.json`, with root
review in `verification/android-coordinator-join-root-review/wifi-runtime-1-review.json`.
The owned PID 20813, process group and ports were cleaned up, as was the
177-file extraction. A separately built instrumentation correction will record
the click-listener return contract and retain all actual state assertions.
Fresh runtime qualification is required; no app acceptance follows from this run.

The corrected click fixture passed 36 fresh root host guards and entry-content
parity checks. Its first native run booted but failed APK installation before
any app assertion: the repack changed `resources.arsc` from stored to compressed.
Root independently confirms identical resource bytes but different compression
methods; the earlier build review did not inspect that metadata. Both failures
remain preserved. Owned PID 26757, its group, ports and 177 extracted files
(172,885,588 bytes) were cleaned. A separate APK-only correction will check
actual local ZIP offsets, stored resources and native-library alignment before
any native command and again before installation. See
`verification/android-coordinator-join-root-review/click-fixture-runtime-1-review.json`.

This headless path has no host GUI dependency; Apple touch/accessibility checks
separately remain blocked by the locked Mac. Physical phones remain deferred.
Public V2, complete input/IME/lifecycle coverage, shared design parity, signed
updates, published FieldLog and GA gates remain open.
