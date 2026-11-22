# FieldLog local account backend handoff

The account service binds to the exact origin `http://127.0.0.1:8765`.
The two registered development callbacks are
`com.fieldlog.dev.ios://account/callback` and
`com.fieldlog.dev.android://account/callback`.

## HTTP contract

| Caller | Request | Result |
| --- | --- | --- |
| Swift | `POST /v1/auth/attempts` with JSON `{"platform":"ios","state":"…","challenge":"…"}` | 201 JSON `{"browserURL":"http://127.0.0.1:8765/v1/auth/attempts/…"}` |
| External browser | Open `browserURL`, then submit the local synthetic sign-in code in the form | 303 to the registered callback with exactly `code` and `state` |
| Swift | `POST /v1/auth/exchange` with JSON `{"platform":"ios","code":"…","state":"…","verifier":"…"}` | 200 JSON with session fields and `token`. `expiresAt` gives the confirmation deadline. |
| Swift | `GET /v1/account/session` with `Authorization: Bearer <token>` | 200 JSON with session fields. The first valid GET confirms receipt and returns the confirmed expiry. Later GETs return the same expiry. |
| Swift | `DELETE /v1/account/session` with `Authorization: Bearer <token>` | 200 JSON `{"signedOut":true}`. Treat 401 as already closed. |

Session fields are `accountID: UUID`, `expiresAt: Int64` in Unix seconds,
and `scopes: [{workspaceID: UUID, projectID: UUID}]`. IDs on the wire are
lowercase. The first slice provisions exactly one scope per synthetic account.
Use `android` for the Android registration. The request has no redirect URL field.

Generate independent 32-byte random values with the platform CSPRNG for the state
and verifier. Encode each as unpadded base64url. Encode SHA-256 of the verifier's
ASCII bytes the same way to get the challenge. These fields, the returned code
and the bearer are 43-character URL-safe strings. Keep the pending state, verifier
and platform private to the current auth generation. Open only the exact returned
origin and attempt path. Accept only the registered scheme, authority and path,
with exactly one code and one matching state, no fragment, user info or port.
Use an ephemeral client with no cookie, cache or redirect handling for JSON.
Bound JSON requests and responses to 1 KiB. The form requires the browser's
exact same-origin POST and sends no cookie. Sign-in attempts last five minutes.
Callback codes last at most one minute. A successful exchange consumes the code,
even if the response is lost. `expiresAt` is the exclusive deadline in both responses.

An exchange reserves one of 32 session slots for 60 seconds. The bearer can
confirm or sign out during that window. Task and entry routes return 401 until
confirmation. The server starts the eight-hour session at the first successful
confirmation and persists it before replying. Later GETs restore the same
session without extending it. Restart preserves both kinds of deadlines.
At or after the pending deadline, confirmation returns 401 and a fresh exchange
can reclaim the slot. A lost exchange response requires a fresh sign-in and
callback. The consumed callback still returns 401.

A malformed request returns 400. Invalid or expired proof or bearer returns
401. A valid bearer outside its scope returns the existing 404. Sign-out
revokes one session. A mismatched browser origin returns 403, an oversized
auth body returns 413, and full attempt or session capacity returns 429.
Keep the bearer out of callback URLs and logs.

## Apply and run locally

Apply one patch at the root of the composed FieldLog checkout. Each patch changes
`Backend/local_entry_sync.py` and produces blob `b6debbc45f8ab96360d2d494e376d80ea5f6abf7`.

| Patch | Required input Git blob | Patch SHA-256 |
| --- | --- | --- |
| [Combined account patch](fieldlog-local-account.patch.b64) | `d6119af3714fa16e15f1cd4ed5c3f403daff4613` | `789a0bd19551dda2f5d03fd35de9878d3466395ce979f4def6626570adfe3e19` |
| [Incremental confirmation patch](fieldlog-local-account-confirmation.patch.b64) | `d942e66c5d46311dbce7e90e7eff5490afea3178` | `ce45be904ef695803c7782b88c3527f5b5571d7ac4ef847b25dcd5658fe8f33a` |

The pinned local-backend and saved-task-sync patches at Mixer
`afe98bad582e80925fc2ef29457a2d650a797aab` produce the combined input.
The pinned ordinary iOS witness recipe embeds the same blob.
Use the incremental patch if you already applied the original account patch.
Check the input with `git hash-object Backend/local_entry_sync.py`.

```sh
python3 -B -c 'import base64, pathlib, sys; sys.stdout.buffer.write(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()))' \
  /path/to/fieldlog-local-account.patch.b64 > "$FIELDLOG_ACCOUNT_SCRATCH/fieldlog-local-account.patch"
git apply --check --whitespace=error-all "$FIELDLOG_ACCOUNT_SCRATCH/fieldlog-local-account.patch"
git apply --whitespace=error-all "$FIELDLOG_ACCOUNT_SCRATCH/fieldlog-local-account.patch"
git hash-object Backend/local_entry_sync.py
python3 -B Backend/local_entry_sync.py init-accounts "$FIELDLOG_ACCOUNT_DB"
python3 -B Backend/local_entry_sync.py provision-account "$FIELDLOG_ACCOUNT_DB" \
  "$FIELDLOG_ACCOUNT_ID" "$FIELDLOG_WORKSPACE_ID" "$FIELDLOG_PROJECT_ID"
python3 -B Backend/local_entry_sync.py serve-accounts "$FIELDLOG_ACCOUNT_DB"
```

Use a new path inside a private directory and synthetic lowercase UUIDs.
The operator copies the generated sign-in code privately into the external
browser. Provisioning is insert-only. The service uses a dedicated owner-only
SQLite file and checks the live session again within task and entry write
transactions before replay lookup or mutation. The listener is single-threaded.
At startup, the account service upgrades databases from the prior account patch.
Existing sessions keep their admission and original expiry. Exchanges made on
the successor use receipt confirmation. Source patch reversal changes source
only. Use a separate database if you run the prior backend again because it
does not enforce confirmation.

## iOS account owner handoff

1. Keep the pending state, verifier, and exchange bearer in the current auth
   generation. Validate the callback and exchange metadata before sending GET.
2. Call `GET /v1/account/session` with the exchange bearer before persisting the
   grant, admitting a workspace, or starting sync. Recheck the auth generation,
   account, and scope after the await. Use the GET response's `expiresAt` as the
   stored deadline. Convert it with `Date(timeIntervalSince1970:)`.
3. If the GET response is lost, a retry with the same bearer can recover the
   confirmed session. If confirmation returns 401 or the exchange response is
   lost, start a fresh browser sign-in. At capacity, a lost exchange can reserve
   its slot until the 60-second deadline.
4. On restore, compare the returned account and scope with the saved binding
   before passing the bearer to the existing sync clients. `TaskSync` receives
   port 8765, the admitted workspace and project UUIDs, and the confirmed bearer.
   The native app owner supplies the callback registration and loopback route.

From the Mixer root, run `python3 -B tests/integration/fieldlog-account/check.py`
to replay strict application and reversal of both patches against fixed Git
blobs. The same test exercises both account and static modes over loopback HTTP
and SQLite. It uses a controlled clock to test slot reclamation after a discarded
response and compares complete task, entry, and photo rows with the pinned static
handler. Native callback delivery and app-root integration remain pending.
