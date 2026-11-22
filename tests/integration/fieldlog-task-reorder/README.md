# Replay the signed FieldLog task reorder on Android

This fixture covers product-plan §22.2.3. It uses the tracked calculation
Activity and loopback delivery on Mixer `71e6ffa51e857d5a1eda3f74c26941996ed275de`
and FieldLog `552559d2d3278abb9b1aa7dcf0288102c09a202b`. The reviewed guest
binds the Android bridge's single `toggle` activation to the File report row
(`91094B1F-51E9-42AD-9CF1-64055970E7CB`), immediately below Valve
(`D8FD094D-6A4E-4B03-930E-1C4BEE0FB8A7`). The button disappears after the move.
The precondition on both UUIDs and the workspace revision is checked inside the
durable FieldLog transaction. Sequence 3 reuses the sequence 1 artifact.

## Build and replay on macOS

Use the tools listed in the sibling calculation fixture's README. The rebuild
runs its toolchain preflight, builds and signs an arm64/API 36 debug APK, then
runs four independent host processes against its exact installed identity,
delivery and seed. It verifies the display, input route, order, one action and
outbox event, signed rollback, origin refusal during cold reopen, and retirement.
The build needs a free ephemeral loopback port and up to 6 GiB of scratch.

```sh
run=$(mktemp -d /tmp/fieldlog-task-reorder.XXXXXXXX)
run=$(cd "$run" && pwd -P)
tests/integration/fieldlog-task-reorder/rebuild.sh "$run/work" "$run/handoff"
(cd "$run/handoff" && shasum -a 256 -c SHA256SUMS)
```

The packet contains a new debug APK signer and OTA root. Remove `work` after
all build stages report closed custody. Preserve the exact stage and scratch
if a stage reports UNKNOWN.

## Root-owned API 36 run

Use the APK and delivery from the same verified packet and a fresh app install.
The fixture uses the calculation package ID
`dev.fieldlog.generatedr90.calculation`. The Activity keeps the bottom-end
launch button inside the delivered system-bar insets and waits for window
focus before opening the workspace. Keep the device's default three-button
navigation. Confirm the button lies above the navigation bar before tapping its
center.

1. Check `SHA256SUMS` and the APK signature. Serve phase 1 and map the packet's
   recorded port to the private loopback origin on the owned device.

   ```sh
   port=$(cat delivery-android/Installed/port.txt)
   printf '1\n' > "$phase_file"
   python3 -B origin.py delivery-android "$phase_file" --port "$port"
   ```

2. Tap **Open signed task reorder** and wait for **Signed checklist | Sequence
   1**. Observe Photograph meter, Valve, File report in that order and capture
   the private `files/FieldLog/workspace.json`.
3. Advance the phase file to 2 and tap **Check for update**. Wait for sequence
   2, confirm the same order, and capture the pre-move workspace. Tap
   **Move up: File report** once. Observe Photograph meter, File report,
   Valve, and the removed Move up button. Capture the post-move workspace.
4. Advance to 3 and tap **Check for update**. Verify the new launch is healthy
   with the baseline artifact and the moved order. Capture the rollback
   workspace. Tap **Done**, verify retirement, then stop the origin and remove
   the owned reverse mapping. Verify the owned device has no network route.
5. Start a new app process offline. Verify that the saved draft opens with
   the original title and multiline note. Open the signed reorder again,
   verify **Using saved checklist release | Sequence 3**, capture the
   offline workspace, then tap **Done** and verify retirement.

The [API 36 receipt](../../../verification/receipts/fieldlog-android-signed-row-api36-d92cb15a.json)
records the three signed phases and offline reopen on Mixer `d92cb15a`.
The updated assembly used that revision's linked native identity. The
installed fixture title is `Valve "北"`.

Capture live recovery state at each phase and retired state after **Done**.
Use the packet's `android-readback.py` with the assignment's runtime, sequence
and artifact and the manifest's payload hash. Keep the installation ID and verify
the offline launch uses the committed rollback candidate with a new launch ID.
Verify the five workspace captures from the packet directory:

```sh
python3 -B verify-workspace.py delivery-android/Installed/calculation-seed.json \
    "$baseline" "$pre_move" "$post_move" "$rollback" "$offline"
```
