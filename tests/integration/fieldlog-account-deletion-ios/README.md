# FieldLog iOS local account deletion

Launch the Debug app with `--fieldlog-local-account`. Set
`FIELDLOG_SYNTHETIC_DELETION_TARGET` to `accountUUID/workspaceUUID/projectUUID`
using the binding from a disposable local fixture. Keep that binding in the
launch environment if you restart during deletion. The Debug Settings account
section shows **Delete test account** for the matching online session. Confirm
**Delete account** to start deletion.

FieldLog saves the deletion intent, locks the workspace, and drains its owner
before the first HTTP request. **Retry deletion** uses the saved bearer
and deletion key even after the session deadline. If the service returns 401,
sign in to the same test account and confirm again. FieldLog keeps sync suspended
during sign-in and until an explicit deletion confirmation. **Finish cleanup**
resumes from a saved positive receipt after an interrupted local cleanup.

## Apply the patch and run the host checks

Reconstruct the recovery tree at `a4e08d9b67d9811dfe160ac71b04b35e0730d954` using
the recipes at public Mixer `660534ec0072f03469352adc13abb6f1e47c1bfa`. Apply
the independently verified deletion backend delta. Use an empty private directory
for the decoded patch and an empty private directory for the host checks. The
host fixture binds ephemeral IPv4 loopback ports while keeping the fixed Host,
Origin, browser URL, and callback checks. [iOS recovery recipe](https://github.com/snowdamiz/mixer/blob/660534ec0072f03469352adc13abb6f1e47c1bfa/tests/integration/fieldlog-account-recovery-ios/README.md) · [Deletion backend contract](https://github.com/snowdamiz/mixer/blob/660534ec0072f03469352adc13abb6f1e47c1bfa/tests/integration/fieldlog-account-deletion/README.md)

```sh
base64 -D -i "$fixture/fieldlog-ios-local-deletion.patch.b64" -o "$work/client.patch"
test "$(shasum -a 256 < "$work/client.patch" | cut -d ' ' -f 1)" = f78bc3ccc0fd3a0fa6614e26643ea7acf69f9351a0e24c5537119d029b283569
test "$(git -C "$app" write-tree)" = 0dd0b86a6105de7d7eed619f971adc3eb3e2a86e
git -C "$app" apply --index --whitespace=error-all "$work/client.patch"
test "$(git -C "$app" write-tree)" = a218654455648bbddcdf829a97bb3002e8ba6b5d

base64 -D -i "$fixture/fieldlog-ios-deletion-callback-startup.patch.b64" -o "$work/callback-startup.patch"
test "$(shasum -a 256 < "$work/callback-startup.patch" | cut -d ' ' -f 1)" = 2bbd21b329e0c2b973b726984e2a40038185242bb6571c72fcc462cb09ca1489
owner=Sources/FieldLogModels/FieldLogAccount.swift
test "$(git -C "$app" rev-parse ":$owner")" = aeab4e80408ac698bdecfecd9fe935ce5c67a0f1
git -C "$app" apply --check --index --whitespace=error-all "$work/callback-startup.patch"
git -C "$app" apply --index --whitespace=error-all "$work/callback-startup.patch"
test "$(git -C "$app" write-tree)" = 5cdfa986b54902b042f3b0bf1824f8d17f719a80
test "$(git -C "$app" rev-parse ":$owner")" = ea55e31a8fc1ec49eda019de48b0bc2cc8d59fee
base64 -D -i "$fixture/fieldlog-apple-pending-replacement.patch.b64" -o "$work/pending-replacement.patch"
test "$(shasum -a 256 < "$work/pending-replacement.patch" | cut -d ' ' -f 1)" = a1434ad3892bce3e8bc265201a810f190645718bcaf7ce50f6b59dd87a9c6876
git -C "$app" apply --index --whitespace=error-all "$work/pending-replacement.patch"
test "$(git -C "$app" write-tree)" = 1ba375bb182e83b0f25054e0178a7185ff3e84c3
test "$(git -C "$app" rev-parse ":$owner")" = 377d020cb8c217d698b4de3d6cc02b2ba2da8b2e
sh "$fixture/run-checks.sh" "$app" "$checks"
```

Reverse the pending replacement and startup callback patches in order.
Check each source tree before reversing the earlier patch.

```sh
git -C "$app" apply --index --reverse --whitespace=error-all "$work/pending-replacement.patch"
test "$(git -C "$app" write-tree)" = 5cdfa986b54902b042f3b0bf1824f8d17f719a80
git -C "$app" apply --index --reverse --whitespace=error-all "$work/callback-startup.patch"
test "$(git -C "$app" write-tree)" = a218654455648bbddcdf829a97bb3002e8ba6b5d
```

After that reversal, `git -C "$app" apply --index --reverse --whitespace=error-all "$work/client.patch"`
restores the deletion backend-only tree `0dd0b86a6105de7d7eed619f971adc3eb3e2a86e`.
Reversal restores source. Use fresh check directories and disposable databases
for each run. [Original deletion verification receipt](../../../verification/receipts/fieldlog-ios-local-account-deletion-host.json)

## Startup callback verification

The callback patch changes only `Sources/FieldLogModels/FieldLogAccount.swift`.
A cold owner can load the stored reauthorization attempt when the configured
target, platform, callback state, and still-valid sign-in attempt match.
The existing durable journal check still fences consumption and confirmation.
Renewed deletion still requires a separate explicit confirmation.

Run the same host command on the original deletion tree with an empty check
directory to reproduce the failure. The restore-first phase passed there, and
`reauthorize-callback-first` failed with owner state `.unavailable`. On
`5cdfa986b54902b042f3b0bf1824f8d17f719a80`, the full host suite passed
using Apple Swift 6.4.2, Python 3.14.8, and Git 2.56.0. The two reauthorization
orders each exercised a real expired bearer, a distinct owner reading an atomic
file-backed slot, a rejected peer sign-in, wrong-target and wrong-state
callbacks, a duplicate callback, renewed confirmation, and exactly one SQLite
deletion receipt. The fixture checks that invalid callbacks preserve the slot,
that each sign-in exchange uses a distinct state, and that each listener releases
its ephemeral loopback port. Native callback delivery and Keychain runtime
verification remain with root.

## Cancelled recovery verification

The shared owner preserves a staged replacement when a recovery exchange
or confirmation is cancelled after the service may have committed. The
host checks also cover a superseded owner and sign-in through a fresh
process. Ordinary sign-out after acknowledgement clears the account
slot. Both deletion reauthorization callback orders and scoped cleanup
still pass. [Host and generic iPhoneOS receipt](../../../verification/receipts/fieldlog-ios-pending-replacement-1ba375bb.json)

## Android attachment

Keep the current GeneratedReport recovery lane on shared owner blob
`d31e9fd87134cf70dd9d5edf3ad5012d0422e62e`. The next Android integration can
adopt deletion owner blob `ea55e31a8fc1ec49eda019de48b0bc2cc8d59fee` with backend
blob `535c33c727f8c0c630c444e180a754ec5625edea`.

- Inject one authorized synthetic `AccountDeletionTarget` and a
  `makeDeletionKey` provider that encodes 32 CSPRNG bytes as unpadded base64url.
  Keep the complete `.deletion` record in the existing Keystore-backed slot
  within its 1 KiB limit.
- When `canStageDeletion` is true, capture the owner's `generation` when
  presenting the explicit confirmation. On confirmation, call
  `stageDeletion(generation:)`. Retire the mounted workspace, join its writers
  and clear assignment routing before the first `resumeDeletion(removeWorkspace:)`.
- Call `restore()` after startup. Handle `.deletionPending` and
  `.deletionCleanup` as locked states and resume through the same retirement
  boundary. The synchronous cleanup closure receives the authorized binding
  after the owner persists the positive receipt. Remove only its app-private
  project directory and treat an absent directory as a completed removal. The
  owner clears the credential slot after the closure succeeds.
- For `.deletionSignInRequired`, use `beginSignIn()` and the existing callback.
  `.deletionReady` means the same scope has a fresh confirmed session.
  Ask for explicit confirmation again. Keep these states out of workspace
  admission and keep bearer tokens and deletion keys out of bridge strings.
