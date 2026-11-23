#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ -z "${ANDROID_HOME:-}" ] || [ -z "${JAVA_HOME:-}" ]; then
    echo "Usage: set ANDROID_HOME and JAVA_HOME, then pass a new output directory" >&2
    exit 2
fi

probe=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
app="$probe/../../app/src/dev/mixer/android"
tools="$ANDROID_HOME/build-tools/37.0.0"
platform="$ANDROID_HOME/platforms/android-37.0/android.jar"
mkdir -- "$1"
output=$(CDPATH='' cd -- "$1" && pwd)
mkdir "$output/classes" "$output/dex" "$output/tmp"
export TMPDIR="$output/tmp"
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$TMPDIR -XX:ActiveProcessorCount=2 -Xmx512m"
export PATH="$JAVA_HOME/bin:$PATH"

"$JAVA_HOME/bin/javac" --release 17 -Xlint:all -Werror -proc:none -classpath "$platform" \
    -d "$output/classes" "$app"/*.java "$probe/EnvironmentObservationProbe.java"
"$tools/d8" --min-api 28 --lib "$platform" --output "$output/dex" \
    "$output/classes/dev/mixer/android"/*.class
"$tools/aapt2" link -I "$platform" --manifest "$probe/AndroidManifest.xml" \
    --min-sdk-version 28 --target-sdk-version 34 -o "$output/unsigned.apk"
zip -qj "$output/unsigned.apk" "$output/dex"/classes*.dex
"$tools/zipalign" -f 4 "$output/unsigned.apk" "$output/aligned.apk"
"$JAVA_HOME/bin/keytool" -genkeypair -keystore "$output/probe.p12" -storetype PKCS12 \
    -storepass android -keypass android -alias up2-probe -dname "CN=Mixer UP2 Probe" \
    -keyalg RSA -keysize 2048 -validity 30
"$tools/apksigner" sign --ks "$output/probe.p12" --ks-pass pass:android \
    --v2-signing-enabled true --out "$output/probe.apk" "$output/aligned.apk"
"$tools/apksigner" verify --verbose "$output/probe.apk"
