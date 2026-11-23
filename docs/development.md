# Develop Mixer

This page covers building and testing Mixer itself. To build an app with
Mixer, see [Getting started](guides/getting-started.md).

## Requirements

You need Xcode with Swift 6.2 or later, Rust, Go 1.26.4, and Python 3.12 or
later. Node is used only as a development test oracle. The default Xcode
compiler does not match the Android and Wasm SDKs. See
[`release/toolchain-candidate.json`](../release/toolchain-candidate.json) for
cross-target compiler candidates.

## Run the tests

The CLI tests need the `mixer` executable built with the same Swift toolchain.

```sh
swift test
swift build --package-path cli --product mixer -j 2
MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"
test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"
MIXER_STORE_CUSTODY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mixer-cli-tests.XXXXXX")"
MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" \
	MIXER_STORE_CUSTODY_DIR="$MIXER_STORE_CUSTODY_DIR" \
	MIXER_SUITE_HOLD="$MIXER_STORE_CUSTODY_DIR/SUITE-HOLD.json" swift test --package-path cli
swift test --package-path updates
swift test --package-path capabilities
cargo test --manifest-path vm/Cargo.toml
cd services && go test -race ./...
```

Native session and activation tests need the owned static VM archive. Follow
[`runtime/README.md`](../runtime/README.md) and
[`activation/README.md`](../activation/README.md) to build a frozen source
revision and pass its isolated library directory to Swift. Do not point the
linker at a Cargo directory that has both static and dynamic VM libraries. CI
does the static build and runs the matching host suites.

`tests/integration/release-workflow.py` runs local HTTP delivery, the Swift
verifier, and the integer VM together. See the integration README for its
prerequisites.

`python3 scripts/check-policy.py` checks dependency manifests and gate
integrity. It is a guardrail, not a security, legal, or provenance
certification.

## Use the SDK as a Swift package

The repository root is a Swift package. It exports `MixerCore`, `MixerUI`,
`MixerApple`, `MixerGuest`, and `MixerCapabilities` from the same sources as
`sdk/`. To use it from another project, add
`https://github.com/snowdamiz/mixer.git` with a full commit revision and the
package identity `mixer`. Pin a reviewed revision: these are development APIs
with no stable release tag. The root package does not ship the VM, updater, or
activation binary.

## Repository layout

| Directory | Contents |
| --- | --- |
| [`sdk/`](../sdk/README.md) | Swift state and effects, UI protocol, native Apple controls, guest codecs |
| [`cli/`](../cli) | The `mixer` command: create, export, build, run, import, and inspect |
| [`vm/`](../vm) | MixerVM, the Rust interpreter that runs signed updates |
| [`runtime/`](../runtime/README.md) | Typed native Swift sessions over the VM |
| [`activation/`](../activation/README.md) | Signed cold-start selection, health checks, and fallback |
| [`capabilities/`](../capabilities) | Generated Swift and Java codecs for native capabilities |
| [`native/android/`](../native/android) | Swift, JNI, and native Android widgets |
| [`updates/`](../updates/README.md) | Signed artifact verifier and recovery store |
| [`hosted/`](../hosted) | Phoenix control plane over PostgreSQL and Oban |
| [`console/`](../console) | SolidJS web console |
| [`services/`](../services) | Go release API and signed contracts |
| [`compiler/`](../compiler) | Compiler corpus and size experiments |

Each component's README lists what it implements and its limitations.

## Planning and evidence records

- [STATUS.md](../STATUS.md) is the integrated state, newest first, and
  [PLAN.md](../PLAN.md) is the execution index.
  [mixer-product-plan.md](../mixer-product-plan.md) defines the full scope.
- [`gates/local.json`](../gates/local.json) holds the L01–L08 completion
  checklist, and [`gates/ga.json`](../gates/ga.json) the G01–G38 launch gates.
- [`work-graph.json`](../work-graph.json) tracks the W01–W18 work packages, and
  [`dogfood/receipts/milestones.json`](../dogfood/receipts/milestones.json) the
  FieldLog milestones.
- `verification/receipts/` holds compact receipts. Build logs and generated apps
  stay in `verification/local/`. See the
  [verification guide](../verification/README.md).
- `python3 scripts/progress.py` prints the README progress table and badge URL
  from these records.
