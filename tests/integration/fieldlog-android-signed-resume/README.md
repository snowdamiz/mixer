# Replay an interrupted signed Android update

This fixture verifies §22.2.6 on one installed FieldLog development APK.
The local origin serves two signed releases for the same runtime. It can
interrupt the second artifact after 1,024 bytes or alter one byte in its
previously recorded prefix. The Android delivery path requests the full JSON
envelope and compares the saved prefix before appending new bytes.

## Prepare the packet and origin

Build the APK and its matching signed packet using the [Android halt packet
recipe](../fieldlog-android-halt-v64/README.md). Use the baseline and reviewed
assignments from `packet/delivery-android`. Verify the packet's
`SHA256SUMS`, APK signature and alignment.

Create a private capture directory. Run from the Mixer repository root.

```sh
fixture="$PWD/tests/integration/fieldlog-android-signed-resume"
printf '%s\n' baseline > "$capture/phase"
python3 -B "$fixture/origin.py" "$packet" "$capture/phase" "$capture/responses.jsonl"
```

The origin prints its loopback port. Install the APK once on an owned
Android API 36 arm64 emulator. Use gesture navigation on the disposable
profile so taps above the navigation bar reach the checklist launcher.
Bind the device's port from `Installed/port.txt` to the printed port through
the emulator's private ADB server.

```sh
p=dev.fieldlog.generatedr90.calculation
device_port="$(cat "$packet/delivery-android/Installed/port.txt")"
d() { adb -H 127.0.0.1 -P "$adb_port" -s "$serial" "$@"; }
d reverse "tcp:$device_port" "tcp:$origin_port"
d shell am start -W -n "$p/dev.fieldlog.generatedr90.androidhost.PublicActivity"
```

Change the phase by replacing the phase file atomically. Use a fresh
`responses.jsonl` for the run and keep the same file across the origin restart.

## Capture the six phases

At each checkpoint, open the signed checklist from the ordinary button.
Save the native frame as `screen.xml`, the app's process ID as `pid`, and the
workspace and live recovery snapshot using the commands below. Tap **Done**,
wait for the sheet to close, and capture `retired.json` using the same state
path.

```sh
d shell uiautomator dump /data/local/tmp/mixer-resume.xml
d exec-out cat /data/local/tmp/mixer-resume.xml > "$stage/screen.xml"
d shell pidof -s "$p" > "$stage/pid"
d exec-out run-as "$p" cat files/FieldLog/workspace.json > "$stage/workspace.json"
d exec-out run-as "$p" cat files/signed-checklist/recovery/state.json > "$stage/live.json"
# After Done and sheet closure
d exec-out run-as "$p" cat files/signed-checklist/recovery/state.json > "$stage/retired.json"
```

1. **baseline** uses origin phase `baseline`. Sequence 1 renders 0%, 100%,
   and 0%. Confirm the transport spool is absent.
2. **interrupted** uses phase `partial`. The app renders saved sequence 1.
   Copy `files/signed-checklist/artifact.partial` with `run-as` to
   `interrupted/artifact.partial`.
3. **cold-offline** starts after removing the ADB reverse mapping and
   verifying the origin's exit and listener closure. Enable airplane mode,
   disable Wi-Fi and mobile data, and wait for empty IPv4 and IPv6 main
   defaults. Use `ip -4 route get 192.0.2.1` and
   `ip -6 route get 2001:db8::1` to confirm the network is unreachable.
   Force-stop only the fixture app and reopen it. Save the identical spool
   and record both route observations in `offline-network.json`, with keys
   `-4` and `-6` and fields `mainDefault`, `lookupExit` and `lookupOutput`.
4. **changed-prefix** restarts the origin in phase `changed-prefix` and binds
   its new port through the private reverse. The app keeps saved sequence 1
   and removes the conflicting spool.
5. **partial-again** offers phase `partial` again. Save the exact spool while
   the old candidate stays healthy.
6. **resumed** uses `complete`. Sequence 2 renders 33%, 100%, and 0% through
   both health milestones. Confirm the spool is absent and capture retirement.

Use the bold labels as directory names under the capture directory. For
each of the three absent-spool phases, check absence on the device with
`run-as "$p" test ! -e files/signed-checklist/artifact.partial`.

```sh
python3 -B "$fixture/verify.py" "$packet" "$capture"
python3 -B -O "$fixture/verify.py" "$packet" "$capture"
```

Remove the reverse mapping and device XML and stop the owned origin,
emulator and private ADB server. Verify the owned process exits and port
reuse before removing the disposable emulator data.
[Installed Android receipt](../../../verification/receipts/fieldlog-android-signed-resume-native-20261120.json)
