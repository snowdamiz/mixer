#!/bin/sh
# Selected tool/compile prerequisite only. Never execute helper or load NIF.
set -u
PATH=/usr/local/bin:/usr/bin:/bin
export PATH
unset HOME
LANG=C.UTF-8
LC_ALL=C.UTF-8
ERL_CRASH_DUMP=/dev/null
ERL_CRASH_DUMP_SECONDS=0
export LANG LC_ALL ERL_CRASH_DUMP ERL_CRASH_DUMP_SECONDS
output=/tmp/mixer-tool-payload
mkdir -m 700 "$output" || exit 1
failed=0
missing=0
printf 'MIXER_SCOPE=tool_payload_and_compile_only\n'
id
uname -a
printf 'MIXER_CORE_LIMIT='
ulimit -c

identify() {
    path=$1
    if [ -f "$path" ]; then
        resolved=$(readlink -f "$path") || return 1
        printf 'MIXER_FILE=%s\n' "$path"
        ls -ld "$path" "$resolved"
        sha256sum "$resolved"
    else
        printf 'MIXER_FILE_MISSING=%s\n' "$path"
        return 1
    fi
}

for tool in elixir erl cc gcc ld as readelf objdump file timeout sha256sum readlink getconf openssl; do
    found=$(command -v "$tool" 2>/dev/null || true)
    if [ -n "$found" ]; then
        printf 'MIXER_TOOL=%s:%s\n' "$tool" "$found"
        identify "$found" || failed=1
    else
        printf 'MIXER_TOOL_MISSING=%s\n' "$tool"
    fi
done
for essential in timeout sha256sum readlink; do
    if ! command -v "$essential" >/dev/null 2>&1; then
        printf 'MIXER_PREREQUISITE_MISSING=%s\n' "$essential"
        exit 78
    fi
done

flags='+S 2:2 +SDcpu 1 +SDio 1 +A 2 -start_epmd false'
if command -v elixir >/dev/null 2>&1; then
    timeout -k 1 15 env -i PATH="$PATH" LANG=C.UTF-8 LC_ALL=C.UTF-8 ERL_CRASH_DUMP=/dev/null ERL_CRASH_DUMP_SECONDS=0 \
        elixir --erl "$flags" --version > "$output/elixir-version.txt" 2>&1
    code=$?
    cat "$output/elixir-version.txt"
    printf 'MIXER_ELIXIR_VERSION_EXIT=%s\n' "$code"
    [ "$code" -eq 0 ] || failed=1
    grep -q '^Elixir 1\.20\.4 ' "$output/elixir-version.txt" || failed=1
else
    missing=1
fi

erlroot=
if command -v erl >/dev/null 2>&1; then
    timeout -k 1 15 env -i PATH="$PATH" LANG=C.UTF-8 LC_ALL=C.UTF-8 ERL_CRASH_DUMP=/dev/null ERL_CRASH_DUMP_SECONDS=0 \
        erl +S 2:2 +SDcpu 1 +SDio 1 +A 2 -start_epmd false -noshell -noinput -eval \
        'io:format("MIXER_ERTS=~s~nMIXER_OTP_RELEASE=~s~nMIXER_CODE_ROOT=~s~nMIXER_SYSTEM_ARCHITECTURE=~s~n", [erlang:system_info(version), erlang:system_info(otp_release), code:root_dir(), erlang:system_info(system_architecture)]), init:stop().' \
        > "$output/erlang-version.txt" 2>&1
    code=$?
    cat "$output/erlang-version.txt"
    printf 'MIXER_ERLANG_VERSION_EXIT=%s\n' "$code"
    [ "$code" -eq 0 ] || failed=1
    grep -q '^MIXER_ERTS=17\.1$' "$output/erlang-version.txt" || failed=1
    grep -q '^MIXER_OTP_RELEASE=29$' "$output/erlang-version.txt" || failed=1
    erlroot=$(sed -n 's/^MIXER_CODE_ROOT=//p' "$output/erlang-version.txt")
    case "$erlroot" in /usr/local/lib/erlang|/usr/lib/erlang) ;; *) failed=1; erlroot= ;; esac
else
    missing=1
fi

headers=
if [ -n "$erlroot" ]; then
    if [ -f "$erlroot/releases/29/OTP_VERSION" ]; then
        printf 'MIXER_OTP_VERSION='
        cat "$erlroot/releases/29/OTP_VERSION"
        printf '\n'
        identify "$erlroot/releases/29/OTP_VERSION" || failed=1
        [ "$(cat "$erlroot/releases/29/OTP_VERSION")" = 29.1.1 ] || failed=1
    else
        missing=1
    fi
    headers="$erlroot/usr/include"
    for name in erl_nif.h erl_drv_nif.h erl_int_sizes_config.h; do
        identify "$headers/$name" || missing=1
    done
    for executable in "$erlroot/erts-17.1/bin/beam.smp" "$erlroot/erts-17.1/bin/erlexec"; do
        identify "$executable" || missing=1
        if command -v readelf >/dev/null 2>&1 && [ -f "$executable" ]; then
            readelf -h -l -d --version-info "$executable" || failed=1
        fi
    done
fi

