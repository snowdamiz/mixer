# FieldLog local account recovery

This backend patch implements the recovery service for FieldLog's local account flow in product-plan §21.2. It uses the existing dedicated account SQLite database and the fixed origin `http://127.0.0.1:8765`.

## Source identity

Mixer `fa6367ab3ccac4cdacc8fe5da39f3c0d0fcc9bb0` contains the baseline account fixtures in `tests/integration/fieldlog-account` and the full app composition recipe in `tests/integration/fieldlog-account-ios/prepare.sh`. Compose the account baseline, then apply this patch in the FieldLog checkout.

| Item | Identity |
| --- | --- |
| Input `Backend/local_entry_sync.py` Git blob | `b6debbc45f8ab96360d2d494e376d80ea5f6abf7` |
| Result `Backend/local_entry_sync.py` Git blob | `4d487e779c213b387cd2eee89fe0f48033a0b029` |
| Decoded [patch](fieldlog-local-recovery.patch.b64) SHA-256 | `29e4b5af4b06e89027f82367319fbb0ade7a25cd5695096896b3b9c0db09d3f6` |

Set `FIELDLOG_RECOVERY_PATCH_B64` to the absolute path of the supplied fixture. Set `FIELDLOG_RECOVERY_PATCH` to a file in your owned scratch directory.

```sh
python3 -B -c 'import base64, pathlib, sys; sys.stdout.buffer.write(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()))' \
  "$FIELDLOG_RECOVERY_PATCH_B64" > "$FIELDLOG_RECOVERY_PATCH" &&
test "$(git hash-object Backend/local_entry_sync.py)" = b6debbc45f8ab96360d2d494e376d80ea5f6abf7 &&
git apply --check --whitespace=error-all "$FIELDLOG_RECOVERY_PATCH" &&
git apply --whitespace=error-all "$FIELDLOG_RECOVERY_PATCH" &&
test "$(git hash-object Backend/local_entry_sync.py)" = 4d487e779c213b387cd2eee89fe0f48033a0b029
```

Use `git apply --reverse --whitespace=error-all "$FIELDLOG_RECOVERY_PATCH"` to restore the input source. Reversal affects source only. Use a separate database copy to replay the older backend.

## Local operator fixture

Use the synthetic account and its existing scope in a disposable private account database. The operator approves recovery by matching the test participant to the account UUID in the local fixture record. From a private terminal at the FieldLog root, issue a code for that approved account.

```sh
python3 -B Backend/local_entry_sync.py provision-recovery "$FIELDLOG_ACCOUNT_DB" "$FIELDLOG_ACCOUNT_ID"
```

The command prints a single `flr_` code for the operator to hand directly to the synthetic participant. Keep it out of logs, URLs, and recorded output. The UUID selects an existing account. The command also works against the pinned account database before the first recovery-enabled service start.

The 47-character code contains 32 random bytes. It expires after 15 minutes, with an exclusive deadline. Only its digest is stored. Each account has at most one active code. Issuing a fresh code invalidates the previous code and any browser approval that used it. The code is consumed when the recovery exchange commits.

## App and browser contract

Open recovery from an explicit **Recover account** action. Generate independent 32-byte random values for `state`, `verifier`, and the replacement sign-in code `newProof` using the platform CSPRNG. Encode each as unpadded base64url. The `challenge` is the unpadded base64url encoding of SHA-256 over the verifier's ASCII bytes.

Keep the state, verifier, and selected recovery route in the active auth generation. Store the replacement sign-in code in private durable credential storage before requesting exchange. Keep the code available through response loss and make it available to the user as their new FieldLog sign-in code. Send JSON with the existing ephemeral client and 1 KiB bounds.

| Step | Request | Result |
| --- | --- | --- |
| Start | `POST /v1/account/recovery/attempts` with `{"platform":"ios","state":"…","challenge":"…"}` | 201 with `{"browserURL":"http://127.0.0.1:8765/v1/account/recovery/attempts/…"}`. The final component is a 43-character URL-safe value. |
| Show intent | Open the exact recovery URL in the external browser. Enter the operator code and select **Recover account**. | The form explains that recovery replaces the sign-in code and signs out existing sessions. It sends `recoveryCode=<code>&intent=recover` as form data with the exact FieldLog Origin. |
| Receive callback | Read the existing registered callback for the selected platform. | 303 to `com.fieldlog.dev.ios://account/callback` or `com.fieldlog.dev.android://account/callback`, with exactly `code` and the matching `state` in the query. |
| Exchange | `POST /v1/account/recovery/exchange` with `{"platform":"ios","code":"…","state":"…","verifier":"…","newProof":"…"}` | 200 with `token`, `accountID`, `scopes`, and `expiresAt`. The token is pending confirmation for 60 seconds. |
| Confirm | `GET /v1/account/session` with `Authorization: Bearer <token>` | 200 with `accountID`, `scopes`, and the confirmed `expiresAt`. The eight-hour lifetime starts on the first successful confirmation. |

Use `android` for the Android registration. Check the callback scheme, authority, path, code, and state with the ordinary sign-in validator. Track recovery in the private pending generation to choose the exchange endpoint. The server binds callbacks to their attempt purpose, platform, challenge, and state. The browser attempt lasts at most five minutes. After approval, the callback lasts at most one minute and cannot outlive the operator code.

Use the existing session metadata and lowercase UUID wire formats. Check the current auth generation after each network call and compare the account and scope with any existing binding. Persist the grant and start sync after successful confirmation. Use the expiry from the confirmation response. All deadlines are exclusive Unix seconds.

The exchange consumes the operator code, installs the replacement proof, revokes the account's prior bearers and approved callbacks, and creates a pending session in one SQLite transaction. This covers confirmed and pending bearers. Account and scope IDs, tasks, entries, and photos keep their existing rows and identifiers. A failed transaction leaves the existing authentication and recovery code usable until their deadlines.

Invalid or expired codes and mismatched attempt purpose return 401. Malformed requests and replacement proofs already in use return 400. A mismatched form Origin returns 403. Oversized auth bodies return 413. The service shares the existing 64 live browser-attempt slots and returns 429 at capacity. An ordinary exchange retains its existing contract.

## Recover from a lost response

1. If the browser callback never arrives, start a new recovery attempt and submit the same still-valid operator code.
2. If the recovery exchange reply is lost, retry the same callback exchange with the staged replacement code while the callback might still be valid. If the exchange returns 401 or the pending attempt is gone, start ordinary browser sign-in with the staged replacement code. A committed recovery accepts that code even if the app never received the bearer.
3. If ordinary sign-in rejects the staged code after an uncertain exchange, restart recovery with the operator code if it is still valid. The operator can approve and issue a fresh code when needed.
4. If the confirmation reply is lost, retry the same GET with its bearer. If confirmation returns 401, use ordinary sign-in with the replacement code.

## Replay

```sh
python3 -B tests/integration/fieldlog-account-recovery/check.py
```

If another lane owns port 8765, add `--isolated-loopback`. The option binds disposable sockets on IPv4 loopback and retains the exact Host, Origin, browser URL, and callback assertions. The replay reconstructs the pinned backend, checks strict patch application and reversal, runs the pinned ordinary-account suite against both versions, and drives recovery against disposable SQLite. It tests HTTP form and callback responses. Native callback delivery and app composition are outside this service replay.
