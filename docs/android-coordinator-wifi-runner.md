# Android coordinator runner with process-local Wi-Fi fallback

This separate runner preserves the immutable candidate-2 APK, its 105 source
inputs, 177 artifacts, eight prepared JNI/Swift/coordinator operations, all app
assertions, and the accepted extraction/command-group cleanup. The root-dispatched
boot-only experiment passed with the process-local `-feature -WiFiPacketStream`
fallback. That boot receipt does not qualify the APK or any app assertion.

`verification/android-coordinator-wifi-runner/run.py` binds the original cleanup
runner by SHA-256 and applies ten individually counted exact source replacements.
The concrete transformed source, its SHA-256, and an explicit diff are retained
in the host review. Any base/helper/probe/contract/boot receipt drift fails before
native execution. It does not rebuild the APK or copy its frozen evidence packet.

The only emulator launch delta is appending `-feature -WiFiPacketStream` after the
original base session equality succeeds. Ownership checks use the accepted boot
probe's exact installed launcher or `qemu-system-aarch64-headless` path and require
PID equal to the newly owned group, AVD `megpt-parity-api37`, port `5586`, approved
GPU, disposable flags, and the fallback pair. The observed executable is hashed
again before every use or cleanup decision. The four existing process queries
include PGID; current source revision/tree commands bind runner evidence. APK/source/archive checks and all app assertions remain intact.

Port 5586 with ADB 5587 exceeds the installed `-help-port` recommendation. This
known limitation stays unchanged to preserve the proven one-variable experiment.
No shared netsimd/global configuration or other project's process/data is changed.
Physical phones remain disconnected and their final matrix remains deferred.

Root alone may dispatch a fresh attempt after reviewing the frozen host packet:

```sh
python3 -B verification/android-coordinator-wifi-runner/run.py \
  --build candidate-2 --attempt runtime-1 --execute-native
```

Host tests execute the transformed main with injected synthetic tools/child
objects and run the original extraction guards against the transformed runner.
They cannot qualify APK, emulator runtime, physical-phone, public/signed,
FieldLog, store, customer, or GA acceptance. Actual runtime acceptance remains
pending until root dispatch produces the unchanged app assertions and a stopped
owned emulator, absent group/ports, and removed owned extraction.
