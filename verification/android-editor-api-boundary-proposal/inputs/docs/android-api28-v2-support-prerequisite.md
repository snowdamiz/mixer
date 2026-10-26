# Android API 28–35: private V2 compatibility prerequisite

**Source proposal only; root selection and independent review are pending.**
The smallest defensible next slice is a public-API observation boundary with
isolated SDK-specific calls and explicit unavailable results. It cannot yet open
private V2 on API 28–35. The reviewed Android reference first exposes the required
high-contrast read and change listener on API 36, while the shared V2 contract
requires unknown visual-accessibility contexts to fail. Treating that observation
as `false` would change the contract without implementing support.

This does not raise the product baseline: product §19.1 still proposes Android
API 28+ subject to qualification. Product §§7.4, 8 and W05 still require host-owned
native resources, native input/accessibility, design parity, lifecycle and real
Android evidence. The accepted private owner is the starting point, not public
routing acceptance. Its exact [C5 acceptance](../verification/android-private-owner-effect-integration-root-review/candidate-5-owner-acceptance.json)
has SHA-256 `b3d45bcdb04fbb9260ad81de554d163d1ff28f71b18b4fab4a1c2cd21d8b3822`.
The inherited context revision is `d275c072b6c89b8e99213e4eb4dafdc4722f5f40`;
this is not a live HEAD assertion. Twenty-eight enumerated current files are
frozen in [source-map.json](../verification/android-api28-v2-support-prerequisite/source-map.json),
with source-map SHA-256 `276bdb5d0285cd77ecbd5306efa4eacf4fc72798768210c17662816deda709b3`.
All source references below address those frozen files; the generated
[source index](../verification/android-api28-v2-support-prerequisite/source-index.json)
records exact line spans and snippets.

## What actually depends on later Android APIs

The following is an inventory of the named concrete V2 subjects and their direct
descriptor/geometry/owner/build references, not a complete executable-library
compatibility proof. Official reference findings were checked on October 26,
2026 and are retained with URLs in
[official-findings.json](../verification/android-api28-v2-support-prerequisite/official-findings.json).

