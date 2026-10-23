# Installed capability material and factory proposal

Root implementation proposal, 2026-10-23. This is a design for the next slice;
it grants no execution authority. The immutable definitions remain
capability-execution-v1, runtime-identity-v2, release-v3 and activation-v2, frozen
by `verification/capability-authority-contract-freeze-2026-10-23.json`.

The new package is `capability-activation`, product `MixerCapabilityActivation`.
It depends on MixerExperimentalCapabilityRuntime, MixerRuntimeIdentity,
MixerUpdates and SDK MixerCapabilities. It never imports MixerRuntime or the old
MixerActivation product. Its linker must select the single experimental archive
containing both C families and the shared registry. Current signature and identity
proofs are prerequisites, not proof that this package already exists.

## First slice: immutable installed material, without public execution

Proposed public input and installed-policy surface:

```swift
public struct CapabilityMaterialFile: Sendable {
    public enum Role: Sendable {
        case bridgePolicy
        case configuration(capabilityID: String)
        case installedGrant(capabilityID: String)
    }
    public init(role: Role, bytes: Data)
}

public struct InstalledCapabilityExecution: Sendable {
    public let runtimeFingerprint: String
    public init(identityJSON: Data, materials: [CapabilityMaterialFile],
                trustRootsJSON: Data, privateContainer: URL) throws
}
```

Input objects are untrusted values until this initializer succeeds. The embedding
supplies the trusted application-private container root using its native platform
API. A downloaded release cannot supply or replace the identity, roots, material,
container, startup name or adapter configuration. Before owned copies, bound identity
JSON to131072 bytes and roots JSON to65536 bytes. Reuse the identity2 parser's owned
snapshot rather than parsing caller-backed bytes again. The initializer captures
bounded owned bytes and immutable typed values. It constructs neither a native session nor
HTTP/storage adapters and performs no filesystem initialization or network I/O.
It schedules no tasks. There is no public adapter, closure, policy DTO or arbitrary
service argument and no public method returning an executable session in this
first slice. The future coordinator owns this value and its private verifier.
Preserve or copy that same verifier context into the private updater. Reinitializing
a verifier from identical DTOs and roots intentionally produces a different context
that cannot reuse existing opaque artifacts.

Validate at most five material files, at most65536 bytes each and327680 bytes total
before any owned material copies. Reject duplicated, missing or unused roles;
exactly one bridge policy plus one configuration and one installed grant for each
identity capability is required. Role IDs must equal the known identity entries.
After copying, hash each exact file before parsing and compare its role's digest
from the same captured identity. Never reopen a caller path. Require exact
canonical JSON bytes: sorted ASCII object keys, compact separators, ASCII escaping,
unsigned shortest decimal integers and one final LF. Use a bounded strict scanner
and exact re-encoding equality, with depth8 and8192 values per material file.
Lexical forms that normalize to the same value still reject.

Parse the closed bridge, HTTP, storage and grant schemas in the frozen execution
contract. In particular, HTTP concurrency must equal the identity's native/host
request count; only normal-system-TLS URLSession is supported. Storage uses the
fixed app-private implementation, a single ASCII directory component, and bounded
bytes/entry ceilings. Empty grants remain denials, including empty storage
namespaces; do not manufacture a namespace to satisfy a constructor.

Check each capability's native implementation digest against the linked
`CapabilityNativeIdentity.sha256`, and check that linked constant against the
execution contract's frozen implementation reference. Check known schema and
semantic constants against the linked generated schemas as well as the identity.
These checks bind the selected concrete adapter implementation family. They do
not attest arbitrary caller-declared engine/toolchain/dependency artifact hashes
or prove that a complete installed build graph was consumed. The build pipeline
must later capture and embed those exact inputs. Preserve this limitation in the
public documentation and receipts; do not represent a matching digest string as
an independently inspected final binary.

The generated native digest's preimage is the canonical array of source path and
SHA256 records used by `capabilities/tools/generate.py`, not its hexadecimal digest
text. Add a separate read-only export/check helper for that exact preimage when
preparing a real identity2 capture. It must reproduce the already generated SDK
digest without changing the generator, SDK, contracts or generated identities.
This native preimage is sorted compact ASCII JSON with no final LF, unlike capability
material files, which require one final LF. The helper must be read-only, support
`--check`, and never import the generator module because importing it writes files.
Synthetic native inputs from identity-parser tests cannot qualify this factory.

