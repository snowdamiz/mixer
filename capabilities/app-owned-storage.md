# Bind an app-owned repository to Mixer storage

Use `InstalledApplicationStorageServing` to make an app-private repository available to a signed guest. The app supplies the repository when it installs the runtime. The guest uses the registered `storage.keyValue.v1` capability and its existing typed operations. Mixer admits two native capability IDs at this revision, `network.http.v1` and `storage.keyValue.v1`. Adding a native capability requires a new app binary and a new runtime identity.

## Implement the repository

Conform to `InstalledApplicationStorageServing` from `MixerCapabilities`. An actor or a transactional repository can serialize reads and mutations. Keep blocking I/O off the main actor. The conformance receives typed arguments through three async, throwing methods.

| Method | Contract |
| --- | --- |
| `get(_:)` | Read the exact namespace and key. Return `KVGetResponse(found: false, valueBase64: "")` for an absent key. Use `found: true` for a stored empty value. |
| `put(_:maximumTotalBytes:maximumEntries:)` | Decode canonical padded Base64. Check both installed quotas against the resulting retained bytes and entries in the same transaction that writes the value. A replacement counts one entry and replaces the old byte count. Return `KVMutationResponse(committed: true)` after your durability boundary. |
| `delete(_:)` | Remove the exact namespace and key. Make deletion idempotent and report `committed: true` once the deletion is durable or the key is already absent. |

Use a private app directory or database and enforce the namespace at the repository boundary, including when native code calls the repository directly. Use namespace and key as case-sensitive identifiers. Each accepts ASCII letters, digits, `_`, and `-`. The wire limits are 64 bytes for a namespace, 128 bytes for a key, and 65,536 decoded bytes per value. Installed configuration permits 1 to 4,194,304 total bytes and 1 to 1,024 entries. Count retained data against both quotas. The app-owned binding accepts exactly one installed namespace. [Storage wire schema](schema/v1.json), [typed repository protocol](../sdk/Sources/MixerCapabilities/InstalledCapabilityAdapters.swift).

Base64 is an encoding. The capability exposes ordinary app-private values to authorized guests. Keep secrets in a platform secret store. Keep paths, file descriptors, and database handles in the app. Avoid logging keys or values, or forwarding them to network services. Your app owns encryption, retention, deletion, backup policy, and migration. Keep multi-key transactions and compare-and-swap in the native repository. [Storage privacy metadata](plugins/storage.keyValue.v1.json).

## Bind the repository to the installed runtime

1. Declare the registered `storage.keyValue.v1` capability at schema version `1` in the installed identity. Use `CapabilitySchemas.storageID` and `CapabilitySchemas.storageSHA256`. The schema digest at this revision is `4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd`. Use the existing typed storage operations and guest transport. [Schema hashes](schema/hashes.json), [guest transport contract](../contracts/guest-capability-transport-v1.json).
2. Build the installed storage configuration with `schema` set to `1`, `implementation` to `app-private-kv-v1`, and `container` to `application-private`. Set `directory_component`, `maximum_total_bytes`, and `maximum_entries`. The directory component is an identifier. It selects the built-in store's directory when the app uses that store. For app-owned storage, the app chooses and opens the repository location. The configured quotas still reach `put`.
3. Build the installed grant with `capability_id`, `schema_sha256`, `permissions: ["storage.appPrivate"]`, and `namespaces` containing the single bound namespace. Set `origins` and `methods` to empty arrays. Encode the configuration and grant as canonical installed material with sorted ASCII keys, compact JSON, and one final newline. Put their exact byte SHA-256 digests in the identity descriptor. The descriptor also binds the linked capability implementation, bridge policy, and trust-root bytes. [Installed-material parser](../capability-activation/Sources/MixerCapabilityActivation/InstalledCapabilityExecution.swift), [test configuration](../capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/storage.json), [test grant](../capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/storage-grant.json).
4. Derive the fingerprint from the finalized descriptor with `CapabilityRuntimeIdentity`. It hashes the v2 identity domain and canonical CBOR. Pass the fingerprint and the installed namespace to `InstalledApplicationStorage`, then pass that binding to `InstalledCapabilityExecution`. Record the native repository implementation and dependencies in the app's build identity. The initializer verifies declared material and binding values. The embedding is responsible for linking the declared repository. [Runtime identity](../runtime-identity/Sources/MixerRuntimeIdentity/CapabilityRuntimeIdentity.swift).
5. Target that fingerprint in the signed v3 release and assignment. The signed release grant must include the exact schema, `storage.appPrivate`, and the same namespace for the guest to use storage. Mixer intersects the installed and signed grants. A request outside the intersection returns `permissionDenied` before repository dispatch. [Installed execution policy](../capability-activation/Sources/MixerCapabilityActivation/CapabilityExecutionPolicy.swift), [host dispatch](../sdk/Sources/MixerCapabilities/Host.swift).

Use the public installed APIs from the `capability-activation`, `runtime-identity`, and `sdk` source packages. The signed host control uses the default `allowsDeferredGuestUIStartup: false`.

