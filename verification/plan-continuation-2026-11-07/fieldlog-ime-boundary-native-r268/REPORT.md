# Native long-note boundary

PASS on the owned API37 arm64 emulator. The corrected test-only InputMethodService submitted the fixed 100,001-byte ASCII payload through the OS InputConnection with its own boundary bypass explicitly enabled. The actual EditText remained empty, without truncation; a subsequent 45-byte multiline Unicode input passed. InputConnection returned true, so refusal is established by the actual field readback and unchanged repository, not by that return value.

No Save or Commit ran. The complete workspace bytes remained equal at navigation, before/after the rejected input, after valid unsaved recovery, and final observation: six tasks, eleven outbox records, one committed entry and no drafts. The separate original app was byte-equal. See result-boundary.json, preservation.json, one-byte-over.json and one-byte-over-readback-0.json for direct evidence.

The original default/enabled/subtype IME settings were restored exactly, the fixture uninstalled, the owned emulator exited zero and its serial disappeared; the external baseline remained empty. Active run: 57.36 seconds. The script and exact runtime plan are retained.

This is staged V4 + viewport + root-removal development evidence. Source-pair/public generator adoption, other over-limit payloads, UIKit, physical phones, immutable packages and GA remain pending. No historical hold was released.
