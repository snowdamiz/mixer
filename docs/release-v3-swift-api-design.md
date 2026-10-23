# Explicit Swift release-v3 verifier and proof API

Design for root review, 2026-10-23. This document changes no implementation or
contract. The binding definitions are the four exact hashes approved in
`verification/capability-authority-contract-freeze-2026-10-23.json`: execution
`898ea22b93a5b0dcd94c3b54f7cc97c41a259cd2285cbacd54bf0bd52ba48c97`, identity2
`d66c44d49f79325a643516f33bd19ba882ef711a5139afb54499b39931ba48b8`, release3
`935c2311fb32a72d4b1e49ce55fd1c63f9f8448386a7076db48550767f6212f0`, activation2
`e72c75d69e089cc3a23e09cc2f65e1902d9fc8f0bee401555507ec36d5e224d4`.

The first implementation slice adds a strict verifier and opaque signed/payload
proofs plus agreed Go/Swift vectors. It does not add a durable v3 updater, accepting
validator closure, concrete adapter factory, execution/coordinator, hosted route,
store migration, retained-health exception, or release publication. Root owns Go
v3 and shared vector authorship; identity2 and bounded native validation have their
own lanes. Old entrypoints and bytes remain unchanged.

## Public verifier surface

```swift
public struct ReleaseVerifierV3: Sendable {
    public let host: InstalledRuntime

    public init(host: InstalledRuntime, roots: [TrustRoot]) throws

    public func verifyArtifact(
        signedManifest: Data, payload: Data, now: UInt64
    ) throws -> VerifiedArtifactV3

    public func verifyAssignment(
        signedAssignment: Data, artifact: VerifiedArtifactV3,
        channel: String, installation: String,
        lastSequence: UInt64, now: UInt64
    ) throws -> VerifiedAssignmentV3

    public func revalidateArtifact(
        _ artifact: VerifiedArtifactV3, payload: Data, now: UInt64
    ) throws -> VerifiedArtifactV3
}
```

`InstalledRuntime`, `UpdateScope`, `ResourceLimits` and `TrustRoot` remain immutable
configuration values, not verified authority. The proposed identity2 type
`CapabilityRuntimeIdentity` can expose its `.installedRuntime` through the existing
DTO without creating a dependency cycle: runtime-identity depends on updates.
The future installed factory must derive this DTO and all execution/material
configuration from its same trusted identity2 snapshot; a caller-created host DTO
alone is not installed-material, executable, graph or provenance proof.

The new initializer accepts only protocol3/guestABI2/UI1, valid exact scope and
fingerprint, at most the two known capability IDs with their exact frozen schema
hashes, payload and linear-memory ceilings1..4194304, fuel1..1000000 and
startup1..60000ms. Validate bounded unique roots as before, with exact pinned roles,
scope, validity and canonical32-byte public keys. Snapshot root key bytes into
private owned storage; do not retain externally mutable/no-copy Data backing as
an immutable root policy. No version parameter, permissive enum, public validator
strategy, fallback initializer or try-another-version path exists.

`ReleaseVerifier(host:roots:)` continues to accept only protocol1/2 + guestABI1 and
its existing bounds, including its existing wider wire bound where applicable.
Its methods continue returning the old proof types. Old identity, activation,
vectors, signature domains, acceptance/rejection and errors need no changes.

All new entrypoints are synchronous pure verification. They enqueue no Task or
work queue. JSON inputs reject above65536bytes before copying/decoding; payload
rejects above the installed4MiB maximum before bounded snapshot/hash work.
Capture owned immutable input snapshots when needed to ensure the bytes hashed,
decoded and checked are the same. No retained payload copy is required in the
returned metadata proof. Thread/executor choice belongs to a bounded caller;
this API does not itself assert a global memory or concurrent-verification cap.

## Distinct opaque proofs and readable values

Proposed public values, all immutable and Sendable:

