# Signed host replay for FieldLog D8 F08

The recorded comparison is FieldLog `00c8fe04` → `c6562ba8`. The introduced
Android factory routes completion through `toggleTask` and a separate move
through a bounded adjacent swap and `reorderTasks`. Both use the expected
workspace revision in `WorkspaceRepository.transact`. The tracked installed
Pair25 receipt establishes the original one-page Android journey and its
revision 3 → 4 → 5 workspace and outbox. The older paired signed F02/F08
receipt uses a separate three-task fixture.

This replay uses the original installed seed verbatim and the exact model and
repository blobs from the retained historical F08 selector pin `552559d`.
The Guest UI V1 documents and controls are reauthored host projections. The
prior and rollback show the checklist and read-only queue. The successor
adds the two actions exercised by the installed F08 witness. The host route
does not replicate Android's full checklist navigation or native rendering.
The two new event UUIDs and timestamps come from the real repository during
this run. The historical Android event UUIDs and timestamps remain in its receipt.

Use local pinned Git objects, cached locked dependencies, and the stock
origin/CLI from the F02 replay. Run from the Mixer checkout, with `work` an
empty owned directory under `verification/local/`, `fieldlog` the offline
checkout containing `552559d`, `tools` the retained stock binary directory,
and `seed` the read-only F08 fixture whose digest is in the installed receipt.

```bash
recipe=tests/integration/fieldlog-d8-f08-signed
bash "$recipe/build.sh" "$work" "$fieldlog"
python3 -B "$recipe/journey.py" \
  "$work/swift/out/Products/Debug/F08Control" \
  "$work/source/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures" \
  "$work/guest" "$work/rust/release/libmixer_vm.a" \
  "$tools/stock-mixer-service" "$tools/mixer" "$work/run" "$seed"
```

The driver verifies the origin audit, signed candidate and rollback lineage,
the Android-scoped runtime descriptor's 50 ms VM turn ceiling, action routing,
workspace byte deltas, and a cold launch after the stock origin stops. Retain the
receipt and remove owned scratch after terminal custody is established.
