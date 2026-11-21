# Replay one Swift checklist macro

Run from a Mixer checkout containing `98ef14202e14661dcc3532f37068aae20ddb70cc`.
Use Apple silicon, Swift 6.3.3, Rust 1.99.0, and Xcode 26.6
at `/Applications/Xcode_26.6.app`. The replay builds the plugin with the
Swift toolchain's host libraries and archives the pinned VM source.

```sh
mkdir -p verification/local
python3 -B -m unittest discover -s compiler/experiments/w07-checklist-macro/tests
area=$(mktemp -d "$PWD/verification/local/checklist-macro-receipt.XXXXXXXX")
python3 -B compiler/experiments/w07-checklist-macro/replay.py "$area/receipt.json"
```

The compiler expands `#checklistCount(mask)` to
`boundedChecklistCount(mask)` on both targets. The missing-plugin build
reports the original call site. The unsigned Guest UI V1 module uses
zero imports, one fixed page, and the existing fuel ceiling. The
strict-session replay matches native frames, verifies refusal and
retirement, and reclaims the slot. Rebuilds may have different Wasm hashes.

The runner reserves a new receipt before launch. Keep any scratch it
reports as unresolved. The test covers this synthetic macro and its
helper. It leaves other plugins and product qualification open.
[Independent replay](../../../verification/receipts/w07-l03-checklist-macro-maintained-root-98ef1420.json)
