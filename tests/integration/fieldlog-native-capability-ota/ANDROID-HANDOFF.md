# Replay the Android native capability change

Use the sealed development pair on one root-owned arm64 API 36 emulator.
Both APKs use `dev.fieldlog.generatedr90.calculation` and the same signing
certificate. The old APK has version code 1 and accepts only task storage.
The successor has version code 2 and requires both task storage and the
installed HTTPS adapter. The corrected guest Wasm and workspace seed are
identical. The guest makes no HTTPS calls.

## Verify the packet and start the relay

Run these commands from the sealed handoff directory. Set `owned_work`
to the root-owned campaign scratch directory first.

```sh
packet="$PWD"
shasum -a 256 -c SHA256SUMS
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
tools=/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0
for cohort in old successor; do
  "$tools/apksigner" verify --verbose --print-certs -Werr "$cohort/FieldLog.apk"
  "$tools/zipalign" -c -P 16 4 "$cohort/FieldLog.apk"
done
port=$(cat old/Installed/port.txt)
phase_file=$(mktemp "$owned_work/phase.XXXXXXXX")
printf 'old\n' > "$phase_file"
python3 -B android-origin.py "$packet" "$phase_file"
```

Use a phase file and origin process that you own. Use the port in both APKs
for the exact ADB reverse. If the port is already in use, preserve the
listener and wait for the port to become available. In another terminal,
set `packet` to the absolute handoff path. Set `serial` and `adb_port`
for the owned emulator and ADB server.

```sh
adb_owned() { adb -P "$adb_port" -s "$serial" "$@"; }
pkg=dev.fieldlog.generatedr90.calculation
port=$(cat "$packet/old/Installed/port.txt")
adb_owned reverse "tcp:$port" "tcp:$port"
adb_owned install "$packet/old/FieldLog.apk"
adb_owned shell am start -n "$pkg/dev.fieldlog.generatedr90.androidhost.PublicActivity"
```

## Capture the old runtime

1. Select **Filter inspection** and open the saved **Valve "北"** task
   (`D8FD094D-6A4E-4B03-930E-1C4BEE0FB8A7`). Tap **Open signed checklist**.
   Capture the 33%, 100%, and 0% calculation rows.
2. Read the installed base APK hash with `pm path` and `adb pull`. Compare
   it to `build.json`. Read the workspace and installation ID from the
   app sandbox. Keep the same installation ID across every checkpoint.
3. While the checklist is open, capture the old recovery state. Tap **Done**
   and capture it again. Verify the live and retired states as shown below.
4. Set the phase to `refuse` using an atomic file replacement:
   `printf 'refuse\n' > "$phase_file.new" && mv "$phase_file.new" "$phase_file"`.
   Reopen the same checklist. The relay presents the deliberately incompatible
   sequence-3 offer signed for the old runtime. Capture the fallback label,
   the original healthy sequence 2, and the unchanged workspace. Retire the
   checklist. Restore phase `old` and check that the normal old offer is
   still served.
5. Stop the relay with the checklist closed. Remove its ADB reverse rule and
   disable emulator networking. Cold-start the app and reopen the same
   task offline. Capture sequence 2 with the same candidate and
   workspace, and a fresh launch ID. Retire the checklist. Save the retired
   old recovery file before the upgrade.

Read the files with `adb_owned exec-out run-as "$pkg" cat PATH`.

| Checkpoint | Path |
| --- | --- |
| Workspace | `files/FieldLog/workspace.json` |
| Installation ID | `shared_prefs/signed-checklist.xml` |
| Old recovery | `files/signed-checklist/recovery/state.json` |
| Successor recovery | `files/signed-checklist/recovery-$runtime/state.json` |
| Copied identity and capability files | `files/checklist-installed/` |

Use the selected cohort's `host.json`, `assignment.json`, and
`manifest.json` for `runtime`, `sequence`, `artifact`, and `payload`
in the readback command. Get the installation ID from the app sandbox.

```sh
python3 -B "$packet/android-readback.py" "$live" --retired "$retired" \
  --runtime "$runtime" --installation "$installation" --sequence "$sequence" \
  --artifact "$artifact" --payload "$payload"
```

## Upgrade in place and capture the successor

1. Set the phase to `both` and restart the owned relay on the same port.
   Re-enable emulator networking and restore the ADB reverse. Force-stop the old app and run `adb_owned install -r "$packet/successor/FieldLog.apk"`.
   Verify the installed APK hash against the successor entry in `build.json`.
2. Reopen the same task and tap **Open signed checklist**. Capture the
   identical calculation and read back sequence 3 from the successor
   recovery path. Compare the copied materials with the successor
   `Installed/` files. The old APK has no `http.json` or `http-grant.json`.
3. Tap **Done** and verify retirement. Compare the workspace bytes and
   installation ID across the upgrade. Compare the old recovery file
   byte-for-byte with the retired copy saved before installation.
4. Stop the owned origin and remove only its ADB reverse with
   `adb_owned reverse --remove "tcp:$port"`. Record the emulator, ADB,
   origin, and scratch cleanup under the root-owned native run.

`host-replay.json` records the macOS presentation witnesses and the
cohort response checks. `verifier.json` records signed compatibility and
assignment refusals. `build.json` records APK signatures, alignment,
linked members, and material hashes. Installed-device evidence comes
from the emulator run above.
