#!/bin/sh
set -eu
fixture=$(cd "$(dirname "$0")" && pwd -P)
app=$(cd "$1" && pwd -P)
scratch=$(cd "$2" && pwd -P)
cd "$app"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library \
  -module-name FieldLogModels Sources/FieldLogModels/*.swift \
  -o "$scratch/libFieldLogModels.dylib"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library \
  -I "$scratch" -L "$scratch" -lFieldLogModels -module-name FieldLogStorage \
  Sources/FieldLogStorage/*.swift -o "$scratch/libFieldLogStorage.dylib"
swiftc -D DEBUG -swift-version 6 -parse-as-library -I "$scratch" -L "$scratch" \
  -lFieldLogModels -lFieldLogStorage -Xlinker -rpath -Xlinker "$scratch" \
  ios/FieldLog/FieldLogAccountApple.swift "$fixture/AccountChecks.swift" \
  -o "$scratch/account-checks"
mkdir "$scratch/data"
python3 -B "$fixture/run-host.py" "$app" "$scratch/account-checks" "$scratch/data"
