# Ordinary Android coordinator runtime status

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

An isolated read-only crash diagnosis is in progress before another experiment.
This headless path has no host GUI dependency; Apple touch/accessibility checks
separately remain blocked by the locked Mac. Physical phones remain deferred.
Public V2, complete input/IME/lifecycle coverage, shared design parity, signed
updates, published FieldLog and GA gates remain open.
