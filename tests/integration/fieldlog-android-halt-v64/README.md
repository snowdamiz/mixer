# Replay the signed FieldLog Android rollout halt

This fixture pairs one activated Android installation with one installation
whose artifact transfer is interrupted. It commits the halt through the
stock CLI and configured local Phoenix. Both installations check after the
halt, then the activated installation reopens offline.

Apply [replay.patch](replay.patch) in a fresh detached checkout of Mixer
`ad295143090e4c975564895030d81e5620b20253`. The SHA-256 is
`f438490ce745b7eb97fe808925064c475c3e11b6494b635b514bf56657d3c975`.

From that checkout, build the stock CLI with locked dependencies. Generate a
fresh development APK and its matching assignments using the patched
calculation packager.

```sh
swift build --package-path cli --force-resolved-versions --product mixer
MIXER_FIELDLOG_HALT_PACKET=1 tests/integration/fieldlog-task-calculation/android-packaging/rebuild.sh \
  "$packet_work" "$handoff/packet"
```

Use new private work and output directories. Follow
`tests/integration/fieldlog-android-halt/README.md` from the patched checkout
to start Phoenix, check the stock CLI, and capture the two Android users.
Use macOS arm64, PostgreSQL 17, and the Android API 36 arm64 image. Set
`LC_ALL=C` before starting the PostgreSQL fixture on macOS.

On each disposable Android user, enable gesture navigation before tapping
the bottom-right checklist launcher. After switching users, wait for
`am start -W --user` to report success and for the checklist launcher to
have focus. If the active user returns to the launcher without a request,
force-stop the app for that user and resume with its same persisted data.

For the offline witness, remove the reverse mapping and wait for the relay to
close. Enable airplane mode and disable Wi-Fi and mobile data. Confirm both
main routing tables have empty defaults. An IPv4 lookup for `192.0.2.1` and
an IPv6 lookup for `2001:db8::1` must both report the network unreachable.
The Android image can retain default entries through the dummy interface in
other tables. Save the main default outputs as `offline.ipv4` and
`offline.ipv6`, and preserve the lookup results with the offline receipt.

The retained run used one owned emulator with two fresh users. Its recorded
health counts describe those two installations and one induced transfer
failure. [Installed receipt](../../../verification/receipts/fieldlog-android-rollout-halt-native-20261120.json)
