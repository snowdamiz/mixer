# MixerUpdates native verification and cold-start recovery

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
to new assignment acceptance. The cold-start store below separately defines retained
healthy offline authority.

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
or persist the assignment sequence. `ColdStartUpdater` provides the optional durable
store. Its executable validator must be installed host policy and must actually
validate the owned VM profile; there is no accepting default. Selection is not execution.

V1 accepts an uncompressed single payload, at most16MiB, with no separate assets.
Direct pinned roots only: delegation/revocation distribution and key-rotation device
qualification are pending. No physical-device OTA or GA acceptance is claimed.

`ColdStartUpdater.open(configuration:verifier:executableValidator:)` opens an actor
owning one private recovery directory. Supply a stable installed channel and an
app-private random installation identity. Its parent directory must already exist;
the store creates the last component with mode0700, locks it exclusively across
processes, and uses descriptor-relative regular files with no symlink/hard-link
following. Close the old actor before reopening. Extensions must coordinate ownership.

The host-facing lifecycle is:

1. `beginDownload(signedManifest:signedAssignment:now:)` validates signed headers and
   rollout, reserves disk, and atomically records the higher sequence **before** bytes
   are accepted. A cancellation, interruption or failed payload never lowers it.
2. `downloadOffset()` and `appendDownload(_:atOffset:now:)` support exact-offset resume
   with chunks at most1MiB. File contents and directory entries are synced. `finishDownload`
   verifies the complete hash, signatures, compatibility and installed executable policy,
   then renames and stages it. A rename completed before a journal interruption can be
   finished after reopening. `cancelDownload()` preserves the sequence high-water.
3. `selectAtColdStart(now:)` is called once per opened process session. It persists the
   attempt before returning `.provisional`. `.healthy` returns an earned retained
   candidate; `.nativeFallback` carries no bytes. Selection contains immutable `Data`,
   SHA-256 identities and a provisional launch ID, never an external mutable path.
   The host executes only that exact snapshot through its installed engine.
4. `markHealthy(launchID:now:completedMilestones:)` requires the matching process attempt,
   all configured milestones, and an elapsed process-local monotonic observation
   (default10seconds). Wall time changes cannot earn observation. A restart cannot
   resume observation. Current signatures, cache bytes and executable policy are checked
   again before the healthy pointer is written.
5. `reportFailure(launchID:reason:)` accepts a trusted host classification. Only
   `.deterministicTrap` counts toward quarantine (default2). Native crashes, user quit
   and unknown interruption do not count. An unclassified attempt on reopening is
   cleared as unknown and falls back for that session; the next session may retry.

Wall `now` is used for signing authority and stored audit time only. Durable replay
authority is the signed assignment sequence for this installed runtime/channel, not
wall time. A rollback requires a fresh greater signed sequence even for older content.
An already healthy offline candidate deliberately ignores later key expiry/revocation
flags, matching the Go reference's availability policy. Every launch still verifies
its retained artifact **and assignment signatures** using the current installed key
bytes, scopes and roles, plus runtime/capability/state compatibility and executable
policy. Removing/replacing a key or its role invalidates that cache; this is distinct
from merely marking the same key expired/revoked. Staged candidates and new downloads
always need current signing authority. This policy is explicit, not revocation bypass
for a new assignment.

Metadata writes use a private temporary file, file `fsync`, atomic `renameat`, and
directory `fsync`. An uncertain journal/rename/cleanup failure poisons the actor;
operations fail until close/reopen. `snapshot().requiresReopen` identifies diagnostics
that may reflect newer in-memory state than durable state. Injected faults cover
write/file-sync/rename/directory-sync boundaries. These tests are process-interruption
models, not proof of physical power-loss behavior on every device/filesystem.

Two healthy generations plus a staged candidate and pending download are retained.
Unknown private files are preserved; recognized orphan payload/transaction files are
pruned. Missing/corrupt candidates fall back; invalid staged bytes are quarantined.
History is bounded to256 quarantine/failure entries and fails closed at capacity
until native maintenance. Metadata is bounded to1MiB and exact fields, duplicate-key,
UTF-8, nesting and type checks apply when reopening. Missing replay metadata in an
existing directory fails closed. An incompatible installed host contract also needs
explicit native maintenance; automatic journal migration is not implemented.

