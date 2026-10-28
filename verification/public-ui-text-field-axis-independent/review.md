# Independent source review: public text-field axis

No blocking source findings. The six-file slice is **accepted for root-coordinated remote CI only** at base `fb7c7f20f8a308424ef4b7092d19d3d4de2c7627`. All six SHA256 values match the coordinated candidate; exact values, command outputs, and supporting source hashes are in `receipt.json`.

The public initializer appends `axis` after `onSubmit`, and both omitted and explicit horizontal authoring retain the old schema-1 properties and action sequence. Vertical admission is explicit in `UIValidator`; its default remains horizontal and its existing resource/action limits remain in force. Invalid type, unknown axis, and wrong-kind properties fail validation before reconciliation mutates a snapshot.

The Apple host opts into both axes by default and preserves any narrower supplied validator on initialization and update. The private native node receives a validated snapshot and passes the admitted axis to SwiftUI. The source package still targets iOS 26/macOS 14. I found no source-level API-signature, MainActor, or immutable Sendable-global mismatch in the seven UI tests and two Apple host tests. Compiler acceptance is pending.

The existing native packet and appearance V1/V2 entry points, default guest codec, and Android document session revalidate with the portable validator. The Android packet decoder excludes `axis` from the text-field property whitelist and rejects the candidate before native view use. The guest execution exchange still admits only vStack/text/button. Codec opt-in establishes data admission only. The existing Apple test file already imports SwiftUI unconditionally; the new host test file does not establish a new Linux-test regression.

The ordinary remote `verify.yml` Swift job pins Xcode 26.3 and invokes root `swift test`; root and SDK package manifests both include these new test paths. **No compiler or tests were run in this review.** Native input/wrapping/focus/IME/accessibility, Android multiline/shared-theme behavior, physical phones, and immutable separate-repository FieldLog consumption remain pending.

Reviewer scope was limited to this evidence directory. No canonical edits, commits, pushes, CI/GitHub calls, local compiler/guest/native/simulator/emulator/UI/capture calls, private FieldLog source reads, process inventories, or process mutations were performed. All active pause, stopped-v5, UnitA, PID and custody holds remain in place.

