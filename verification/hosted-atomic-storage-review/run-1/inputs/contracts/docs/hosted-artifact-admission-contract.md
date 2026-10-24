# Hosted v3 artifact admission implementation contract

Status: root-owned implementation boundary, **not implemented or accepted**.
This follows the accepted artifact CBOR encoder and the proposed hosted
membership/storage contract. The product plan remains binding. Existing Go
protocols, signatures, migrations, fixtures and public routes remain unchanged.

## Ownership and API

Implement independently under new `MixerHosted.Protocol` modules, with matching
tests. Reuse the accepted `ArtifactCBOR` encoder and OTP standard Ed25519/SHA-256.
No new dependency, signer, private key, network fetch, database, HTTP route,
Application wiring or release execution is included. Do not modify the identity
verifier/key-owner lane or its JSON/base64 helpers. Those have a different input
contract.

The component accepts an exact bounded artifact-envelope binary, an explicitly
supplied trusted v3 host configuration, explicitly supplied trusted artifact
roots and a checked integer verification time. It returns checked immutable
data or a closed rejection. A second entry point rechecks retained checked
data against the **current** trusted host/roots/time for later transaction use.
Neither result supplies tenant permission, executable authority, validation or
publication status. No version guessing, v1/v2 fallback or assignment admission.
Root owns subsequent HTTP, policy lookup and repository integration.

Retain original bounded envelope bytes for request hashing; exact signed JSON
value bytes; immutable manifest values; canonical manifest CBOR; signature;
payload; manifest and payload SHA-256; and the signed target. No raw identity
token, caller-selected role or mutable global configuration enters this value.
The final name/signatures may be proposed by the implementation owner before
dependent changes. Avoid accepting an arbitrary callback, Repo or signature
algorithm as configuration.

## Byte admission and closed JSON

Apply limits to the actual supplied binary before decoding or base64 allocation:

| Material | Bound |
| --- | --- |
| Complete upload envelope, including whitespace | 6,291,456 bytes |
| Complete standalone signed document, including whitespace | 65,536 bytes |
| Embedded `signed_manifest` JSON value, including whitespace within that value | 65,536 bytes |
| Decoded payload | 1–4,194,304 bytes |
| Signature | Exactly 64 bytes, represented by 88 canonical padded-base64 characters |
| Canonical manifest output | 65,536 bytes, using accepted encoder limits |

The envelope contains exactly `signed_manifest` and `payload`. The signed value
contains exactly `manifest` and `signature`. Require every manifest, scope,
limits and grant-descriptor field from the existing closed v3 models, including
explicit empty maps/arrays. Reject unknown, missing, duplicate, escaped-equivalent
duplicate, wrong-case, null and wrong-type fields at every level. Reject malformed
UTF-8, invalid escapes/surrogates, trailing values, JSON numeric fractions or
exponents for integer fields, negative values and unsigned overflow. Never
create atoms from untrusted names. Preserve bytes and exact case; do not normalize
URLs, scope IDs, digests or signed values.

Before invoking a general JSON decoder on attacker input, bound nesting and
structural work independently of the payload string's length. An owned bounded
lexical preflight may locate the two outer value spans and reject excessive
structure; it cannot establish schema, cryptographic validity or release
authority. Use at most depth 16, 256 entries per container and 4,096 structural
items including map keys/containers, compatible with the accepted CBOR bounds.
The admitted v3 schema is substantially smaller. Count/check before growing
collections; scan long strings linearly without building an unbounded list of
characters. A decoder such as Jason may be used only after that admission,
preserving ordered object members until duplicate checks finish. Keep encoded
and decoded size arithmetic checked. Do not decode a large base64 string and
only then discover it exceeds the payload bound. Verify canonical base64 by
the standard padded alphabet, exact round trip and zero unused tail bits.

Standalone signed-document limits include leading/trailing whitespace. For the
embedded value, use its actual raw JSON span rather than reserializing a map to
estimate its size. Keep the whole-envelope limit even when its extra bytes are
only whitespace. Test the exact and one-byte-over boundaries explicitly.

## Semantic and cryptographic parity

Existing owned authorities are `services/protocol/v3.go`, `v2.go`, `protocol.go`,
`json_shape.go`, `v1_json.go`, and `services/release/versioned.go`. They define
the wire contract, not code to import into the Elixir runtime. Preserve the
following v3 behavior, with executable shared-vector comparisons:

- Schema/protocol 3, guest ABI 2 and UI schema 1 only. Scope has exactly
  organization/project/app/environment/platform; the first four are 1–128 ASCII
  characters from `[A-Za-z0-9_.-]`, and platform is `ios` or `android`.
