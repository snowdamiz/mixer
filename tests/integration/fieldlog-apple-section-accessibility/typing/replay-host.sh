#!/bin/zsh
set -euo pipefail
if (( $# != 1 )); then
  print -u2 "Usage: replay-host.sh FIELDLOG_CHECKOUT"
  exit 2
fi
fieldlog=${1:A}
delivery=${0:A:h}
repo=$(git -C "$delivery" rev-parse --show-toplevel)
umask 077
mkdir -p "$repo/verification/local"
work=$(mktemp -d "$repo/verification/local/fieldlog-apple-typing.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/tmp" "$work/source/mixer/sdk/Sources" "$work/source/AXProbe" "$work/source/fieldlog"
export TMPDIR="$work/tmp"
export SWIFT_MODULE_CACHE_PATH="$work/swift-modules"
export CLANG_MODULE_CACHE_PATH="$work/clang-cache"
export GIT_NO_LAZY_FETCH=1 GIT_ALLOW_PROTOCOL=file
git -C "$fieldlog" archive 552559d2d3278abb9b1aa7dcf0288102c09a202b Sources Tests/FieldLogTests |
  tar -xf - -C "$work/source/fieldlog"
for module in MixerCore MixerUI MixerApple; do
  cp -R "$repo/sdk/Sources/$module" "$work/source/mixer/sdk/Sources/"
done
patch -s -F 0 -p1 -d "$work/source/fieldlog" -i "$delivery/fieldlog-opt-in.patch"
cp "$delivery/TaskEditorSaveOrderingTests.swift" "$work/source/fieldlog/Tests/FieldLogTests/"
cp "$delivery/HostPackage.swift" "$work/source/Package.swift"
cp "$delivery/AXProbe.swift" "$work/source/AXProbe/main.swift"

swift test --package-path "$work/source" --scratch-path "$work/build" \
  --cache-path "$work/cache" --config-path "$work/config" --security-path "$work/security" \
  --manifest-cache local --disable-dependency-cache --disable-automatic-resolution \
  -j "${FIELDLOG_HOST_JOBS:-8}"
"$work/build/debug/AXProbe" >"$work/ax.log"
python3 -B - "$work/ax.log" <<'PY'
import json
import sys

with open(sys.argv[1]) as log:
    assert next(log).strip() == "AXIsProcessTrusted=true"
    cases = dict((name, json.loads(raw)) for name, raw in (line.split(" ", 1) for line in log))

def rows(case, identifier):
    return [row for row in cases[case] if row["id"] == identifier]

def fields(case, identifiers):
    for identifier in identifiers:
        assert [row["role"] for row in rows(case, identifier)] == ["AXTextField"], (case, identifier)

fieldlog = rows("fieldlog-form", "task.fields")
assert [(row["role"], row["label"]) for row in fieldlog] == [("AXHeading", "Task")]
fields("fieldlog-form", ["task-title", "task.responsible"])
titled = rows("titled-form", "probe.section")
assert [(row["role"], row["label"], row["help"], row["value"]) for row in titled] == [
    ("AXHeading", "Section label", "Section hint", "Section value")
]
fields("titled-form", ["probe.first", "probe.second"])
for case in ["headerless-form", "headerless-stack"]:
    assert all(row["role"] != "AXHeading" for row in cases[case]), case
    fields(case, ["probe.first", "probe.second"])
print("PASS live macOS AX for opt-in FieldLog, titled and headerless sections")
PY
