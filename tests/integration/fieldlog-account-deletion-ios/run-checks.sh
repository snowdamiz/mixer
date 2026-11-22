#!/bin/sh
set -eu
umask 077
ulimit -c 0
fixture=$(cd "$(dirname "$0")" && pwd -P)
app=$(cd "$1" && pwd -P)
scratch=$(cd "$2" && pwd -P)
shift 2
test "$(git hash-object "$app/Backend/local_entry_sync.py")" = 535c33c727f8c0c630c444e180a754ec5625edea
mkdir "$scratch/modules" "$scratch/data" "$scratch/compiler"
export TMPDIR="$scratch"
export CLANG_MODULE_CACHE_PATH="$scratch/compiler"
cd "$app"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library   -module-name FieldLogModels Sources/FieldLogModels/*.swift   -o "$scratch/modules/libFieldLogModels.dylib"
swiftc -swift-version 6 -parse-as-library -emit-module -emit-library -enable-testing   -I "$scratch/modules" -L "$scratch/modules" -lFieldLogModels -module-name FieldLogStorage   Sources/FieldLogStorage/*.swift -o "$scratch/modules/libFieldLogStorage.dylib"
swiftc -D DEBUG -swift-version 6 -parse-as-library -I "$scratch/modules" -L "$scratch/modules"   -lFieldLogModels -lFieldLogStorage -Xlinker -rpath -Xlinker "$scratch/modules"   ios/FieldLog/FieldLogAccountApple.swift "$fixture/DeletionChecks.swift" -o "$scratch/deletion-checks"
python3 -B "$fixture/run-host.py" "$app/Backend/local_entry_sync.py" "$scratch/deletion-checks" "$scratch/data" "$@"