```swift
import MixerCapabilities
import MixerCapabilityActivation
import MixerRuntimeIdentity

let identity = try CapabilityRuntimeIdentity(json: identityJSON)
let storage = InstalledApplicationStorage(
    runtimeFingerprint: identity.fingerprint,
    namespace: namespace,
    service: repository
)
let execution = try InstalledCapabilityExecution(
    identityJSON: identityJSON,
    materials: materials,
    trustRootsJSON: trustRootsJSON,
    privateContainer: privateContainer,
    applicationStorage: storage
)
```

Use deferred Guest UI startup only for an installed identity that declares that mode and a guest with the required hydration export. That mode also requires the effective signed storage grant for the bound namespace before effects can open. [Installed execution modes](../capability-activation/Sources/MixerCapabilityActivation/CapabilityInstalledExecutionMode.swift).

## Keep the repository alive across guest launches

Open one host for the originating guest. In the control, `CapabilityGuestUIRuntime.open` takes the installed execution, `beginDownload` and `appendDownload` stage signed bytes, `finishDownload` validates them, and `start` selects the guest and enables admitted effects. Mixer owns the host and its request lifetimes. The embedding owns the repository across runtime launches. Await each runtime's `close()` and confirm its recovery snapshot is closed with `activation.cleanupPending == false`. Let the app's repository work finish before closing the repository. If runtime shutdown is unconfirmed, keep the repository open and preserve its files, runtime recovery files, and diagnostics. The runtime releases its adapter reference and leaves repository shutdown to the app. [Public runtime](../capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift), [adapter teardown](../experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Lifecycle.swift).

Use `quotaExceeded` for quota failures and `unavailable` for a closed repository. Mixer forwards `CapabilityFailure`, maps `CancellationError` to `cancelled`, maps wire validation errors in callback results to `invalidResponse`, and maps other implementation errors to `ioFailure`. Keep native error text private. The host can select `deadlineExceeded` before the repository returns. Check cancellation before entering a mutation's commit boundary. Cancellation, a deadline, or host closure can win after commit starts. Re-read the key through a live, authorized owner before retrying an uncertain mutation. [Host response selection](../sdk/Sources/MixerCapabilities/Host.swift).

## Run the signed control on macOS

Use the checkout containing `testInstalledApplicationStorageGrantDenialAndColdReadback`. The control was verified against public Mixer `9c21d3edb4738c6e0c51a6cc6355465ac18c208c` with the test changes applied. Use macOS with Xcode and Swift 6.2 or later, and put Cargo and Rust on `PATH`. SwiftPM may fetch the exact dependencies in `capability-activation/Package.resolved`. Run from the checkout root.

```sh
(
    set -eu
    umask 077
    source_root="$PWD"
    mkdir -p "$source_root/verification/local"
    run=$(mktemp -d "$source_root/verification/local/w09-storage.XXXXXXXX")
    trap 'if [ -d "$run" ]; then printf "Retained W09 scratch at %s\n" "$run" >&2; fi' EXIT
    mkdir "$run/lib" "$run/tmp"
    TMPDIR="$run/tmp" CARGO_TARGET_DIR="$run/vm" cargo build --offline --locked \
        --manifest-path "$source_root/vm/Cargo.toml" --release \
        --features experimental-capability-native --lib
    cp "$run/vm/release/libmixer_vm.a" "$run/lib/libmixer_vm_capability_experimental.a"
    test_status=0
    TMPDIR="$run/tmp" swift test --package-path "$source_root/capability-activation" \
        --scratch-path "$run/swiftpm" --cache-path "$run/swift-cache" \
        --config-path "$run/swift-config" --security-path "$run/swift-security" \
        --manifest-cache local --disable-dependency-cache --force-resolved-versions \
        -Xcc -I -Xcc "$source_root/vm/include" -Xlinker -L -Xlinker "$run/lib" \
        --filter GuestUISignedRuntimeTests/testInstalledApplicationStorageGrantDenialAndColdReadback \
        > "$run/signed-test.log" 2>&1 || test_status=$?
    cat "$run/signed-test.log"
    if [ "$test_status" -ne 0 ]; then
        exit "$test_status"
    fi
    if ! grep -Fxq 'W09 signed storage retirement confirmed' "$run/signed-test.log"; then
        printf 'The signed test did not confirm retirement.\n' >&2
        exit 1
    fi
    rm -rf -- "$run"
)
```

Expect one passing XCTest. The fixture signs two guests in the same test-only installation scope and uses the same installed and signed storage grant for both. The first guest sends a typed `put` to `material_test` and checks `committed: true`. The second guest sends a `put` to `outside_scope` and checks the exact `permissionDenied` completion. The app-owned repository receives one write in total, with the installed quotas. The test confirms both owners retired and their cleanup settled before closing the repository and reading back `AAH+/w==` through a fresh disk-backed instance. The recipe removes its run directory after a successful test with explicit retirement confirmation. If the test fails or confirmation is missing, keep the printed run directory for diagnosis. The control uses synthetic bytes and a test-only signer on a macOS host without mounting a view. Readback uses a fresh repository instance in the same process. [Signed control and repository conformance](../capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedRuntimeTests.swift), [signing and binding fixture](../capability-activation/Tests/MixerCapabilityActivationTests/GuestUISignedFixture.swift), [verification receipt](../verification/receipts/w09-app-owned-storage.json).
