#!/bin/zsh
set -eu
source "${0:A:h}/environment.zsh"
exec python3 -B "$recipe/seal-and-package.py" --work "$work" --project "$work/prepared"     --java "$work/java" --native "$work/payload" --reference "$2" --output "$3" "${@:4}"