for tool in /usr/bin/cc /usr/bin/ld /usr/bin/as /usr/bin/readelf /usr/bin/objdump; do
    if [ -x "$tool" ]; then
        "$tool" --version
    else
        printf 'MIXER_PREREQUISITE_MISSING=%s\n' "$tool"
        missing=1
    fi
done
if command -v getconf >/dev/null 2>&1; then getconf GNU_LIBC_VERSION || failed=1; fi
if command -v openssl >/dev/null 2>&1; then openssl version -a || failed=1; fi
for library in /lib/aarch64-linux-gnu/libc.so.6 /usr/lib/aarch64-linux-gnu/libc.so.6 \
    /lib/aarch64-linux-gnu/libcrypto.so* /usr/lib/aarch64-linux-gnu/libcrypto.so* \
    /lib/aarch64-linux-gnu/libssl.so* /usr/lib/aarch64-linux-gnu/libssl.so* \
    /lib/ld-linux-aarch64.so.1; do
    if [ -f "$library" ]; then
        identify "$library" || failed=1
        if command -v readelf >/dev/null 2>&1; then
            readelf -h -l -d --version-info "$library" || failed=1
        fi
    fi
done
for header in /usr/include/stdio.h /usr/include/stdlib.h /usr/include/unistd.h \
    /usr/include/linux/capability.h /usr/include/aarch64-linux-gnu/sys/prctl.h \
    /usr/include/aarch64-linux-gnu/sys/resource.h /usr/include/aarch64-linux-gnu/sys/socket.h; do
    identify "$header" || missing=1
done

if [ -x /usr/bin/cc ]; then
    /usr/bin/cc -print-search-dirs
    for component in cc1 collect2 as ld; do
        executable=$(/usr/bin/cc -print-prog-name="$component")
        case "$executable" in /*) ;; *) executable=$(command -v "$executable" 2>/dev/null || true) ;; esac
        if [ -n "$executable" ]; then identify "$executable" || missing=1; else missing=1; fi
    done
fi

# Keep compiler flags/argument order and fixed process environment from V5.
# The native ERTS include directory is an observed tool input, not a rootfs.
if [ -x /usr/bin/cc ] && [ -n "$headers" ] && [ "$failed" -eq 0 ]; then
    printf 'MIXER_COMPILE_HELPER_BEGIN=1\n'
    timeout -k 1 20 env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 ERL_CRASH_DUMP=/dev/null ERL_CRASH_DUMP_SECONDS=0 \
        /usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror /inputs/fault_helper.c -o "$output/fault_helper" \
        > "$output/helper-compile.stdout" 2> "$output/helper-compile.stderr"
    code=$?
    printf 'MIXER_COMPILE_HELPER_EXIT=%s\n' "$code"
    wc -c "$output/helper-compile.stdout" "$output/helper-compile.stderr"
    cat "$output/helper-compile.stdout"
    cat "$output/helper-compile.stderr" >&2
    if [ "$code" -ne 0 ] || [ -s "$output/helper-compile.stdout" ] || [ -s "$output/helper-compile.stderr" ]; then
        failed=1
    else
        printf 'MIXER_HELPER_COMPILED=1\n'
        identify "$output/fault_helper" || failed=1
        if command -v readelf >/dev/null 2>&1; then readelf -h -l -d --version-info "$output/fault_helper" || failed=1; fi
    fi
    printf 'MIXER_COMPILE_NIF_BEGIN=1\n'
    timeout -k 1 20 env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 ERL_CRASH_DUMP=/dev/null ERL_CRASH_DUMP_SECONDS=0 \
        /usr/bin/cc -std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared -I "$headers" /inputs/control_nif.c -o "$output/control_nif.so" \
        > "$output/nif-compile.stdout" 2> "$output/nif-compile.stderr"
    code=$?
    printf 'MIXER_COMPILE_NIF_EXIT=%s\n' "$code"
    wc -c "$output/nif-compile.stdout" "$output/nif-compile.stderr"
    cat "$output/nif-compile.stdout"
    cat "$output/nif-compile.stderr" >&2
    if [ "$code" -ne 0 ] || [ -s "$output/nif-compile.stdout" ] || [ -s "$output/nif-compile.stderr" ]; then
        failed=1
    else
        printf 'MIXER_NIF_COMPILED=1\n'
        identify "$output/control_nif.so" || failed=1
        if command -v readelf >/dev/null 2>&1; then readelf -h -l -d --version-info "$output/control_nif.so" || failed=1; fi
    fi
else
    printf 'MIXER_COMPILE_UNAVAILABLE=required_tool_or_version_prerequisite\n'
    missing=1
fi
printf 'MIXER_HELPER_EXECUTED=0\nMIXER_NIF_LOADED=0\nMIXER_RESOURCE_ROWS_EXECUTED=0\n'
if [ "$failed" -ne 0 ]; then printf 'MIXER_PREREQUISITE_STATUS=failed\n'; exit 1; fi
if [ "$missing" -ne 0 ]; then printf 'MIXER_PREREQUISITE_STATUS=unavailable\n'; exit 78; fi
printf 'MIXER_PREREQUISITE_STATUS=tool_and_compile_controls_completed\n'
