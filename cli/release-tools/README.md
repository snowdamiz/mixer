# Produce and inspect a local FieldLog update

Use this recipe to qualify the FieldLog confirmation edit and test the effect of
adding an Android camera permission. It compiles the guest for both targets,
reads the native contracts from packaged apps, and drives the signed offers on
macOS hosts. The result is a local technical assessment. It leaves publication
disallowed and policy review pending.

## Prepare the tools and inputs

Start from a Mixer checkout at `c5eb07615d58fd09bb4c9da61fd23865e6bb76a5`
with this recipe applied. Use macOS with Xcode, Python 3.12 or newer, and the
host Swift version from the FieldLog template's `mixer.lock`. Use the Swift 6.3.3
toolchain with Embedded Wasm support for the guest, Android build tools with
`aapt2`, `zipalign`, and `apksigner`, an Android 37 platform JAR, JDK 25, and
OpenSSL 3 with Ed25519 support. The recorded run used Android build-tools
36.0.0 for APK repackaging and 37.0.0 for the template's Android driver.

The FieldLog app and host-observation lanes supply these inputs separately.
Obtain the owners' approved SHA-256 inventories before staging. Compare the
app, source, guest and probe files to those inventories before running
`pin`. Use the host executables that the inventories approve, with any
resources their builders supply. Pinning records that selection for subsequent
drift checks.

| Input | What to obtain |
| --- | --- |
| FieldLog source | The Git tar archive of revision `552559d2d3278abb9b1aa7dcf0288102c09a202b` and the downstream `fieldlog-l04.patch`. If you have the FieldLog checkout, recreate the tar with `git -C "$FIELDLOG_SOURCE" archive --format=tar 552559d2d3278abb9b1aa7dcf0288102c09a202b`. |
| Guest inputs | `hydrated/Guest.swift`, `hydrated/TaskWire.swift`, and `hydrated/CapabilityImports.c` from that downstream build. The producer applies the confirmation edit to this guest and compiles it. |
| Native inputs | The signed development `FieldLog.app` directory for `dev.mixer.fieldlog`, `FieldLog-public-development.apk` for `dev.fieldlog.generatedr90`, and the corresponding `apk-manifest.xml` and `network.zip` resource overlay used to relink the Android manifest. Keep the complete app directory, including `ChecklistRelease` and the code signature. |
| Release input | `manifest-template.json` from that downstream build. Its v3 manifest provides the guest protocol and capability fields. The producer binds the actual payload, runtime, scope, and source, then signs a fresh offer. |
| Project template | The app lane's generated FieldLog project with `mixer.yml`, `mixer.lock`, and `Generated/`. Use a template generated or upgraded by the selected Mixer CLI so the locked Android driver matches that CLI. |
| Host probes | The macOS `fieldlog-ios-host` and `fieldlog-host-exact` executables from the host-observation lanes. Each takes `observe PACKET VARIANT OUTPUT`. The Android probe also takes `refuse INSTALLED_PACKET PROPOSED_OFFER RETAINED_STATE`. Include the Android probe's three FieldLog source files listed in the staging command. The producer checks those files against the patched project. |

The downstream patch, guest hydration, release template, native app builds,
and both probe builds are external FieldLog dependencies. Obtain them from
their owners. The Mixer checkout contains the inspector and the optional local
release service. The macOS probes need to execute the signed guest through the
Apple presentation host and Android host bridge, respectively. An existing
behavior report cannot stand in for either probe.

## Stage the project and pin the inputs

Set `HOST_SWIFT` to the selected host toolchain's actual `swift` binary. For
the selected Xcode, use `xcrun --find swift`. The build, upgrade, producer,
and inspector use that toolchain to check the project's Swift lock.

Set `FIELDLOG_HANDOFF` to the supplied app files, including the Git tar archive
and the Android probe's source files. Set `FIELDLOG_TEMPLATE`, `IOS_PROBE`, and
`ANDROID_PROBE` to the template and the two executable paths. Run these
commands from the Mixer checkout. Use an absolute, private scratch directory
for `work`.

