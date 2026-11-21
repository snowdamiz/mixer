# Build the Pair25 FieldLog APK with Rust notices

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
python3 -B "$notice_recipe/prepare-successor.py" --mixer "$repo" "$work"
test "$(git -C "$work/fieldlog" write-tree)" = 0c38770065656bf7c5a2aa768055ff8b453b082d
```

## Include the reviewed project pickers

To build the product with the installed Android picker and the Apple
pagination change, apply both patches after the notice preparation.
Run this before the host CLI, Java, or JNI build. The photo-only
predecessor above remains available for historical replay.

```bash
fieldlog="$work/fieldlog"
android_patch="$repo/verification/receipts/fieldlog-android-project-picker-ad6c8dba.patch"
apple_patch="$repo/verification/receipts/fieldlog-apple-project-pagination-00406fe7.patch"
printf '%s  %s\n' \
  53a221508c9d2fee4c6821e9954aaf8f880a4a9d5a4c77af82e516e64335d85a "$android_patch" \
  4fbbb6e6c63afd886df2054d36c1024e3cdcab014a4307d14c1a896900ae2c4e "$apple_patch" |
  shasum -a 256 -c
git -C "$fieldlog" apply --index --unidiff-zero --whitespace=error "$android_patch"
git -C "$fieldlog" apply --index --whitespace=error "$apple_patch"
test "$(git -C "$fieldlog" write-tree)" = bb1aff13c8f4ed27c7bed24f0fde96fbe873a15b
```

The Android build uses a fresh development signer. Use a fresh
disposable install for the replay. [Installed Android evidence](../../../../verification/receipts/fieldlog-android-project-picker-installed-ad6c8dba.json)

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

Preflight writes `$work/pair25-notice-inputs.json` with the five notice
hashes and the hash of the complete VM receipt. Both producer receipts
bind the same values. Packaging verifies those receipts before the
guest build and again before sealing and signing. The sealed build
inputs and signed ZIP readback include all five notice hashes.

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
The test recreates the pinned photo composition and checks the actual
producer and packager code with inert tools.

```bash
python3 -B "$notice_recipe/test-packaging.py" \
	--mixer "$repo" --android-sdk "$ANDROID_HOME" \
	--swift-sdk "$MIXER_ANDROID_ARTIFACT_PATH" --scratch "$scratch"
```
