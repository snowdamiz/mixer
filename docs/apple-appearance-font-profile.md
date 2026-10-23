# Apple type profiles and contextual font candidates

The full 12-level native type table is now an executable input to shared recipe
review. A separate frozen derivative tests only explicit public font modifiers:
section header Text `.font(.headline)`, Button `.font(.body)` and Toggle `.font(.body)`.
Read the [receipt](../verification/apple-appearance-font-profile/receipt.json),
[raw type profiles](../verification/apple-appearance-font-profile/type-profiles.json),
[candidate comparisons](../verification/apple-appearance-font-profile/candidate-comparisons.json)
and [gallery](../verification/apple-appearance-font-profile/gallery.html).
Both previous appearance evidence sets, including the 359-artifact measurement
seal and its findings document, remain immutable.

## Full native type profiles

All 12 public SwiftUI DynamicTypeSize cases were selected through actual simulator
content_size preferences, separately in Debug and optimized Release. Each run
exports its observed SwiftUI size and native preferred category, public
`Font.resolve(in: fontResolutionContext)` values, CoreText metrics/traits, actual
public navigation-title UILabel UIFont properties, and native one/two-line text
geometry. The complete table uses the Typography fixture in light/LTR/en_US on
the dedicated iPhone 18 Pro simulator, iOS 27.0 24A434, 3× scale. Xcode 27.1,
iOS Simulator SDK 27.1 and Swift 6.4 built both variants. No physical device was
inventoried, used or requested. The local public SDK declarations establish the
12-case coverage and the iOS 26+ Font resolution API used by this harness.

Point sizes below are observations. Body/title/caption resolve regular (CoreText
weight trait 0), headline resolves semibold (trait 0.3), and actual expanded titles
use bold UIFont (trait 0.4). Names, cap/x heights, ascent/descent/leading and raw
trait values remain in JSON. Public `.largeTitle.bold()` has the same resolved
font name and point size as the actual largest title UILabel at every observed
preference. This is a measured source for the expanded-title recipe; compact
navigation behavior and glyph-level fallback remain separate.

| Shared profile proposal | Observed SwiftUI size | Body | Headline | Title | Caption | Actual expanded title |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| xs | xSmall | 14 | 14 | 25 | 11 | 31 |
| s | small | 15 | 15 | 26 | 11 | 32 |
| m | medium | 16 | 16 | 27 | 11 | 33 |
| l | large | 17 | 17 | 28 | 12 | 34 |
| xl | xLarge | 19 | 19 | 30 | 14 | 36 |
| xxl | xxLarge | 21 | 21 | 32 | 16 | 38 |
| xxxl | xxxLarge | 23 | 23 | 34 | 18 | 40 |
| a1 | accessibility1 | 28 | 28 | 38 | 22 | 44 |
| a2 | accessibility2 | 33 | 33 | 43 | 26 | 48 |
| a3 | accessibility3 | 40 | 40 | 48 | 32 | 52 |
| a4 | accessibility4 | 47 | 47 | 53 | 37 | 56 |
| a5 | accessibility5 | 53 | 53 | 58 | 43 | 60 |

The following is actual laid-out geometry for hidden fixed-size `Text("Ag")` and
`Text("Ag\nAg")`, with the four explicit semantic fonts in the current environment.
Each cell is **one-line height / added height for the second line**, in points.
Decimals abbreviate exact retained native values; thirds reflect 3× layout.
The probes receive no width constraint, truncation or line-spacing modifier.
They are hidden backgrounds, so the unchanged visible fixture remains the pixel
control. Their eight native sizes and complete geometry are exported per run.

| Profile | Body one / increment | Headline one / increment | Title one / increment | Caption one / increment |
| --- | ---: | ---: | ---: | ---: |
| xs | 17 / 19 | 17 / 19 | 30 / 31 | 13.333 / 13 |
| s | 18 / 20 | 18 / 20 | 31.333 / 32 | 13.333 / 13 |
| m | 19.333 / 21 | 19.333 / 21 | 32.333 / 33 | 13.333 / 13 |
| l | 20.333 / 22 | 20.333 / 22 | 33.667 / 34 | 14.333 / 16 |
| xl | 23 / 24 | 23 / 24 | 36 / 36 | 17 / 19 |
| xxl | 25.333 / 26 | 25.333 / 26 | 38.333 / 38 | 19.333 / 21 |
| xxxl | 27.667 / 29 | 27.667 / 29 | 40.667 / 41 | 21.667 / 23 |
| a1 | 33.667 / 34 | 33.667 / 34 | 45.667 / 46 | 26.333 / 27 |
| a2 | 39.667 / 40 | 39.667 / 40 | 51.333 / 51 | 31.333 / 32 |
| a3 | 48 / 48 | 48 / 48 | 57.333 / 57 | 38.333 / 39 |
| a4 | 56.333 / 56 | 56.333 / 51 | 63.333 / 61 | 44.333 / 44 |
| a5 | 63.333 / 62 | 63.333 / 62 | 69.333 / 68 | 51.333 / 51 |

