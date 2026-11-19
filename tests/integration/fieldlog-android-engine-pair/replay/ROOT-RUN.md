# Root-owned Android upgrade

Verify the packet before installing. Run from the handoff directory with a
caller-owned private evidence directory in `owned_work`.

```sh
shasum -a 256 -c SHA256SUMS
./replay/origin.py serve --cohorts both --seconds 900 \
  --work-parent "$owned_work" --result "$owned_work/native-origin.json"
```

Wait for `Serving FieldLog both`. The origin binds only to the loopback port in
`old/Installed/port.txt`. Root chooses a fresh owned API 36+ arm64 emulator,
checks that `dev.fieldlog.generatedr90` is absent, and configures an exact ADB
reverse for this port. Install `old/FieldLog.apk` (24101) and compare the
installed APK SHA-256 with `package-result.json`. Launch
`dev.fieldlog.generatedr90.androidhost.PublicActivity`, select an ordinary
saved task, and open **Open signed checklist**. Observe the selected task and
sequence 7, allow both health milestones, and close the checklist.

Capture `files/FieldLog/workspace.json` as `workspace-before.json`,
`shared_prefs/signed-checklist.xml` as `install-before.xml`, and
`files/signed-checklist/recovery-<old-runtime>/state.json` as `old-before.json`
with the owned package's `run-as`. The two runtime fingerprints are in
`old/host.json` and `new/host.json`.

Force-stop and upgrade in place using `adb install -r new/FieldLog.apk`
(24102). Compare the installed hash again, reopen the same task, and observe
the healthy sequence 1 checklist. Capture the workspace and installation
preferences as `workspace-after.json` and `install-after.xml`, and the journals
for both fingerprints as `old-after.json` and `new-after.json`. Keep the task
unchanged until the continuity readbacks are complete.

```sh
python3 -B replay/check-readback.py "$owned_work" > "$owned_work/installed-readback.json"
```

Close the checklist, remove the exact reverse, close the origin, and verify
owned-device cleanup. The host receipt covers the build and loopback controls.
Package Manager replacement, installed JNI, native rendering, and the
continuity readbacks belong to the root-owned run.
