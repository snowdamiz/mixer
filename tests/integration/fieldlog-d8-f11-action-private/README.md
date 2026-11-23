# Private F11 signed host actions

This macOS headless replay composes the verified F11 vertical overlay in an
owned disposable tree. It runs the real signed Wasm owner with the original
50 ms turn limit and reuses the original F11 guest, codec, seed, and read-only
storage adapter. The worker reads the stock recipe from Stage commit
`b9d227c81c` and verifies the overlay producer and Pair25 source tree.

The host fixture captures the current revision 2 ticket from the signed
presentation after the exact note-edit delivery. A host action consumes one
permit bound to the presentation, attachment, frame, expected workspace
revision, action, and exact displayed UTF-8. Pair25 checks that revision and
the target draft inside its transaction. The Save closes its repository, and
the Commit uses a new repository opened on the saved workspace. The signed
presentation stays live to authorize both actions. A separate process reopens
the committed workspace.

The replay uses the original F11 raw JSON assertions to check sibling and
prior rows byte for byte. It checks one linked `entrySaved` append and
unchanged workspace bytes after rejected requests. A separate signed owner
exercises attachment loss before Save. The stock codecs and all 11 stock
identity vectors run in the same replay.

```sh
python3 -B tests/integration/fieldlog-d8-f11-action-private/replay.py \
  "$stage" "$local_fieldlog_git_checkout" "$verified_vertical_recipe"
```

Use the retained Stage F11 and F12 fixture inputs, a local FieldLog Git
checkout containing the Pair25 base and the three F11 source anchors, the
tracked `tests/integration/fieldlog-d8-f11-vertical-private` overlay with its receipt, and the overlay's
offline SwiftPM, Cargo, and Wasm toolchains. The runner writes JSON to stdout,
uses private temporary scratch outside the input checkout, caps the run at
12 minutes and 1.5 GiB of sampled scratch, and records any
unresolved process group as a hold. This scope uses headless presentation
tickets and ephemeral signing.
