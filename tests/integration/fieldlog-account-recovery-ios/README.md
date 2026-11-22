# FieldLog iOS local account recovery

Launch the iOS Debug app with `--fieldlog-local-account`. Select **Recover account** on the welcome screen and enter the operator-issued code in the browser. The browser uses the existing iOS account callback. After FieldLog confirms the session, select **Show replacement sign-in code** and save it before continuing to the workspace.

If a recovery exchange commits and its reply is lost, FieldLog returns to the welcome screen. Open **Show replacement sign-in code**, then use that code in ordinary browser sign-in. If the browser refuses the code, start recovery again with a valid operator-issued code. See the [local service contract](../fieldlog-account-recovery/README.md).

## Shared Swift owner

| API | Contract |
| --- | --- |
| `FieldLogAccountOwner(..., makeRecoveryCode:)` | The platform supplies 32 independently generated random bytes as unpadded base64url. Existing initializer calls retain ordinary sign-in. |
| `beginRecovery()` | Returns the validated recovery URL and persists its purpose and proof within the same attempt model as `beginSignIn()`. |
| `acceptCallback(_:)` | Validates the existing platform callback and active state. The stored purpose selects the exchange endpoint. A secure write stages the replacement code before any recovery exchange. |
| `restore()` | Retries an in-memory confirmation with the same bearer and generation. After process loss, the staged replacement remains available for ordinary sign-in. |
| `hasReplacementSignInCode` and `replacementSignInCodeForUser()` | The boolean drives the explicit reveal action. Call the getter only inside that user flow. Keep the code out of state strings, logs, diagnostic payloads, and URLs. |
| `acknowledgeReplacementSignInCode()` | After confirmed recovery and user acknowledgement, drops the local code while preserving the confirmed session. Successful ordinary sign-in or explicit sign-out also drops the local code. |

The credential store reads and atomically replaces the complete `AccountCredentialRecord`. The new `.recovery` case retains the staged code and, when present, the pending browser attempt or the confirmed recovery session. Existing attempt records without a purpose decode as sign-in. Existing session and revocation records retain their format. The iOS store uses its device-only, unlocked Keychain item. The iOS copy action uses the local clipboard for two minutes and the view hides the code when the app leaves the foreground.

Both exchanges use the same confirmation logic. The confirmation GET must match the exchanged account and exact workspace/project scope. The owner uses the confirmed expiry. The iOS route presents the replacement code before mounting a confirmed recovery workspace. Its existing retirement path still closes the account model and clears assignment routing before any different scope mounts.

## Android attachment points

- In the Android account preparation recipe, update the shared Swift owner input to the output blob below. Apply the independently pinned backend delta to the Android candidate's matching backend blob.
- In `Integrations/GeneratedReport/Sources/FieldLogAndroid/AndroidAccount.swift`, inject a `makeRecoveryCode` provider via the existing secure-random bridge and add an explicit recovery command alongside `beginSignIn()`. Keep the whole encoded record in `AndroidCredentialSlot` and the existing Keystore-backed Android account store. Enforce the existing 1 KiB transport and credential bounds.
- In the development account screen in `PublicActivity.java`, send the recovery command through `PublicBridge` and use `AndroidAccount.openBrowser`. Keep `AndroidAccount.Callback` forwarding `com.fieldlog.dev.android://account/callback` to the shared owner. Match both account and scope in the existing mount and retirement path.
- Add a dedicated user-triggered reveal command for the staged code. Keep the code out of the normal `fieldlog_account_tick` status string. After confirmed recovery, allow the user to save and acknowledge it before opening the workspace. After a lost reply, keep the ordinary sign-in action available.

## Replay the patch and checks

Start with a separate Mixer checkout at `41d1b96fe4a0ddf67b5e7aa0ff4ea1cf473645c1`. Set `pinned` to that checkout, `fixture` to this directory, and `work` and `checks` to empty private directories. Reserve TCP loopback port 8765 for the checks.

```sh
bash "$pinned/tests/integration/fieldlog-account-ios/prepare.sh" "$work"
app="$work/source/fieldlog"
base64 -D -i "$fixture/fieldlog-ios-recovery.patch.b64" -o "$work/client.patch"
base64 -D -i "$pinned/tests/integration/fieldlog-account-recovery/fieldlog-local-recovery.patch.b64" \
  -o "$work/backend.patch"
git -C "$app" apply --index --whitespace=error-all "$work/client.patch"
test "$(git -C "$app" write-tree)" = f478bec7d45a5960d514e5fe53960de9f25f73f5
git -C "$app" apply --index --whitespace=error-all "$work/backend.patch"
test "$(git -C "$app" write-tree)" = a4e08d9b67d9811dfe160ac71b04b35e0730d954
sh "$fixture/run-checks.sh" "$app" "$checks"
```

Reverse the client patch with `git apply --index --reverse --whitespace=error-all`. The client delta touches three Swift files. Both patches can be reversed independently. Reversal applies to source only. Use a disposable database for each replay.

| File | Base Git blob | Output Git blob |
| --- | --- | --- |
| `Sources/FieldLogModels/FieldLogAccount.swift` | `d6e383eeca9756d249c692cd01173951b8b9a419` | `d31e9fd87134cf70dd9d5edf3ad5012d0422e62e` |
| `ios/FieldLog/FieldLogAccountApple.swift` | `92887cfa2d1589ac5c14e111cbc48219add7cdf8` | `cb2c4540494d4bedb155c95d0c2c38f53ef5e58d` |
| `ios/FieldLog/FieldLogAccountRoute.swift` | `0c1f5255b3071ca2f5d540329eb356b5a0c611cb` | `94712bf8a94df831d07930b04f892adb8cfad986` |
| `Backend/local_entry_sync.py` | `b6debbc45f8ab96360d2d494e376d80ea5f6abf7` | `4d487e779c213b387cd2eee89fe0f48033a0b029` |

The decoded client patch has SHA-256 `1081df87e7362e46e39c4d74f110ae3ae32b1ea5fff197ea39c2d081d5f23a12`. The [verification receipt](../../../verification/receipts/fieldlog-ios-account-recovery-host.json) records the replay and generic build. Native browser delivery, Keychain behavior, and Simulator acceptance remain with root.