Debug/Release font properties and all eight native line-probe sizes agree at every
preference. Font metrics and laid-out boxes are distinct data: for example, large
body has a 20⅓ pt one-line box and adds 22 pt for its second line. At accessibility4,
headline has a 56⅓ pt first line and adds 51 pt for the second. Its CoreText leading
is −5.087890625 pt; the native Text probe confirms the 51 pt increment rather than
requiring an inference from that metric. Other large roles also have increments
smaller than their first-line extent. **Do not reuse line advance as the minimum
first-line box.** The raw `metricBaselineAdvanceIncludingLeadingPoints` field is
the computed ascent+descent+leading reference; actual repeated-line increments
are independently measured in `nativeLineBoxProbes`.

This closes size, weight and native Latin line-layout inputs for these semantic
roles across the 12 preferences. It does not establish a universal box for Arabic,
emoji, combining marks, other fonts, baseline alignment with mixed scripts, or
arbitrary text. Actual shaping/fallback can require more height. Font profile data
must not become a clipping rule; adapters must grow to contain admitted text.
Bold Text, other accessibility settings and other OS/font versions were not
independently configured or qualified here.

## Bounded contextual candidate result

The candidate matrix compares entire decoded PNGs against immutable prior native
measurement PNGs. It covers Typography, Controls and Layouts at large, Arabic RTL
at accessibility-medium, and LTR Typography/Controls at accessibility-medium,
each light/dark: 12 Debug cases. Release repeats Typography light, Controls dark
and RTL light. Three candidate-disabled Debug controls (Typography light, Controls
dark, RTL light) protect nonperturbation of the new font export and hidden line
samplers. All use exactly the previous fixture bytes. No tint, color, spacing,
padding, list style, control geometry or other font recipe is changed.

All 15 candidate comparisons and all three unmodified controls have zero differing
pixels out of 3,162,132 per image. The explicit headline header and body control
fonts therefore preserve the observed output in this bounded matrix. Large and
accessibility1, LTR/Arabic RTL, light/dark, normal/destructive/cancel/disabled
buttons and on/off/disabled toggles are included where those fixtures contain them.
UITextField font modifiers were not part of this candidate; existing public field
font observations remain a separate input. The type table supplies the complete
public `.headline` and `.body` values, but native contextual equivalence at the
other ten sizes was not tested. A native default cannot be declared universally
headline/body from these fixtures. Root can explicitly adopt these as the app's
shared roles, with this coverage and remaining qualification stated.

## Proposed bounded shared normalization

Select **one of 12 shared profile IDs** (`xs` through `a5`) and resolve every role
from the selected profile together. Default `l` preserves the observed ordinary
sizes. Each profile needs distinct text roles for body/headline/title/caption,
expanded navigation and section header/control labels. The observed point-size
and line-increment table is the numeric input; recipe review must keep first-line
extent separate from line advance and account for native shaping. This is a
proposal, not a product/schema edit or an accepted cross-platform font family.

Apple's mapping is exact and direct: the observed native preferred category and
SwiftUI size map to the matching row. `normalization-proposal.json` retains all
12 native category strings. An app override may name a valid profile explicitly;
unknown/missing profiles must fail admission rather than silently extrapolate.

For a continuous host preference, a concrete proposed common policy is to select
the nearest **body-size anchor divided by 17**. Use a positive UInt32
`preferredBodyScale1024`, compare against exact rational anchors, choose the larger
profile at an exact midpoint, and clamp outside the first/last anchor. The resulting
ID selects every role's full metric tuple; the scalar never multiplies each role.
For example, body 17→28, title 28→38 and caption 12→22 cannot be reproduced by one
uniform multiplier. Executable policy checks cover all anchors, monotonicity,
clamping, the exact 1536 midpoint and invalid inputs.

For Android, propose observing the platform-converted **17sp body anchor** with
current window DisplayMetrics: divide `TypedValue.applyDimension(SP,17,metrics)`
by `TypedValue.applyDimension(DIP,1,metrics)`, validate finite positive results,
then round the ratio to 17 into `preferredBodyScale1024`. This is an app policy
inferred from the documented dimension conversion API; it has not been executed
on Android here. Android documents that `Configuration.fontScale` is informational
under nonlinear scaling and should not be used as a direct font-size equation.
The platform conversion preserves that boundary before the app selects its explicit
shared profile. See [Configuration.fontScale](https://developer.android.com/reference/android/content/res/Configuration#fontScale)
and [TypedValue.applyDimension](https://developer.android.com/reference/android/util/TypedValue).
No Android preference range, equivalent nonlinear curve, native font output or
accessibility parity is asserted. A native Android receipt must verify preference
conversion, rounding, environment-change handling and the resulting role metrics.

## Evidence and pending work

`capture-source-lock.json` records exact build/harness input hashes before build
and verifies the same bytes after native capture. Commands, tool versions, SDK
version versus runtime version, stdout/exit codes, app hashes, raw observations,
fixture equality and earlier seal checks are retained. `finish.py` tests the PNG
analysis and proposed normalizer and checks source stability. The final receipt
seals all retained artifacts plus this findings document. No outside-owned product,
schema, tracker, commit or push was made by this slice.

This provides bounded candidate matches and full Apple preference data for root's
next shared-recipe contract review. It does not approve native Android consumption,
common glyph/font resources, arbitrary contextual font defaults, physical iOS/Android
side-by-side design parity, native input/focus/navigation/accessibility behavior,
signed display/health, immutable published FieldLog, signing/store/customer/
operational qualification or any GA gate. Phones remain disconnected and those
checks remain pending.
