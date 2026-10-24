# Android native paths for measuredShared2

`AppearanceNativePathsV2.make(AppearanceGeometryV2.Path, int density1024)` is the
first Android toolkit consumer of the closed V2 geometry. The package-private
adapter returns a fresh mutable `android.graphics.Path` with explicit nonzero
`WINDING` fill. Root froze this bounded interface before implementation, alongside
the separate Apple CoreGraphics primitive.

The input can only be constructed by the existing geometry owner's private
constructor and three factories: full-group continuous cubic 2, fixed 63×28 track,
and fixed 37×24 thumb. The adapter consumes all move, line, cubic and close
commands. It accepts no descriptor bytes, arbitrary path, platform radius,
rectangle substitution, downloaded assets or styling dictionary.

Coordinates are local physical pixels with top-left `(0,0)`, x increasing right
and y increasing down. Density is already normalized by the geometry layer;
128…16384 is admitted, including for an empty zero-area path. Other values throw
the existing `AppearanceGeometryV2.Failure` with `density` code; null geometry
throws `IllegalArgumentException`. Each logical 64th converts once through
`coordinate64*density1024/65536` in double precision and then casts to the float
required by Android `Path`. Fractional cubic controls remain fractional; integer
pixel-edge rounding is a separate layout operation. A native float can lose low
coordinate bits at large extents. CoreGraphics on the current Apple targets uses
`CGFloat` precision, so exact cross-platform floating equality is not claimed.

The caller owns returned path mutation, pixel-space translation, fill paint,
clipping and lifetime. No path is cached or shared. A caller can translate its
Canvas to an already-converted pixel origin; it must not apply density a second
time. This adapter does not translate, clip, draw, stroke, mirror or apply thumb
placement. The geometry owner's `thumbOrigin` remains the source of that separate
logical placement. There is no renderer integration or new support authority.

Run the bounded verifier with the installed SDK/JDK:

```sh
python3 verification/android-appearance-native-paths-v2/qualify.py --output candidate-2 --emulator emulator-5580
python3 verification/android-appearance-native-paths-v2/verify-seal.py verification/android-appearance-native-paths-v2/candidate-2 --check-live
```

The optional serial must have the exact `emulator-N` shape, and the verifier checks
the target's emulator property before installing its standalone debug-only test
package. It never enumerates devices, connects a phone, downloads tooling or
changes the production application. Without a serial it compiles the production
adapter and prepared instrumentation and records native execution as pending.
API34+ `PathIterator` is used only in tests; production consumes API1 Path calls.
The current project packaging minimum API28 is retained for production D8 checks.

The test corpus includes all three shapes; ordinary, clamped, zero-radius, odd,
maximum and zero-area group extents; five densities including both bounds and
fractional 2731/1024; native operation and control inspection; literal fractional
track controls; native closure and one-contour checks; invalid-density/null
rejection; independent returned-path mutation; and software Canvas fill/clip with
caller translation. Small retained interior/exterior samples are a native API
smoke check, not a reference-image comparison or display qualification.

The retained [candidate-2 receipt](../verification/android-appearance-native-paths-v2/candidate-2/receipt.json)
records **5,610 passed checks, 45 native paths and 630 native verbs** on Android17
API37 arm64 emulator `emulator-5580` (`sdk_gphone64_arm64`). The dedicated existing
`megpt-parity-api37` AVD ran headless, read-only, with no snapshots; its observed
process flags and installed image metadata hashes are retained in
[emulator-session.json](../verification/android-appearance-native-paths-v2/emulator-session.json).
No physical-device discovery or run occurred. JDK25.0.4.1 compiled Java17 with
`-Xlint:all -Werror`; D8 9.2.4-dev compiled the production closure for minimum
API28 and the standalone instrumentation for API34. The minimum-API28 result is
compile evidence only; native execution was API37. Emulator37.2.12 used the
already installed API37 Google APIs image. Candidate1 is the earlier passing
run before explicit future-operation rejection and evidence sealing were added;
candidate2 is the final source closure.

The receipts record commands, tool versions, source revision and bounded source
hashes, native/API tooling hashes, package/dex hashes, target emulator identity,
explicit instrumentation pass marker, and test scope. The source snapshot binds
the exact three Java sources and verifier inputs; unrelated active lanes are not
compiled into the standalone test package. An artifact seal binds every retained
input, command log, standalone test APK and software raster PNG. The private local
test key remains in ignored `build/`; it is not release signing material. No new
dependency is introduced.

Pending: NativeRenderer integration, real displayed views, hardware Canvas,
physical iOS/Android side-by-side reference pixels and interactions, native
preference/environment capture, resources/fonts, complete operation support,
ordinary atomic attachment, signed V2 installation/authority/display/health,
immutable published FieldLog packages from its separate repository, store,
customer and operational qualification, and all GA gates. Phones remain
disconnected; this work requests no physical run.

Platform semantics were checked against official Android documentation for
[Path](https://developer.android.com/reference/android/graphics/Path),
[PathIterator](https://developer.android.com/reference/android/graphics/PathIterator)
and [Canvas](https://developer.android.com/reference/android/graphics/Canvas).
The independently authored geometry and local source are the implementation
inputs; no third-party engine source or fixture is used.