```sh
set -eu
umask 077
repo="$PWD"
work="$(mktemp -d "${TMPDIR:-/tmp}/mixer-fieldlog-inspect.XXXXXXXX")"
work="$(cd "$work" && pwd -P)"
mkdir "$work/input" "$work/operator" "$work/tmp"
export TMPDIR="$work/tmp"
export PATH="$(dirname "$HOST_SWIFT"):$PATH"

"$HOST_SWIFT" build --package-path "$repo/cli" --scratch-path "$work/mixer-build" \
  --force-resolved-versions --product mixer
mixer="$("$HOST_SWIFT" build --package-path "$repo/cli" \
  --scratch-path "$work/mixer-build" --show-bin-path)/mixer"
```

Keep `MixerCLI_MixerBuild.bundle` beside `mixer` if you copy the executable.
Pin the operator-selected executables and any resource bundles provided by the
probe builders against their separate inventory. To build offline, stage the
approved cached repositories for `cli/Package.resolved` under
`$work/mixer-build/repositories` before the first build command and add
`--disable-dependency-cache --skip-update` to that command.

For a template produced by an earlier CLI, upgrade a copy. At the pinned
Mixer revision the current Android driver differs from the driver in the
original FieldLog template. The upgrade uses the local Android SDK, NDK r27d,
Swift Android SDK, build tools 37.0.0, and JDK 25. The CLI checks these inputs
and regenerates the project snapshot and lock. Set `ANDROID_HOME` and
`JAVA_HOME` to the approved installations and `WASM_TOOLS` to the
Embedded-capable Swift toolchain's `usr/bin` directory. If the Swift Android
SDK is outside `$HOME/.swiftpm/swift-sdks`, set `MIXER_SWIFT_SDKS_PATH` to its
parent directory.

```sh
export ANDROID_HOME
export MIXER_JDK="$JAVA_HOME" MIXER_SWIFT="$WASM_TOOLS/swift"
"$mixer" upgrade "$work/template" --directory "$FIELDLOG_TEMPLATE" \
  --sdk-path "$repo/sdk" --android-adapter-path "$repo/native/android"
FIELDLOG_TEMPLATE="$work/template"
```

Copy the approved files into the producer's input layout.

```sh
input="$work/input"
for name in fieldlog.tar fieldlog-l04.patch FieldLog.app \
  FieldLog-public-development.apk apk-manifest.xml network.zip \
  manifest-template.json hydrated; do
  cp -R "$FIELDLOG_HANDOFF/$name" "$input/"
done
for name in FieldLogModels/Workspace.swift \
  FieldLogStorage/WorkspaceRepository.swift \
  FieldLogTaskStorageIntegration/FieldLogTaskStorage.swift; do
  mkdir -p "$input/probe-package/$(dirname "$name")"
  cp "$FIELDLOG_HANDOFF/probe-package/$name" "$input/probe-package/$name"
done
mkdir "$input/project-template"
for name in mixer.yml mixer.lock Generated; do
  cp -R "$FIELDLOG_TEMPLATE/$name" "$input/project-template/"
done
```

Set `WASM_TOOLS` to the Embedded-capable Swift toolchain's `usr/bin`
directory, `ANDROID_BUILD_TOOLS` to your selected Android build-tools directory,
`ANDROID_JAR` to the platform JAR, `JAVA_HOME` to JDK 25, and `OPENSSL` to the
OpenSSL 3 binary. Resolve tools from an approved installation. The producer
pins the listed binaries, the Java launcher, the `apksigner` JAR, and the CLI
resource bundle. Keep the rest of the selected toolchain installations stable.

