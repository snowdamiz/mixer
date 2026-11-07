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
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-runtime-policy.json)" = 1a5ac109b1b7919306e634b0a0ca350dedbf9d0744046e020008d6d45e303064 ] || { echo 'refused altered external admission python-runtime-policy.json' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-files.sha256)" = b7fe7a29972570c21e0b486db50777b7df2be94352f5b87a89050499a093cfc8 ] || { echo 'refused altered external admission python-files.sha256' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-links.tsv)" = 3dfa4f9541bc5ac86c731d9e6a6fc07b3a2a48eb253f00cf47eafda443590ab2 ] || { echo 'refused altered external admission python-links.tsv' >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-prefix-pathset.txt)" = ea5efec3dfa84bca429cbb56500e94d2c696cd74e0f86227b723928d20d47775 ] || { echo 'refused altered external admission python-prefix-pathset.txt' >&2; exit 2; }
[ "$(digest /bin/sh)" = 84ca7f9b83021621e16059a1c7850df72a462d879e8239d566236ca6ddd00953 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/env)" = 2b2a1145527f00e8369fda0d2ffc523b520201bb08dbaf4b0bded837f7652ce0 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/find)" = 419f5b358926c458cdd439c5d50067de6a27b28f91ff6964d03f628be7c873e3 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/sort)" = e279743c4020dd1ca7d271997ae5876edc83e0782d9bf3c70e79a525cecc9d70 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/cmp)" = 02a004739c0e461713c71ad7623844ace1dd1691b637a57d7f5d614001e4de91 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/readlink)" = 2dc55748b64cf63d2452300bcf2cd3fc337425e76c76f8c484212026840d5a3c ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/shasum)" = 0812595f981a26f813d98dc380af14d4af427626c9339eda29eb849ae13de1e3 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/perl)" = 85e5621137742a37be052f58800372b2005f91f609ad55019832214b5d9e61bc ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/mktemp)" = 14a9ae4763a720460ab50fb14b340ad59882645dd3d0b4f94f8b8ce8fe6ca454 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /bin/rm)" = a28fd10330466ee02c66cdbc4e2b0af23c236b773b1a8a3b210ff9613d9319d8 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /usr/bin/otool)" = 34129c71a01a74f7f3b2443521519b2e5447553fa187f5fcafaaf8c42cc192e2 ] || { echo "refused changed external OS utility identity" >&2; exit 2; }
[ "$(digest /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/bootstrap.py)" = 98be827264d3ac70185e55e6e9889e20f69ecedb31741ad00b2f5e1bc430ae58 ] || { echo "refused altered selected bootstrap" >&2; exit 2; }
[ ! -L /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14 ] || { echo "refused runtime prefix alias" >&2; exit 2; }
/usr/bin/find /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14 -path /opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages -prune -o \( -type f -o -type l \) -print > "$work/paths.raw"
/usr/bin/sort "$work/paths.raw" > "$work/paths.sorted"
/usr/bin/cmp -s "$work/paths.sorted" /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-prefix-pathset.txt || { echo "refused missing/extra runtime path" >&2; exit 2; }
/usr/bin/shasum -a 256 -c /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-files.sha256 > "$work/file-checks" 2>&1 || { echo "refused changed/missing runtime file" >&2; exit 2; }
tab=$(printf "\t")
while IFS="$tab" read -r path target; do [ -L "$path" ] && [ "$(/usr/bin/readlink "$path")" = "$target" ] || { echo "refused changed/missing runtime symlink" >&2; exit 2; }; done < /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/external-admission/python-links.tsv
/usr/bin/env -i PATH=/usr/bin:/bin LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 TZ=UTC /opt/homebrew/bin/python3 -I -B -S /Users/andreyyurlov/Documents/dev/mixer/verification/android-editor-membership-compiled-boundary-qualification/interface-v5/integrity-controls-2/owned-bootstrap-control-4tv59y_k/positive/bootstrap.py "$@"
