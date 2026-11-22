# FieldLog local account deletion

This service patch implements the account-deletion transaction for FieldLog product-plan §21.2. It uses the dedicated FieldLog account SQLite database and the local account origin `http://127.0.0.1:8765`.

## Source and replay

Follow the recovery reconstruction at Mixer `41d1b96fe4a0ddf67b5e7aa0ff4ea1cf473645c1` to recover `Backend/local_entry_sync.py`. Apply the deletion patch from the FieldLog checkout. [Recovery reconstruction](https://github.com/snowdamiz/mixer/tree/41d1b96fe4a0ddf67b5e7aa0ff4ea1cf473645c1/tests/integration/fieldlog-account-recovery) · [Deletion patch capsule](fieldlog-local-account-deletion.patch.b64)

| Item | Identity |
| --- | --- |
| Recovered backend Git blob | `4d487e779c213b387cd2eee89fe0f48033a0b029` |
| Deletion backend Git blob | `535c33c727f8c0c630c444e180a754ec5625edea` |
| Deletion patch SHA-256 | `44aab1c0a6083b8495bb4e29777595570decab31760f43280ccb25466f7b6c43` |

Set `FIELDLOG_DELETION_CAPSULE` to the absolute path of the patch capsule and
`FIELDLOG_DELETION_PATCH` to a file in your owned scratch directory.

```sh
python3 -B -c 'import base64, pathlib, sys; sys.stdout.buffer.write(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()))' \
  "$FIELDLOG_DELETION_CAPSULE" > "$FIELDLOG_DELETION_PATCH" &&
test "$(git hash-object Backend/local_entry_sync.py)" = 4d487e779c213b387cd2eee89fe0f48033a0b029 &&
git apply --check --whitespace=error-all "$FIELDLOG_DELETION_PATCH" &&
git apply --whitespace=error-all "$FIELDLOG_DELETION_PATCH" &&
test "$(git hash-object Backend/local_entry_sync.py)" = 535c33c727f8c0c630c444e180a754ec5625edea
```

Use `git apply --reverse --whitespace=error-all "$FIELDLOG_DELETION_PATCH"` to restore source. To replay the older service with pre-deletion data, use a separate database copy.

Run the service replay from Mixer with `GIT_NO_LAZY_FETCH=1 python3 -B tests/integration/fieldlog-account-deletion/check.py`. It reconstructs the pinned sources, checks strict apply and reversal, runs the inherited account and recovery suites, and exercises deletion on disposable synthetic SQLite databases. The pinned transport adaptation uses ephemeral IPv4 loopback sockets while preserving the fixed Host, Origin, browser URL, and callback assertions.

## Service contract

Send `POST /v1/account/deletion` with the confirmed local session's `Authorization: Bearer <token>` and an exact JSON object within the existing 1 KiB auth-body limit.

```json
{
  "intent": "delete",
  "accountID": "lowercase account UUID",
  "workspaceID": "lowercase workspace UUID",
  "projectID": "lowercase project UUID",
  "deletionKey": "43-character unpadded base64url value"
}
```

Generate the deletion key from 32 independent random bytes using the platform CSPRNG. Keep it private as part of the pending operation. The first successful request requires a live, confirmed bearer and the exact account and sole scope reported by session confirmation. An expired or unconfirmed bearer returns 401. A mismatched account or scope for a confirmed bearer returns 404. Invalid shapes or intent return 400.

The transaction removes the account's sign-in proof, confirmed and pending sessions, account-bound sign-in and recovery approvals, operator recovery proof, task heads and events, and entry events and photos. It commits a deletion receipt in the same transaction. The response is `200` with `deleted: true` and the exact `accountID`, `workspaceID`, and `projectID`.

If the response is lost, send the identical request with the original bearer and deletion key. The receipt survives service restart and stays available for the lifetime of the database. The database retains two digests per completed request. The original bearer can retrieve that receipt with the staged request and key. All deleted sessions lose account access. Reusing the recorded key with different credentials or identity returns 401 before any new deletion. `DELETE /v1/account/session` still revokes a single session.

## Native handoff

1. After the user explicitly confirms **Delete account**, capture the confirmed local account, workspace, project, and active account generation. Stage the original bearer, intent, scope, and fresh deletion key in durable private storage before any network send. Keep the pending record available through app restarts and suspend that account's normal sync while the deletion awaits a result.
2. Send with the existing ephemeral HTTP client. After transport failure, timeout, or a retryable service error, resend the staged request with its original bearer, including after the session deadline. Bind each response to the staged operation that issued the request.
3. Accept only HTTP 200 with `deleted: true` and all three IDs matching the staged account and scope. Recheck the local account generation before acting on the response. Persist the validated confirmation before clearing scoped local data so a crash can resume cleanup. Clear local data only for that staged binding, then retire its pending record and credential material.
4. Keep local data on any unconfirmed outcome. If the exact retry returns 401 because the original bearer expired or was revoked before commit, require a fresh confirmed session for the same account and scope and renewed explicit confirmation before staging a new request. Keep a receipt or error from an earlier account generation from clearing the active account's data.
