# Private native V2 transaction independent review

The bounded JNI/CLI source audit and final Android headless source/evidence
review pass. **Current native acceptance is pending.** Apple switch paint/input
qualification remains unresolved, and current Android Section/baseline
regressions have compiled but have not run on Android. The user paused computer
use, screen capture and native simulator/emulator runtime work before those
checks could finish.

This review covers private ordinary UIKit/Android appearance V2 consumers using
`systemSans` and an empty resource catalog. The binding product plan, measured V2
contract and staging/implementation-boundary decisions remain authoritative.
It does not qualify a native engine/renderer coordinator, public V2 bootstrap,
signed delivery, custom resources/fonts, physical phones, real IME or assistive
technology breadth, published FieldLog packages, stores, operations or GA.

The reviewer owns only this document and
`verification/native-v2-transaction-independent-review/`. Product corrections,
native execution and integration remain with their existing owners. No producer
files or shared trackers were edited, no native target was created/discovered,
no redundant product/native suite was run, and no commits or pushes were made
by this reviewer.

## Review and coordinated corrections

The complete Apple renderer, installed/environment capture, native views and
layout files and complete Android renderer, installed/environment capture and
native views files were read. Dependent validation/resolved payload and native
fixture code were followed where needed. Root's previously requested exact
native snapshots, action generations, focused ancestor moves, RTL/source
accessibility order, field width/focus radius, Android V1 lazy initialization and
authoritative native switch acknowledgement were treated as known work.

Concrete findings were sent promptly to root and the affected producer. Their
bounded source dispositions are:

| Finding | Source disposition |
| --- | --- |
| Both platforms left old committed actions active after environment invalidation or unsupported recapture. | Close action/input/draw gates immediately; synchronously check the committed tuple; unsupported recapture retires the owner. Only a successful transaction can reopen it. |
| Apple retained an unacknowledged field/toggle value when a new document repeated the prior bound value. | A new guest document/revision is authoritative even when the binding value is unchanged. Genuine same-revision environment-only updates may retain transient native input. Unsafe composing writes reject before effects. |
| Android measured Button intrinsic size before applying admitted nonzero label insets. | Apply the admitted insets before the native AT_MOST probe; retain the positive packaged inset fixture. |
| Apple dropped admitted accessibility label/hint/value/identifier properties. | Apply to the actual native traversal leaf; reject unsupported semantic overrides on nonleaf containers. Explicit UISwitch backing preserves authored overrides; clearing it delegates to native semantics. |
| Apple painted the pressed toggle overlay above its thumb. | Paint track, overlay, then thumb. |
| Apple centered strokes outside the authored visual bounds. | Inset the path by half the stroke width and adjust radius coherently. |
| Apple admitted direct control rows smaller than the native hit envelope. | Reject the arrangement before attachment when the actual control frame does not fit the row. |
| Android could emit an event after epoch exhaustion retired its owner. | Recheck that the owner is still live after advancing the epoch. |
| Indirect navigation/container/List combinations reached an unqualified compact relayout path. | Reject that combination before effects in both consumers. |
| Apple selectable UITextView omitted the admitted RTL/LTR alignment. | Apply and copy its native text alignment. |
| Android non-list Section forced the full proposal width, changing ZStack/HStack intrinsic layout relative to Apple. | Native AT_MOST header measurement; Section width is max(header, children); place the header at logical leading within that extent. Structural navigation/List title paths remain separate. |
| Section first/last baseline edges differed between platforms. | First uses header.first when a header exists, otherwise firstChild.first. Last uses lastChild.last when children exist, otherwise header.last. Include placement offsets; preserve selected unavailable edges. |
| Apple HStack copied the chosen alignment baseline into both outward baseline edges. | Propagate the actual placed first/last source-child edges. |
| Interactive control baseline scalars were unavailable or did not match the drawn label. | Shared bounded subset marks Button/Field/Toggle baselines unavailable; required baseline alignment rejects. Ordinary top/center/bottom layout is unchanged. |

Root confirmed the shared document-authority and baseline decisions. They require
no public contract schema change. Final Android source recheck also caught and
removed two early TextView baseline assignments which had accidentally kept
control scalars available despite the new text-only final assignment.

Six historical pre-correction source copies, with original paths, byte counts
and SHA-256 digests, are retained in `audit-inputs/`. They substantiate the source
findings; they are not the current accepted closure.

## Native evidence boundary

Actual native runs found issues that source review alone did not establish:

- Disabling the UIKit root resigned its focused editor. Suspension now uses a
  root hit-test blocker and closed action/proposal gates while preserving focus.
