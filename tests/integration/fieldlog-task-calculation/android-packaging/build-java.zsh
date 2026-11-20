#!/bin/zsh
set -eu
if (( $# < 3 || $# > 4 )); then
    print -u2 'Usage: build-java.zsh FIELDLOG_CHECKOUT MIXER_CHECKOUT OUTPUT [ADAPTER_PINS]'
    exit 2
fi
recipe=${0:A:h}
app=${1:A}/Integrations/GeneratedReport/Platforms/Android
adapter=${2:A}/native/android
payload=${3:A}
pins=${4:-"$recipe/java-adapter-pins.json"}
sdk=${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}
tools="$sdk/build-tools/36.0.0"
jar="$sdk/platforms/android-36/android.jar"
export JAVA_HOME=${MIXER_JDK:-/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home}
mkdir "$payload"
mkdir "$payload/classes" "$payload/dex" "$payload/jni"
python3 -IBS - "$pins" "$adapter" > "$payload/adapter-inputs.txt" <<'PYTHON'
from hashlib import sha256
from pathlib import Path
import json
import sys

pins, adapter = map(Path, sys.argv[1:])
for name, pin in json.loads(pins.read_bytes()).items():
    path = adapter / name
    data = path.read_bytes()
    if len(data) != pin["bytes"] or sha256(data).hexdigest() != pin["sha256"]:
        raise SystemExit(f"Pinned Java adapter source differs: {name}")
    print(path)
PYTHON
native=("${(@f)$(< "$payload/adapter-inputs.txt")}")
"$JAVA_HOME/bin/javac" --release 17 -Xlint:all,-options -Werror -classpath "$jar" -h "$payload/jni" -d "$payload"/classes \
    "${native[@]}" "$app"/Java/dev/fieldlog/generatedr90/androidhost/*.java
"$JAVA_HOME/bin/jar" --create --file "$payload"/classes.jar -C "$payload"/classes .
"$tools/d8" --min-api 36 --lib "$jar" --output "$payload"/dex "$payload"/classes.jar
python3 -IBS "$recipe/manifest.py" "$app/AndroidManifest.xml" "$payload"/AndroidManifest.xml
/usr/bin/arch -arm64 "$tools/aapt2" compile -o "$payload"/network.zip "$app/res/xml/checklist_network.xml"
/usr/bin/arch -arm64 "$tools/aapt2" link -I "$jar" --manifest "$payload"/AndroidManifest.xml -o "$payload"/manifest.apk "$payload"/network.zip
