#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
swiftc=/usr/bin/swiftc
out="$work/${FIELDLOG_SEAL_BUILD:-sealer}"
mkdir "$out"
export CLANG_MODULE_CACHE_PATH="$out/clang"
updates="$work/mixer/updates/Sources/MixerUpdates"
durable="$work/mixer/updates/Sources/MixerDurableIO"
printf 'module MixerDurableIO { header "%s" export * }\n' "$durable/include/MixerDurableIO.h" > "$out/module.modulemap"
/usr/bin/clang -I "$durable/include" -c "$durable/lock.c" -o "$out/durable.o"
identity="$work/mixer/runtime-identity/Sources/MixerRuntimeIdentity"
# Apple's CryptoKit is Swift Crypto's backing implementation on this host.
printf '%s\n' '@_exported import CryptoKit' > "$out/Crypto.swift"
"$swiftc" -swift-version 6 -parse-as-library -emit-module -module-name Crypto "$out/Crypto.swift"     -emit-module-path "$out/Crypto.swiftmodule"
"$swiftc" -swift-version 6 -parse-as-library -I "$out" -whole-module-optimization -package-name MixerUpdates -module-name MixerUpdates     -emit-module -emit-module-path "$out/MixerUpdates.swiftmodule" -emit-object     "$updates"/*.swift -o "$out/MixerUpdates.o"
"$swiftc" -swift-version 6 -parse-as-library -I "$out" -whole-module-optimization -module-name MixerRuntimeIdentity     -emit-module -emit-module-path "$out/MixerRuntimeIdentity.swiftmodule" -emit-object     "$identity/CapabilityRuntimeIdentity.swift" -o "$out/MixerRuntimeIdentity.o"
"$swiftc" -swift-version 6 -parse-as-library -I "$out" "$recipe/SealDraftScenario.swift"     "$out/MixerUpdates.o" "$out/MixerRuntimeIdentity.o" "$out/durable.o" -o "$out/SealDraftScenario"