```sh
driver="$repo/cli/release-tools/fieldlog_provenance.py"
python3 -B "$driver" pin --inputs "$input" --settings "$work/inputs.json" \
  --java-home "$JAVA_HOME" \
  --tool mixer "$mixer" --tool hostSwift "$HOST_SWIFT" \
  --tool iosProbe "$IOS_PROBE" --tool probe "$ANDROID_PROBE" \
  --tool swiftc "$WASM_TOOLS/swiftc" --tool clang "$WASM_TOOLS/clang" \
  --tool wasm-ld "$WASM_TOOLS/wasm-ld" --tool android.jar "$ANDROID_JAR" \
  --tool aapt2 "$ANDROID_BUILD_TOOLS/aapt2" --tool apksigner "$ANDROID_BUILD_TOOLS/apksigner" \
  --tool zipalign "$ANDROID_BUILD_TOOLS/zipalign" --tool keytool "$JAVA_HOME/bin/keytool" \
  --tool openssl "$OPENSSL"
```

The paths in `inputs.json` resolve relative to that file. To move the inputs
with the inventory, preserve their relative layout. If an installed tool's
relative path changes, update its path and keep its verified hash. The
project lock also records the Android toolchain used to prepare the template.

## Produce and inspect the variants

```sh
run="$work/run"
trust="$work/operator/producer-trust.json"
python3 -B "$driver" produce --settings "$work/inputs.json" \
  --output "$run" --producer-trust "$trust"

"$mixer" release inspect --directory "$run/review-source" \
  --qualification "$run/compatible" --producer-trust "$trust"

permission_status=0
"$mixer" release inspect --directory "$run/permission-source" \
  --qualification "$run/permission-change" --producer-trust "$trust" \
  || permission_status=$?
test "$permission_status" -eq 2
```

The producer writes the fresh public trust file directly to your operator
directory after the run succeeds. Keep it outside the run. When moving a
qualification to another operator, share the trust file via an independent
trusted channel. The inspector rejects an anchor inside the qualification.

The confirmation edit reports `ota-compatible` for both targets and exits 0.
The producer verifies the original APK signature and checks that its package ID,
compiled manifest and permissions match the baseline relink. The permission case
keeps the exact compiled confirmation guest. It links, aligns, signs, and
inspects the APK with the extra camera permission. Both APKs retain the input
DEX and native libraries. Inspection exits 2 with
`store-build-required` for Android and `ota-compatible` for iOS.

The host probes drive the baseline and confirmation variants, close the
owners, and reopen persisted storage. The original Android runtime also
rejects the permission-changing offer and reopens the retained sequence-2
guest with the completed task. The Apple probe acknowledges display at the
host boundary. This covers host behavior on macOS. Simulator rendering and
installed mobile behavior require separate evidence.

A host can miss a successor frame. The producer retries the same signed
offer in fresh storage only after the probe reports owner closure. After
three unsuccessful attempts it stops without writing the producer trust file.

## Run the regression checks

The inspector test substitutes individual files in a private copy of the
compatible qualification. It reads the original run for the positive inputs
and permission case.

```sh
python3 -B "$repo/cli/build-tests/test_release_inspection.py" "$mixer" "$run" \
  --producer-trust "$trust" --openssl "$OPENSSL"
```

To exercise service admission as well, build the local Go service and run the
loopback check. It checks that both refusals preserve the original signed
offers and that the service and its listener close after each run.

```sh
go -C "$repo/services" build -mod=readonly -o "$work/mixer-service" ./cmd/mixer-service
python3 -B "$repo/cli/release-tools/verify_fieldlog_admission.py" \
  "$run" "$work/mixer-service" "$work/origin"
```

Keep any needed public reports and the operator trust file if you need to
inspect the qualification again. The producer uses disposable signing keys
and no account credentials. Normal completion deletes the private keys and
regression copy. Check the command results before removing the exact `$work`
directory created by `mktemp`. A producer or regression `HOLD.json`, an
unresolved origin lifecycle record, or an interruption without a terminal
result means you must preserve that run directory and its recorded process
group. Do not signal, retry, or delete a held run.

After confirming terminal closure, remove the owned scratch directory.

```sh
python3 - "$work" <<'PY'
from pathlib import Path
import shutil
import sys

work = Path(sys.argv[1])
if work != work.resolve() or not work.name.startswith("mixer-fieldlog-inspect."):
    raise SystemExit("Expected the exact private FieldLog scratch path")
shutil.rmtree(work)
PY
```