```swift
public struct VerifiedArtifactV3: Sendable {
    public let manifest: CanonicalValue
    public let artifactSHA256: String
    public let payloadSHA256: String
    public let releaseID: String
    public let payloadBytes: UInt64
    public let resourceLimits: ResourceLimits
    public let capabilityGrants: VerifiedCapabilityGrantsV3
    // private evidence/context; explicit nonpublic initializer
}

public struct VerifiedAssignmentV3: Sendable {
    public let assignment: CanonicalValue
    public let artifactSHA256: String
    public let sequence: UInt64
    public let cohortBucket: UInt64
    // private evidence/context and exact artifact/channel/installation binding
}

public struct VerifiedCapabilityGrantsV3: Sendable {
    public static let descriptorSHA256: String
    public let schema: UInt64
    public let schemaSHA256: String
    public let entries: [VerifiedCapabilityGrantV3]
    // private origin binding to enclosing artifact and verifier context
}

public struct VerifiedCapabilityGrantV3: Sendable {
    public let capabilityID: String
    public let schemaSHA256: String
    public let permissions: [String]
    public let origins: [String]
    public let methods: [String]
    public let namespaces: [String]
    // nonpublic initializer; readable values do not independently grant effects
}
```

These types have no public/memberwise initializer, Codable/Decodable conformance,
conversion from old proofs, raw-DTO proof constructor, or unchecked deserialization
hook. Use explicit private/fileprivate initializers in the defining new source
file. `@testable` must not provide a second construction route for production
consumers. They are distinct from v2's `VerifiedArtifact` and verified grant types;
no accidental cross-protocol assignment or grant acceptance can typecheck.

Grants are mandatory even when entries are empty. Keep the schema1 descriptor
object and digest unchanged. Readable arrays are exact validated sorted signed
values, not the intersection with installed grants. Missing/empty entries deny.
Individual entries or an aggregate copied out of an artifact must never be an
independent factory input authorizing I/O. The later factory/coordinator accepts
only its private updater selection, rebinds the whole artifact with its exact
payload and installed identity/verifier, and then derives/intersects grant values.
It must not accept an old proof, a grants-only argument or caller policy object.

A verified artifact proves checked signed metadata, host compatibility and exact
payload length/hash at verification. It does not prove executable validity,
assignment eligibility, durable sequence reservation, native object binding,
effects-open state, health, expiry-free future use or permission beyond installed
intersection. An assignment proof adds current assignment authority, artifact/
channel/installation binding, greater sequence and cohort eligibility against the
supplied high-water. It is not the durable commit or an updater selection token.

## Context binding and re-verification

Use a private immutable reference context owned by the new verifier. It contains
its exact host and captured root policy. Swift value copies of a verifier share
this context; separately initialized verifier values have different contexts,
even when their public DTOs happen to compare equal. Private proof evidence holds
that context identity and canonical signed manifest/signature (and bounded exact
JSON snapshot if needed for later internal re-verification), plus artifact,
payload, limit and grant bindings. No context identifier is serialized, part of
a signature, or exposed as a user-controlled string.

`verifyAssignment` first rejects an artifact from another context with a distinct
`v3.proof.context` error. It then revalidates the artifact's complete v3 structure,
host/scope/fingerprint/state/capability map and artifact signature against the
current context roots and supplied `now`, followed by the assignment structure,
signature/role/scope/validity, exact artifact/release/channel/runtime, monotonic
sequence and cohort. A previously successful artifact token never skips a fresh
artifact signing-authority check. Verification does not probe old domains.

`revalidateArtifact` similarly requires the same context, reauthorizes the signed
artifact at `now` and checks the newly supplied exact payload snapshot's length
and hash. It returns a current proof; changed payload or stale authority fails.
Callers holding a token from an independently initialized/reopened verifier must
verify the original signed bytes and payload with that verifier, rather than
retargeting a token. A future durable store persists signed data and replay state,
not serialized in-memory proofs. Reopening recreates authority by verification.

This instance-context rule intentionally narrows accidental proof reuse in the
new API. It is not a change to old verifier semantics, a process-wide permit or a
cryptographic claim about native callers. The future factory creates one pinned
verifier and passes value copies to its private updater; it does not independently
rebuild a verifier and try to reuse another context's tokens.

No public retained-healthy verifier, `allowExpired` flag, time-zero bypass or root
policy mutation is added in this slice. A future private retained-health path must
be bound to an exact previously durably healthy record and separate authority
mode; it cannot mint new-content/download authority or relax newly offered data.
Current-time fresh v3 methods always enforce their captured roots' stated policy.

