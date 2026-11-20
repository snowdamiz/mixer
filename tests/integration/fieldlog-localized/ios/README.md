# Prepare the localized FieldLog iOS checklist test

The L02 and L08 §22.2.5 fixture uses signed sequences 1 and 2 on one FieldLog
installation. It stages the maintained iOS key-rotation recipe and applies
the exact signed Apple V1 scroll host from public Mixer
`8ee46c7ecd3a828d638fb5e25af0812e1f707d1e`. The Debug overlay seeds one
isolated workspace through ordinary FieldLog repository transactions. The
test selects `فحص المضخة 07` and reuses the saved task UUID on later launches.

## Stage the sources and typecheck XCTest

Use Bash, Python 3.12 or newer, and Xcode 27.2 (27B52). Start in an isolated
checkout at `9d0eec8ac194254ce19779d87fbdd93f107c4de6`. Apply the fixture
commit with `git cherry-pick --no-commit <fixture-commit>` to keep the
checkout at the public pin. Supply the verified Android guest export directory as `FIELDLOG_GUESTS`. It
contains `binding.json`, `baseline.wasm`, and `reviewed.wasm`. The preparer reads
those three files and verifies the source binding, VM tree, deferred guest
transport, storage adapter, and both payload digests.

```bash
set -e
: "${FIELDLOG_GUESTS:?Set FIELDLOG_GUESTS to the verified guest export directory}"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
recipe="$PWD/tests/integration/fieldlog-localized/ios"
mkdir -p "$PWD/verification/local"
scratch="$(mktemp -d "$PWD/verification/local/fieldlog-ios-localized.XXXXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT
mkdir "$scratch/tmp" "$scratch/modules"
export TMPDIR="$scratch/tmp"

python3 -B "$recipe/prepare.py" "$scratch/work" --guests "$FIELDLOG_GUESTS"
packet="$scratch/work/packet"
python3 -B "$packet/identity_binding.py"
python3 -B "$recipe/test_fixture.py" "$packet"
sdk="$(xcrun --sdk iphonesimulator --show-sdk-path)"
platform="$(dirname "$(dirname "$sdk")")"
xcrun --sdk iphonesimulator swiftc -typecheck -swift-version 6 \
	-target arm64-apple-ios26.0-simulator -sdk "$sdk" \
	-F "$platform/Library/Frameworks" -I "$platform/usr/lib" \
	-module-cache-path "$scratch/modules" \
	"$scratch/work/source/fieldlog/ios/FieldLogUITests/ChecklistJourney.swift"
du -sh "$scratch"
```

The preparer checks the reconstructed rotation source inventories before
applying the localized overlays. It recomputes both owning digests before
signing. The linked package inventory uses the five ordinary iOS package roots
under `source/mixer`, with paths relative to `source`. The native fallback
inventory uses FieldLog `Sources` and `ios/FieldLog`, with paths relative to
`source/fieldlog`. Both hash the ordinary sorted SHA-256/path lines. The
generated `ios/FieldLog/ChecklistRelease` resource copy is excluded from the
fallback inventory and is checked separately against signed material.
`packet/localized-binding.json` also binds the overlay files, staged recipes,
identity template, guest inputs and exact XCTest selector. The inert controls
use synthetic receipts and public material placeholders and start no listeners.

## Sign, validate and build generic Simulator products

Stage a fresh work directory with `prepare.py` and keep it through readback.
Use the signing, `validate-host.py`, origin smoke, installed-host probe, and
generic build commands from the
[iOS rotation recipe](../../../../capability-activation/verification/fieldlog-ios/rotation/README.md).
Use the staged scripts and already admitted Arabic guests. Set `packet` and
`source` to the staged directories and skip the rotation guest compilation.
Run `python3 -B "$packet/identity_binding.py"` immediately before signing.
Generate fresh signatures for the localized identity. The signer updates the
public-root digest and binds the assignments to the resulting runtime.
The staged `validate-host.py` checks the staged inputs and the signed identity
before running the host verifier, including the rotation refusal cases.
The staged host probe expects the Arabic title and the two different
status/action pairs while checking headless health, committed workspace
bytes and owner retirement.

Build with the pinned Simulator VM archive and explicit staged sources and
headers, without choosing a device. Follow the rotation recipe's strict
ad hoc signature, `arm64`, `IOSSIMULATOR`, and loopback Info.plist checks.
Run `python3 -B "$packet/prepare-run.py" iphonesimulator "$products"` after
the build. It rechecks source bindings and compares the exact embedded
`ChecklistRelease` file set and bytes against the signed fixture. Record
the build command, VM archive hash, identity template and binding hashes,
and SHA-256 of the final app, test runner, and XCTest executables. Record
the post-build resource check with those hashes and recheck them before
dispatch. The generic plan check verifies the enabled UI target and selector
filters. Only the device run can establish that XCTest dispatched that method.

## Run and reconcile the root-owned XCTest

After root's Accessibility preflight and device admission, use the staged
`origin.py` and `prepare-run.py` for the exact selector
`FieldLogUITests/ChecklistJourney/testSignedLocalizedChecklist`. Keep the
actual argv in `test-command.json`, the exported XCTest summary and attachment
manifest/files, and the stopped origin's `origin/origin-receipt.json`. After
the test finishes and the app exits, copy the exact isolated workspace
named in the `workspace-folder` attachment into the evidence directory.
Then run:

```bash
python3 -B "$packet/verify-readback.py" "$evidence" "$owned_udid"
```

Readback matches both served signed offers and artifacts to the fixture bytes.
Relaunches can fetch the current offer without downloading its artifact.
It reconciles data listener closure at `offline` and control closure after
`complete`, then checks cold sequence-2 health, the final recovery state,
workspace revision 3, and one appended `taskSaved` for the same UUID. The
XCTest taps the stable Done selector and waits for the sheet to disappear
before observing that task's completed project row. The ordinary Done path
dismisses only after guest close reports no incomplete attempt or pending
cleanup. Verify owned-device cleanup separately.

The layout attachment reports the enclosing FieldLog sheet's SwiftUI direction
and text size. The signed guest has a separate hosting controller. Read the
guest screenshots and bounds for Arabic glyph order, visible digits `07`,
text scaling and clipping. Its hosting environment has no direct direction
measurement in this fixture.
