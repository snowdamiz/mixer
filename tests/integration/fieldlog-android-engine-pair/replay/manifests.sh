#!/bin/zsh
set -euo pipefail
cd "${1:A}"
export TMPDIR="$PWD/tmp"
export JAVA_HOME=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home
/bin/zsh -f ./compile-android-java.sh
aapt=/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0/aapt2
jar=/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar
for label in old new; do
  case "$label" in old) version=24101 ;; new) version=24102 ;; esac
  sed -e "s/android:versionCode=\"1\"/android:versionCode=\"$version\"/" \
      -e "s/android:versionName=\"0.1.0\"/android:versionName=\"0.1.0-cohort.$label\"/" \
      manifest-base.xml > "apk/manifest-$label.xml"
  "$aapt" link -I "$jar" --manifest "apk/manifest-$label.xml" -o "apk/manifest-$label.apk" apk/network.zip
done
