# Manage a local signed update

Use a trusted release service on this machine. Set `MIXER_RELEASE_ORIGIN`
to `http://127.0.0.1:PORT` and load a scoped publisher bearer into
`MIXER_RELEASE_TOKEN`. Plain HTTP relies on the local listener being the
service you intend to trust. The CLI refuses redirects.

Ask your deployment signer for a v3 signed manifest and a signed assignment
for each operation. Put `signed-manifest.json` and `payload.wasm` in the
candidate directory. Configure the service with the verification roots and
the registered host for the signed scope.

```sh
mixer update publish ./candidate --organization org-a --project project-a \
  --assignment ./publish.json --channel production --rollout 5

mixer update promote "$artifact_sha256" --organization org-a --project project-a \
  --assignment ./promote.json --channel production --rollout 25

mixer update rollback "$previous_artifact_sha256" --organization org-a --project project-a \
  --assignment ./rollback.json --channel production --reason 'validation regression'
```

Publish and promote take a whole percentage from 1 through 100. The CLI checks
that the percentage matches the signed rollout. You can omit `--channel` on
promote and rollback to select the channel from the signed assignment. Supply
the flag to enforce the channel you intend to change.

Promotion expands the current artifact's rollout. Rollback uses a
higher-sequence assignment for a previously published artifact. The service
records the reason in its audit log. Use 1 to 512 printable ASCII bytes
without leading or trailing spaces.

Publish makes three requests. The service uploads the artifact, validates it,
and then commits the channel assignment. If a stage fails, successful earlier
stages can remain in storage. The channel changes only when the service commits
the assignment. Use the v3 public offer endpoint to check the current channel
for an eligible installation.

## Halt an unhealthy rollout

Record the release sequence you observed and the installation counts at the
time of the failure. For example, this sample describes one installation that
activated sequence 2, one still pending, and one adverse signal.

```json
{"sequence": 2, "activated": 1, "pending": 1, "adverse_signals": 1}
```

Save the sample as `health.json`. Ask the assignment signer for a newer
zero-percent assignment for the **same artifact, runtime and channel**.
Use the active artifact’s SHA-256 for `$artifact_sha256` and the same organization
and project as the publish command.

```sh
mixer update halt "$artifact_sha256" --channel production --health ./health.json \
  --organization org-a --project project-a --assignment ./halt.json
```

The receipt echoes the sample and the signed halt sequence. A stale sample
leaves the current rollout in place. After a successful halt, new update
checks for that rollout return HTTP 204. Installed clients can reopen their
healthy release offline, and previously issued offers retain their signed
authorization. To resume delivery, promote with a newer signed assignment.

## Resolve an interrupted command

If the outcome is uncertain, repeat the command against the same origin with
the same signed file bytes, payload, options, health counts, rollback reason, and publisher
identity. Keep the signed files byte-for-byte intact. Each stage derives its
idempotency key from its method, route, request bytes, and reason. If the service
already committed a stage, it returns the recorded response. A successful
replay confirms the original operation. The current channel may have advanced
since then.

The JSON receipt reports the artifact digest, sequence, rollout in basis points,
and `delivery: local_only`. The local service verifies signed protocol and host
compatibility. Compiler eligibility, native activation, and release qualification
have separate checks.

See the [local release integration instructions](../tests/integration/README.md)
to replay the commands with a disposable service and separate one-shot signer.
