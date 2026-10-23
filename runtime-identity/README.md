# Installed runtime identity

This package gives a declared installed build one exact, domain-separated SHA-256
identity. It validates a closed, bounded descriptor and hashes its canonical CBOR.
Both JSON whitespace and object member order are irrelevant. Arrays representing
dependencies and capabilities must already be sorted uniquely by their ASCII IDs.
Unknown fields, duplicate JSON keys, omitted fields, unsupported platform/profile
combinations and malformed digests fail closed.

The descriptor covers app/environment/bundle identity; platform, architecture,
minimum OS and device/simulator environment; engine and UI/bridge versions;
compiler/SDK/build-tool identities; native dependency versions and artifacts;
generated bridges, linker inputs, native fallback code, build settings, permissions,
entitlements, trust roots, installed capability grants/configuration and resource
policy. Execution ceilings and state schema are part of that identity. It produces
the `InstalledRuntime` used by the verifier so the fingerprint and its directly
represented host policy cannot accidentally diverge.

This is a build-input identity, not an attestation. A caller who omits a linked
dependency or supplies an invented hash has not described the actual binary.
The build pipeline must capture the complete resolved graph and immutable input
bytes, embed this descriptor and pin its resulting fingerprint in the signed
native binary. Signed build provenance must bind the final binary hash to the
descriptor. Hash pre-embedding native fallback/link inputs rather than hashing the
final identity-bearing binary into itself. System frameworks are represented by
the target SDK identity and explicit native dependency records, never by an
invented device OS binary hash. Runtime compatibility uses exact equality; there
is no version-range acceptance or cross-architecture fallback.

Distribution, actual signed-binary embedding, complete graph collection, artifact
publication and independent release/security review remain open. This module is
not part of the root public SDK package yet. No physical-device check is implied.

The wire contract is `../contracts/runtime-identity-v1.json`. The command-line
tool opens the descriptor nonblocking with final-symlink rejection, checks the
opened descriptor's regular-file type/size, then reads within the byte bound. It
prints its fingerprint and host
configuration. It never stages a release or changes installed authority.

```sh
swift run --package-path runtime-identity mixer-identity inspect descriptor.json
swift test --package-path runtime-identity
```
