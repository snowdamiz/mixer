#!/bin/sh
set -eu
umask 077
ulimit -c 0
fixture=$(cd "$(dirname "$0")" && pwd -P)
app=$(cd "$1" && pwd -P)
scratch=$(cd "$2" && pwd -P)
cd "$app"
test "$(git hash-object Backend/local_entry_sync.py)" = 4d487e779c213b387cd2eee89fe0f48033a0b029
mkdir "$scratch/modules" "$scratch/data"
export TMPDIR="$scratch"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library \
  -module-name FieldLogModels Sources/FieldLogModels/*.swift \
  -o "$scratch/modules/libFieldLogModels.dylib"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library \
  -I "$scratch/modules" -L "$scratch/modules" -lFieldLogModels -module-name FieldLogStorage \
  Sources/FieldLogStorage/*.swift -o "$scratch/modules/libFieldLogStorage.dylib"
swiftc -D DEBUG -swift-version 6 -parse-as-library -I "$scratch/modules" -L "$scratch/modules" \
  -lFieldLogModels -lFieldLogStorage -Xlinker -rpath -Xlinker "$scratch/modules" \
  ios/FieldLog/FieldLogAccountApple.swift "$fixture/RecoveryChecks.swift" -o "$scratch/recovery-checks"
python3 -B "$fixture/run-host.py" "$app" "$scratch/recovery-checks" "$scratch/data"
