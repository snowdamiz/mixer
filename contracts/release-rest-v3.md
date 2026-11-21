# Signed release REST v3

[release-rest-v3.json](release-rest-v3.json) defines the signed v3 mutation
routes in Phoenix. The Go development reference implements the artifact and
single-channel operations. The request and
response fields are JSON keys. [release-v3.json](release-v3.json) defines the
signed manifest, assignment, and scope inside those messages. Path identifiers
use 1–128 ASCII letters, digits, hyphens, periods, or underscores, excluding
`.` and `..`. Artifact path digests use 64 lowercase hexadecimal digits.

Send `Content-Type: application/json`, a scoped `Authorization: Bearer` token,
and an `Idempotency-Key` on every request. The CLI always sends
`X-Mixer-Reason` for rollback and stage promotion and only accepts a loopback HTTP origin. It
refuses redirects, cookies, and configured proxies. Upload uses a padded
standard Base64 payload. Sequence, rollout and health values are unsigned
64-bit integers written as JSON integer literals. Successful halt receipts
echo the signed scope, runtime, channel, digest, halt sequence and the
submitted health sample. Upload, validation and channel responses may add
fields. The artifact response decoders retain the CLI's existing checks
for the type of either artifact flag when present. Validation's informational
flags do not affect the CLI receipt.

The CLI derives a lowercase SHA-256 idempotency key from the literal
`mixer-local-release-v3`, method, path, and reason, each followed by one
zero byte, then the exact HTTP request body. An absent reason hashes as
an empty string. Retry an interrupted command against the same origin with
the same publisher identity, options and files. The client retains the
original signed JSON bytes, including whitespace. The order of
`raw-json-members` in the contract is significant. `json-file` uses the
repository's sorted, pretty JSON encoding with a final newline.

If you send requests directly, keep `X-Mixer-Reason` identical on a rollback
retry. Changing the reason with the same key, path, and body returns an
idempotency conflict in Phoenix. The Go development reference returns the
original rollback receipt for that request.

On rejection both servers may return a JSON `error` object with a `code`
and `message`. Server-specific codes and retry or correlation headers can vary.
The CLI outputs the status and any recognized code. It discards server
messages and leaves retry decisions to the caller. Server authorization,
validation, and rollout rules still apply. In particular, use a strictly
increasing rollout for promotion across both implementations.

Use `mixer update promote-environment` for an enrolled Phoenix direction. Pass
the two committed source sequence numbers and the signed destination
assignments with the organization, project, application, and reason. Both
signed assignments refer to already staged destination artifacts. The command
sends their original signed bytes and emits both committed destination receipts.
Retry with the same arguments and files if the connection closes before the
receipt arrives.

Run these commands from the repository root.

```sh
python3 -B cli/release-tools/generate_release_rest_v3.py
python3 -B cli/release-tools/generate_release_rest_v3.py --check --check-router
swift test --package-path cli --filter ReleaseRESTV3Tests
```

The generator's router check compares the scoped mutation declarations in
the Phoenix source. Swift builds compile the
checked-in generated file. The Go stock-CLI
[loopback replay](../tests/integration/public-update/README.md) exercises the
same operations over HTTP.
