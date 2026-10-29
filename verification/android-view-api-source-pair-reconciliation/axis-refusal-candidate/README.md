# Android document text-field axis refusal candidate

Source/data candidate only. No compiler, XCTest, JVM, Rust, product or native runtime was invoked. These files do not select, reserve, publish or qualify a source pair.

## Candidate change

The source copy in `source/MixerAndroidRuntime/DocumentSession.swift` adds two lines in `requireAndroidProfile`. After the existing full-document default `UIValidator` pass, its existing traversal refuses a textField with any explicit `axis` key by throwing `AndroidDocumentError.unsupportedUI`.

The profile check already precedes initial reconciliation. Dispatch already reduces a value copy, checks the next document before applying it to a copied reconciler, and assigns state/revision/reconciler only after successful packet encoding. This candidate changes none of that ordering.

Typed default and explicit-horizontal Authoring continue to omit the axis property. Generic SDK validation, guarded decoding, document encoding and native packet encoding remain unchanged: a raw explicit horizontal property is still admitted and preserved by those SDK paths. The Android session refuses that property before it could publish a packet rejected by the current or derivative Java decoder. The candidate neither removes the property nor adds Android axis support.

The full generic validation pass remains first. Malformed axis values retain `UIValidationError.invalidProperty`; vertical fields retain `UIValidationError.unsupportedTextFieldAxis(.vertical)`. A malformed or vertical node elsewhere in the document also retains priority over the profile-only horizontal refusal.

## Exact identities

| Object | Bytes | SHA256 |
| --- | ---: | --- |
| Canonical baseline DocumentSession.swift | 4,128 | `701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c` |
| Isolated candidate DocumentSession.swift | 4,328 | `cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7` |
| Current SDK22 projection | — | `bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0` |
| Parent proposed adapter24 projection | — | `8cd611a5b07fbf96adb270fa30042577789d4b87b252108697003809f00599b4` |
| Future adapter24 data projection | — | `ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e` |

Projection is SHA256 over ordinal-sorted exported path + NUL + lowercase file SHA256 + LF. Byte counts are checked separately. All 24 parent source rows and all 22 current SDK rows were rehashed against the frozen manifest. The future assembly changes only the DocumentSession row; its other 23 rows, SDK22, wire contracts and descriptor pin remain exact. No policy object or new source-pair identifier is emitted. The parent proposed identifier remains a historical proposal reference only.

`manifest.json` contains the complete future assembly, baseline/candidate identities, 55 named input identities and source/data observations. `DocumentSession.swift.diff` is a two-line insertion against the pinned canonical source. Canonical files and the three frozen parent files were not changed.

## Focused executable test obligations — UNRUN

`tests/AndroidTextFieldAxisRefusalTests.swift` uses XCTest and the actual MixerUI/MixerAndroidRuntime APIs. It is intended for the existing `MixerAndroidRuntimeTests` target after separately authorized isolated staging of the exact candidate.

| XCTest method | Required observation when execution is authorized |
| --- | --- |
| `testTypedDefaultAndExplicitHorizontalKeepEqualPacketsAndSuccessfulUpdates` | Typed forms omit axis, encode equally, match a normal SDK native packet, accept an edit, advance to revision 2 and retain identity. |
| `testRawHorizontalIsPreservedBySDKButRejectedAtAndroidInitialization` | Guarded raw decode, encode and reconciled native packet preserve explicit horizontal; Android initialization throws unsupportedUI. |
| `testRawHorizontalReducerCandidateRollsBackAndOriginalEventIdentityCanRecover` | Two refused reducer candidates preserve value state, revision and previous output; a valid edit using the original identity succeeds; the old event then becomes stale. |
| `testNestedExplicitHorizontalIsRefused` | A field nested through stack/section/row still throws unsupportedUI. |
| `testMalformedAxisKeepsGenericValidationErrorPriority` | Null, boolean, numeric and unknown/empty string axes retain the generic invalidProperty error. |
| `testWholeDocumentMalformedValidationPrecedesAndroidAxisRefusal` | A later malformed sibling is diagnosed before the Android-only axis refusal. |
| `testTypedAndRawVerticalKeepPortableDefaultRefusal` | Typed and raw vertical keep the default unsupportedTextFieldAxis(.vertical) error. |
| `testWholeDocumentVerticalValidationPrecedesAndroidAxisRefusal` | A later vertical sibling is diagnosed before the Android-only axis refusal. |

Future execution requires a separately authorized scratch assembly: use the existing native Android engine package and its current SDK22 dependency, preserve the pinned SessionRegistry source, replace only DocumentSession with this candidate, and add the XCTest source to its existing test target. The focused command would then be `swift test --package-path <isolated-assembly>/native/android/engine --filter AndroidTextFieldAxisRefusalTests`. No scratch assembly or command was created/run here. The existing runtime rollback/routing and transaction tests must also be executed before promotion. Compiler acceptance and all executable observations remain pending.

## Authority and cleanup

Only this new child directory was written. No Git/gh/network, subprocess, subject-module import, process/group/signal/probe, old held work, native/UI/capture, phone operation, new SDK repository, tag, release or publication occurred. No simulator/emulator was started, so this lane created no native cleanup obligation. The focused view16 and frozen227-delivery files remain untouched. All prior holds remain binding.

One source-data check initially used locale-aware path ordering and failed to reproduce the parent projection before metadata output was written. The calculation was corrected to ordinal path ordering and then reproduced both frozen parent projections. That correction exercised source/data hashing only; it provides no executable product acceptance.