- Release, provenance and key IDs use the same ID grammar. Source commit is
  exactly 40 or 64 lowercase hexadecimal characters. Runtime, payload and source
  map hashes are exactly 64 lowercase hexadecimal characters. Creation time is
  a nonzero uint64 audit value; it does not substitute for current root validity
  or authorize replay. Other numeric fields are uint64 with their explicit
  semantic ranges; do not silently lower them to IEEE-754 precision.
- State minimum is no greater than maximum. Compression is exactly `none`;
  compressed and expanded sizes are equal, nonzero and at most 4 MiB. Separate
  asset maps are explicitly empty. Memory is 1–4 MiB, fuel 1–1,000,000 and startup
  milliseconds 1–60,000. Host resource limits may further reduce these ceilings.
- Capability hashes are an explicit map of at most the existing two IDs
  `network.http.v1` and `storage.keyValue.v1`, with their exact frozen hashes.
  The grant descriptor has schema 1 and its exact frozen schema hash, with at
  most two entries strictly sorted by ASCII capability ID. Every entry binds an
  advertised capability/hash. Preserve explicit arrays, sorted uniqueness,
  permission spelling, HTTP method/origin grammar, storage namespace grammar,
  and per-array bounds from `CapabilityGrants.Validate`. Empty grant authority
  remains empty; a schema hash never grants an operation by itself.
- Validate the trusted host as v3, including its explicit bounded capability
  map and resource limits. Match the complete signed scope, runtime and exact
  capability map. Require host state version inside the signed inclusive range
  and every signed resource requirement within the trusted host ceiling.
- Validate the complete supplied root collection before selecting a key:
  1–128 entries, unique valid key IDs, exactly 32 public-key bytes, valid exact
  scope, at least one explicit artifact/assignment role, booleans without
  coercion, uint64 validity times and a valid optional exclusive end. Select
  the exact key ID and scope, require artifact role, not revoked, now at or after
  start and before nonzero end. A malformed unrelated root rejects the whole
  configuration, as in v3. Roots are configuration; never take them from the
  downloaded artifact or an arbitrary URL.
- Encode the complete checked manifest with the accepted deterministic CBOR
  encoder. Verify Ed25519 over `mixer.artifact.v3\0 || canonical_manifest_cbor`
  using OTP standard cryptography. Check actual payload byte length and SHA-256
  against the signed values. Manifest identity is SHA-256 of canonical manifest
  CBOR, never JSON or payload. Preserve the known valid fixture's exact bytes,
  preimage and digest.

Return bounded diagnostics that identify a closed error class without echoing
payloads, raw documents, key material or arbitrary malformed input. Recheck must
not trust a caller-edited field or a success flag instead of the retained exact
material. Elixir immutability helps ownership but does not turn a freely
constructed struct into proof. The repository must obtain checked material
through the component entry point and recheck current policy before effects.

## Executable acceptance

Run the new component in an isolated accepted-source hosted checkout, excluding
unfinished key-owner/other-lane changes. Preserve tool versions, exact input
hashes, output and cleanup; root later integrates complete hosted tests.

1. Reuse `signed-release-v3.json` and all 154 raw signed-manifest cases, 39 origin
   cases and 14 namespace cases in `release-v3-cases.json`, with explicit case
   counts. The 36 assignment cases remain outside this component; report them
   as out of scope. Compare
   the same original inputs against the owned Go verifier. Never rewrite a
   fixture to make a new implementation pass.
2. Exercise all closed fields, escaped duplicates, mixed case, null/type changes,
   malformed Unicode, fractional/exponent/overflow numbers, noncanonical base64,
   trailing input, excessive nesting/structure and exact byte boundaries.
   Include a valid 4 MiB payload signed with an ephemeral test-only key and an
   exact 6 MiB envelope padded with whitespace. No provider/customer key is used
   or retained; label existing deterministic repository vectors as test only.
3. Exercise wrong signature/domain/key/scope/role/revocation/time; malformed and
   duplicate roots; host negotiation/state/capability/resource mismatches;
   payload mutation and size/hash mismatch; unsupported assets/compression/grants.
   Current-policy recheck must reject a previously valid artifact after root
   revocation/expiry or host policy change. Ordinary valid data remains accepted.
4. Observe bounded parser traversal/allocation behavior on worst admitted and
   early-rejected inputs; distinguish input/structural/output bounds from total
   BEAM/RSS or concurrency limits. No regex-only acceptance or skipped negative
   assertions. Request independent semantic review before root acceptance.
5. Run all accepted hosted tests and production compilation without changing
   existing fixture bytes. Actual HTTP, authorization, PostgreSQL, blob storage,
   Linux CI, providers, signed native activation and all GA gates require their
   own subsequent receipts; this component cannot pass them.

The membership storage writer may consume this component only after root
acceptance. HTTP parsing must still bound streaming bytes and concurrent admitted
requests before assembling the body. A private upload remains storage admission;
compiler/runtime eligibility, assignment publication, installation and execution
retain their separate fail-closed checks.
