# Apple appearance measurements

This verification-only derivative measures the existing Apple design frozen at
`958998d92f1c2ba205de09a83d957d738b619572`. It does not apply the provisional shared
theme, edit the product renderer, replace the immutable reference, or qualify
cross-platform parity. Read [the findings and contract recommendation](../../docs/apple-appearance-measurement.md)
and [the screenshot gallery](gallery.html).

`instrumented-sdk` copies the reference SDK Package.swift and Sources exactly,
except the recorded `instrumentation.patch` and new `MeasurementProbe.swift`.
`harness/ReferenceApp.swift` derives from the exact reference harness: the app name
changes and one public measurement export call is appended to its observation.
The bundled fixture bytes remain equal. Structural Section nodes stay intact;
explicit header Text and every non-section node receive a clear background
GeometryReader. No font, tint, palette, padding or control/list style is installed.

The probe records public SwiftUI geometry, explicit semantic Font resolution
(iOS 26+ public API), and typed UIKit properties. It never uses private class names,
KVC, reflection, selectors or internal class-to-node mappings. Public UIKit traversal
paths identify raw observations only. Font/color reference tables are distinguished
from properties of actual rendered views. A nil environment Font or unset UIColor
property is retained as unresolved rather than guessed.

The dedicated simulator is `MixerAppearanceMeasurement`, iPhone 18 Pro, iOS 27.0
24A434. Its own app/container/preferences are separate from the original reference
simulator. No physical device inventory or run was attempted. Both Debug and Release
are built using Xcode 27.1 / iOS Simulator SDK 27.1 / Apple Swift 6.4, and each builds
and captures 12 profiles: four original fixtures light/dark plus typography and
controls at accessibility-medium in LTR light/dark. Root's current SDK is never linked.

Each capture retains native `measurements.json`, environment/document/fixture
admission records and the original 1206×2622 PNG. `analysis.json` decodes PNG filters
without changing images, compares raw decoded pixels, and counts exact encoded
colors within measured rectangles. Its color counts are not a public paint API or
an automatic semantic classification. `commands.json`, build logs and app file
manifests bind the actual commands/tool output. The source revision/tree and exact
comparison inputs are retained independently from the original baseline lock.

Commands used for this evidence:

```sh
python3 verification/apple-appearance-measurement/scripts/capture.py
python3 verification/apple-appearance-measurement/scripts/analyze.py
python3 verification/apple-appearance-measurement/scripts/verify.py
python3 verification/apple-appearance-measurement/scripts/seal.py
python3 verification/apple-appearance-measurement/scripts/verify-seal.py
```

Do not rerun capture into a sealed historical receipt. A new run requires a new
versioned evidence directory and review. The capture program creates/reuses only
its named simulator, builds its own app and changes that simulator's appearance,
text size, status-bar override and Increase Contrast setting; it does not reset,
erase, shut down, or discover physical devices. Build derived data is ignored.

This is simulator measurement and integrity evidence. Accountable design/token
review, physical iOS/Android side-by-side, native input/interaction/accessibility,
other environment profiles, signed display/health, immutable published FieldLog,
store, customer, operational and GA gates remain pending.
