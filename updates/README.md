# MixerUpdates native verifier

This independent Swift module consumes the same release-v1 canonical CBOR contract
as `services/protocol`. It verifies Ed25519 signatures through Apple Swift Crypto
5.0.3 (CryptoKit on Apple; vetted BoringSSL implementation on supported other hosts).
It does not implement cryptographic primitives.

`ReleaseVerifier` is initialized from the **installed** runtime contract and pinned
public roots. These must never be taken from an untrusted update. It checks signed
app/environment/platform/runtime identity, schema versions, exact capability hashes,
state compatibility, resource limits, payload size/hash, signing-key scope/role/
revocation/validity, and distinct artifact/assignment domains. Assignment verification
checks channel, deterministic cohort, and a strictly increasing durable sequence.
`VerifiedArtifact` retains private signing evidence. A new assignment reauthorizes
that artifact signature under the receiving verifier's current roots, roles, scope,
revocation state and verification time. Tokens from an earlier or different verifier
cannot bypass a removed, replaced, expired or revoked artifact key. This check applies
to new assignment acceptance; healthy offline launches remain an update-lifecycle concern.

JSON is an inspection/transport form. Duplicate/unknown fields, excessive nesting,
invalid types and unsupported profile fields fail closed. Canonical CBOR bytes are
reconstructed exactly for signing; the shared static Go vector verifies both canonical
byte strings, signatures, artifact identity and cohort bucket independently in Swift.
Installed runtime, scope, resource-limit and trust-root objects also reject unknown
or missing fields. CLI inputs use bounded reads of regular files; size metadata is
only an early rejection and cannot authorize an unbounded allocation if a file grows.

```sh
swift test --package-path updates
swift run --package-path updates mixer-update verify \
  --manifest manifest.json --payload module.wasm --host installed-host.json \
  --roots pinned-roots.json --assignment assignment.json --channel beta \
  --installation APP_PRIVATE_RANDOM_ID --last-sequence 6 --now 1792627300
```

A successful verifier result is **protocol verification only**. It does not validate
the VM executable profile, approve product/store policy, stage/activate a candidate,
or persist the assignment sequence. The caller must preserve sequence state atomically
with its update lifecycle, enforce VM validation, and retain native fallback. The
Go updater currently serves as a separately tested recovery reference; mobile durable
activation and recovery integration remain W10 work.

V1 accepts an uncompressed single payload, at most16MiB, with no separate assets.
Direct pinned roots only: delegation/revocation distribution and key-rotation device
qualification are pending. No physical-device OTA or GA acceptance is claimed.

`Tests/.../Fixtures/signed-release-v1.json` is an independently authored public test
vector from the owned Go service. Its ephemeral private keys were discarded. Its
payload is a test string, not executable code. Never pin fixture keys in an app.

`verification/independent-review.json` records a separate agent review of the original
verifier, reproductions, exact source digest and post-fix host/cross-build receipts.
The review covers token authority, pinned configuration, signature domains, transport
ambiguity, canonical limits and file-read bounds. It is not an external cryptographic
audit, a formal proof, continuous fuzzing, or mobile durable activation qualification.
