# Local native build attestation

Build with `CGO_ENABLED=1 go build ./cmd/mixer-native-attest` from `services`.
Run both commands on macOS with the key and state on local APFS with ownership
enabled. Use an operator-controlled parent directory for each path. The signer
and verifier refuse extended ACLs and fail if they cannot check ACL metadata.
Review the key and state paths with `ls -lde` before use. Keep the state directory
at mode 0700 and the private key at mode 0600.

Configure the local Phoenix instance with `MIXER_HTTP_BIND=127.0.0.1` and a fixed
`MIXER_HTTP_PORT`, such as 4000. Set `origin` to that exact HTTP origin.
Keep the port, database, artifact storage, attestation state, and pinned public
key across restarts. Pass a current Mixer browser session token on stdin. Provide
the eight fields of the build selection as a URL query string.

Verification checks the signed origin before sending the session token. If the
service comes back on a different port, restart the same Phoenix instance on its
original port and verify again.

The signer accepts a private PKCS#8 PEM. The verifier accepts an independently
pinned Ed25519 public SPKI PEM. Both can be generated with standard tooling.
Keep the development key outside the source, worker, and API trees. The
local proof creates its key only after both the build worker and restricted
processor terminate.

```sh
mixer-native-attest sign -origin "$origin" -selection "$selection" \
  -state "$attestation_store" -key "$development_private_pem" < "$session_file"
mixer-native-attest verify -origin "$origin" -selection "$selection" \
  -state "$attestation_store" -key "$trusted_public_pem" < "$session_file"
```

The result is a JSON envelope with `statement` and a base64 `signature`.
Ed25519 signs the UTF-8 profile string
`mixer.native-build.ios-simulator.development.v2`, a NUL byte, and the exact
compact JSON bytes of `statement` as stored in the envelope. The statement
includes the local origin, the SHA-256 of the trusted public SPKI DER, and the
full build selection. Its provenance contains the journal revision, attempt,
native capture binding hash, and `workerOperationId` from the authorized
`GET /console-api/v1/build-attestation-completion` response. Each of the three
subjects records its kind, byte count, and SHA-256. The signer independently hashes each authenticated download and
matches the inventory's two parent identities and both native archive headers.
The verifier checks the signature with the pinned public key, repeats those
reads against the caller's expected selection, and compares the reconstructed
statement to the signed bytes. The signed product is a
detached native build attestation. No platform code signature or OTA release
grant is represented by this format.

The state directory is the replay scope for one local trust context. The
filename hashes the NUL-separated organization, project, application, platform,
and build IDs. A second sign for that identity is refused. Atomic exclusive
publication has one winner when signers race. Keep the directory intact across
invocations. If publication returns an I/O error after the file appears,
verify the existing attestation before deciding how to recover.

The hosted attachment API checks the v2 statement against the settled worker
operation and the retained product bytes under that operation. It uses its own
authorization and pinned development public key. Replace the operation and the
same envelope will fail attachment, even if all three products match byte for
byte.

`verify` still accepts historical v1 envelopes with their original signature
domain and fields. V1 envelopes lack a signed operation ID, so the hosted
attachment API refuses them. Keep existing v1 files for verification.

This process assumes a trusted local loopback Phoenix server and an
operator-owned state directory. The proof establishes temporal separation for
these local worker processes. Running a signer alongside an untrusted worker
under the same OS account would require an additional key-custody boundary.

On macOS, run the concurrent publication check from the repository root.
Two signer processes race on the same synthetic build and state directory.
The test verifies the single published envelope under the winner’s key and
confirms the other key is refused before HTTP.

```sh
CGO_ENABLED=1 go -C services test -race ./cmd/mixer-native-attest \
  -run '^TestConcurrentAttestationsPublishOneEnvelope$'
```

To run the Go-to-PostgreSQL attachment test, build the signer and set
`MIXER_ATTESTATION_TEST_GO_SIGNER` to its absolute path. Use a fresh disposable
PostgreSQL cluster with a private Unix socket directory, TCP disabled, a
bootstrap role named `mixer_attestation_fixture_admin`, and an empty database
named `mixer_native_attestation_fixture`. Set `MIXER_ATTESTATION_TEST_SOCKET` to
the socket directory's absolute path without symlink components. The test creates
the restricted reader and writer roles and uses an ephemeral key. From `hosted`,
run `mix test test/mixer_hosted/builds/native_attestation_attachment_test.exs`.
