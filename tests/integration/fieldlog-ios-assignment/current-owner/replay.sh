#!/bin/bash
set -euo pipefail

if [[ $# -lt 5 || $# -gt 6 || ${6:-host} != host && ${6:-host} != all ]]; then
  echo "Usage: $0 MIXER_CHECKOUT FIELDLOG_GIT_STORE SWIFT_CRYPTO_GIT_STORE SWIFT_ASN1_GIT_STORE ORIGINAL_ASSIGNMENT_PATCH [host|all]" >&2
  exit 64
fi

mixer=$(cd "$1" && pwd -P)
fieldlog_pin=$(cd "$2" && pwd -P)
crypto=$(cd "$3" && pwd -P)
asn1=$(cd "$4" && pwd -P)
patch=$(cd "$(dirname "$5")" && pwd -P)/$(basename "$5")
mode=${6:-host}
delivery=$(cd "$(dirname "$0")" && pwd -P)
rust_bin=${FIELDLOG_RUST_BIN:-"$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"}
public=e6622741eaa1a4b699fa604870b2168920926582
recipe_revision=050afa201ffbfa0d2c87ba84f9321ea2158d2bf8
recipe=tests/integration/fieldlog-pair25-android/rust-runtime-notices
current=41eaf5b4e5ff22ed990e27166e4a860063b4ac26
after=8c2cc120237e3dff26e959674cdd455a1499a202
fix="$delivery/fieldlog-ios-assignment-review-fixes.patch"

mkdir -p "$mixer/verification/local"
run=$(mktemp -d "$mixer/verification/local/fieldlog-ios-assignment-review-replay.XXXXXXXX")
cleanup() {
  local result=$?
  du -sk "$run"
  python3 -B -c 'from pathlib import Path; import shutil, sys; p = Path(sys.argv[1]); assert p.is_dir() and not p.is_symlink() and p.name.startswith("fieldlog-ios-assignment-review-replay."); shutil.rmtree(p)' "$run"
  test ! -e "$run"
  printf 'Scratch removed %s\n' "$run"
  exit "$result"
}
trap cleanup EXIT
printf 'Scratch opened %s\n' "$run"
ulimit -c 0
mkdir "$run/recipe" "$run/tmp" "$run/mirrors" "$run/hostlib"
export TMPDIR="$run/tmp/" GIT_ALLOW_PROTOCOL=file GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null

require_tree() {
  local actual
  actual=$(git -C "$app" write-tree)
  [[ "$actual" == "$1" ]] || { echo "Expected tree $1, got $actual" >&2; exit 65; }
}

require_sha() {
  local actual
  actual=$(shasum -a 256 < "$1")
  [[ ${actual%% *} == "$2" ]] || { echo "SHA-256 mismatch for $1" >&2; exit 65; }
}

require_absent() {
  if grep -Fq -- "$1" "$2"; then
    echo "Unexpected $1 in $2" >&2
    exit 65
  fi
}

for file in prepare-successor.py fieldlog-packaging.patch fieldlog-l07-notices.patch; do
  git -C "$mixer" show "$recipe_revision:$recipe/$file" > "$run/recipe/$file"
done
require_sha "$run/recipe/prepare-successor.py" 99a8b563f84f345a0d2d6c63b5f11ad6d98434df2b517de34199845a2bf8580f
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="url.file://$fieldlog_pin.insteadOf"
export GIT_CONFIG_VALUE_0=https://github.com/snowdamiz/fieldlog.git
python3 -B "$run/recipe/prepare-successor.py" --mixer "$mixer" "$run/work"

app="$run/work/fieldlog"
sdk="$run/work/mixer"
require_tree 34810962320bdfb7877b8bbdd065495e9ec1e2bb
git -C "$app" apply --index --reverse "$run/recipe/fieldlog-l07-notices.patch"
require_tree 7b2b98f098559f57ce39e213321478058c289c5a
apply_public() {
  local file=$1
  git -C "$mixer" show "$public:verification/receipts/$file" > "$run/$file"
  require_sha "$run/$file" "$2"
  git -C "$app" apply --index --unidiff-zero --whitespace=error "$run/$file"
  require_tree "$3"
}
apply_public fieldlog-ios-settings-bounded-7b2b98f0.patch \
  2639352790e03eadd4fc0ae1cb81fe2fbdcfd4d1c7f7d3f872dc405869fa7418 f2865989693af3eb4a1891a492054baa36ac1e2f
apply_public fieldlog-ios-task-conflict-injected-f2865989.patch \
  f5c09970636d4b4aa650aa7ee709d923f68281f7a09a41d17af05cb2772f7b34 "$current"

git -C "$app" -c user.name=Local -c user.email=local.invalid commit -qm 'Exact current FieldLog candidate'
require_sha "$patch" 80b2a0edfca615d07fbfdb0077719e9bce4efa381a99ed580458cc08ab373eaa
git -C "$app" apply --index --whitespace=error "$patch"
require_tree "$after"
git -C "$app" diff --cached --check
git -C "$app" apply --index --reverse "$patch"
require_tree "$current"
test -z "$(git -C "$app" status --porcelain --untracked-files=all)"
git -C "$app" apply --index --whitespace=error "$patch"
require_tree "$after"
printf 'FieldLog source %s -> %s, reverse verified\n' "$current" "$after"

git -C "$app" -c user.name=Local -c user.email=local.invalid commit -qm 'Pinned assignment candidate'
require_sha "$fix" b80b10699aebeed52b239de41521db7e8ad1dc0654e336992337f80c8cdbe342
fixed=73e9f093470ef9173a8e6a21da56f8537622212f
git -C "$app" apply --index --whitespace=error "$fix"
require_tree "$fixed"
git -C "$app" diff --cached --check
git -C "$app" apply --index --reverse "$fix"
require_tree "$after"
test -z "$(git -C "$app" status --porcelain --untracked-files=all)"
git -C "$app" apply --index --whitespace=error "$fix"
require_tree "$fixed"
printf 'Review fix source %s -> %s, reverse verified\n' "$after" "$fixed"

git clone --bare --shared -q "$crypto" "$run/mirrors/swift-crypto.git"
git clone --bare --shared -q "$asn1" "$run/mirrors/swift-asn1.git"
test "$(git -C "$run/mirrors/swift-crypto.git" rev-parse 'c2cbadd7263439d8015189668f96ff5b5be565ce^{tree}')" = \
  841fdfd88fed694e6532a3200a91b0f85595c340
test "$(git -C "$run/mirrors/swift-asn1.git" rev-parse '3b6410f7dee09eb33cdd26260c5fd47fda19b0e2^{tree}')" = \
  e7ed2e8c1483426c349b678e7d10940509f9d39c
export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0="url.file://$run/mirrors/swift-crypto.git.insteadOf"
export GIT_CONFIG_VALUE_0=https://github.com/apple/swift-crypto.git
export GIT_CONFIG_KEY_1="url.file://$run/mirrors/swift-asn1.git.insteadOf"
export GIT_CONFIG_VALUE_1=https://github.com/apple/swift-asn1.git
require_sha "$sdk/Package.resolved" e7dfdfed9b632538cd61bdff7bc705cb2a30cc7be661f31d6076f18b58d3f1ab

build_vm() {
  PATH="$rust_bin:$PATH" "$rust_bin/cargo" build --manifest-path "$sdk/vm/Cargo.toml" \
    --offline --locked --release --features experimental-capability-native --lib --target "$1" \
    --target-dir "$run/cargo" --jobs 8
}
build_vm aarch64-apple-darwin
ln -s "$run/cargo/aarch64-apple-darwin/release/libmixer_vm.a" "$run/hostlib/libmixer_vm_capability_experimental.a"

host="$run/work/host"
sources="$host/Sources/AssignmentHost"
mkdir -p "$sources"
cp "$delivery/HostPackage.swift" "$host/Package.swift"
cp "$sdk/Package.resolved" "$host/Package.resolved"
cp "$app/ios/FieldLog/"{AssignmentNotification,WorkspacePresentationOwner,WorkspaceModel,SelectedDraftGuestBinding,InstalledDraftGuest,FieldLogPreferences}.swift \
  "$app/Integrations/InstalledGuest/FieldLogDraftStorage.swift" "$delivery/AssignmentHost.swift" "$sources/"
swift --version
swift run --package-path "$host" --scratch-path "$run/host-build" --cache-path "$run/host-cache" \
  --config-path "$run/host-config" --security-path "$run/host-security" --skip-update --force-resolved-versions -j 8 \
  -Xcc "-I$sdk/vm/include" -Xlinker "-L$run/hostlib" AssignmentHost "$run/host-data"

if [[ "$mode" == all ]]; then
  build_vm aarch64-apple-ios
  mkdir "$run/lib"
  vm="$run/cargo/aarch64-apple-ios/release/libmixer_vm.a"
  require_sha "$vm" 54e5957571a574e0f6320529394c4f7294d6d659284fea67085538fc1fb345b4
  ln -s "$vm" "$run/lib/libmixer_vm_capability_experimental.a"
  project="$app/ios/FieldLog.xcodeproj"
  cp "$sdk/Package.resolved" "$project/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
  xcodebuild -version
  xcrun --sdk iphoneos --show-sdk-version
  for configuration in Debug Release; do
    if ! xcodebuild -project "$project" -scheme FieldLog -configuration "$configuration" \
      -sdk iphoneos -destination 'generic/platform=iOS' -derivedDataPath "$run/derived" \
      -clonedSourcePackagesDirPath "$run/packages" -packageCachePath "$run/package-cache" \
      -resultBundlePath "$run/$configuration.xcresult" -disableAutomaticPackageResolution \
      -onlyUsePackageVersionsFromResolvedFile -skipPackageUpdates -disablePackageRepositoryCache \
      -scmProvider system -jobs 8 CODE_SIGNING_ALLOWED=NO ARCHS=arm64 ONLY_ACTIVE_ARCH=NO ENABLE_DEBUG_DYLIB=NO \
      "HEADER_SEARCH_PATHS=\$(inherited) $sdk/vm/include" "LIBRARY_SEARCH_PATHS=$run/lib" \
      LD_GENERATE_MAP_FILE=YES COMPILER_INDEX_STORE_ENABLE=NO "CLANG_MODULE_CACHE_PATH=$run/clang-cache" \
      build > "$run/$configuration.log" 2>&1
    then
      tail -60 "$run/$configuration.log"
      exit 1
    fi
    echo "$configuration generic iPhoneOS build succeeded"
    binary="$run/derived/Build/Products/$configuration-iphoneos/FieldLog.app/FieldLog"
    shasum -a 256 "$binary"
    xcrun vtool -show-build "$binary" > "$run/$configuration.vtool"
    grep -E 'platform IOS$' "$run/$configuration.vtool"
    xcrun otool -l "$binary" > "$run/$configuration.load-commands"
    require_absent LC_CODE_SIGNATURE "$run/$configuration.load-commands"
    xcrun nm -nm "$binary" | xcrun swift-demangle > "$run/$configuration.symbols"
    grep -Eq 'FieldLogAppDelegate.userNotificationCenter.*didReceive:' "$run/$configuration.symbols"
    grep -Fq 'AssignmentNotificationRouter.takeDestination' "$run/$configuration.symbols"
    grep -Fq 'WorkspacePresentationOwner' "$run/$configuration.symbols"
    grep -Fq 'SavedTaskEditorOwner.submit' "$run/$configuration.symbols"
    strings "$binary" > "$run/$configuration.strings"
    grep -Fxq 'fieldlog.task-assignment' "$run/$configuration.strings"
    fixture=--fieldlog-local-assignment-fixture
    if [[ "$configuration" == Debug ]]; then
      grep -Fxq -- "$fixture" "$run/$configuration.strings"
      grep -Fxq 'Post test assignment' "$run/$configuration.strings"
    else
      require_absent "$fixture" "$run/$configuration.strings"
      require_absent "Post test assignment" "$run/$configuration.strings"
    fi
    echo "$configuration assignment caller, saved editor, signing, and posting checks passed"
  done
fi
