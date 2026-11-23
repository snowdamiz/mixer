#!/bin/bash
set -euxo pipefail
run=$1
w=$run/work
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export TMPDIR="$w/tmp" CLANG_MODULE_CACHE_PATH="$run/clang-cache" XDG_CACHE_HOME="$run/xdg-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH" SWIFTCI_USE_LOCAL_DEPS=1
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 GIT_ALLOW_PROTOCOL=file GIT_NO_LAZY_FETCH=1
binding="$w/mixer/native/android/signed-guest-ui/binding/include"
host="$w/mixer/verification/android-binding-stage4/host-bridge"
exec /usr/bin/swift build --package-path "$w/host" --scratch-path "$run/swift-build" \
    --cache-path "$run/swift-cache" --config-path "$run/swift-config" --security-path "$run/swift-security" \
    --manifest-cache local --disable-dependency-cache --disable-index-store --jobs 8 \
    --product fieldlog-d2-host -Xswiftc -gnone -Xcc -g0 -Xcc "-I$w/mixer/vm/include" \
    -Xcc "-I$binding" -Xcc "-I$host" -Xlinker "-L$run/lib" \
    -Xlinker "$run/lib/transport.o" -Xlinker "$run/lib/bridge.o" -Xlinker "$run/lib/observation.o"
