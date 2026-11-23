# Replay the signed F04 task save and retry

Run the replay on arm64 macOS with Apple Swift 6.4.2, the Embedded Swift 6.3.3
toolchain, Rust 1.99.0, Git, Python 3, `jq`, and `rg`. Use the existing local Cargo
registry cache and SwiftPM Git caches for the pinned `swift-crypto` and
`swift-asn1` revisions. Set `F04_RUST_BIN` or `F04_WASM_TOOLS` if those toolchains
live outside their default paths in the driver.

From the delivery checkout, pass the local Stage repository containing
`6c069d95f509e197433118f65b7f39fb3a454412` and a local FieldLog Git checkout or
mirror containing `552559d2d3278abb9b1aa7dcf0288102c09a202b`. The replay uses
pinned Git objects from both repositories and includes a macOS sandbox that
denies network access and writes to those inputs.

```sh
tests/integration/fieldlog-d8-f04-signed/replay-private.sh \
  /path/to/local/mixer-stage /path/to/local/fieldlog
```

The driver prints a JSON result after its process group exits and it removes
its owned scratch under `/private/tmp`. It enforces an eight-minute deadline
and samples scratch use against a 1.2 GiB limit. It reconstructs the Pair25
repository candidate and verifies its tree, the `WorkspaceRepository.swift`
blob, and the historical successor Wasm digest before running the trials.

`task-retry-replay.patch` contains the exact producer source delta from
`4bcfe774f70794b86c014680a351a5f1dbfff3f1`. The driver applies it to a disposable
Stage export and verifies the resulting package and contract trees.
`replay-observations.patch` adjusts the test reporting in that export.
The driver uses direct signed V3 delivery with temporary Ed25519 trust and a
headless display witness.

## Read the result

- `privateRetry` confirms a refusal at the real Pair25 writer's `before_rename`
  boundary. Both field values survive in the same editor, and retry sends the
  identical bytes. Exactly one task and its linked `taskSaved` outbox row reach
  disk. A separate process opens the repository and checks the persisted bytes.
- `stockRefusal` confirms the stock first-frame refusal before presentation.
  Only this refusal trial seeds a previous healthy release. It checks that
  release's identity and the unchanged workspace bytes.
- `misbound` and `wrongKey` confirm refusal before presentation with zero
  storage writes. Neither trial seeds a healthy release.
- `compactEditor` checks the shared F05/F06 compact profile's refusal of the exact
  deferred-startup dependency. `stockVectors` checks the canonical CBOR and
  fingerprints of all 11 stock identities.

This is a test-only host replay. The independent review blocked product
promotion because adding the overlay to canonical source would change the
stock archive selector from 158 to 159 inputs. The overlay's storage adapter
checks the namespace and key on writes. Product promotion requires host-side
proof that the write comes from the current Save action and matches the values
shown in the editor. Device behavior, Apple signing, and product release
acceptance are outside this replay's scope.

[Completed replay receipt](../../../verification/receipts/l08-d8-f04-task-retry-offline-overlay.json)
