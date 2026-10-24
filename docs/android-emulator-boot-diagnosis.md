# Android Emulator boot diagnosis — October 24, 2026

The two private coordinator attempts fail inside host emulator initialization,
before guest boot or APK installation. Both owned QEMU main threads are sleeping
in `netsim::packet::GetChannel` while realizing the virtual Wi-Fi device. The
emulator's hang detector then invokes `CrashReporter::GenerateDumpAndDie`.
This identifies the blocked startup subsystem. It does not establish why the
netsim channel is unavailable.

The separate boot-only experiment adds only `-feature -WiFiPacketStream` to the
original profile. Root dispatched it successfully on October 24 at 11:24 UTC.
The API37 guest booted and its owned process group and ports were cleaned up.
No APK was installed; no product engine or frozen native runner was changed.

## Observed evidence

| Item | First attempt | Second attempt |
| --- | --- | --- |
| Frozen receipt | `verification/android-coordinator-runner-cleanup/runtime-1/receipt.json` | `verification/android-coordinator-runner-cleanup/runtime-2/receipt.json` |
| Owned PID | 12041 | 13312 |
| QEMU launch, local UTC−04 | 07:09:10.3002 | 07:12:32.6744 |
| Crash capture, local UTC−04 | 07:09:45.6185 | 07:13:07.9531 |
| Faulting thread | 4: emulator hang detector | 4: emulator hang detector |
| Blocked startup thread | 37: netsim channel setup | 37: netsim channel setup |
| Android boot polling | Targeted ADB reports offline | Targeted ADB reports offline |
| Product execution | No APK installation or app assertions | No APK installation or app assertions |
| Existing cleanup evidence | Owned group absent; ports 5586/5587 empty; 172,884,977-byte extraction removed | Owned group absent; ports 5586/5587 empty; 172,884,977-byte extraction removed |

The exact crash paths are
`~/Library/Logs/DiagnosticReports/qemu-system-aarch64-headless-2026-10-24-070947.ips`
and `...-071308.ips`. Their PIDs match the owned-instance receipts, and their
parent processes are the two Python runners. Sanitized copies of every thread's
frames, with raw report SHA-256 bindings, are retained in
`verification/android-emulator-boot-diagnosis/analysis-1/runtime-{1,2}-crash-summary.json`.
Unrelated crash report contents were not read.

Both reports show this startup stack:

```text
nanosleep
std::this_thread::sleep_for
netsim::packet::GetChannel
netsim::packet::CreateChannel
android::qemu2::NetsimWifiForwarder::init
virtio_wifi_device_realize
...
main_impl / run_qemu_main / enter_qemu_main_loop
```

The four HVF CPU threads wait in `qemu_cond_wait_impl` /
`qemu_hvf_cpu_thread_fn`. The faulting stack is
`CrashReporter::GenerateDumpAndDie` → hang detector. Thus the macOS SIGSEGV
report records the emulator's deliberate dump-and-exit path after a hang;
it is not evidence that application code dereferenced null.

The frozen process snapshots already contain unrelated netsimd PID 18757,
parented by the preserved Morse emulator PID 18715. This lane made no new
target discovery and did not query, signal, restart, reconfigure, or read
the private logs of that shared daemon or emulator. A shared-daemon problem
is plausible but remains unproven.

## Environment and independent limitations

The profile is emulator 37.2.12.0, build 16428233, macOS 27.0.1 (26A434),
API 37 arm64 image
`google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys`,
AVD `megpt-parity-api37`, with:

```text
-port 5586 -read-only -no-snapshot -no-window -no-audio
-no-boot-anim -gpu swiftshader_indirect
```

The historical appearance candidate-16 receipt passed on this same recorded
profile. Its emulator launcher SHA-256 matches the installed launcher
(`5e2249e94368759aabd8fa942d2961cfef07b980a44639a2ec9b7ced3fbe2281`).
Current exact AVD config and system-image `source.properties` hashes match the
historical session. These checks do not bind all mutable host/daemon state
or every system-image byte.

Both failed logs pass disk/system compatibility checks and initialize the
SwiftShader/ANGLE renderer. No captured active stack establishes a GPU or
host GUI-lock cause. The host lock state therefore is not a demonstrated
explanation for these failures.

There is a separate profile defect: the installed `emulator -help-port`
documents even console ports 5554–5584, while console 5586 reserves ADB 5587.
Both emulator logs warn that ADB 5587 is outside the recommended range.
The diagnostic deliberately preserves that port to change one variable.
The warning must remain a limitation and a later port correction must be
recorded separately; it does not explain the observed netsim stack by itself.

