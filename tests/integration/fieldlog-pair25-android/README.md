# Build and export the FieldLog Android app

Build the ordinary Android app from FieldLog tree `e39a5ea393` and Mixer
`857e4b4aa7`. [The source pins](pins.json) name the public commits, each
FieldLog patch, and the tree produced after each patch.

## Set up the build

Use an Apple silicon Mac with Xcode 27.2 for the host CLI and Xcode 26.6 for
the Android build. Install the tools in the [Android build setup](../../../README.md#build-for-android).
The development signing recipe also needs jq, Android Build Tools 36.0.0, and
Rust 1.99.0 with the `aarch64-linux-android` target and `llvm-tools` component.

Run the following commands in a dedicated Bash shell from the root of a
Mixer checkout with the Git objects named in `pins.json`. Set the tool paths
if you installed them in different locations.

```bash
set -euo pipefail
repo="$PWD"
recipe="$repo/tests/integration/fieldlog-pair25-android"
mkdir -p "$repo/verification/local"
scratch="$(mktemp -d "$repo/verification/local/fieldlog-pair25.XXXXXXXX")"
work="$scratch/work"
python3 -B "$recipe/prepare-sources.py" "$work"

export MIXER_SWIFT="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
export FIELDLOG_SWIFT_BIN="$(dirname "$MIXER_SWIFT")"
export MIXER_SWIFT_SDKS_PATH="$HOME/Library/org.swift.swiftpm/swift-sdks"
export MIXER_ANDROID_ARTIFACT_PATH="$MIXER_SWIFT_SDKS_PATH/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export MIXER_JDK=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
export JAVA_HOME="$MIXER_JDK"
export FIELDLOG_XCODE=/Applications/Xcode_26.6.app/Contents/Developer
export RUSTUP_HOME="${RUSTUP_HOME:-$HOME/.rustup}"
host_xcode=/Applications/Xcode.app/Contents/Developer

export HOME="$work/home"
export CFFIXED_USER_HOME="$HOME"
export TMPDIR="$work/tmp"
export CLANG_MODULE_CACHE_PATH="$work/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$work/module-cache"
export XDG_CACHE_HOME="$work/xdg-cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$TMPDIR"

mirror_root="$HOME/Library/Caches/org.swift.swiftpm/repositories"
mkdir -p "$mirror_root"
fetch_mirror() {
	local name="$1" tag="$2" dir="$mirror_root/$3" commit="$4" tree="$5"
	git init --quiet --bare "$dir"
	git -C "$dir" fetch --quiet --depth=1 --no-tags \
		"https://github.com/apple/$name.git" "refs/tags/$tag:refs/tags/$tag"
	test "$(git -C "$dir" rev-parse "$tag^{commit}")" = "$commit"
	test "$(git -C "$dir" rev-parse "$tag^{tree}")" = "$tree"
}
fetch_mirror swift-crypto 5.0.3 swift-crypto-7e0614ea \
	c2cbadd7263439d8015189668f96ff5b5be565ce 841fdfd88fed694e6532a3200a91b0f85595c340
fetch_mirror swift-asn1 1.7.3 swift-asn1-7065ad2c \
	3b6410f7dee09eb33cdd26260c5fd47fda19b0e2 e7ed2e8c1483426c349b678e7d10940509f9d39c

source "$work/mixer/tests/integration/fieldlog-saved-draft/android/recipe/offline-swiftpm.zsh"
DEVELOPER_DIR="$host_xcode" /usr/bin/swift build \
	--package-path "$work/mixer/cli" --scratch-path "$work/cli-work/build" \
	--cache-path "$work/cli-work/cache" --config-path "$work/cli-work/config" \
	--security-path "$work/cli-work/security" --disable-dependency-cache \
	--disable-prefetching --force-resolved-versions --disable-index-store \
	--jobs 8 --product mixer
cli="$work/cli-work/build/out/Products/Debug/mixer"

export DEVELOPER_DIR="$FIELDLOG_XCODE"
scripts="$work/fieldlog/Integrations/GeneratedReport/scripts"
app="$work/prepared"
python3 -B "$scripts/build-android.py" --mixer "$cli" \
	--sdk-checkout "$work/mixer" --android-adapter-path "$work/mixer/native/android" \
	--output "$app" --prepare-only
```

The script checks the SDK revision, Pair25 lock, appearance descriptor, and
native fingerprint. The prepared project contains the ordinary FieldLog app
and its generated SDK and Android adapter.

## Build the relocated export

Export the prepared app. Move both the export and the preparation project so
that the original project path is absent during validation and build.

```bash
"$cli" export "$scratch/exported" --directory "$work/prepared"
mkdir "$scratch/relocated"
mv "$scratch/exported" "$scratch/relocated/FieldLog"
mv "$work/prepared" "$scratch/original-project"
app="$scratch/relocated/FieldLog"
"$cli" config validate --directory "$app"
"$cli" build --platform android --directory "$app"
```

Find the unsigned APK under `$app/.mixer/android-build/`. Inspect it with
`aapt2 dump badging`. Look for package `dev.fieldlog.generatedr90` and the
launcher `dev.fieldlog.generatedr90.androidhost.PublicActivity`.

## Build the signed Entry Commit development fixture

Use the prepared project or its relocated export. Keep `$app` set to the
directory you want to package. Run Java and JNI in order because both read
the staged FieldLog Git index.

```bash
rev=857e4b4aa7a32cda368257b2be1a63e77106bed8
rustc="$(rustup which --toolchain 1.99.0 rustc)"
export PATH="$(dirname "$rustc"):$PATH"
sdk_registry="$HOME/Library/org.swift.swiftpm/swift-sdks"
mkdir -p "$sdk_registry"
ln -s "$MIXER_SWIFT_SDKS_PATH/swift-6.3.3-RELEASE_android.artifactbundle" "$sdk_registry/"
python3 -B "$work/mixer/experimental-capability-runtime/build-vm.py" \
	--revision "$rev" --target android --output "$work/android-engine" \
	--rustc "$rustc" --ndk "$ANDROID_HOME/ndk/27.1.12297006"

pair="$scripts/pair25"
python3 -B "$pair/build-products.py" java "$work" "$app"
python3 -B "$pair/build-products.py" jni "$work" "$app"

mkdir -p "$work/seal-package/Sources/FieldLogEntryCommitSeal"
cp "$pair/SealPackage.swift" "$work/seal-package/Package.swift"
cp "$pair/SealEntryCommit.swift" "$work/seal-package/Sources/FieldLogEntryCommitSeal/main.swift"
DEVELOPER_DIR="$host_xcode" /usr/bin/swift package \
	--package-path "$work/seal-package" --scratch-path "$work/seal-work/build" \
	--cache-path "$work/seal-work/cache" --config-path "$work/seal-work/config" \
	--security-path "$work/seal-work/security" --disable-dependency-cache \
	--disable-prefetching resolve
diff -u <(jq -S '.pins | sort_by(.identity)' "$work/mixer/cli/Package.resolved") \
	<(jq -S '.pins | sort_by(.identity)' "$work/seal-package/Package.resolved")
DEVELOPER_DIR="$host_xcode" /usr/bin/swift build \
	--package-path "$work/seal-package" --scratch-path "$work/seal-work/build" \
	--cache-path "$work/seal-work/cache" --config-path "$work/seal-work/config" \
	--security-path "$work/seal-work/security" --disable-dependency-cache \
	--disable-prefetching --force-resolved-versions --disable-index-store \
	--jobs 8 --product FieldLogEntryCommitSeal
python3 -B "$pair/package-entry-commit.py" "$work" "$app" "$work/package"
```

The packager rebuilds the 7,606-byte Entry Commit Wasm in two directories
and compares both outputs with the pinned payload. It creates fresh
development signatures and writes the APK and `apk-evidence.json` under
`$work/package`. The APK can be installed on a clean API 36 or later arm64
emulator. Each fresh signature requires a clean install on a disposable
emulator that has a differently signed FieldLog package.
[Reviewed Android artifact](../../../verification/receipts/fieldlog-e39a5ea3-matched-development-artifacts.json) ·
[Offline device replay](../../../verification/receipts/fieldlog-e39a5ea3-857e4b4a-api36-offline-report-commit.json)
