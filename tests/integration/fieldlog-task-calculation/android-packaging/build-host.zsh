#!/bin/zsh
set -eu
work=${1:A}
recipe=${0:A:h}
package="$work/host-package"
source "$recipe/offline-swiftpm.zsh"
export TMPDIR="$work/tmp" CLANG_MODULE_CACHE_PATH="$work/host-clang" SWIFTPM_MODULECACHE_OVERRIDE="$work/host-modules"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
unset SDKROOT TOOLCHAINS SWIFT_EXEC
mkdir -p "$package/Sources/Seal" "$package/Sources/Probe"
cp "$recipe/HostPackage.swift" "$package/Package.swift"
cp "$recipe/Package.resolved" "$package/"
cp "$recipe/Seal.swift" "$package/Sources/Seal/"
cp "$recipe/Probe.swift" "$package/Sources/Probe/"
for module in FieldLogModels FieldLogStorage; do
    ln -sfn "$work/fieldlog/Integrations/GeneratedReport/Sources/$module" "$package/Sources/$module"
done
ln -sfn "$work/fieldlog/Integrations/InstalledGuest" "$package/Sources/FieldLogInstalledGuest"
/usr/bin/swift build --package-path "$package" --scratch-path "$work/host-build" \
    --cache-path "$work/host-cache" --config-path "$work/host-config" --security-path "$work/host-security" \
    --disable-dependency-cache --disable-prefetching --skip-update --force-resolved-versions \
    --jobs 8 --disable-index-store -Xswiftc -DFIELDLOG_CALCULATION_FIXTURE -Xswiftc -gnone \
    -Xcc "-I$work/host-engine/include" -Xlinker "-L$work/host-engine/lib"
