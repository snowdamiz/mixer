#!/bin/bash
# Run on the macOS host after staging the exact inputs listed in README.md.
set -euo pipefail

recipe=$(cd "$(dirname "$0")" && pwd -P)
receipt="$recipe/../../../verification/receipts/managed-android-local-linux-pair25-20261120.json"
stage=$(cd "${1:?usage: replay.sh STAGE}" && pwd -P)
: "${PAIR25_DOCKER_CONTEXT:?set the authorized Docker Desktop context}"
docker_cmd=(docker --context "$PAIR25_DOCKER_CONTEXT")
project="$stage/readonly/Export"

check_hash() {
    local actual
    actual=$(shasum -a 256 < "$1")
    [[ ${actual%% *} == "$2" ]] || { echo "SHA-256 mismatch: $1" >&2; return 1; }
}

check_export() {
    check_hash "$project/mixer.lock" "$(jq -er .source.macMixerLockSHA256BeforeAndAfter "$receipt")"
    check_hash "$project/Platforms/Android/Package.resolved" "$(jq -er .source.platformLockSHA256BeforeAndAfter "$receipt")"
    check_hash "$project/Generated/MixerAndroid/android-build.py" "$(jq -er .source.renderedBuildDriverSHA256 "$receipt")"
    cmp "$project/Platforms/Android/Package.resolved" "$project/Generated/MixerSDK/Package.resolved"
}

check_export
archive_rows=$(jq -er '.toolSources.archives | to_entries[] | [.key, .value.sha256] | @tsv' "$receipt")
while IFS=$'\t' read -r archive digest; do
    check_hash "$stage/archives/$archive" "$digest"
done <<< "$archive_rows"
for package in swift-asn1 swift-crypto; do
    pin=$(jq -er --arg package "$package" '.source.dependencies[] | select(.identity == $package) | .state.revision' "$receipt")
    GIT_NO_LAZY_FETCH=1 git --git-dir="$stage/mirrors/$package.git" cat-file -e "$pin^{commit}"
done

