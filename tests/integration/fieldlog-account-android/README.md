# FieldLog Android local account

Use the **FieldLog Local Account** launcher in a development APK. The
ordinary launcher opens the existing workspace by default. The account
mode uses a separate workspace and a Keystore-backed credential slot
under app-private no-backup storage. The adapter calls the
[local account service](../fieldlog-account/README.md) at
`http://127.0.0.1:8765`. TaskSync retains its existing transport.

## Prepare the source

Run from the Mixer checkout with a fresh output path.

```sh
bash tests/integration/fieldlog-account-android/prepare.sh "$PWD" "$FIELDLOG_ACCOUNT_WORK"
```

The script verifies ordinary FieldLog tree
`807c198cfe800e1b3be7c94795240b29bdd9e3d5`, applies the Android shell,
and copies the byte-exact confirmed Swift owner from the
[iOS recipe](../fieldlog-account-ios/README.md).
It also applies the workspace, cold-start, and active expiry corrections.
The result is `000c3321f7c1d63160b31fbedb3f1f14554e658b` in
`$FIELDLOG_ACCOUNT_WORK/fieldlog`. Its Pair25 SDK is
`857e4b4aa7a32cda368257b2be1a63e77106bed8` in
`$FIELDLOG_ACCOUNT_WORK/mixer`. Use the
[Pair25 rebuild steps](../fieldlog-pair25-android/rust-runtime-notices/README.md)
beginning with the prepared workspace, including the modern 12-notice
packaging path. For the original link and startup reproduction, pass
`--baseline` to prepare tree `11d989672893be5e5cdb2488901469d57fae71f9`.

Run the host workspace regression with the prepared FieldLog tree and
an empty output directory. The check exercises a failed first write,
a competing workspace owner, cold reopen, and ordinary workspace defaults.

```sh
sh tests/integration/fieldlog-account-android/run-seed-check.sh \
  "$FIELDLOG_ACCOUNT_WORK/fieldlog" "$FIELDLOG_ACCOUNT_HOST_OUTPUT"
```

## Local installation check

Provision one synthetic account with account, workspace, and project
UUIDs ending in `8765`, `8766`, and `8767` respectively, each with prefix
`00000000-0000-4000-8000-00000000`. Run the confirmed account service from a
disposable database. On the owned emulator, use a private ADB connection
and reverse TCP port 8765. Open **FieldLog Local Account**, then
**Sign in with browser**. The registered reply URI is
`com.fieldlog.dev.android://account/callback`. The server's confirmed
session opens the one bound workspace. Force-stop and relaunch to check
Keystore restore. **Sign out of local account** revokes the session
and clears the credential while preserving the workspace. The
**Open ordinary FieldLog** button returns to the original data directory.

After a verified sign-in, remove the private ADB reverse mapping for
TCP 8765. Force-stop and reopen the app while the session is unexpired.
The existing workspace should open from its stored credential with no
service requests. In a disposable expiry fixture, record the confirmed
deadline, force-stop before it, then reopen offline after it. Expect
**Local session expired**, a cleared credential, and both workspace files
unchanged. Restore the mapping to repeat the normal sign-in or sign-out
flow. The [installed receipt](../../../verification/receipts/fieldlog-android-account-offline-expiry-api36-066e5038.json)
records both runs and the shortened lifetime used by the expiry fixture.

For the active-session expiry check, leave the workspace open when the
confirmed session reaches its deadline. The activity should retire the
workspace, clear the credential, and display **Local session expired**
without a process restart. The [active expiry receipt](../../../verification/receipts/fieldlog-android-account-active-expiry-api36-000c3321.json)
records the original behavior, the corrected build, and the separate
ordinary sign-out regression.
