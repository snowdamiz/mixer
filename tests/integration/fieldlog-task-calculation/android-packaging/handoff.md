# FieldLog Android calculation development handoff

The APK targets arm64 Android API 36. It has a fresh development certificate
and uses the Android-scoped OTA root in `delivery-android/Installed/roots.json`.
Use the APK and the delivery directory together with a fresh app installation.

Verify the handoff from this directory.

```sh
shasum -a 256 -c SHA256SUMS
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
tools=/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0
"$tools/apksigner" verify --verbose --print-certs -Werr FieldLog-calculation-debug-api36.apk
"$tools/zipalign" -c -P 16 4 FieldLog-calculation-debug-api36.apk
```

To serve the signed assignments, create a phase file with `1` and use the
loopback port in `delivery-android/Installed/port.txt`.

```sh
python3 -B origin.py delivery-android "$PHASE_FILE" --port "$HOST_PORT"
```

Phase 1 displays 0%, 100%, 0%. Phase 2 displays 33%, 100%, 0%. Phase 3
restores 0%, 100%, 0%. A cold offline reopen retains phase 3 and its previous
healthy phase 2. The workspace remains byte-exact at revision 9. Storage
allows only reads of `completion-rows` in `fieldlog-task-v1`.
The guest has a 50 ms turn limit and 1,000,000 fuel.

`host-receipt.json` records the macOS presentation witness.
`build-receipt.json` records the exact APK, signer, members, and runtime.
`rebuild-receipt.json` records verified tools, inputs, and closed commands.
Device qualification for the fresh signed APK is a separate run.
