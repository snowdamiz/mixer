# Verify FieldLog assignment notifications on Android

## Prepare the Pair25 app

Run `prepare.py` from the Mixer checkout. Omit `--fixture` for the ordinary product tree. The candidate retains the exact Pair25 SDK and the saved-task baseline with Settings, camera, queue, site map, report, and task-conflict support.

```bash
repo="$PWD"
delivery="$repo/tests/integration/fieldlog-pair25-android/assignment-notifications"
mkdir -p "$repo/verification/local"
scratch="$(mktemp -d "$repo/verification/local/fieldlog-assignment-device.XXXXXXXX")"
work="$scratch/work"
python3 -B "$delivery/prepare.py" --mixer "$repo" --fixture "$work"
test "$(git -C "$work/fieldlog" write-tree)" = c4c133d68d98f76a7f8822d43aa5ad0882cf5d4a
```

Start at the toolchain exports in the [Pair25 build recipe](../README.md). Keep the reconstructed checkout as `$work` and continue through `build-android.py --prepare-only`. Continue with the [Pair25 notice preflight, producers, and packaging recipe](../rust-runtime-notices/README.md#produce-seal-and-package). Use the recipe and notice texts at Mixer `e6622741`. Root owns the signing and the disposable API 36 arm64 test installation.

## Apply the launcher and Camera2 corrections

Apply both patches in order to the prepared tree. The same sequence applies
with or without the local posting fixture.

```bash
git -C "$work/fieldlog" apply --index --whitespace=error \
    "$repo/verification/receipts/fieldlog-android-assignment-single-top.patch"
git -C "$work/fieldlog" apply --index --whitespace=error \
    "$repo/verification/receipts/fieldlog-android-assignment-camera-launcher.patch"
git -C "$work/fieldlog" write-tree
```

The corrected ordinary tree is `412409f11ce962f34b94324cccdfdecde89e1436`.
The corrected fixture tree is `22c00318e305718cbfa757417119c2f0ad82d12f`.
Rebuild Java and DEX with the pinned API 36 and Pair25 inputs. The
[installed receipt](../../../../verification/receipts/fieldlog-android-assignment-camera-launcher-api36-22c00318.json)
binds the exact tested APK and the inherited JNI and notice bytes.

The [host model](fieldlog-android-launcher-host-model.py) runs the exact
production launcher guard and early finish branch. Give it the corrected
FieldLog checkout, a JDK's `bin/java` path, and an existing owned scratch directory.

## Exercise a genuine status notification tap

1. Install the fixture build in the owned offline test profile. Use FieldLog to save a synthetic task. Record its workspace, project, and task UUIDs in lowercase. For an identity control, save a same-titled task in another project with a different responsible person.
2. Grant notification permission to the fixture package on this test install. Open FieldLog, enter an unsaved task title, and record the process ID and the SHA-256 of `files/FieldLog/workspace.json`. The snapshot includes the outbox and selected project.

```bash
pkg=dev.fieldlog.generatedr90
# Set adb to the already-owned transport and route to workspace/project/task.
"${adb[@]}" shell pm grant "$pkg" android.permission.POST_NOTIFICATIONS
"${adb[@]}" shell am broadcast -n "$pkg/$pkg.androidhost.AssignmentNotificationFixture" \
	-a "$pkg.POST_ASSIGNMENT_FIXTURE" --es route "$route"
```

3. Confirm the broadcast returns `result=-1`. Open the system notification shade and tap **FieldLog assignment test**. Verify **Task assignment** names the exact project, task, responsible person, and status. Close it. Check that the process ID, unsaved title, and workspace bytes match the warm baseline.
4. Post a second notification, send FieldLog to the background, and verify the posted notification remains after terminating the confirmed fixture PID from the fixture's own UID. Verify that PID is absent before tapping. Tap it in the shade. Check that FieldLog opens in a fresh process, shows the same task, and preserves the workspace bytes.
5. Repeat with a missing task, foreign workspace, and an existing task paired with the wrong project. Each tap should show **Assignment unavailable** and preserve the snapshot. As boundary controls, send the same action and URI to the exported launcher and try to launch the private `AssignmentTap` alias from the test shell. The launcher should show its normal screen and the system should refuse the direct alias launch.
6. Record the APK digest, shade and destination readback, before and after process IDs, snapshot digest, and owned resource cleanup under the root run.

## Verify Camera2 after launcher return

After the cold shade tap, close the assignment and open an entry. Open
**Capture photo** and check the genuine Camera2 shutter. Go to Home and
return with the normal launcher action. Verify Android restored the shutter
and kept the original FieldLog Activity as the result recipient. Exercise
Back and compare the workspace bytes. Open the camera again, return through
the launcher, and accept one image. Verify one revision increment and
one attachment. For a new entry, the same transaction saves its draft and
restoration pointer. Cold-launch FieldLog and check the restored draft,
exact JPEG bytes, and unchanged preexisting drafts and outbox.
