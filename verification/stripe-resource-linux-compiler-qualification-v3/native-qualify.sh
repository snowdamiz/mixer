#!/bin/sh
# Proposed C6 compiler-only qualification. Never run without root selection.
set -eu
PATH=/usr/bin:/bin
LANG=C.UTF-8
LC_ALL=C.UTF-8
export PATH LANG LC_ALL
unset HOME
unset GCC_EXEC_PREFIX COMPILER_PATH LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH LD_PRELOAD GCC_COLORS TMPDIR
prefix=/opt/mixer-compiler/toolchain
out=/tmp/mixer-compiler-qualification
mkdir -m 700 "$prefix" "$out"
/usr/bin/sha256sum -c /inputs/prelaunch.sha256
/usr/bin/tar --extract --file=/inputs/compiler-payload.tar --directory="$prefix" --no-same-owner
/usr/bin/sha256sum -c /inputs/payload-files.sha256
# New compiler-sysroot alias only; no original C5 link is changed.
[ ! -e "$prefix/lib" ] && [ ! -L "$prefix/lib" ]
ln -s usr/lib "$prefix/lib"
while IFS=' ' read -r expected source; do
    source=${source# }
    case "$source" in
        /usr/lib/aarch64-linux-gnu/*) target="$prefix$source" ;;
        *) exit 78 ;;
    esac
    [ ! -e "$target" ] && [ ! -L "$target" ] || exit 78
    cp -L "$source" "$target"
    printf '%s  %s\n' "$expected" "$target" | /usr/bin/sha256sum -c -
done < /inputs/base-libraries.sha256
# libc.so's unmodified absolute linker-script path is rooted inside this sysroot.
cp -L /lib/ld-linux-aarch64.so.1 "$prefix/usr/lib/ld-linux-aarch64.so.1"
loader=$(sed -n 's@^\([a-f0-9]*\)  /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1$@\1@p' /inputs/base-libraries.sha256)
[ -n "$loader" ]
printf '%s  %s\n' "$loader" "$prefix/usr/lib/ld-linux-aarch64.so.1" | /usr/bin/sha256sum -c -
LD_LIBRARY_PATH="$prefix/usr/lib/aarch64-linux-gnu"
export LD_LIBRARY_PATH
driver="$prefix/usr/bin/aarch64-linux-gnu-gcc-13"
readelf="$prefix/usr/bin/aarch64-linux-gnu-readelf"
"$driver" --version
"$driver" -dumpmachine
"$driver" -dumpfullversion
"$driver" -print-search-dirs
"$driver" -print-sysroot
# Explicit prefixes constrain compiler subprograms, includes, start objects and ld scripts.
set -- "-B$prefix/usr/libexec/gcc/aarch64-linux-gnu/13/" "-B$prefix/usr/bin/" \
    "-B$prefix/usr/lib/gcc/aarch64-linux-gnu/13/" "--sysroot=$prefix" \
    -isystem "$prefix/usr/include/aarch64-linux-gnu" -isystem "$prefix/usr/include" \
    "-L$prefix/usr/lib/gcc/aarch64-linux-gnu/13" "-L$prefix/usr/lib/aarch64-linux-gnu"
for component in cc1 collect2 as ld; do
    printf 'MIXER_PROGRAM=%s\n' "$component"
    resolved=$("$driver" "$@" "-print-prog-name=$component")
    printf '%s\n' "$resolved"
    case "$resolved" in "$prefix"/*) [ -x "$resolved" ] ;; *) exit 78 ;; esac
done
for object in Scrt1.o crti.o crtbeginS.o crtendS.o crtn.o libc.so libgcc.a libgcc_s.so; do
    printf 'MIXER_LINK_INPUT=%s\n' "$object"
    resolved=$("$driver" "$@" "-print-file-name=$object")
    printf '%s\n' "$resolved"
    case "$resolved" in "$prefix"/*) [ -f "$resolved" ] ;; *) exit 78 ;; esac
done
for iteration in 1 2; do
    mkdir -m 700 "$out/run-$iteration"
    # Only compilation/linking occurs. Products live on a noexec filesystem.
    /usr/bin/timeout -k 1 20 "$driver" "$@" -std=c11 -O2 -Wall -Wextra -Werror -v -Wl,-t \
        /inputs/fault_helper.c -o "$out/run-$iteration/fault_helper"
    /usr/bin/timeout -k 1 20 "$driver" "$@" -std=c11 -O2 -Wall -Wextra -Werror -fPIC -shared \
        -I /usr/local/lib/erlang/usr/include -v -Wl,-t \
        /inputs/control_nif.c -o "$out/run-$iteration/control_nif.so"
    /usr/bin/sha256sum "$out/run-$iteration/fault_helper" "$out/run-$iteration/control_nif.so"
    "$readelf" -h -l -d --version-info --dyn-syms --wide "$out/run-$iteration/fault_helper"
    "$readelf" -h -l -d --version-info --dyn-syms --wide "$out/run-$iteration/control_nif.so"
done
cmp "$out/run-1/fault_helper" "$out/run-2/fault_helper"
cmp "$out/run-1/control_nif.so" "$out/run-2/control_nif.so"
printf 'MIXER_C6_COMPILES=4\nMIXER_HELPER_EXECUTED=0\nMIXER_NIF_LOADED=0\nMIXER_BEAM_EXECUTED=0\nMIXER_RESOURCE_ROWS_EXECUTED=0\n'
