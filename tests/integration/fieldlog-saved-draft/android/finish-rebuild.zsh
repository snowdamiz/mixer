#!/bin/zsh
set -eu -o pipefail
umask 077
if (( $# != 1 )); then
    print -u2 'Usage: zsh -f finish-rebuild.zsh FRESH_PREPARED_OUTPUT_DIR'
    exit 2
fi

source_dir=${0:A:h}
out=${1:A}
work="$out/work"
packet="$out/packet"
mixer_revision=5dea19db36610e312b51918b384364ba590b6ef8

(cd "$source_dir" && shasum -a 256 -c SHA256SUMS)
test "$(git -C "$work/fieldlog" rev-parse HEAD)" = 552559d2d3278abb9b1aa7dcf0288102c09a202b
test "$(git -C "$work/fieldlog" write-tree)" = 29f6fdb31dbb5008964b16b07ed2d82510e8821b
test "$(git -C "$work/mixer-checkout" rev-parse HEAD)" = "$mixer_revision"
cmp "$source_dir/pair24-mixer.lock" "$work/prepared/mixer.lock"
test ! -e "$work/payload"
test ! -e "$work/android-build"
test ! -e "$work/logs/native.log"
test ! -e "$packet/FieldLog-selected-draft-dev-arm64.apk"
test -s "$work/guests/baseline.wasm"
test -s "$work/guests/optional.wasm"
test -s "$work/java/dex/classes.dex"
export TMPDIR="$work/tmp/"

recipe="$source_dir/recipe"
export FIELDLOG_SEAL_BUILD=sealer2
run() {
    local label=$1
    shift
    print -r -- "$label"
    "$@" > "$work/logs/$label.log" 2>&1 || {
        tail -60 "$work/logs/$label.log"
        return 1
    }
}

run press-trace-host /bin/zsh -f "$source_dir/check-trace-host.zsh" "$work"
run native /bin/zsh -f "$recipe/build-app.zsh" "$work" native

export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export SDKROOT="$DEVELOPER_DIR/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.5.sdk"
run host-engine python3 -B "$work/mixer/experimental-capability-runtime/build-vm.py"     --revision "$mixer_revision" --target host --rustc "$(rustup which rustc)" --output "$work/host-engine"
run guest-preflight-compile /usr/bin/clang -std=c11 -Wall -Wextra -Werror     -I "$work/host-engine/include" "$source_dir/guest-preflight.c"     "$work/host-engine/lib/libmixer_vm_capability_experimental.a" -o "$work/guest-preflight"
(
    cd "$work"
    run guest-preflight ./guest-preflight guests/baseline.wasm guests/optional.wasm
)

run seal /bin/zsh -f "$recipe/package.zsh" "$work" "$source_dir/reference" "$packet" --seal-only
run package-stage /bin/zsh -f "$recipe/package.zsh" "$work" "$source_dir/reference" "$packet"
run verifier-compile env -u SDKROOT DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer     /usr/bin/swiftc -swift-version 6 -parse-as-library -I "$work/sealer2" "$source_dir/VerifyDelivery.swift"     "$work/sealer2/"{MixerUpdates.o,MixerRuntimeIdentity.o,durable.o} -o "$work/verify-delivery"
uuidgen | tr '[:upper:]' '[:lower:]' > "$packet/host-replay-installation.txt"
installation=$(<"$packet/host-replay-installation.txt")
verify_delivery() {
    "$work/verify-delivery" "$packet/delivery-android" "$@" "$source_dir/reference/prior-renderer-roots.json" "$installation"
}
{
    verify_delivery "$source_dir/reference/Installed/identity.json"         753cd11261b296a7bfad2eb728aaebc556436a91fd8648bb25f74554a0b06ca4
    verify_delivery "$source_dir/reference/rebuild-identity.json"         c863982cd775e22c75e229fd447cbcb88bae1856fcf2e73e7bc17bb92e513bc2
    verify_delivery "$source_dir/reference/root-failed-run-identity.json" \
        3d7eb3852af2711bd66aaea45c93f2f7ab3fc9dc22ca4c6ce3049fd8469c71f2
    verify_delivery "$source_dir/reference/prior-diagnostic-identity.json" d3b27668cb0dcf166b0c2fe9b9eac07743324a1214e76c90ce938f3fa315685b
    verify_delivery "$source_dir/reference/prior-storage-identity.json" e7acccf6968248089294f5ed4f3b9603b5b7bfe0ba483f0183b3bf969581820a
    verify_delivery "$source_dir/reference/prior-renderer-identity.json" \
        aabfe7e0f2d22f59efbecfe8cb971b1881967db045018074f8d8f4f343b37a80
} > "$work/logs/verify-delivery.log" 2>&1

/bin/zsh -f "$recipe/replay-packet.zsh" "$work" "$packet/delivery-android" "$installation" \
    > "$packet/host-replay.jsonl" 2> "$work/logs/host-replay.log" || {
    tail -70 "$work/logs/host-replay.log" >&2
    exit 1
}

export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0/apksigner verify --print-certs-pem     -Werr "$packet/FieldLog-selected-draft-dev-arm64.apk" > "$work/logs/certificate.log"     2> "$work/logs/certificate.stderr"
sed -n '/^-----BEGIN CERTIFICATE-----$/,/^-----END CERTIFICATE-----$/p' "$work/logs/certificate.log"     | /usr/bin/openssl x509 -noout -dates -sha256 -fingerprint > "$work/logs/certificate-interval.log"
cp "$recipe/origin.py" "$packet/origin.py"
python3 -B "$source_dir/finalize-packet.py" "$work" "$packet"
(cd "$packet" && shasum -a 256 -c SHA256SUMS)
