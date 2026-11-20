#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
swiftc=/usr/bin/swiftc
out="$work/${FIELDLOG_HOST_BUILD:-host-proof}"
mkdir "$out"
export CLANG_MODULE_CACHE_PATH="$out/clang"
sdk="$work/mixer/sdk/Sources"
fieldlog="$work/fieldlog/Integrations/GeneratedReport/Sources"
installed="$work/fieldlog/Integrations/InstalledGuest"
native="$sdk/MixerCapabilities/NativeIO"
printf 'module MixerCapabilityIO { header "%s" export * }\n' "$native/include/MixerCapabilityIO.h" > "$out/module.modulemap"
/usr/bin/clang -I "$native/include" -c "$native/lock.c" -o "$out/lock.o"
compile_module() {
    local name="$1"
    shift
    "$swiftc" -swift-version 6 -parse-as-library -I "$out" -whole-module-optimization         -package-name "$name" -module-name "$name" -emit-module -emit-module-path "$out/$name.swiftmodule"         -emit-object "$@" -o "$out/$name.o"
}
compile_module MixerCore "$sdk/MixerCore/"*.swift
compile_module MixerUI "$sdk/MixerUI/"*.swift
compile_module MixerAndroid "$sdk/MixerAndroid/"*.swift
compile_module MixerCapabilities "$sdk/MixerCapabilities/"*.swift
compile_module FieldLogModels "$fieldlog/FieldLogModels/"*.swift
compile_module FieldLogStorage "$fieldlog/FieldLogStorage/"*.swift
compile_module FieldLogFeatures "$fieldlog/FieldLogFeatures/"{EntryEditor,TaskEditor,TaskEditorPresentation}.swift
compile_module FieldLogInstalledGuest "$installed/"{FieldLogDraftStorage,SelectedDraftBinding}.swift
"$swiftc" -swift-version 6 -DFIELDLOG_SIGNED_CHECKLIST -parse-as-library -I "$out"     "$fieldlog/FieldLogAndroid/PublicFactory.swift" "$recipe/EditorBindingProof.swift" "$out/"*.o -o "$out/proof"
"$out/proof" "$out/data"
