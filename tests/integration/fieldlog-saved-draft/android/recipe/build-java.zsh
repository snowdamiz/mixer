#!/bin/zsh
set -eu
if (( $# != 3 )); then
    print -u2 'Usage: build-java.zsh FIELDLOG_CHECKOUT PUBLIC_V4_PROJECT OUTPUT'
    exit 2
fi
recipe=${0:A:h}
app=${1:A}/Integrations/GeneratedReport/Platforms/Android
adapter=${2:A}/Generated/MixerAndroid/app/src/dev/mixer/android
payload=${3:A}
sdk=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}
tools="$sdk/build-tools/36.0.0"
jar="$sdk/platforms/android-37.0/android.jar"
export JAVA_HOME=${MIXER_JDK:-/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home}
mkdir "$payload"
mkdir "$payload/classes" "$payload/dex" "$payload/jni"
native=()
for source in "$adapter/"*.java; do
    case "${source:t}" in MixerActivity.java|AdapterInstrumentation.java) continue;; esac
    native+=("$source")
done
"$JAVA_HOME/bin/javac" --release 17 -Xlint:all,-options -Werror -classpath "$jar" -h "$payload/jni" -d "$payload"/classes \
    "${native[@]}" "$app"/Java/dev/fieldlog/generatedr90/androidhost/*.java
"$JAVA_HOME/bin/jar" --create --file "$payload"/classes.jar -C "$payload"/classes .
"$tools/d8" --min-api 36 --lib "$jar" --output "$payload"/dex "$payload"/classes.jar
python3 -B "$recipe/manifest.py" "$app/AndroidManifest.xml" "$payload"/AndroidManifest.xml
"$tools/aapt2" compile -o "$payload"/network.zip "$app/res/xml/checklist_network.xml"
"$tools/aapt2" link -I "$jar" --manifest "$payload"/AndroidManifest.xml -o "$payload"/manifest.apk "$payload"/network.zip
