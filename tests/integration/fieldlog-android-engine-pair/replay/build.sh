#!/bin/bash
set -euo pipefail

recipe=$1
campaign=$2
phase=$3
scratch=$campaign/scratch
handoff=$campaign/handoff
app=$scratch/app
tools=$handoff/tools
export TMPDIR="$scratch/tmp"
export XDG_CACHE_HOME="$scratch/xdg-cache"
export CLANG_MODULE_CACHE_PATH="$scratch/clang-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$CLANG_MODULE_CACHE_PATH"
export CARGO_HOME="$scratch/cargo"
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export SDKROOT=$DEVELOPER_DIR/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
swift=${SWIFT_EXEC%/*}
go=${MIXER_RECIPE_GO:?}
rust="$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
ndk="$ANDROID_HOME/ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin"
export PATH="$rust:$PATH"
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$ndk/aarch64-linux-android28-clang"
test "$(rustc --version)" = 'rustc 1.99.0 (b940084d7 2026-09-28)'
test "$("$JAVA_HOME/bin/javac" -version)" = 'javac 25.0.4.1'
echo "1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3  $app/prepared/Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json" | shasum -a 256 -c

case "$phase" in
    native)
        echo 'Building the pinned Rust VM archives and linking each Android JNI library'
        for label in old new; do
            pair=$scratch/pair-$label
            for target in android host; do
                args=()
                if [[ "$target" = android ]]; then
                    args=(--target aarch64-linux-android)
                fi
                cargo build --manifest-path "$pair/vm/Cargo.toml" --offline --locked --release --jobs 4 \
                    --features experimental-capability-native --lib --target-dir "$pair/target" "${args[@]+"${args[@]}"}"
            done
            /usr/bin/clang -std=c11 -Werror -Wall -Wextra -I"$pair/vm/include" \
                "$recipe/replay/guest-readback.c" "$pair/target/release/libmixer_vm.a" \
                -framework Security -o "$scratch/$label-guest-probe"
            /bin/zsh -f "$recipe/replay/android-jni.sh" "$app" "$label" \
                "$pair/target/aarch64-linux-android/release/libmixer_vm.a" > "$scratch/$label-jni.log" 2>&1 ||
                { tail -35 "$scratch/$label-jni.log"; exit 1; }
        done
        /bin/zsh -f "$recipe/replay/manifests.sh" "$app"
    ;;
    guests)
        echo 'Building and running both source-derived guests against both host VM archives'
        mkdir "$scratch/guest-modules"
        (
            cd "$scratch/guest-source"
            "$swift/clang" --target=wasm32-unknown-none -Oz -c CapabilityImports.c -o "$scratch/capability.o"
            for label in old new; do
                args=()
                if [[ "$label" = new ]]; then
                    args=(-D REQUIRE_REVIEW)
                fi
                # Keep Swift's incremental module hash zero for reproducible guest bytes.
                "$SWIFT_EXEC" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
                    -enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
                    -Xfrontend -disable-stack-protector -Xfrontend -disable-incremental-llvm-codegen \
                    -module-cache-path "$scratch/guest-modules" \
                    -emit-object "${args[@]+"${args[@]}"}" Guest.swift TaskWire.swift -o "$scratch/$label.o"
                "$swift/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
                    --export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
                    --export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
                    "$scratch/$label.o" "$scratch/capability.o" -o "$scratch/$label.wasm"
            done
        )
        printf '%s\n' \
            "5cf12aa09b638767e145f699eb396d3587b868839b60c58555d9df0dcabb0112  $scratch/old.wasm" \
            "5cad7f40d9544a6109c17c827e97e09c69a5b512944256eb3aa36a7a0f65ea31  $scratch/new.wasm" | shasum -a 256 -c
        mkdir "$handoff/host-controls"
        for engine in old new; do
            for guest in old new; do
                "$scratch/$engine-guest-probe" "$scratch/$guest.wasm" "$guest" \
                    > "$handoff/host-controls/$engine-$guest.log"
            done
        done
    ;;
    tools)
        echo 'Building maintained Mixer release service and verification commands'
        (
            cd "$scratch/host/services"
            export HOME="${MIXER_RECIPE_GO_HOME:?}"
            "$go" build -p 4 -mod=readonly -modcacherw -o "$tools/mixer-service" ./cmd/mixer-service
            "$go" build -p 4 -mod=readonly -modcacherw -o "$scratch/sign-cohort" "$recipe/replay/sign.go"
        )
        (
            cd "$app"
            source "$app/offline-env.sh"
            for product in mixer-identity mixer-update; do
                case "$product" in
                    mixer-identity) package_path=$app/mixer/runtime-identity ;;
                    mixer-update) package_path=$app/mixer/updates ;;
                esac
                build_dir=$scratch/host-$product
                "$swift/swift" build --package-path "$package_path" --scratch-path "$build_dir" \
                    --cache-path "$scratch/host-cache" --config-path "$scratch/host-config" \
                    --security-path "$scratch/host-security" --disable-dependency-cache --disable-prefetching \
                    --skip-update --force-resolved-versions --disable-index-store --jobs 6 -Xswiftc -gnone -Xcc -g0 \
                    --product "$product" > "$build_dir.log" 2>&1 || { tail -35 "$build_dir.log"; exit 1; }
                cp "$build_dir/debug/$product" "$tools/"
            done
        )
        cp "$recipe/replay/verify-release.py" "$tools/verify-release"
        chmod +x "$tools/verify-release"
    ;;
    package)
        python3 -B "$recipe/replay/package-pair.py" "$campaign" "$recipe"
    ;;
    *) echo "Unknown build phase: $phase" >&2; exit 2 ;;
esac
