#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
    echo 'Usage: build.sh <fresh or owned absolute output directory>' >&2
    exit 2
fi
case "$1" in
    /*) ;;
    *) echo 'Use an absolute output path.' >&2; exit 2 ;;
esac
project=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work=$1
mkdir -p "$work/tmp" "$work/android-user" "$work/gradle-home"
export MIXER_COMPOSE_WORK="$work"
export GRADLE_USER_HOME="$work/gradle-home"
export ANDROID_USER_HOME="$work/android-user"
export TMPDIR="$work/tmp"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Djava.io.tmpdir=$TMPDIR"
gradle_command=${MIXER_GRADLE:-gradle}
if ! "$gradle_command" --version | grep -qx 'Gradle 9.8.1'; then
    echo 'The Compose host build requires Gradle 9.8.1.' >&2
    exit 2
fi
if [ ! -f "$work/debug.keystore" ]; then
    "${JAVA_HOME:?Set JAVA_HOME to JDK 25}/bin/keytool" -genkeypair -noprompt \
        -keystore "$work/debug.keystore" -storepass android -keypass android \
        -alias androiddebugkey -dname 'CN=Mixer UP4 Debug' -keyalg RSA -keysize 2048 -validity 30
fi
exec "$gradle_command" --no-daemon --console=plain --project-dir "$project" \
    --project-cache-dir "$work/project-cache" "-Pkotlin.project.persistent.dir=$work/kotlin" \
    authorityCheck assembleDebug assembleDebugAndroidTest