| Concrete source use | Public API floor / finding | Consequence |
| --- | --- | --- |
| `NativeEnvironmentV2.Observer` and `NativeRenderer.requireV2Live` both reject `SDK_INT < 36` | These are independently authored support gates, not Android API calls. | Removing only one gate cannot enable the lane; removing both would expose the remaining dependencies and unknown observations. |
| Observer field, registration, removal and read use `AccessibilityManager.HighContrastTextStateChangeListener`, `addHighContrastTextStateChangeListener`, `removeHighContrastTextStateChangeListener`, `isHighContrastTextEnabled` | All four are public starting at API 36. [AccessibilityManager](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager#isHighContrastTextEnabled()), [listener type](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager.HighContrastTextStateChangeListener). | Every API 28–35 observation is unavailable through this reviewed public surface. Do not reflect into hidden APIs or read an undocumented settings key. |
| Observer field/add/remove/read use `UiModeManager.ContrastChangeListener` and `getContrast()` | API 34; documented contrast range is −1…1 and neutral is 0. [UiModeManager](https://developer.android.com/reference/android/app/UiModeManager#getContrast()). | API 28–33 has no observation through this surface. Current `> 0` rejection is not a complete neutral-value test; negative/nonfinite values need an explicit policy. |
| `Configuration.fontWeightAdjustment` and `FONT_WEIGHT_ADJUSTMENT_UNDEFINED` | API 31; the sentinel means undefined. [Configuration](https://developer.android.com/reference/android/content/res/Configuration#fontWeightAdjustment). | API 28–30 cannot read that member. The adapter must represent absence and the sentinel honestly, rather than synthesize zero. |
| `WindowInsets.getInsets(WindowInsets.Type.systemBars() \| WindowInsets.Type.displayCutout())` returns `android.graphics.Insets` | Typed query/type masks are API 30. [getInsets](https://developer.android.com/reference/android/view/WindowInsets#getInsets(int)), [Type](https://developer.android.com/reference/android/view/WindowInsets.Type). | A base class/signature must not require these newer types. API 28–29 legacy getters are not a documented exact replacement for this query. |
| `NativeAppearanceViewsV2` installs authored cursor and all three selection-handle Drawables | Setter overloads are API 29. [TextView](https://developer.android.com/reference/android/widget/TextView#setTextCursorDrawable(android.graphics.drawable.Drawable)). | API 28 fields require a separate supported implementation or explicit rejection; skipping setters would expose undeclared platform appearance. Selectable text needs its own handle/selection coverage review too. |
| V2 bind calls `View.setStateDescription` only at API ≥30 | API 30. [View](https://developer.android.com/reference/android/view/View#setStateDescription(java.lang.CharSequence)). | API 28–29 must explicitly reject a required `accessibilityValue` before native preparation unless equivalent native semantics are separately implemented. Present V2 bind merely skips the setter; the legacy V1 preflight rejection does not apply to V2. |
| One anonymous field `InputConnectionWrapper` declares `TextAttribute` commit/composing overloads, `setImeConsumesInput`, `replaceText`, handwriting/preview methods | IME consumption is API 31; `TextAttribute` and its three overloads are API 33; replace/handwriting/preview are API 34. [InputConnection](https://developer.android.com/reference/android/view/inputmethod/InputConnection), [TextAttribute](https://developer.android.com/reference/android/view/inputmethod/TextAttribute), [wrapper](https://developer.android.com/reference/android/view/inputmethod/InputConnectionWrapper). | A future compatibility editor needs API-specific wrapper classes, including signature types, not only a conditional inside a shared anonymous class. Rejecting an operation does not remove its class-linkage prerequisite. |
| Descriptor, resolver, geometry, views and accepted `OwnerLifecycleV2` call `List.copyOf`; resolver calls `Map.copyOf`; geometry/views/core use `List.of`/`Map.of` | Copy factories are API 31; `of` factories are API 30. [List](https://developer.android.com/reference/java/util/List#copyOf(java.util.Collection)), [Map](https://developer.android.com/reference/java/util/Map#copyOf(java.util.Map)). | API 28–30 also needs a Java-library compatibility decision. The inspected native/generated D8 calls have `--min-api 28 --lib android.jar`, without an explicit library-desugaring configuration at those call sites. That command alone supplies no execution proof. |
| `Typeface.create(Typeface, weight, false)` and `TextView.setFallbackLineSpacing(true)` | Both are API 28. [Typeface](https://developer.android.com/reference/android/graphics/Typeface#create(android.graphics.Typeface,%20int,%20boolean)), [fallback line spacing](https://developer.android.com/reference/android/widget/TextView#setFallbackLineSpacing(boolean)). | These named calls do not force a later baseline. They still need real shaping/weight/coverage evidence. |
| Body-size conversion uses `TypedValue.applyDimension(SP,17,metrics) / applyDimension(DIP,1,metrics)` | `applyDimension` is API 1. Nonlinear font scaling must use platform conversion, not a `fontScale` equation. [TypedValue](https://developer.android.com/reference/android/util/TypedValue#applyDimension(int,%20float,%20android.util.DisplayMetrics)), [Configuration](https://developer.android.com/reference/android/content/res/Configuration#fontScale). | Keep the actual window metrics, finite/range checks, twelve anchors and ties-up selector. Do not replace conversion with `scaledDensity`, a uniform multiplier or a fabricated curve. |

The installed-appearance restrictions are separately intentional unfinished
behavior. `InstalledAppearanceV2.capture` validates the complete canonical ≤64KiB
descriptor and both themes, then rejects every nonempty resource catalog and any
bundled font in either theme, including an unused declaration/unselected platform.
`AppearanceResolverV2.validate` and the Swift `AppearanceResolutionV2` validator
reject `boldText` or `increasedContrast`. These are not missing Android symbols
and an SDK guard cannot implement them.

## Exact observations without invented values

Use an internal immutable availability-bearing observation; it is **not** an
`AppearanceResolverV2.Environment`, a native capture, a readiness token or build
support. Suggested shape: `Observed<T>(status, value, reason)`, where status is
`KNOWN`, `UNAVAILABLE_API`, `UNAVAILABLE_SEMANTICS`, `UNDEFINED` or `READ_FAILED`.
Only `KNOWN` carries a value. No serialized schema or public Swift API is selected.
An absent API must never use numeric zero/boolean false as its value.

| Observation | API 28–29 | API 30 | API 31–33 | API 34–35 | API 36+ reviewed surface |
| --- | --- | --- | --- | --- | --- |
| Window resources, explicit night mask, resolved direction, first locale, metrics/body conversion, root/window identity/size | Read actual values; reject undefined/malformed/unavailable data | Same | Same | Same | Same |
| Exact safe-area source `systemBars \| displayCutout` | `UNAVAILABLE_SEMANTICS`; retain raw legacy readings only as labelled diagnostics | Typed query available | Same | Same | Same |
| Font-weight adjustment | `UNAVAILABLE_API` | `UNAVAILABLE_API` | Read, preserving undefined sentinel | Same | Same |
| System contrast | `UNAVAILABLE_API` | `UNAVAILABLE_API` | `UNAVAILABLE_API` | Read finite documented value | Same |
| High-contrast text | `UNAVAILABLE_API` | `UNAVAILABLE_API` | `UNAVAILABLE_API` | `UNAVAILABLE_API` | Read actual boolean; register actual listener |
| Animator preference | Read exact documented setting; missing/denied/invalid is unavailable, not 1 | Same | Same | Same | Same |
| Admitted V2 environment under unchanged visual-accessibility requirements | Rejected | Rejected | Rejected | Rejected | Candidate only after complete known neutral context and existing native checks; no new qualification claimed |

For API 28–29, legacy `getSystemWindowInset*` may include IME and other windows,
whereas `Type.systemBars()` excludes IME. Display-cutout dispatch semantics also
vary with window policy; a null legacy cutout is not sufficient proof of no cutout.
Do not apply a `max(legacy,cutout)` approximation or subtract guessed IME sizes and
call it the V2 safe area. This inference follows from the documented query
definitions, not a device experiment. [Legacy insets](https://developer.android.com/reference/android/view/WindowInsets#getSystemWindowInsetBottom()),
[typed masks](https://developer.android.com/reference/android/view/WindowInsets.Type#systemBars()).
An exact pre-30 safe-area implementation needs a separately selected window/IME/
cutout policy and native evidence; this proposal leaves that gate closed.

Proposed normalization rejects a night mask other than explicit YES/NO, an invalid
resolved direction, empty/invalid locale, nonfinite/out-of-range density/body,
unavailable insets, or missing/invalid animator preference. Font adjustment must
be known zero; undefined is not zero. Contrast must be finite, in −1…1 and exactly
zero; other values remain unsupported. High contrast must be known false. Motion
must be a known finite nonnegative setting, with zero mapping to reduced motion.
These are proposed stricter admission rules, requiring root selection. Current
source instead treats every non-YES night mask as light, accepts the undefined
font sentinel, rejects only positive contrast, and uses animator default 1.
This packet records those source facts; it neither rewrites them nor retroactively
describes them as complete accessibility evidence.

## Recommended first implementation, if root selects it

**A: isolate actual environment observations while preserving closed pre-36
admission.** This is useful source work with a finite acceptance boundary, rather
than a promise of API 28 rendering. Future ownership should be limited to:

| Proposed owned path | Selected behavior required before editing |
| --- | --- |
| New `native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java` | One concrete public-API reader and listener adapters. Base surface uses only API-28-safe types. Nested separately emitted `Api30`, `Api31`, `Api34`, `Api36` classes isolate later method/field/signature types. Each is reachable only after a real `SDK_INT >= N` branch. A smaller SDK never instantiates, reflects on or links its later-only listener class deliberately. Exact verifier/class-loading behavior remains native-pending. |
| `NativeEnvironmentV2.java` | Delegate the same current-window reads and API-specific listener calls to that boundary. Keep `Observer` the only eight-slot lifecycle owner and sole capture mint. Preserve the constructor pre-36 rejection, real main-Looper checks, registration order, retirement, exact retained targets, uncertain acquisition/removal handling and second complete synchronous read. Apply proposed stricter undefined/read-failure policies only as explicitly selected above. |
| New bounded platform-observation host tests/leaf closure and runner under `native/android/tests/` | Compile actual reader/observer sources against separately authored finite leaves. Assert which API branch was entered and the exact unavailable result. Never substitute a translated lifecycle model or allow caller-crafted observations to mint captures. |
| `cli/Sources/MixerBuild/AndroidSDKCompatibility.swift` and focused admission tests | Root selects a new immutable source-pair profile including the new Java file and edited observer identity. Preserve historical profile receipts. Reject old/changed/recomputed locks before tool/output access through both common CLI and rendered driver; use the one compiled policy authority. No profile ID is chosen in this proposal. |

The proposed listener boundary returns an API-28-safe internal registration
handle; its implementation privately retains the exact platform manager,
listener identity and executor. Observer still records possible ownership before
calling add, and still attempts disposal after a throwing add. The handle must
be available to that cleanup even when add reenters/throws; never hide acquisition
inside a factory that can throw before returning its disposition handle. Remove
through the retained target exactly once. Every callback reaches the existing
observer main-thread/retirement barrier; no second generation, sink, Handler,
readiness observer, fallback root or listener ownership state machine is added.
All eight sites exist for the still-admitted API 36+ observer. A direct diagnostic
snapshot on older SDKs is read-only, makes no subscriptions, and cannot start an
owner/coordinator/session or grant `ready()`.

Keep `NativeRenderer`'s independent API-36 guard and the private V2-only root
ownership restriction. `MixerActivity` stays on its current V1 path. No changes
to the owner core, coordinator commit interval, JNI, Swift state, descriptor,
wire format, installed capture, renderer/view implementation or public routing
belong in A. If implementation reveals one is required, stop and amend the
contract before dependent edits. Root coordinates its metadata and delivery.

Before A is implemented, root must choose the exact source closure/profile and
the stricter-read policy, then independent review must approve that candidate.
This packet authorizes neither implementation nor selection. No dependency is
needed for the proposal or the recommended reader isolation.

## Later prerequisites for actual API 28–35 rendering

1. Resolve visual-accessibility observability/behavior explicitly. The public
   surface reviewed here supplies no high-contrast read/change pair below 36,
   weight adjustment below 31 or system contrast below 34. No hidden API,
   undocumented settings key, test-only override, configuration default, caller
   declaration or previously observed setting proves a current native preference.
   A different platform-rendering strategy would need its own shared appearance
   contract, implementation and native accessibility/parity evidence; it is not
   selected here. Merely adding an `unknown` enum cannot make unknown admissible.
2. Resolve the exact pre-30 safe-area semantics described above.
3. Select Java-library compatibility for the actual closure, including the
   accepted core. Prefer independently authored API-28-safe snapshot helpers or
   replacements using public platform collections, preserving immutability after
   source mutation, element order where specified, null rejection and identity
   contracts. Never swap `copyOf` for a live unmodifiable view. Changes to core
   bytes require explicit coordination/review despite equivalent intent. A
   dependency/desugaring alternative needs an explicit pinned provenance and
   build-tool decision, THIRD_PARTY entry and demonstrated emitted/runtime
   behavior; no such dependency is introduced or assumed here.
4. Select one API-28-safe editor boundary, splitting base, API31, API33 and API34
   wrappers. Keep identical operation/mutation authority and stale-IME checks on
   every dispatch and delegate return; reject content, correction, replace,
   handwriting and private commands as today. Review inherited default methods
   per API so dispatch cannot bypass rejection. Do not backport a newer method
   by invoking an absent `super` method. On API28 reject fields and selectable
   text until authored cursor/selection appearance is implemented through public
   supported APIs and qualified; do not silently expose default handles.
5. Add explicit pre-30 required `accessibilityValue` rejection, or separately
   implement native equivalent semantics with TalkBack evidence. Do not substitute
   the label or append value text as a guessed semantic equivalent.
6. Only after those contracts are implemented/reviewed may root select changes
   to both SDK guards and private admission. Public Activity routing is a further
   distinct selection requiring its inset ownership, saved-state continuity,
   input/navigation/accessibility and parity gates. No silent V1 fallback is
   allowed when a requested V2 context is rejected.

## Fail-closed support matrix

This proposal adds **zero** admitted rendering contexts. “Available” above means
a named platform read exists, not tested support. The following restrictions
remain mandatory for a future compatibility candidate:

| Case | Required disposition |
| --- | --- |
| API below 28, or API28–35 with any required observation unavailable/undefined | Explicit `unsupportedNativeOperation` through existing owner failure/cleanup; never construct a successful Environment, start a substitute owner or retry in V1. A bounded internal diagnostic can retain the exact unavailable reason. |
| Known nonzero weight, high contrast, nonzero system contrast, unknown/unsupported accessibility transformation | Reject until actual native/shared behavior is implemented and reviewed. No ignore, weight synthesis, color remapping or false booleans. |
| Valid reduced motion on any SDK | Preserve known preference; this recipe has no timed animation. This does not qualify TalkBack, focus order or native behavior. |
| Missing descriptor; oversized/noncanonical/malformed descriptor; invalid unselected theme/catalog | Preserve existing specific decode/byte/resource failures before native preparation. No default descriptor at runtime. |
| Any resource declaration, including unused image/font, valid bytes, wrong bytes or missing bytes | Existing native slice rejects the entire catalog after semantic validation. No image placeholders, system icons, network fetch, default substitution or resource path access as a support shortcut. |
| Bundled font in either platform theme, including unselected theme and any fallback policy | Reject. SystemSans in both themes with an empty complete catalog is the only current admitted source policy. Do not silently convert bundled/fallback:none to systemSans. |
| Future declared font support | Separate immutable installed-byte capture, digest/identity/weight/style/coverage and native shaping contract first; wrong/missing face/glyph fails unless a declared implemented fallback covers it. No synthetic weight or undeclared fallback. |
| API28 field/selectable text or pre30 required accessibility value | Explicit rejection before native preparation until the separately reviewed behavior exists. The proposal does not claim this preflight is implemented today. |
| Existing unsupported node/layout/row/navigation/rich-text/IME operation | Preserve existing rejection and exact transaction/terminal behavior; compatibility cannot weaken it. |
| Read/add/remove/attach failure, uncertain native effect, linkage error or fatal error | Preserve terminal sealing, independent cleanup ledgers and fatal precedence. No broad catch that converts uncertainty to known neutral observations or ordinary accepted edits. |

Unknown means unavailable to this implementation, not “the user has disabled it.”
The current systemSans policy explicitly permits native script/emoji fallback,
with platform-specific shaping/rasterization differences. It does not qualify
every glyph, font weight, IME or accessibility context automatically.

## Owner, source-profile and verification obligations

Preserve the accepted owner lifetime, scalar terminal fence, exact drain/work
identity and synchronous input/no-replay policy. Dirty notification closes actual
current/pending gates before external work. Stale delivered callbacks do not read,
increment, dispatch, refresh or register. The real observer remains the capture
authority bound once to its renderer; forged pure data is never admission proof.
Safe area is intersected with the actual root once, after obtaining an exact
window source. Refresh retains the same committed packet and Swift revision,
without feature execution/effects. No callback, native setter, capture, allocation
hook or API adapter call may enter the successful `commitV2` → `finishV2` interval.
Terminal cleanup stays outside active nonreentrant coordinator operations, and
returned removals/close calls do not imply physical reclamation.

Required future tests are bounded by these concrete obligations:

| Gate | Finite required evidence |
| --- | --- |
| Actual host source + API leaves | SDK28,29,30,31,32,33,34,35,36 boundaries; lower-API branches never enter newer read/listener methods; unknown has no value; no creator can mint capture/support from diagnostics; known/undefined/read-failure cases for each source; fresh second-read mismatch; all actual observer acquisition/removal/fatal/reentry controls retained. |
| Environment rejection | Contrast −1/0/+1, NaN/infinities/out-of-range; font zero/nonzero/undefined; night YES/NO/undefined; missing/denied animator, zero/nonzero/negative/nonfinite; malformed locale; null insets; zero/unattached/stale root; range/ties across all twelve body anchors. Default-free reads do not become known neutral on failure. |
| Source-pair migration | Exact new files/digests; common CLI and direct driver positives; old/missing/recomputed/edited lock, copied SDK/adapter and descriptor negatives before tools/output; changed core only if separately selected. No auto-refresh. |
| Library/editor later slices | Mutation-after-copy/null/order/identity cases; exact emitted linkage inspection; per-SDK wrapper factory selection; stale focus/selection/composition and returned delegate scopes; explicit unsupported fields/values/extensions before mutation. These are later requirements, not executed tests here. |
| Native compiler | Exact pinned official SDK/JDK/D8/Swift/JNI producer and independent consumer evidence after source selection, including class signatures/linkage and old-API library resolution. Not run by this proposal; compilation cannot establish runtime support. |
| Android native effects/runtime | When authorized: real class loading on representative API28–35 and 36, same target root/metrics/insets, keyboard/show-hide/cutout/rotation/multiwindow, preference changes, partial listener acquisition/removal, terminal setters, stale IME/input/draw/accessibility and actual cleanup. No inference from host leaves. |
| Final public/product | Physical low/midrange/Pixel/Samsung/tablet matrix; TalkBack roles/actions/focus; separate iOS/Android design-parity review; saved-state/process recreation/back; immutable published packages consumed by separate-repository FieldLog; signing/store/operations/accountable GA evidence. All pending. |

The [offline checker](../verification/android-api28-v2-support-prerequisite/check_packet.py)
checks the frozen source identities/snippets, official finding IDs/API floors,
complete per-SDK observation matrix, retained rejections and pending-gate flags.
It includes in-memory negative controls for a forged neutral pre-36 observation,
invented pre-30 insets equivalence and an enabled public/release flag. These are
source/specification consistency checks, not product behavioral tests. No regex,
snippet match, host pass or manifest can authorize OTA or public V2.

The [receipt](../verification/android-api28-v2-support-prerequisite/receipt.json)
records exact offline commands, Python version, stdout/stderr and scope; the
[manifest](../verification/android-api28-v2-support-prerequisite/manifest.json)
seals this document, checker, findings, source index and frozen inputs. Computer
use, capture, native simulator/emulator/UI tests and process inventories remain
paused; phones remain disconnected. No native compiler/runtime/process inventory,
Git command, dependency/credential change, publication or customer action occurred.