Trust roots are separate from the five capability material files. Bound raw roots
JSON to65536 bytes and128 roots. Its exact top-level shape is `[TrustRoot]`, matching
the existing update CLI. Factory identity capture must use `kind: file` for the
`build.trust_roots_sha256` input, not the generic capture tool's collection form.
Copy once, compare the exact raw-file SHA256 to
`build.trust_roots_sha256` from the captured descriptor, then strictly decode every
closed TrustRoot field and initialize one private ReleaseVerifierV3. Root role,
scope, time, duplicate-ID and key-encoding checks remain the verifier's checks.
The initializer does not accept an independent verifier whose configuration could
diverge from the identity or root snapshot. Root JSON needs no newly invented
canonicalization rule: its exact captured bytes are the identity-bound preimage.

## Later construction inside the coordinator

Only the later private updater selection can reach adapter/session construction.
It supplies one immutable payload and the enclosing VerifiedArtifactV3 minted by
the same private verifier; standalone grants, another verifier's artifact, a path
or public selection DTO cannot authorize construction. Revalidate artifact bytes
and current authority, compute effective base limits, and await the bounded native
validator using the exact same module/startup/configuration tuple as construction.
No public accepting validator callback is introduced.

Effective fuel and startup time are the minimum of signed and installed limits.
Memory pages are floor(min(signed bytes, installed bytes)/65536), including exact
zero. Stack, depth, host calls, request count, reservation, timeout, turn and rate
limits come only from installed identity/material. Batch turns4, batch budget8ms
and10ms active timer remain the frozen scheduler policy. A signed release cannot
select or widen them.

After complete validation and the coordinator's current-generation/cancellation/
deadline recheck, construct actual closed adapters from the captured configuration.
Build CapabilityPolicy by independently intersecting the installed and verified
signed sets; never union or accept a caller's precomputed intersection. Omit HTTP
when effective permission/origin/method sets deny it. Omit storage when effective
permission or namespace sets deny it. Otherwise initialize storage beneath the
trusted container using the captured component and quotas. This initializer may
create/lock app-private files; distinguish that setup from guest-dispatched I/O.
Preserve these concrete adapter instances for the owner lifetime.

Reserve a bounded whole-attempt coordinator slot before initializing adapters. The
bridge's own permit is acquired by `prepare` after concrete adapter arguments exist,
so it cannot bound adapter initialization. On bridge busy, cancellation or constructor
failure, retain the attempt and cleanup owner until the concrete adapters actually
close. Do not release the slot early or launch unbounded detached cleanup tasks.
The later coordinator design must specify that reservation and ownership handoff;
the material-only first slice adds no execution or reservation API.

Construction performs its own exact full admission and creates an effects-disabled
native session. Startup runs once. Its result must still be followed by current
generation/cancellation/deadline checks before publication and private enablement.
The public coordinator must not expose the development session's enableEffects
method or a raw session/adapter/host handle. Once effects have ever opened, failure
requires the frozen recoveryRequired behavior and reconciliation of possible
committed I/O; it cannot silently start another guest or native fallback.

## Durable updater dependency requiring a separate design

The old ColdStartUpdater owns a strict legacy verifier and synchronous accepting
validator parameter. It cannot be silently generalized into this route. The new
coordinator requires private durable v3 state, greater-sequence reservation before
download, immutable signed records, generation-aware async staging and selection,
retained-healthy authority limited to previously committed exact records, and
single-use opaque selection ownership. Its storage must preserve uncertain-commit
poisoning and identity-mismatch rejection. Decide the shared durable-I/O factoring
before implementing this layer; do not expose a public callback merely to reuse
the old actor. The material-only first slice should not add placeholder updater
or always-accepting selection methods.

## Review and verification

Before implementation, independently review these API and ownership boundaries.
For the first slice, test exact frozen material preimages, every role/digest/schema
substitution, raw-byte canonical mismatch, all size/depth/count boundaries, missing
and empty grant denials, known linked native/schema checks, root-byte substitution,
externally backed Data mutation and directory-component rejection. Confirm no
adapter constructor or native/session call occurs during initializer execution.
Keep old identity/verifier/activation bytes and acceptance unchanged. Compile the
new package with one archive and use public-consumer negative compilation to show
that policy values cannot produce or enable a session. Later actual adapter and
durable startup slices need their own I/O, cancellation, stale-generation, fallback,
health and recovery fault tests before claiming execution integration.
