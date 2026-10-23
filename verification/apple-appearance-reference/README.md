# Unchanged Apple appearance reference

Eight native simulator screenshots preserve the Apple renderer before any shared
theme is applied. All Mixer source/package/contract inputs come from Git revision
`958998d92f1c2ba205de09a83d957d738b619572`; the app links the copied package under
`frozen/sdk`, never the concurrently edited SDK checkout. `input-lock.json`
records all 50 exact frozen file hashes and the Git tree. No production file,
default, packet, host or signed presentation path was changed by this reference.

Open [the paired screenshot gallery](gallery.html). Each fixture uses exactly the
same bundled `MixerUI.UIDocument` bytes in light and dark appearances. The frozen
SDK decodes/validates all fixtures and initializes `MixerUIHost`; the app checks
that each host snapshot equals its source document. The actual rendered bytes,
validation result and native window/environment observation accompany every PNG.

| Fixture | Native content covered | Requested environment |
| --- | --- | --- |
| typography | body/headline/title/caption; wrapping, maxLines=2, disabled text | LTR, standard large text, light/dark |
| controls | normal/destructive/cancel and disabled buttons; empty/filled field; checked/unchecked/disabled toggle | LTR, standard large text, light/dark |
| layouts | explicit VStack, baseline HStack, ZStack with two children, absent VStack spacing/alignment; list/section/navigation | LTR, standard large text, light/dark |
| rtl-large | Arabic headline/body/button/toggle, list/section/navigation | harness RTL + Arabic locale; accessibility-medium, light/dark |

The dedicated `MixerAppearanceReference` iPhone 18 Pro simulator runs iOS 27.0
`24A434`. Native observation reports a 402×874 point screen/window, scale 3 and
1206×2622 native pixels. The PNG header independently records 1206×2622 pixels.
Observed window safe-area insets are top 62/bottom 34/left 0/right 0 points. These
are runtime values, not values inferred from declarations. No individual node
frame, font size, control dimension, color value or inset was measured here.

Xcode 27.1 `27A9275`, iOS Simulator SDK 27.1 and Apple Swift 6.4 built the harness.
The runtime OS is 27.0; SDK and runtime versions are recorded separately. Exact
commands, outputs and exit codes are in `commands.json` and `logs/`. Status bar
time/connectivity/battery were fixed using simulator overrides. Increase Contrast
was explicitly disabled. The harness sets only locale and layout direction; text
size and appearance come from simulator settings and are observed inside the app.
No font, tint, palette, padding, button/toggle/list style or theme is installed by
the harness. The screenshot black display mask and system status bar remain
system-owned surfaces. No interaction or keyboard was active during capture.

`scripts/verify.py` verifies exact Git inputs, fixture and screenshot integrity,
equal light/dark document bytes, actual native environment, portrait orientation,
all-ten-kind SDK admission and successful compilation of the frozen renderer.
This is executable baseline integrity evidence, not a parity or release decision.
`scripts/seal.py` runs those checks and hashes the complete retained evidence set.
`build/` is ignored local derived data; `built-app-manifest.json` records the exact
built `.app` files. The root controller owns commits and pushes.

```sh
python3 verification/apple-appearance-reference/scripts/freeze-inputs.py
python3 verification/apple-appearance-reference/scripts/verify.py
python3 verification/apple-appearance-reference/scripts/verify-seal.py
```

To deliberately repeat native capture on the same dedicated simulator, run
`scripts/capture.py`. It asserts the named simulator identity, uses an explicit
Xcode simulator destination and replaces only this reference app's capture files.
It never resets/erases/shuts down any simulator. This historical receipt binds
the existing output bytes; a new run needs a new reviewed seal. If the recorded
simulator is absent, recreate the dedicated simulator using the exact device and
runtime identifiers in `simulator.json` and deliberately update the local script
identifier before making a separate new receipt. No physical discovery is used.

All eight screenshots were visually inspected by the producing agent for readable
content, complete fixture visibility and obvious clipping. See
[the observations and pending review](observations.md). An accountable human's
token/design review, physical iOS/Android comparison, native behavior/a11y/input,
signed display/health, immutable published FieldLog and GA qualification remain
pending. No phone was discovered or used and no reconnection is requested.
