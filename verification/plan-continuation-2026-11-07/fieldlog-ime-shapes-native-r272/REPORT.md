# Native additional full-size note shapes

PASS on the owned API37 arm64 emulator. The corrected test-only OS InputMethodService entered three additional 100,000-UTF-8-byte payloads through the real InputConnection: 100,000 ASCII characters, 50,000 precomposed accented characters and 25,000 `row\n` lines. Each actual native field readback was complete and matched the exact payload SHA-256 after model processing. The R252 durable flow separately covered decomposed accents and emoji.

No Save or Commit ran. The complete workspace bytes remained equal after every shape and final observation: six tasks, eleven outbox records, one entry and no drafts. The separate original app was byte-equal. Direct evidence is in result-shapes.json, preservation.json, each shape write/echo JSON and raw commands.

The original default/enabled/subtype IME settings were restored exactly, the fixture uninstalled, the owned emulator exited zero and its serial disappeared; the external baseline remained empty. Run: 92.62 seconds. No native fatal or surface failure occurred.

These are staged V4 emulator development results. Public source-pair/generator adoption, UIKit, physical phones, immutable packages, full keyboard/window/accessibility parity and GA remain pending. No historical hold was released.