swift=$(jq -er .toolSources.swiftArm64Image "$receipt")
ubuntu=$(jq -er .toolSources.x86CompatibilityLibrariesImage "$receipt")
python=$(jq -er .toolSources.pythonArm64Image "$receipt")
check_image() {
    local ref=$1 arch=$2 config=$3 descriptor
    # The registry supplies the config digest bound by the selected manifest.
    descriptor=$(gtimeout 30 "${docker_cmd[@]}" manifest inspect --verbose "$ref")
    jq -e --arg manifest "${ref##*@}" --arg arch "$arch" --arg config "$config" '
        .Descriptor.digest == $manifest and .Descriptor.platform.os == "linux"
        and .Descriptor.platform.architecture == $arch
        and (.OCIManifest.config.digest // .SchemaV2Manifest.config.digest) == $config
    ' <<< "$descriptor" > /dev/null
    gtimeout 15 "${docker_cmd[@]}" image inspect --platform "linux/$arch" "$ref" |
        jq -e --arg manifest "${ref##*@}" --arg arch "$arch" --arg config "$config" '
            .[0] | .Os == "linux" and .Architecture == $arch
            and .Descriptor.digest == $manifest and (.Id == $manifest or .Id == $config)
        ' > /dev/null
}
swift_config=sha256:3af9ff4bbeb3912a60bee99a537e4bd44e9010a8f933eefe29161e0f472464e9
ubuntu_config=sha256:7da97f743f397971f35dd21cd2d19a7da070a150e0cfa3eda559e71891ec7533
python_config=sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c
check_image "$swift" arm64 "$swift_config"
check_image "$ubuntu" amd64 "$ubuntu_config"
check_image "$python" arm64 "$python_config"

run=$(mktemp -d "$stage/pair25-replay.XXXXXXXX")
name=${run##*/}
volume="$name-inputs"
volume_owned=
pending=
containers=()
cleanup() {
    local status=$? id remaining failed=0
    trap - EXIT
    trap '' HUP INT TERM
    for id in ${containers[@]+"${containers[@]}"}; do
        if ! gtimeout 30 "${docker_cmd[@]}" rm -f "$id" > /dev/null ||
           ! remaining=$(gtimeout 15 "${docker_cmd[@]}" ps -aq --no-trunc --filter "id=$id") ||
           [[ -n $remaining ]]; then
            echo "Could not verify removal of owned container $id" >&2
            failed=1
        fi
    done
    if [[ -n $pending ]]; then
        echo "Docker creation unresolved for $pending. Preserve $run and volume $volume." >&2
        exit 1
    fi
    if [[ -n $volume_owned && $failed == 0 ]]; then
        if ! gtimeout 30 "${docker_cmd[@]}" volume rm "$volume" > /dev/null ||
           ! remaining=$(gtimeout 15 "${docker_cmd[@]}" volume ls -q --filter "name=^${volume}$") ||
           [[ -n $remaining ]]; then
            echo "Could not verify removal of owned volume $volume" >&2
            failed=1
        fi
    fi
    if ((failed)); then
        echo "Retained replay directory: $run" >&2
        exit 1
    fi
    rm -rf "$run"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

isolation=(--network none --ipc private --read-only --cap-drop ALL
    --security-opt no-new-privileges=true --memory 5g --memory-swap 5g --cpus 4
    --pids-limit 128 --log-driver local --log-opt max-size=8m --log-opt max-file=1
    --log-opt compress=false --tmpfs '/tmp:rw,nosuid,nodev,exec,size=512m')
create() {
    local phase=$1 arch=$2 ref=$3 config=$4
    shift 4
    pending="$name-$phase"
    cid=$(gtimeout 30 "${docker_cmd[@]}" create --name "$pending" --pull never \
        --platform "linux/$arch" "${isolation[@]}" "$@")
    [[ $cid =~ ^[a-f0-9]{64}$ ]]
    containers+=("$cid")
    pending=
    # Compare the resolved manifest of this exact unstarted container.
    gtimeout 15 "${docker_cmd[@]}" container inspect "$cid" |
        jq -e --arg ref "$ref" --arg manifest "${ref##*@}" --arg config "$config" '
            .[0] | .State.Status == "created" and .Platform == "linux" and .Config.Image == $ref
            and .ImageManifestDescriptor.digest == $manifest and (.Image == $manifest or .Image == $config)
        ' > /dev/null
}

run_worker() {
    local seconds=$1 status
    gtimeout 15 "${docker_cmd[@]}" start "$cid" > /dev/null
    if ! status=$(gtimeout --kill-after=5 "$seconds" "${docker_cmd[@]}" wait "$cid"); then
        echo "Docker wait failed or hit its ${seconds}s limit for $cid" >&2
        return 1
    fi
    gtimeout 15 "${docker_cmd[@]}" container inspect "$cid" |
        jq -e --argjson status "$status" '
            .[0].State | select(.Status == "exited" and .Pid == 0 and .ExitCode == $status
                and (.OOMKilled or .Dead) == false)
        '
    gtimeout 15 "${docker_cmd[@]}" logs "$cid"
    [[ $status == 0 ]]
}

mkdir "$run"/{glibc,lib64,python,lock,deliver}
# These bind mounts are private to the host user but writable by guest UID 65534.
chmod 0777 "$run/lock" "$run/deliver"
create glibc amd64 "$ubuntu" "$ubuntu_config" --entrypoint /bin/sh "$ubuntu" -c :
gtimeout 45 "${docker_cmd[@]}" cp "$cid:/usr/lib/x86_64-linux-gnu/." "$run/glibc"
ln -s /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 "$run/lib64/ld-linux-x86-64.so.2"
create python arm64 "$python" "$python_config" --entrypoint /bin/sh "$python" -c :
gtimeout 45 "${docker_cmd[@]}" cp "$cid:/usr/local/." "$run/python"

pending="$volume"
[[ $(gtimeout 15 "${docker_cmd[@]}" volume create --label "mixer.pair25.run=$run" "$volume") == "$volume" ]]
[[ $(gtimeout 15 "${docker_cmd[@]}" volume inspect --format '{{index .Labels "mixer.pair25.run"}}' "$volume") == "$run" ]]
volume_owned=1
pending=
compat=(--mount "type=bind,src=$run/glibc,dst=/lib/x86_64-linux-gnu,readonly"
    --mount "type=bind,src=$run/lib64,dst=/lib64,readonly"
    --mount "type=bind,src=$recipe,dst=/recipe,readonly")
create setup arm64 "$swift" "$swift_config" "${compat[@]}" --user 0:0 \
    --mount "type=bind,src=$stage/archives,dst=/archives,readonly" \
    --mount "type=volume,src=$volume,dst=/toolchain,volume-nocopy" \
    --entrypoint /bin/sh "$swift" /recipe/prepare-toolchain.sh
run_worker 160

worker=("${compat[@]}" --user 65534:65534
    --tmpfs '/work:rw,nodev,nosuid,exec,size=3g,mode=0700,uid=65534,gid=65534'
    --mount "type=bind,src=$project,dst=/project,readonly"
    --mount "type=bind,src=$stage/android-sdk,dst=/android-sdk,readonly"
    --mount "type=bind,src=$stage/mirrors,dst=/mirrors,readonly"
    --mount "type=bind,src=$run/python,dst=/python,readonly"
    --mount "type=volume,src=$volume,dst=/toolchain,readonly,volume-nocopy"
    --env "PAIR25_VERIFIED_SWIFT_MANIFEST=${swift##*@}"
    --env HOME=/work/home --env PYTHONHOME=/python --env PYTHONDONTWRITEBYTECODE=1
    --env GIT_CONFIG_GLOBAL=/dev/null --env GIT_CONFIG_NOSYSTEM=1 --env GIT_ALLOW_PROTOCOL=file
    --env GIT_CONFIG_COUNT=2
    --env GIT_CONFIG_KEY_0=url.file:///mirrors/swift-asn1.git.insteadOf
    --env GIT_CONFIG_VALUE_0=https://github.com/apple/swift-asn1.git
    --env GIT_CONFIG_KEY_1=url.file:///mirrors/swift-crypto.git.insteadOf
    --env GIT_CONFIG_VALUE_1=https://github.com/apple/swift-crypto.git
    --env 'JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=4 -Xmx1024m')
entrypoint=(--entrypoint /bin/sh "$swift" -euc
    "umask 022; mkdir /work/home; ulimit -f 524288; umask 077; exec /python/bin/python3.12 /recipe/worker.py \"\$1\""
    pair25-worker)
create lock arm64 "$swift" "$swift_config" "${worker[@]}" \
    --mount "type=bind,src=$run/lock,dst=/deliver" "${entrypoint[@]}" lock
run_worker 150

linux_lock="$run/lock/linux-mixer.lock"
check_hash "$linux_lock" "$(jq -er .source.localLinuxLockSHA256 "$receipt")"
jq -e -s '.[0].android.toolchain == .[1].toolchain' "$linux_lock" "$receipt" > /dev/null
jq -e -s '(.[0] | del(.android.toolchain)) == (.[1] | del(.android.toolchain))' \
    "$project/mixer.lock" "$linux_lock" > /dev/null
check_export
create build arm64 "$swift" "$swift_config" "${worker[@]}" \
    --mount "type=bind,src=$linux_lock,dst=/project/mixer.lock,readonly" \
    --mount "type=bind,src=$run/deliver,dst=/deliver" "${entrypoint[@]}" build
run_worker 600
check_export

# Keep just the proof outputs in a new host-owned directory.
output=$(mktemp -d "$stage/pair25-result.XXXXXXXX")
mv "$run/deliver/"{UpgradeStarter-unsigned.apk,debug-symbols.zip,resource-inventory.json,readback.json} \
    "$linux_lock" "$output/"
echo "Pair25 proof outputs: $output"