## Strict v3 wire semantics

Keep the existing restricted deterministic CBOR implementation and strict JSON
lexical scanner as version-neutral utilities. The new entrypoint independently
requires closed v3 field sets at every nested object, duplicate decoded-key
rejection, canonical unsigned UInt64 integer tokens, canonical64-byte padded
base64 signatures and every mandatory field. Apply the64KiB signed document
limits before decode; bound any canonical result and intermediate collections.

Artifact and assignment messages use literal UTF8 `mixer.artifact.v3` or
`mixer.assignment.v3`, exactly one NUL byte, then deterministic CBOR. Artifact
identity hashes only canonical manifest CBOR. Retain the unchanged cohort map/
algorithm and schema1 grant descriptor/hash. Compare exact installed capability
maps, known hashes, scope/runtime/state, no compression, equal positive compressed/
expanded bytes, empty assets and signed limits no wider than installed/frozen.
Unknown version/ABI/field/capability/encoding fails closed. Schema hashes confer
compatibility, never grants. Verifier errors may use distinct `v3.*` UpdateError
codes; do not modify old error meanings to unify implementations.

Recommended first implementation leaves `Verifier.swift` byte-for-byte unchanged
and puts the new proof types, private context and v3-only validators in
`VerifierV3.swift`. This avoids widening old version branches and resolves the
old grant constructors' fileprivate boundary with new distinct types. A future
private version-neutral factoring is optional only with full old-vector and
rejection parity; there is no need to factor it in this slice. Pure canonical,
cohort or digest helpers may be reused without using an old verifier as fallback.

## Deferred durable v3 updater and asynchronous validation

Current `ColdStartUpdater` owns a `ReleaseVerifier` and synchronous public
`ExecutableValidator(Data, VerifiedArtifact) throws`. Its synchronous actor
operations rely on having no suspension inside verification/staging/selection.
Do not change that typealias to async, pass v3 through it, silently widen its old
verifier, or adapt an arbitrary success closure into capability admission.
The first slice adds no offer, download, selection, recovery or storage API.

The later additive coordinator/updater must keep v3 proofs/selection distinct.
The coordinator itself chooses the complete capability validator and supplies the
same immutable payload, installed startup and effective signed/installed config
used for construction. Numeric's proposed interface is:

```swift
ExperimentalCapabilityValidator.prepare(
    module: Data, startupExport: String,
    configuration: ExperimentalCapabilityConfiguration
) throws -> ExperimentalCapabilityValidation

// Prepared handle: one-shot async validate() throws -> Void; synchronous cancel().
```

This validation returns no transferable executable-authority token. Proposed
validation ownership has two synchronous process permits acquired before module
snapshot/capture, a dedicated serial off-UI queue, and at most two total prepared/
queued/running/draining validations. Cancellation before publication wins over an
ordinary result, but a queued/running permit stays held through dequeue/C return.
Current C validation cannot be interrupted or assigned a hard wall-time bound.
Construction separately revalidates the exact same tuple. These are prerequisites
awaiting their own approved implementation, not claims established by this design.

Before any await in a later `finishDownload` or selection operation:

1. On the updater actor, require open/not poisoned, take one explicit operation
   slot and fresh nonwrapping generation, and identify the exact pending download
   or candidate/sequence plus installed verifier context. No overlapping mutation
   starts another operation; snapshots and close remain responsive.
2. Read a private immutable payload snapshot; verify exact signed data, current
   root authority, length/hash, assignment and durable reserved sequence. Freeze
   startup/effective limits and the operation identity together. Acquire the
   bounded validator preparation before queuing/capturing worker Data. If busy or
   failed, release only this operation slot; never lower acceptedSequence.
3. Await only work owning those immutable values and its own prepared handle.
   Native validation must not retain updater storage descriptors, mutable actor
   state, an external payload path or any native adapter.
