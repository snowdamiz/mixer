# Android pointer runtime checkpoint — October 24

The API 37 arm64 emulator run reached the first three actions. Tap and hold
each committed exactly one authoritative revision. The first rightward drag
failed: all ten scheduled events arrived, including the terminal UP, but the
revision remained 3 and both authoritative and native toggle state remained off.
The full twenty-action matrix is **not accepted**.

Root first accepted the timing/history oracle correction on the unchanged
candidate-5 APK and unchanged gesture schedule: 55 producer host tests and twelve
independent root controls pass (four valid observations accepted, eight invalid
observations rejected). The correction closes F06/F07 without changing platform
code or input coordinates. The preceding immutable reviews and failures remain
available.

The actual run has 53 assertions: 52 passed and one failed on the expected
authoritative revision increment. These include setup and cleanup assertions,
not 52 completed gestures. The instrumentation process exits with code zero,
but its explicit failed status causes the host runner to reject the attempt.
Root independently verifies 61 sealed runtime files, 43 command outputs, seven
exported files, 63 observation rows and all fourteen synchronous event deliveries.
P03's before/after packet hash, revision, task identities, editor state and scroll
position are unchanged. No contained native-input failure or retirement was
reported. Internal platform touch state was not observed, so the cause still
requires diagnosis; an Activity delivery alone does not establish thumb handling.

The source closure is
`9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce`;
APK SHA-256 is
`57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714`.
The target reports Android 17/API 37, `sdk_gphone64_arm64`, fingerprint
`google/sdk_gphone64_arm64/emu64a:17/CE2A.260420.019/15611780:userdebug/dev-keys`.
Native tooling versions, commands, timestamps and output hashes are retained
in the runtime receipt; this is an emulator receipt, not a physical-phone result.

Owned emulator process group 57676 and its children were stopped, ports 5586
and 5587 had no remaining listener, and the 179-file/172,952,201-byte extraction
was removed after an empty holder check. Root's subsequent process snapshot
confirms that group is absent and the unrelated `morse-api37` emulator remains
running. No physical target was queried.

Evidence:

- `verification/android-pointer-timing-root-review/receipt.json`
- `verification/android-pointer-timing-correction/runtime/runtime-1/receipt.json`
- `verification/android-pointer-native-root-review/receipt.json`

Replay with `python3 -B verification/android-pointer-native-root-review/review.py`.
The read-only replay does not start a simulator or emulator. Full pointer, system
IME/accessibility, cross-platform appearance, public/signed transport, FieldLog,
physical-phone and GA qualification remain pending.
