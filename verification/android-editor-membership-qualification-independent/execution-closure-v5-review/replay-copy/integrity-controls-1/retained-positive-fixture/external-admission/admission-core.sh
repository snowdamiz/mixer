#!/bin/sh
set -efu
PATH=/usr/bin:/bin; LANG=C; LC_ALL=C; TZ=UTC; export PATH LANG LC_ALL TZ
# Caller supplies only an already-owned scratch directory, followed by quoted bootstrap arguments.
scratch=$1; shift
case "$scratch" in /*) ;; *) echo 'refused nonabsolute owned scratch' >&2; exit 2;; esac
[ -d "$scratch" ] && [ ! -L "$scratch" ] || exit 2
work=$(/usr/bin/mktemp -d "$scratch/owned-python-admission.XXXXXX")
trap '/bin/rm -rf -- "$work"' EXIT HUP INT TERM
digest(){ result=$(/usr/bin/shasum -a 256 -- "$1"); result=${result%% *}; printf '%s' "$result"; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-runtime-policy.json)" = 1a5ac109b1b7919306e634b0a0ca350dedbf9d0744046e020008d6d45e303064 ] || { echo 'refused altered external admission python-runtime-policy.json' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-files.sha256)" = b7fe7a29972570c21e0b486db50777b7df2be94352f5b87a89050499a093cfc8 ] || { echo 'refused altered external admission python-files.sha256' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-links.tsv)" = 3dfa4f9541bc5ac86c731d9e6a6fc07b3a2a48eb253f00cf47eafda443590ab2 ] || { echo 'refused altered external admission python-links.tsv' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-prefix-pathset.txt)" = ea5efec3dfa84bca429cbb56500e94d2c696cd74e0f86227b723928d20d47775 ] || { echo 'refused altered external admission python-prefix-pathset.txt' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/bootstrap.py)" = 953c678c2b4d367a54416d8ba5612713e9f351b9233e912938d6037718bb5316 ] || { echo "refused altered selected bootstrap" >&2; exit 2; }
[ ! -L /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14 ] || { echo "refused runtime prefix alias" >&2; exit 2; }
/usr/bin/find /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14 -path /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages -prune -o \( -type f -o -type l \) -print > "$work/paths.raw"
/usr/bin/sort "$work/paths.raw" > "$work/paths.sorted"
/usr/bin/cmp -s "$work/paths.sorted" /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-prefix-pathset.txt || { echo "refused missing/extra runtime path" >&2; exit 2; }
/usr/bin/shasum -a 256 -c /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-files.sha256 > "$work/file-checks" 2>&1 || { echo "refused changed/missing runtime file" >&2; exit 2; }
tab=$(printf "\t")
while IFS="$tab" read -r path target; do [ -L "$path" ] && [ "$(/usr/bin/readlink "$path")" = "$target" ] || { echo "refused changed/missing runtime symlink" >&2; exit 2; }; done < /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/external-admission/python-links.tsv
/usr/bin/env -i PATH=/usr/bin:/bin LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 TZ=UTC /opt/homebrew/bin/python3 -I -B -S /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-1/owned-bootstrap-control-or6lh45f/positive/bootstrap.py "$@"