- Android's `SpannableString(nativeBuffer)` journal copy notified live framework
  watcher spans during preparation. The journal now snapshots an immutable
  string while retaining buffer identity and separate composing metadata.
- Held UIKit UISwitch did not report `isTracking`. A public nonpreventing touch
  observer supplies authored pressed state while UISwitch retains activation and
  accessibility. Late denied checked callbacks restore only the last admitted
  scalar boolean; this does not claim IME restoration.
- Android native assertions passed while one compositor image showed the prior
  screen and another was blank. Candidate15 used actual frame commitment,
  PixelCopy, retained attempt images and hardware/software content checks.
- Apple candidate12 exposed UIKit replacing an explicit switch accessibility
  value; candidate13's explicit override/update/clear checks passed. Actual held
  pixels still showed elevated native glass outside the zero-area mask.
- Apple candidate14's opacity experiment failed: setting layer opacity to zero
  also made UIView alpha zero, violating the native input invariant.

Failed and intermediate receipts remain failed or historical. Apple now has an
unqualified opaque authored-cover prototype using the same real UISwitch,
restricted to admitted opaque uniform direct List row contexts. Its proposed
padding is not a proven bound on elevated native paint. Successful compilation
cannot establish held/cancel pixels, native hit behavior, exactly-one activation
or accessibility ownership; those checks remain pending after user resumption.

Android candidate15 is retained historical API37 development evidence: 460 main
assertions, 14 positive-inset assertions and five packaged negative cases. The
independent replay verifies its 173 sealed evidence files and explicitly records
the source differences from current Section/baseline work. Its native pass does
not transfer to current source. Minimum-28 DEX compilation is not API28 runtime
qualification; the private prototype's native floor remains separately declared.

Owned Apple simulator/harness and Android emulator cleanup receipts are retained
by the producers and the root pause receipt. Offline review checked the recorded
exact owned process/port absence and preserved the unrelated project process.
No new GUI, capture, device or native runtime calls were issued by this reviewer.

## Sealed headless results

`verification/native-v2-transaction-independent-review/jni-cli-source-review-1/receipt.json`
records **no new blocking finding** in JNI cleanup, link/export or generated ABI
handling. It captures exactly six sources: JNI, private C header, NativeBridge,
engine Bridge, AndroidProject and the Android build driver. Closure SHA-256:
`7c414ec10246b7e9c868faeaf1d6f935037c5f3fd79f841fe4926ff3f7976081`.

The audit followed every prepare delivery-failure cleanup path, exception
preservation, opaque token conversion, scalar commit/abort, generated C signature,
source export, guarded output cleanup and actual generated-library link path.
Offline checks bind the existing root host JNI replay's 153 bindings, all eight
production/derived debug/release normal/interpreted results (585/199 assertions
per mode), successful command logs and retained artifacts. These tests were not
rerun here. Generated Activity still uses the legacy path; copying private V2
dependencies does not opt it into V2.

`verification/native-v2-transaction-independent-review/android-headless-review-1/receipt.json`
passes **641 checks across 552 evidence files** against final producer
`headless-section-4`: 25 current/captured inputs, nine successful strict
Java/bytecode/DEX commands, 308 retained class/DEX artifacts, four tool hashes and
35 current seal files. Source closure SHA-256:
`8a650a03aefe891aaf422817e21c4c8f9e9925798f6568fffcf55db325b24567`.
Final `NativeAppearanceViewsV2.java` SHA-256:
`25611d389dfe6ab4c962bee2db1429d2bd2c84a1e474093f6d8214b5a7c6a8dc`.

No remaining blocking source finding was identified in that requested bounded
Android transaction/environment/Section/baseline correction scope. Runtime
Section native measurement, nested/RTL layout, selected unavailable baseline
edges and ordinary-control layout checks remain unexecuted. Root owns the final
generated-consumer source export and cross-build binding.

Both receipts record their exact command, Python version, source revision/tree,
current input digests and evidence hashes. The source-audit sealing command
intentionally refuses to overwrite its existing output. A fresh offline Android
replay can write a new bounded output directory:

```sh
python3 verification/native-v2-transaction-independent-review/replay-android-headless.py --candidate headless-section-4 --output android-headless-review-2
```

`replay.py` is an **unexecuted prospective native replay draft**, including
installed-app/native-artifact binding. It issued no acceptance receipt and needs
reconciliation with the eventual frozen Apple paint path before use. Current
native acceptance remains false, all deferred product/physical/GA gates remain
open, and no OTA publication is authorized by this source/headless review.
