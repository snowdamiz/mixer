#!/bin/zsh
set -eu
source_dir=${0:A:h}
work=${1:A}
bridge="$work/fieldlog/Integrations/GeneratedReport/Platforms/Android/Bridge"
out="$work/press-trace-host"
mkdir "$out" "$out/android"
printf '%s\n' '#define ANDROID_LOG_INFO 4' 'int __android_log_print(int, const char *, const char *, ...);' > "$out/android/log.h"
xcrun clang -std=c11 -Wall -Wextra -Werror -DCLOCK_BOOTTIME=CLOCK_MONOTONIC \
    -I"$out" -I"$bridge" -pthread "$bridge/DraftPressTrace.c" "$source_dir/trace-host.c" -o "$out/control"
"$out/control"
