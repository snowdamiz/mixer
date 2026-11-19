#!/bin/zsh
set -euo pipefail
sdk=/opt/homebrew/share/android-commandlinetools
build_tools="$sdk/build-tools/36.0.0"
platform="$sdk/platforms/android-37.0/android.jar"
android="$PWD/fieldlog/Integrations/GeneratedReport/Platforms/Android"
mkdir -p apk/{classes,dex}
"$JAVA_HOME/bin/javac" --release 17 -cp "$platform" -d apk/classes \
    "$PWD"/mixer/native/android/app/src/dev/mixer/android/*.java \
    "$android"/Java/dev/fieldlog/generatedr90/androidhost/*.java
"$JAVA_HOME/bin/jar" --create --file apk/classes.jar -C apk/classes .
"$build_tools/d8" --min-api 36 --lib "$platform" --output apk/dex apk/classes.jar
"$build_tools/aapt2" compile --dir "$android/res" -o apk/network.zip
sed -e 's/<uses-sdk/<uses-permission android:name="android.permission.INTERNET" \/>\n  <uses-sdk/' \
    -e 's/<application /<application android:networkSecurityConfig="@xml\/checklist_network" /' \
    "$android/AndroidManifest.xml" > manifest-base.xml