4. On resume, check the same generation and operation identity, open/poison state,
   cancellation and monotonic startup cutoff. Reconfirm the pending candidate/
   download digest, sequence and verifier/material configuration, and recheck
   current signed authority using the embedding's current trusted wall clock.
   A result for a retired generation cannot publish, commit, mark healthy or
   clear a newer operation. No await occurs between the final checks and its
   synchronous durable state transition.
5. Close/cancel synchronously retires that generation and cancels the prepared
   handle; its late native completion only releases its retained validation
   ownership. Close does not wait for a potentially hung validator. Cancelled
   downloads preserve replay high-water. A native result after cancellation is
   never converted to successful staging or selection.

Payload publish/rename and durable metadata commit remain under existing
uncertain-commit/poison rules. Selection records the durable startup attempt
before execution; health and effects ordering remain activation-v2's separate
state machine. Before-effect fallback and post-effect recovery cannot be inferred
from a successful validation or signature. Exact API/storage factoring and fault
injection for these actor transitions require another root-reviewed slice.

## Files, shared vectors and first-slice verification

Proposed ownership after root API approval:

| File | First-slice purpose |
| --- | --- |
| `updates/Sources/MixerUpdates/VerifierV3.swift` (new) | Explicit verifier, distinct opaque proof/grant values, immutable private context and v3-only checks. |
| `updates/Tests/MixerUpdatesTests/VerifierV3Tests.swift` (new) | Public wire/host/domain/limit/vector cases and preservation oracles. |
| `updates/Tests/MixerUpdatesTests/VerifierV3AuthorityTests.swift` (new) | Same-context copy, foreign context, fresh authority, payload substitution and nontransferable grant/proof cases. |
| `updates/Tests/MixerUpdatesTests/Fixtures/signed-release-v3.json` (new exact copy) | Root-owned shared positive Go/Swift vector, copied byte-for-byte from its agreed canonical path. |
| `updates/Tests/MixerUpdatesTests/Fixtures/release-v3-cases.json` (new exact copy) | Root-owned shared raw-document negative corpus once agreed. |
| `verification/release-v3-swift/` (new) | Exact source/fixture freeze, public external-client/negative-compile proofs, commands/outputs and bounded qualification receipt. |
| `updates/README.md` | Add explicit v3 scope/limits after implementation; do not relabel old release routes. |

Root selects/owns the authoritative shared-vector paths and generation. Freeze
fixture bytes and hashes before dependent Swift tests. Reuse the same fixtures in
Go and Swift; do not derive expected Swift canonical bytes from Swift itself.
Positive vector fields should retain the v2 convention: test_only, explicit host/
roots, binary payload, signed_manifest/assignment, exact manifest/assignment CBOR
hex, domain-prefixed signed messages or their exact definition, signatures,
artifact SHA256, exact unchanged grant descriptor/CBOR/hash, installation/cohort,
verification time and prior sequence. Only public test key material is used.
Negative cases need raw JSON strings to preserve duplicate/escaped keys, malformed
UTF8/encodings and lexical numbers; tests must not normalize malformed input before
verification. Swift may independently sign test-only shape mutations to prove a
shape rejection is not merely signature failure.

Required tests include correct v3 canonical/signature bytes in both implementations;
v1/v2-domain and version/ABI mismatch; host cap/unknown schema/map mismatch;
exact/+1 wire/payload/resource bounds; narrowing and state ranges; all closed nested
fields, duplicate escaped keys, UInt64/boolean/exponent/null/base64 errors; strict
ASCII sorted grants, missing/empty denial; revoked/expired/wrong-role/scope/key;
artifact-from-other-context and same-context copy; assignment reauthorizes an
expired artifact; changed payload; wrong artifact/channel/installation, stale/
rollback sequence and cohort. External non-@testable compile negatives prove no
public construction/decoding of proofs and no v2-to-v3 proof substitution.

Run all existing updates tests unchanged plus v3 cases in debug/release, relevant
Swift TSan where concurrency tests justify it, exact shared-fixture parity and
public-client typechecking. Preserve old canonical/signature fixtures, domains,
contract hashes and negative acceptance. This slice qualifies signatures and
metadata/payload proof boundaries only; no Wasm execution, material consumption,
OTA/health/recovery, mobile run, hosted storage, final signed embedding, published
package, physical device, store or GA gate becomes verified by these tests.
