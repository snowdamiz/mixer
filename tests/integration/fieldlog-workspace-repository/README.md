# Replay the shared FieldLog workspace repository

The replay reconstructs FieldLog tree `eb08569c13b5`, applies the reviewed
repository patch, and runs both ordinary package paths with the same local
fixtures. It needs a Mixer checkout containing `062aaf116b`, Xcode, and
Python 3.14. The helper verifies the exact dependency and source trees.

Use fresh sibling directories for the work and the receipt. Run from the
Mixer checkout.

```sh
area=$(mktemp -d)
python3 -B tests/integration/fieldlog-workspace-repository/replay.py \
  "$PWD" "$area/work" "$area/result" --host-only
```

The host run compares the complete disk observations and exercises the
focused package tests. Omit `--host-only` to include the documented
Android and generic iPhoneOS compiler paths. Those use Swift 6.3.3 with
the pinned Android SDK and Xcode 26.6 for the Android link, and Xcode 27.2
for the iPhoneOS app. The iPhoneOS app is unsigned and uses placeholder
guest resources.

For the cleanup controls, pass a fresh child path below a canonical
temporary directory.

```sh
controls=$(mktemp -d /private/tmp/mixer-workspace-controls.XXXXXXXX)
python3 -B tests/integration/fieldlog-workspace-repository/test_cleanup.py "$controls/suite" &&
rmdir "$controls/suite" "$controls"
```

The replay checks one terminal receipt per launch, reads each command
log, and verifies its digest before allowing cleanup. Preserve any path
the runner reports as unresolved. On success the result directory contains
the replay receipt and disk afterimages.
[Reviewed repository patch and build receipt](../../../verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb.json)
