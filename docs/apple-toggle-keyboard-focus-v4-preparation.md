# Private Settings diagnostic: V4 host repair

Root selected only the three host corrections in
`verification/apple-toggle-keyboard-focus-v3-root-review/v4-repair-selection.json`
(`b8ae22a67823022f397f5b0efca8d92bfcda75043f7415afb0cf102cd765a807`).
All earlier packets, failed observations and independent review remain immutable.
This packet is always `DIAGNOSTIC_ONLY`; six application cases stay unrun, even
if public Settings setup succeeds. No native run, compiler, UI, device or process inspection,
private preference, host setting, Git or tracker operation occurred here.

`settings_telemetry.py` now uses one expected-switch predicate for initial-enabled,
after-switch, poll and terminal window samples as well as required observations.
It requires the same initial switch identifier, expected label/type, existence,
hittability, enabled flag and foreground/state. Invalid samples remain raw
diagnostic evidence and cannot supply an enabled-window sequence.

Each route tap binds its latest observed search row. Expected row labels are
Accessibility, Keyboards & Typing and Full Keyboard Access. Expected identifiers
are those labels or respectively ACCESSIBILITY, KEYBOARDS and
FULL_KEYBOARD_ACCESS; expected types are Cell or StaticText. These are validation
expectations, not native observations. An unknown present row stays raw and
unqualified. Only an explicitly absent old selector is allowed after navigation;
its empty metadata/zero geometry/absent value are checked. Matched taps and raw
claimed taps are recorded separately. No native payload is normalized.

The host receipt cursor includes start, requires nondecreasing times, and advances
only with successful persistence. Start/event/chunk persistence failures preserve
accepted time, sequence and upload state. Offline replay uses the same checks.
The one conditional tap, anchored three-second window, finite bounds, original
qualification assertion and independent cleanup remain unchanged.

The runner source, all 69 product entries and archive are byte-identical to V3:
product `e267bb779734cf11c49bd29abbe4f57cb4506db95217c7c1e024d7ad9fb29597`,
archive `2bd1c1f9fed7b6248242c3e312a516d02f763c0b02dfb1008ef3c4be318aef1b`.
App closure remains
`f9ddf3e2615a80930d551351e1496f12ea476cac3e8d1bfd38d8cd101a1d2a46`,
archive `b9a864d11182ac546d76110d7d4ea342821df98d1e32b3474e57cf07de04b393`.
The V2 strict keyboard oracle is byte-identical. No rebuild occurred; recorded
V3 tool/build revision context is retained as provenance, without a Git query.

Controls include 22 focused V4 methods, 17 independent methods with unchanged
class/function AST, the exact 44 original V3 methods and unchanged 29 V2 methods.
The same 44 assertions also run against V4 with only their positive route fixture
metadata aligned to the new contract; no assertions or negative checks change.
The first fixture-adapter run exposed an invalid-index handling error in that
adapter; its failed receipt is retained and the fixture guard was corrected.
The original three V3 finding methods still fail (five subcase failure records)
against sealed V3, with synthetic witnesses retained. Those expected failures are
not presented as a clean test pass. Complete failing setup still retains AX/PNG
and replays as failure; unknown metadata never establishes successful setup.

Read-only preflight and post-run journal replay, from the repository root:

```sh
python3 -B verification/apple-toggle-keyboard-focus-v4/run.py verify
python3 -B verification/apple-toggle-keyboard-focus-v4/replay.py
```

Root alone selects any native run with `run.py run --scope interaction
--reviewed-seal <seal>`. The expected inherited diagnostic qualification assertion
remains separate from actual Settings/XCTest failure. Physical keyboard, phone,
application keyboard/carrier and GA acceptance remain pending.
