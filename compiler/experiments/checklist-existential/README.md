# Replay the Swift checklist formatter

Run the formatter fixture on an arm64 Mac with the pinned Swift 6.3.3,
Xcode 26.6, Rust 1.99.0, and Git 2.56.0 installations. The replay checks
their recorded digests and fetches the exact public Mixer commit
`857e4b4aa7a32cda368257b2be1a63e77106bed8`. The local checkout must also
contain that Git object.

```sh
fixture=compiler/experiments/checklist-existential
mkdir -p verification/local
python3 -I -B "$fixture/controls.py" -v
python3 -I -B "$fixture/regression_controls.py" "$fixture/replay.py" corrected
python3 -I -B "$fixture/replay.py" verification/local/checklist-existential.json
```

Each replay needs a fresh receipt path. The runner creates a sibling
`.journal` and removes owned scratch after it confirms command custody.
The journal and any retained scratch identify an incomplete run.

The native fixture selects one of two protocol conformances from actual
event bytes. Embedded Swift rejects that existential at
`ChecklistFormatter.swift:47:32`. The static variant takes the same events
through Guest UI V1. The replay checks the same frames, four refused inputs
that leave the frame intact, and stale-handle refusal after retirement.
[Reviewed replay](../../../verification/receipts/w07-l03-checklist-existential-publication-fix-857e4b4.json)
