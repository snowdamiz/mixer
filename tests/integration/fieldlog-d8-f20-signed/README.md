# FieldLog F20 signed host replay

Run this replay on arm64 macOS with the pinned FieldLog Git objects,
locked dependencies cached locally, and the Embedded Swift toolchain
named in the build script. The guest browses the historical 23 drafts
and 43 entries and opens a saved draft from page two. The draft view is
read-only.

Run from the Mixer checkout. Set `work` to an empty owned scratch
directory, `fieldlog` to the local FieldLog checkout containing
`552559d2`, and `tools` to the stock origin and CLI whose hashes appear
in the replay receipt. Set `fixture` to the archived F20 fixture
directory containing `workspace.json` and `pair25-projection.json`.

```bash
stage="$PWD"
recipe="$stage/tests/integration/fieldlog-d8-f20-signed"
bash "$recipe/build-host.sh" "$work" "$stage" "$fieldlog"
bash "$recipe/build-guest.sh" "$work/guest"
python3 -B "$recipe/journey.py" "$stage" \
  "$work/swift/out/Products/Debug/F08Control" \
  "$work/source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$work/guest" "$work/rust/release/libmixer_vm.a" \
  "$tools/stock-mixer-service" "$tools/mixer" "$work/run" "$fixture/workspace.json"
```

The replay verifies the signed baseline, replacement, and rollback, two
cold launches with the origin closed, and exact workspace preservation
with zero write attempts. The receipt records the cold page observations
as equality with the retained online pages. Installed signed Android
delivery remains open.
[Replay receipt](../../../verification/receipts/l08-d8-f20-signed-host-5df25f39.json)
