# Signed release protocols

Release-v1's declared fields, canonical bytes, signature domains, and original
fixtures remain unchanged. V1 capability hashes describe compatibility and confer no permission.
The existing local service and CLI publication API continue to accept only v1.

[release-v2](../../contracts/release-v2.json) adds mandatory signed capability
grants and explicitly requires an installed protocol-2 host, schema-2 manifest,
and schema-2 assignment. Its domains are `mixer.artifact.v2` and
`mixer.assignment.v2`, each followed by one NUL byte and canonical CBOR. Guest
ABI/UI schema remain 1. There is no implicit upgrade or downgrade.

Use `DecodeSignedManifestV2` and `DecodeSignedAssignmentV2` for untrusted transport:
they bound each document to 64 KiB and reject missing, extra, duplicate, and
case-aliased fields. Signatures require canonical padded base64 text; numeric
arrays, ignored newlines and nonzero pad bits are rejected. `ManifestV2`,
`AssignmentV2`, and signed wrappers remain
separate from the v1 structs. `VerifyManifestV2` verifies host compatibility,
scope/key authority, signature, payload digest and size; header verification alone
does not verify executable payload bytes. `VerifyAssignmentV2` accepts the signed
artifact, rechecks artifact authority, verifies assignment binding and signature,
requires a greater sequence, and evaluates the cohort. Rollback uses old content
with a fresh greater assignment sequence.

Grants use a closed descriptor whose SHA-256 is
`b394ffd165ef28977de9743b1c1a98c419504787f2912e30d419cfb1582e15e1`.
The hash covers canonical CBOR of `capability_grant_descriptor` in the contract.
Every present entry must match both the known capability schema and its signed
`capability_hashes` entry. Empty or absent entries grant no authority even if the
host declares those adapters. Arrays and entries must arrive in strictly sorted,
unique ASCII order; implementations reject rather than sort or deduplicate them.
HTTP supports exact canonical HTTPS DNS origins and the six declared methods.
Storage supports case-sensitive ASCII identifiers, including distinct `Drafts`
and `drafts`; it cannot carry HTTP authority. Neither family supports wildcards.

The Swift verifier returns public typed `resourceLimits` for both versions.
`capabilityGrants` is nil for v1 and an explicit `VerifiedCapabilityGrants` value
for v2, including an empty value. Its immutable entries expose ordered arrays.
The verified artifact/grant types have no public initializers or decoders.
Only the returned verified token supplies signed policy to a native composition;
that composition must intersect it with its own installed grants and include
configuration, generated/native implementations, dependencies, platform, and
toolchain in its runtime fingerprint. A Go protocol struct or a public
configuration constructor does not independently authorize execution.

Run the bounded host qualification from the repository with an installed Swift
6.2+ compiler and its matching `DEVELOPER_DIR`:

```sh
DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
python3 services/protocol/verification/verify-v2.py \
  --swift /Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift \
  --output-dir /tmp/mixer-release-v2-fresh
```

The directory must be new. The harness records actual tools, source hashes,
commands and output hashes; race/vet and bounded Go fuzz execution; Swift debug
and release tests; byte-identical fixture reproduction; a public local-checkout
verifier-to-capability-policy consumer; and compiler rejection of invented
verified tokens. Shared fixtures include 115 signed cases and 53 origin/namespace
grammar cases. Fixture keys are explicitly public TEST ONLY material; never pin
them in an application or service. The payload is a non-executable test string.

These are protocol and local recovery checks. They do not qualify native guest
capability imports, immutable published package adoption, HTTP v2 delivery,
physical devices, store/OTA policy, or hosted operations.

Legacy v1 wire decoding now uses the same strict shape rules as Swift: every
closed model field is mandatory, including zero and false values, and fixed
names match exactly after JSON escape decoding. Numeric signature arrays,
base64 newlines, missing padding and nonzero pad bits are rejected. Canonical
public-key and HTTP payload byte strings follow the same text rule. Valid
existing signatures and canonical CBOR identities are preserved. Distinct
dynamic map keys such as `SCHEMA`, `Schema` and `schema` remain distinct; arrays
and raw JSON values do not acquire fixed-model field names. A single escaped
spelling of a declared key is valid, while duplicate decoded keys are rejected.

The Go closed model decoders enforce their invariants under direct
`json.Unmarshal` too. They decode into fresh values and assign only on success,
so reused maps are replaced and failed input cannot partly mutate the receiver.
Generic configuration DTOs keep their omitted-field defaults; exact fixed names
and canonical byte text still apply when decoded through `DecodeJSON`. Use
bounded `DecodeJSON` for untrusted v1 documents (1 MiB), and the v2 helpers above
for v2 (64 KiB). Direct standard-library `json.Unmarshal` strips outer whitespace
before a model callback and is therefore not a complete transport size guard.

The original cross-language reproducer found alternate wire forms of valid
signed bytes, including Go case folding and base64 pad-bit acceptance in both
verifiers; it did not establish a signature or tenant-authority bypass. The
shared 271-case `legacy-v1-wire-cases.json` corpus tests strict rejection and
preserved dynamic names through the actual Go and Swift signature verifiers.
Run its complete host regression with `verification/verify-wire.py` using the
same `--swift` and fresh `--output-dir` options shown above. That harness also
runs the existing services suite, CLI integration tests, v2/policy regressions,
receiver-reuse tests and external constructor checks. PostgreSQL integration
requires its separate explicit local database setup; host unit runs do not
constitute real database evidence.
