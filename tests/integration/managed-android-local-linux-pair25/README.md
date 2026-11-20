# Package a Pair25 Starter in a private Linux worker

The recorded run built and read back an unsigned public V4 APK offline on
Apple Silicon with Docker Desktop. The macOS CLI rendered the export. The
[Linux build receipt](../../../verification/receipts/managed-android-local-linux-pair25-20261120.json)
records the successful run, including the hashes of the recipe files used at
the time. See the [public Pair25 upgrade and standalone export guide](../../../docs/guides/upgrade-recover-and-exit.md#exercise-the-pair24-to-pair25-upgrade-with-a-public-v4-starter)
for the macOS workflow.

## Render the macOS export

Use a fresh private directory for `stage` and set `mixer_repo` to the checkout
that contains the pinned revision. Use the Android toolchain variables from the
[repository README](../../../README.md#build-for-android).
The retained export can also be staged directly at `readonly/Export`.

```sh
rev=a7588b902202f11afb0989fbbe5e4435856187ed
cd "$stage"
mkdir source readonly
git -C "$mixer_repo" archive --format=tar "$rev" cli sdk updates runtime-identity native/android > source.tar
tar -xf source.tar -C source
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
    swift build --package-path source/cli --only-use-versions-from-resolved-file --jobs 4 --product mixer
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
mixer="$stage/source/cli/.build/debug/mixer"
"$mixer" create UpgradeStarter --platform android --android-host public-v4 \
    --directory Starter --sdk-path source/sdk --android-adapter-path source/native/android
"$mixer" export readonly/Export --directory Starter
```

Use the Xcode 27.2 path for the CLI build and Xcode 26.6 for create and export.
Keep `readonly/Export` intact. The launcher checks the rendered driver, Mac
lock, and Android package lock against the receipt before accessing Docker.

## Stage the locked inputs

Set `recipe` to this directory and `receipt` to the Linux build receipt above.
Place the five archives listed in `toolSources.archives` under `$stage/archives`
with the receipt's file names. Verify each SHA-256 before extracting anything.
Extract the Google build-tools and platform ZIPs into separate directories.
Both archives contain an `android-37.0` directory. Move the directories that
directly contain `aapt2` and `android.jar` to
`$stage/android-sdk/build-tools/37.0.0` and
`$stage/android-sdk/platforms/android-37.0`, respectively. The setup container
extracts the Swift SDK, NDK, and JDK into a case-sensitive volume.

Create a bare mirror for each locked package and check the tag against the
revision in the receipt. Make the staged export, SDK, and mirrors readable by
the worker's UID 65534. Keep the host staging directory private.

```sh
mkdir "$stage/mirrors"
for package in swift-asn1 swift-crypto; do
    mirror="$stage/mirrors/$package.git"
    pin=$(jq -er --arg p "$package" '.source.dependencies[] | select(.identity == $p)' "$receipt")
    url=$(jq -er .location <<< "$pin")
    version=$(jq -er .state.version <<< "$pin")
    revision=$(jq -er .state.revision <<< "$pin")
    git init --bare "$mirror"
    git --git-dir="$mirror" fetch --no-tags "$url" "refs/tags/$version:refs/tags/$version"
    test "$(git --git-dir="$mirror" rev-parse "refs/tags/$version^{commit}")" = "$revision" || exit 1
done
```

Use an authorized Docker Desktop context with the three exact image references
already present. To stage images on a daemon reserved for this proof, use these
platform-specific pulls.

```sh
docker --context "$PAIR25_DOCKER_CONTEXT" pull --platform linux/arm64 "$(jq -er .toolSources.swiftArm64Image "$receipt")"
docker --context "$PAIR25_DOCKER_CONTEXT" pull --platform linux/amd64 "$(jq -er .toolSources.x86CompatibilityLibrariesImage "$receipt")"
docker --context "$PAIR25_DOCKER_CONTEXT" pull --platform linux/arm64 "$(jq -er .toolSources.pythonArm64Image "$receipt")"
```

## Run the worker

With Bash, `jq`, and GNU `gtimeout` on the host, run the launcher against the
authorized context. The recorded context was `desktop-linux`.

```sh
PAIR25_DOCKER_CONTEXT=desktop-linux "$recipe/replay.sh" "$stage"
```

The launcher checks the registry manifest, platform, and config digest for
each image, then checks the Docker-resolved manifest of each unstarted
container. It copies Ubuntu's x86-64 libraries and arm64 Python from unstarted
containers. The setup and worker containers mount the x86-64 libraries and
loader read-only. The lock and build containers run offline as UID and GID
65534 with separate writable output directories and read-only input mounts.
The launcher routes the exact two Git URLs to the staged mirrors and restricts
Git transport to `file`.

The lock phase writes `linux-mixer.lock`. The launcher checks the expected
Linux toolchain and verifies that only `android.toolchain` differs from the
Mac lock. The build mounts that file at `/project/mixer.lock` over the
read-only export. The launcher rechecks the original Mac input hashes and
prints the result directory containing the unsigned APK, debug-symbol ZIP,
resource inventory, readback, and Linux lock. The readback lists the three
deliverable kinds with their SHA-256 digests and sizes.

The launcher bounds setup, lock, and build waits to 160, 150, and 600 seconds.
It checks Docker's terminal state and removes its exact container IDs and
owned volume, including after a worker timeout. If Docker creation or cleanup
is unresolved, preserve the reported resources by exact identity. The
launcher uses `--pull never` and leaves pre-staged image references alone.
