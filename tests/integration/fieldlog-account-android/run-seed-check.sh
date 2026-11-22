#!/bin/sh
set -eu
fixture=$(cd "$(dirname "$0")" && pwd -P)
app=$(cd "$1" && pwd -P)
scratch=$(cd "$2" && pwd -P)
cd "$app"

models=Integrations/GeneratedReport/Sources/FieldLogModels
repository=Sources/FieldLogStorage/WorkspaceRepository.swift
cmp "$repository" "Integrations/GeneratedReport/$repository"
swiftc -swift-version 6 -parse-as-library -module-cache-path "$scratch/module-cache" -emit-module -emit-library \
  -module-name FieldLogModels "$models/"*.swift -o "$scratch/libFieldLogModels.dylib"
swiftc -swift-version 6 -parse-as-library -module-cache-path "$scratch/module-cache" -emit-module -emit-library \
  -I "$scratch" -L "$scratch" -lFieldLogModels -module-name FieldLogStorage \
  "$repository" -o "$scratch/libFieldLogStorage.dylib"
swiftc -swift-version 6 -parse-as-library -module-cache-path "$scratch/module-cache" -I "$scratch" -L "$scratch" \
  -lFieldLogModels -lFieldLogStorage -Xlinker -rpath -Xlinker "$scratch" \
  "$fixture/AccountWorkspaceSeed.swift" -o "$scratch/account-workspace-seed"
"$scratch/account-workspace-seed" "$scratch/data"