The app-private metadata and all configuration, monotonic clock, fault hooks,
milestone reports, trap classifications and validator callbacks are trusted host
inputs. The guest must have no write access to the directory or these APIs. The
store resists untrusted signed/unsigned update bytes and process interruption; it
does not authenticate local metadata against a compromised host, malicious backup
rollback or deletion of the entire directory. Native install/backup/migration policy
must preserve the sequence/installation relationship. It does not implement network
downloads, secure hardware counters, background transfer, app-data migrations,
live replacement, actual owned Swift/Wasm activation, or product/store approval.

`Tests/.../Fixtures/signed-release-v1.json` is an independently authored public test
vector from the owned Go service. Its ephemeral private keys were discarded. Its
payload is a test string, not executable code. Never pin fixture keys in an app.

`verification/independent-review.json` records a separate agent review of the original
verifier, reproductions, exact source digest and post-fix host/cross-build receipts.
The review covers token authority, pinned configuration, signature domains, transport
ambiguity, canonical limits and file-read bounds. It is not an external cryptographic
audit, a formal proof, continuous fuzzing, or mobile durable activation qualification.

`verification/cold-start-store.json` records the implementer's host fault/integrity
tests and iOS/Android compilation evidence for the store. These fixture-policy tests
do not substitute for actual engine validation, independent review, physical cold
starts/power-loss recovery, published packages, or FieldLog release qualification.

For a separate Android test runner, the installed SDK supplies dynamic `Testing`.
Build with dynamic Swift libraries and enable testability explicitly for release:

```sh
DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
  /Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift \
  build --package-path updates --swift-sdks-path /Users/andreyyurlov/.swiftpm/swift-sdks \
  --swift-sdk aarch64-unknown-linux-android28 -c release --build-tests \
  -Xswiftc -enable-testing --scratch-path updates/.build/android-tests
```

This produces `updates/.build/android-tests/aarch64-unknown-linux-android28/release/`
`MixerUpdatesPackageTests.xctest`. Copy that executable and its sibling
`MixerUpdates_MixerUpdatesTests.resources` directory together to a disposable test
directory. Supply the matching official SDK's `swift-aarch64/android` dynamic
libraries and their platform dependencies through `LD_LIBRARY_PATH`, and point
`TMPDIR` at an existing writable test directory. Invoke the runner with
`--testing-library swift-testing`; the default XCTest route has zero of these tests.
The production `mixer-update` CLI has no new self-test command or activation behavior.
The receipt proves runner compilation only; a device run needs its own exit/output,
executable/library/resource hashes and device identity evidence.

## Explicit release-v3 verification

`ReleaseVerifierV3(host:roots:)` is a separate synchronous verifier for the frozen
protocol3/guestABI2/UI1 contract. It requires known exact capability schema maps
with zero to two entries, signed documents at most64KiB, payload and linear-memory
ceilings at most4MiB, fuel at most1M and startup at most60000ms, all narrowed by the
installed host. The original `ReleaseVerifier` remains strict protocol1/2 + ABI1.
No existing updater, activation, CLI, service or recovery route selects v3.

Successful verification returns distinct `VerifiedArtifactV3`,
`VerifiedAssignmentV3` and readable v3 grant values. They have no public constructor
or decoder. Verifier value copies share one immutable private context; an
independently initialized verifier must verify signed bytes again. Assignment
verification rechecks artifact signing authority at the supplied current time.
`revalidateArtifact(_:payload:now:)` also checks the exact supplied payload and
current authority. Root key bytes are privately captured. A proof is not serialized
replay state, executable validation, installed adapter authority, durable selection,
effects enablement or health. A later factory must consume a private verified
selection, rebind the whole artifact/payload and intersect installed/signed grants;
a standalone grant array or caller-created host/policy object is insufficient.

The initial v3 slice has no retained-health authority exception, asynchronous
updater validator, v3 durable store/coordinator, hosted delivery or device proof.
Those remain separate reviewed work. The API design is
`docs/release-v3-swift-api-design.md`; source-bound host tests, shared Go/Swift
vectors and public-client opacity checks are recorded under
`verification/release-v3-swift/`. Fixture keys and payloads are test-only.
