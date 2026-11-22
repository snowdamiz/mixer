#!/bin/bash
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd -P)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
work="$(cd "$1" && pwd -P)"

bash "$repo/tests/integration/fieldlog-ios-assignment/ordinary-witness/prepare.sh" "$repo" "$work"
app="$work/source/fieldlog"

apply() {
    local name="$1" input="$2" sha="$3" tree="$4"
    local patch="$work/$name.patch"
    python3 -B - "$input" "$sha" "$patch" <<'PY'
import base64
import hashlib
from pathlib import Path
import sys

data = base64.b64decode(Path(sys.argv[1]).read_bytes())
if hashlib.sha256(data).hexdigest() != sys.argv[2]:
    raise SystemExit("FieldLog patch digest differs")
Path(sys.argv[3]).write_bytes(data)
PY
    git -C "$app" apply --index --whitespace=error-all "$patch"
    test "$(git -C "$app" write-tree)" = "$tree"
}

apply fieldlog-ios-account "$here/fieldlog-ios-account.patch.b64"     a46526c61b402a1763b58b20181d1fa1d6d6aaf5a0272afb967bd43f87aa3a1e     88148e9849ee9b8791d8098eb533a729b78bc98c

apply fieldlog-local-account "$here/../fieldlog-account/fieldlog-local-account.patch.b64"     789a0bd19551dda2f5d03fd35de9878d3466395ce979f4def6626570adfe3e19     c1c3b1a7548432e61192703aa752cf963ccbf02a

apply fieldlog-ios-account-confirmation "$here/fieldlog-ios-account-confirmation.patch.b64"     b08fc8d67993fd5cb611ca248b94613a9cca3158cf7c96fd49b3da6065aed3cc     ebb53f9e95534c342966d701ee9dfd45374b267e
printf 'Prepared FieldLog account tree %s\n' "$(git -C "$app" write-tree)"
