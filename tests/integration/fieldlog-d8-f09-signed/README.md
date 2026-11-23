# FieldLog D8 F09 signed host replay

The archived Android introduction adds a 20-task page size, global row
numbering, boundary-aware Previous and Next controls, and page focus that
follows a moved task. The historical parent has no Android factory at that
path. The signed host baseline and rollback use an unpaged, read-only
projection of the same 23 records. The successor projects the archived
pagination and the one move under test.

The successor moves Verify café drain across the page boundary, then shows
both pages again in a fresh process. The installed repository's reorder
refreshes the selected project's task timestamps and swaps only positions
20 and 21. The replay checks the full canonical workspace, one revision and
one linked outbox append, and verifies the unchanged lock file and signed
packets. The last process opens the rollback artifact after the loopback
origin is confirmed closed. The installed Android journey and D2 host
checks remain separately scoped ordinary evidence.

Run from the Mixer checkout. Use an empty owned work directory, a local
FieldLog checkout containing the pinned objects, the F08 stock tools,
and the two read-only files from the archived F09 fixture directory.

```bash
recipe=tests/integration/fieldlog-d8-f09-signed
bash "$recipe/build.sh" "$work" "$fieldlog"
python3 -B "$recipe/journey.py" \
  "$work/swift/out/Products/Debug/F09Control" \
  "$work/source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$work/guest" "$work/rust/release/libmixer_vm.a" \
  "$tools/stock-mixer-service" "$tools/mixer" "$work/run" \
  "$fixture/workspace.json" "$fixture/expected-pages.json"
```

The receipt is `verification/receipts/l08-d8-f09-signed-host-304c75a8.json`.
It identifies the archived inputs and records the signed lineage, page
visits, disk hashes, and scope. The replay uses an ephemeral local key and
a headless macOS display witness. Native signed Android and iOS are pending.
