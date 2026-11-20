#!/bin/zsh
set -eu -o pipefail
source "${0:A:h}/environment.zsh"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
tree="$work/fieldlog"
app="$tree/Integrations/GeneratedReport/Sources"
mixer="$work/mixer"
package="$work/host-replay"
bridge="$mixer/verification/android-binding-stage4/host-bridge"
binding="$mixer/native/android/signed-guest-ui/binding/include"
observation="$recipe/../../host/host-observation.c"
test "$(git hash-object "$observation")" = 745e90264bc451792332395a60a09f791f111375
delivery=${2:A}
mkdir "$package" "$package/"{headers,lib,data}
mkdir -p "$package/Sources/"{FieldLogFeatures,FieldLogInstalledGuest,FieldLogPacketReplay}
cp "$recipe/ReplayPackage.swift" "$package/Package.swift"
cp "$recipe/Package.resolved" "$package/Package.resolved"
ln -s "$app/FieldLogModels" "$app/FieldLogStorage" "$package/Sources/"
ln -s "$app/FieldLogFeatures/"{EntryEditor,TaskEditor,TaskEditorPresentation}.swift "$package/Sources/FieldLogFeatures/"
ln -s "$tree/Integrations/InstalledGuest/"{FieldLogDraftStorage,SelectedDraftBinding}.swift "$package/Sources/FieldLogInstalledGuest/"
ln -s "$app/FieldLogAndroid/PublicFactory.swift" "$recipe/ReplayPacket.swift" "$package/Sources/FieldLogPacketReplay/"
printf 'module FieldLogHostTest { header "%s" header "witness.h" export * }\n' "$bridge/host_test.h" > "$package/headers/module.modulemap"
cat > "$package/headers/witness.h" <<'HEADER'
#include "mixer_ui_binding.h"
uint64_t mxfield_recorded_probe(uint64_t);
uint32_t mxfield_host_packet(uint64_t, uint64_t, uint8_t *, uint32_t);
HEADER
flags=(-fPIC -std=c11 -Wall -Wextra -Werror -DMIXER_UI_TRANSPORT_TESTING -D_DARWIN_C_SOURCE "-I$binding" "-I$bridge")
/usr/bin/clang $flags -c "$mixer/native/android/signed-guest-ui/transport/transport.c" -o "$package/lib/transport.o"
/usr/bin/clang $flags -DMIXER_UI_WITNESS_TESTING -Dmxis_apply=mxis_host_apply -c "$bridge/host_bridge.c" -o "$package/lib/bridge.o"
/usr/bin/clang $flags -c "$observation" -o "$package/lib/observation.o"
# Keep build output on stderr so stdout is a machine-readable runtime receipt.
/usr/bin/swift build --package-path "$package" --scratch-path "$work/host-replay-build" \
    --cache-path "$work/host-replay-cache" --config-path "$work/host-replay-config" \
    --security-path "$work/host-replay-security" --disable-dependency-cache --disable-prefetching \
    --force-resolved-versions --disable-index-store --build-system native --jobs 8 --product FieldLogPacketReplay \
    -Xswiftc -DFIELDLOG_SIGNED_CHECKLIST -Xswiftc -gnone -Xcc -g0 \
    -Xcc "-I$binding" -Xcc "-I$bridge" -Xcc "-I$package/headers" -Xcc "-I$work/host-engine/include" \
    -Xlinker "-L$work/host-engine/lib" -Xlinker "$package/lib/transport.o" -Xlinker "$package/lib/bridge.o" \
    -Xlinker "$package/lib/observation.o" >&2
exec "$work/host-replay-build/debug/FieldLogPacketReplay" "$delivery" "$package/data" "$3"