## Documented experimental control

Android's official
[interconnect documentation](https://developer.android.com/studio/run/emulator-networking-interconnect)
documents the per-process `-feature -WiFiPacketStream` fallback to the previous
networking model. The installed emulator's `-help-feature` documents disabling
features with a leading minus. Its installed `advancedFeatures.ini` has
`WiFiPacketStream = on`.

Current public platform source also explains the stack shape:
[`NetsimWifiForwarder::init`](https://android.googlesource.com/platform/external/qemu/+/ae9d18d2b6261179fbd57fffec720a04f7bfb053/android-qemu2-glue/netsim/NetsimWifiForwarder.cpp)
obtains a channel before constructing the Wi-Fi packet stream, and
[`GetChannel`](https://android.googlesource.com/platform/tools/netsim/+/aaebb6787db0840a22d417fae5c97655946edbf4/src/backend/packet_streamer_client.cc)
serializes setup and sleeps between readiness retries. These are pinned
public reference revisions, not proven source matches for the installed
binary. The local symbolicated crash stacks supply the direct failure evidence.
No emulator implementation was copied into product code.

Official URLs, retrieval time, source revisions, and response hashes are in
`verification/android-emulator-boot-diagnosis/official-sources.json`.

## Boot-only probe and verification

Root approved a separate probe that preserves the exact original arguments,
AVD/image/tool metadata, GPU mode, port pair, read-only mode, no-snapshot mode,
180-second boot deadline, and bounded cleanup. Its only launch-argument delta
is `-feature -WiFiPacketStream`.

The executable is `verification/android-emulator-boot-diagnosis/boot_probe.py`:

- SHA-256: `97acdc54e9f45e5a08ab629154101e97328886e63460e21dae0019962827b366`.
- Contract SHA-256: `954c48ab47b5b3da0c3aaca3b0e65b7c0727771dc8a9b39234e617bdb02bbec4`.
- Root dispatch: `PYTHONDONTWRITEBYTECODE=1 python3 verification/android-emulator-boot-diagnosis/boot_probe.py --attempt boot-probe-1 --execute-native`.

The probe binds the original runner, accepted process-group helper, both
failure receipts/crash summaries, exact source metadata, installed emulator /
headless QEMU / netsimd / ADB hashes, and official control receipt. It requires
empty reserved ports and refuses an existing process using console 5586.
Ownership checks require the exact PID, process group, installed executable,
AVD, port, GPU, feature, and disposable-mode arguments. The explicitly allowed
headless executable matches both original crash reports and is hash-bound.
Wrong executable/PID/port/AVD and duplicate flags fail closed.

On successful boot it records the exact emulator identity, then stops only its
owned child and verifies group/port absence. The `finally` path performs the
same cleanup after a boot error; an unavailable identity or cleanup check is
recorded as failure. There is no APK install, app invocation, viewport or
settings change, global ADB discovery, physical-phone query, shared-daemon
reset, or AVD data edit in the probe.

Fifteen host-only tests exercise exact identity positives/rejections, contract
drift, explicit dispatch refusal, reserved-port/process refusal, success,
early exit, virtual boot deadline, wrong target, identity drift, termination
fallbacks, and cleanup unavailability. Every emulator, ADB, and process operation
in those tests is injected; no runtime was launched by this lane. The retained
command/tool/source/output receipt is
`verification/android-emulator-boot-diagnosis/host-review-1/receipt.json`.

The read-only collector separately passed 69 evidence assertions. It records
tool versions, exact commands and output hashes, current source revision,
analysis input-tree digest, raw-crash hashes, and unchanged frozen inputs in
`verification/android-emulator-boot-diagnosis/analysis-1/receipt.json`.

## Root-dispatched result

`boot-probe-1/receipt.json` records successful boot at source revision
`a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343`. The owned PID and process group were
17396; the guest reported API37, arm64-v8a, the expected fingerprint and
`sys.boot_completed=1`. Startup took about ten seconds. The only launch delta
was the documented process-local Wi-Fi fallback. The owned group was empty
after cleanup, and both reserved ports had no listeners.

Root independently replayed fifteen host guards and verified 102 saved input,
command-output and runtime evidence bindings. See
`verification/android-coordinator-join-root-review/boot-probe-acceptance.json`.
This shows that bypassing this Wi-Fi path allows this profile to initialize.
It does not establish the shared daemon's underlying defect or validate the
coordinator app. The separately bound full APK runner adaptation is next;
physical, lifecycle, IME, FieldLog, signed-package, store, operational and GA
evidence remain independent requirements.
