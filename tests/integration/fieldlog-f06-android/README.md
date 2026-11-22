# Private Android F06 vertical editor witness

This development fixture adds the historical F06 vertical title field to
the [private F05 Android projection](../fieldlog-f05-android/README.md).
Decode the two patches and verify their SHA-256 values in the
[installed receipt](../../../verification/receipts/fieldlog-f06-android-rebuilt-editor-api36-7fa6b6ea.json).
Apply the F06 source patch over that F05 projection, then apply the
vertical-packet patch to its projected Mixer inputs.

The original F06 link used the default horizontal-only encoder. The
corrected editor branch passes the horizontal and vertical axes to the
existing native packet encoder. Java still requires a vertical title and
uses stock V4. The development scope and guest execution limits stay fixed.

The 102,348-byte rebuilt F06 guest has SHA-256
`2b2563b48d12a163efd4312bf1d001bf6028735ef75607e0018dbfdfb6077ce8`.
Its historical document oracle matches byte for byte. The archived guest
digest is `a80e759d3988e0e25df1a883d664df2c2eaa46ac46cd87dd4df26d6d9def5464`.
The installed receipt applies to the rebuilt digest.

The private package is `dev.mixer.fieldlog.f06signed` and the synthetic
installation is `fieldlog-f06-android`. The local driver starts the
Activity with `developmentF06` enabled on a fresh offline ARM64 API 36
emulator. Cancel preserves the seed bytes and retires the owner. A new
process recovers the same signed candidate, saves `Inspect pump P-17`
and appends one linked outbox event. The replay waits for each character's
native frame commitment. The exact historical editor is also verified on API 36. Apply the
[historical-payload patch](f06-historical-payload.patch.b64) after the
F06 and vertical patches and use the archived Wasm digest above when
linking and sealing. The historical compiler object output path affects
the last 16 bytes in `.swift_modhash`. The source and toolchain pins
and the installed candidate readback are recorded in the
[exact replay receipt](../../../verification/receipts/fieldlog-f06-android-exact-editor-api36-7fa6b6ea.json).
Apply the [absent Saving patch](f06-absent-saving.patch.b64) or the
[rejected Saving patch](f06-rejected-saving.patch.b64) over the
historical-payload composition. Use the matching archived guest and a
fresh development seal. The signed API 36 replay requires native Add at
revision and input sequence 2, one terminal event, zero workspace write
attempts and an unchanged workspace after cold launch. The rejected
variant must record refusal of revision 3. When the keyboard is visible,
the first Back dismisses it and the second retires the Activity owner.
The [Saving controls receipt](../../../verification/receipts/fieldlog-f06-android-saving-refusals-api36-c8a27e36.json)
records both exact payloads and the installed readbacks.

## Replay buffered title input

Apply the [private F06 title patch](f06-private-title-input.patch.b64) to
the exact F06 flat Java projection. Use the Java sources from Mixer
`7fa6b6ea813f73055c38e7d2bf8e607c75c9c384` and the Activity and frame probe
from the exact F06 link delivery. The patch enables buffering for the
vertical `task.title` on the private opt-in surface. Add waits for the
final committed title echo.

Run the Java producer and host checks with an empty output directory.

```sh
python3 -B replay-title-input.py "$MIXER_CHECKOUT" "$F06_LINK_NATIVE" "$OUTPUT"
```

The new DEX requires a fresh development seal. In the
[installed replay](../../../verification/receipts/fieldlog-f06-android-buffered-title-api36-7fa6b6ea.json),
a single Android input-text dispatch produced 17 committed title echoes.
Add wrote one task and its outbox event. A fresh offline process read the
same saved workspace. Plain, unspanned IME commits passed host controls.
Composition and other advanced IME operations are outside this private buffer.


## Build the disposable IME fixture

Build the fixture in an empty output directory.

```sh
python3 -B title-ime/build.py "$OUTPUT"
```

The fixture accepts a synthetic test action only from a sender with
Android's `DUMP` permission. The active input connection must belong to
the private F06 app and report its vertical title flags. The action
sends two fixed plain commits. The [installed receipt](../../../verification/receipts/fieldlog-f06-android-plain-ime-api36-7fa6b6ea.json)
records both echoes, Save, cold readback, and keyboard restoration.

The [stock keyboard replay](../../../verification/receipts/fieldlog-f06-android-stock-ime-api36-7fa6b6ea.json)
tapped **P** in Android LatinIME. The title wrapper refused the composing
batch and the title remained blank. Cancel preserved the workspace
and retired the owner.

The [composing candidate replay](../../../verification/receipts/fieldlog-f06-android-latinime-save-retirement-d92cb15a.json)
accepted **P** and saved one task on two owned API 36 emulators. The Save
owner's JNI retirement remained unconfirmed, so the driver stopped before
cold readback. The candidate remains private.

The private close path expects the historical title `Inspect pump P-17`.
The [full-title native replay](../../../verification/receipts/fieldlog-f06-android-latinime-full-title-api36-d92cb15a.json)
used the same signed APK and entered that title with stock LatinIME.
All 17 edits committed. Add saved one linked task event, and a fresh
offline process read the same workspace after confirmed retirement.
