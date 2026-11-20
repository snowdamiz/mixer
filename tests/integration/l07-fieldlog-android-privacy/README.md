# Check the installed FieldLog updater’s local privacy boundary

This test uses the signed development calculation APK and packet from
the [Android halt recipe](../fieldlog-android-halt-v64/README.md).
Use one owned API 36 arm64 emulator, its private ADB server, and a fresh
capture directory. Check the packet seal and installed APK hash.

Start the owned emulator with `-no-metrics`. Enable airplane mode and disable
Wi-Fi and mobile data. Wait for empty main IPv4 and IPv6 defaults and
unreachable lookups for `192.0.2.1` and `2001:db8::1`. The private ADB reverse
is the app’s route to the origin.

```sh
fixture="$PWD/tests/integration/l07-fieldlog-android-privacy"
printf '%s\n' delivery > "$capture/phase"
python3 -B "$fixture/observe.py" "$packet" "$capture/phase" "$capture/requests.jsonl"
```

The origin prints its loopback port. Reverse the port from the sealed
`delivery-android/Installed/port.txt` to that port on the private ADB
transport. Install the APK once and start the ordinary FieldLog activity.

For each phase, open **Open signed checklist**, then capture the UI as
`screen.xml` and the recovery and workspace files as shown in the [signed
transfer replay](../fieldlog-android-signed-resume/README.md#capture-the-six-phases).
Save `live.json`, `workspace.json`, and, after tapping **Done**, `retired.json`
under the phase directory. Record `network.json` with keys `-4` and `-6`
set to true only after checking that family’s routes.

```sh
p=dev.fieldlog.generatedr90.calculation
d() { adb -H 127.0.0.1 -P "$adb_port" -s "$serial" "$@"; }
pid="$(d shell pidof -s "$p")"
printf '%s\n' "$pid" > "$phase_dir/process"
d logcat -d -v threadtime --pid="$pid" > "$phase_dir/app.log"
```

1. **delivery** serves the signed sequence 1 offer and artifact. Capture the
   normal signed checklist and its healthy recovery state.
2. **failure** starts after atomically replacing the phase with `failure`.
   Force-stop the same app, start a new process, and open the checklist.
   The origin offers a valid sequence 2 assignment and returns HTTP 503
   for its artifact. Capture the saved sequence 1 checklist, retirement,
   and the same workspace bytes.

Stop the origin and remove its ADB reverse. The verifier checks the four
observed update requests, exact response digests, the individual process
logs, and recovery after the failure.

```sh
python3 -B "$fixture/verify.py" "$packet" "$capture"
python3 -B -O "$fixture/verify.py" "$packet" "$capture"
```

The retained receipt covers the fixture app’s log entries and requests at its
owned origin. It records the marker labels, log digests, and route evidence.
OS diagnostics and the separate privileged BEAM metadata finding need their
own evidence. Remove disposable app data and raw logs after the owned
processes and ports close.
[Installed privacy receipt](../../../verification/receipts/l07-fieldlog-android-updater-native-20261120.json)
