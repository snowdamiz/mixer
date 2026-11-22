# Build the Pair25 FieldLog APK with runtime notices

## Prepare the paired L07 fixture

The default `prepare-successor.py` command creates the paired FieldLog app. It verifies
eight recorded patches and the paired FieldLog tree
`7b2b98f098559f57ce39e213321478058c289c5a` before applying the notice patch.

```bash
repo="$PWD"
notice_recipe="$repo/tests/integration/fieldlog-pair25-android/rust-runtime-notices"
mkdir -p "$repo/verification/local"
scratch="$(mktemp -d "$repo/verification/local/fieldlog-pair25-notices.XXXXXXXX")"
work="$scratch/work"
python3 -B "$notice_recipe/prepare-successor.py" --mixer "$repo" "$work"
test "$(git -C "$work/fieldlog" write-tree)" = 34810962320bdfb7877b8bbdd065495e9ec1e2bb
```

Keep the Rust notice and the adjacent `networking-crypto/` directory in
place. Continue with the original recipe's toolchain exports and
`build-android.py --prepare-only`. Then use the commands under **Produce,
seal, and package** below.

Both producer receipts bind the twelve notice hashes, the VM receipt, the
Swift Crypto lock inputs, and the official Swift 6.3.3 arm64
FoundationNetworking ELF hash. The sealer binds the exact JNI ELF hash
after linking. The packager checks both ELF hashes and the complete notice
inventory in the unsigned and signed APKs.

The SDK SBOM names BoringSSL `fips-20220613`. Its upstream tag supplies the
notice text. The exact SDK build commit remains unproven. The Swift Crypto
copy of BoringSSL has a separate source pin. See the [pinned notice
sources](networking-crypto/sources.json).

The standalone APK packager requires `--pair25-rust-notice` on this
source tree. The same twelve notices and both ELF checks apply to the
Android Settings composition.

## Prepare the historical Rust-only fixture

Use a fresh build directory for this development APK. The FieldLog photo
source tree is `00406fe735a3e48b075dd545d8df77670caab336`.
The original Pair25 packaging patch produces
`f4422116bb914c3c549f8ba31f1e30f7b94e0e9d` when applied to that tree.
`prepare-successor.py` checks the SHA-256 of the original recipe and
photo patch, then applies and verifies the notice successor.
It also checks out Mixer `857e4b4aa7a32cda368257b2be1a63e77106bed8`
with the VM inputs available.

## Prepare the photo successor

Use a dedicated Bash shell. Set `repo` to the Mixer checkout that carries
this directory and has the Git objects pinned in `prepare-successor.py`.
The [original Pair25 recipe](../README.md) specifies the toolchains and
host CLI setup.

```bash
set -euo pipefail
repo="$PWD"
recipe="$repo/tests/integration/fieldlog-pair25-android"
notice_recipe="$recipe/rust-runtime-notices"
mkdir -p "$repo/verification/local"
scratch="$(mktemp -d "$repo/verification/local/fieldlog-pair25-notices.XXXXXXXX")"
work="$scratch/work"
python3 -B "$notice_recipe/prepare-successor.py" --historical-rust-only --mixer "$repo" "$work"
test "$(git -C "$work/fieldlog" write-tree)" = 0c38770065656bf7c5a2aa768055ff8b453b082d
```

Keep the historical checkout at the recorded photo-only tree for this
replay. Use the default preparation command for the paired product with
the reviewed pickers, camera, queue, and map.

Continue the original recipe's setup at `export MIXER_SWIFT=` through
`build-android.py --prepare-only`. Keep `$app` set to the prepared
project or its relocated export.

## Produce, seal, and package

Run the original recipe's signed fixture commands through
`build-vm.py --target android`. Then run the preflight and both
producers in this order.

```bash
pair="$work/fieldlog/Integrations/GeneratedReport/scripts/pair25"
notice="$notice_recipe/Rust-1.99.0-Android-NOTICES.txt"

python3 -B "$pair/build-products.py" preflight "$work" "$app" --rust-notice "$notice"
python3 -B "$pair/build-products.py" java "$work" "$app" --rust-notice "$notice"
python3 -B "$pair/build-products.py" jni "$work" "$app" --rust-notice "$notice"
```

Run the original recipe's sealer package setup, dependency lock
comparison, and Swift build. Use this command for final packaging.

```bash
python3 -B "$pair/package-entry-commit.py" \
	--rust-notice "$notice" "$work" "$app" "$work/package-with-rust-notices"
```

Preflight writes `$work/pair25-notice-inputs.json` with the notice hashes
and the hash of the complete VM receipt. Both producer receipts bind the
same values. Packaging verifies those receipts before the guest build
and again before sealing and signing. The sealed build inputs and signed
ZIP readback include every notice hash.

The packaging destination must be fresh. The packager links the completed
evidence file into place without replacing an existing file. A sidecar
collision aborts before APK publication. Read `package.log` in the
destination after a refusal.

The original baseline manifest binds `{}` without a trailing newline as
the empty source map. If the guest uses a different map, the signed
manifest must bind those exact bytes. The notices bind through
`link_inputs_sha256`.

The Rust notice bundle covers the runtime observed in the retained APKs.
[sources.json](sources.json) records the 27 upstream text hashes.
The exact linked NDK libunwind copy remains unresolved between r27b and
r27d. Both toolchains ship the same notice and identify the same
Android LLVM source revision.

## Run the inert checks

Use the installed NDK r27b and Swift 6.3.3 Android SDK notice files.
The tests recreate the paired successor and exercise its producer and
packager code with inert tools. Pass `--historical-rust-only` to test
the exact historical photo-only composition.

```bash
python3 -B "$notice_recipe/test-packaging.py" \
	--mixer "$repo" --android-sdk "$ANDROID_HOME" \
	--swift-sdk "$MIXER_ANDROID_ARTIFACT_PATH" --scratch "$scratch"
```
