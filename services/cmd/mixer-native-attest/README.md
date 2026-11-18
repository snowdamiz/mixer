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
`mixer.native-build.ios-simulator.development.v1`, a NUL byte, and the exact
compact JSON bytes of `statement` as stored in the envelope. The statement
includes the local origin, the SHA-256 of the trusted public SPKI DER, the full
build selection, the journal revision and attempt, the shared native capture
binding hash, and the kind, byte count, and SHA-256 of each of the three
products. The signer independently hashes each authenticated download and
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

The current read API already supplies every input required by this slice.
Any endpoint that later records the result should treat the envelope as
untrusted input, obtain the authoritative build selection and current bytes
under its own authorization, and verify under a separately configured
development trust key before linking it to that exact journal revision and
attempt. The worker's full compile report and standalone SLSA statement are
outside the current authenticated download contract. The provenance here binds
the public build pins and retained native capture binding.

This process assumes a trusted local loopback Phoenix server and an
operator-owned state directory. The proof establishes temporal separation for
these local worker processes. Running a signer alongside an untrusted worker
under the same OS account would require an additional key-custody boundary.
