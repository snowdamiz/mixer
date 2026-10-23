# Shared text profile data

The next shared appearance recipe uses twelve coordinated size profiles instead
of multiplying every text role by one scalar. `UISharedTextProfileV1` supplies
the accepted iOS reference sizes and weights for body, headline, document title,
caption, section header and expanded navigation title. Buttons and toggle labels
use body. Compact navigation remains a separate recipe decision.

The numeric source is the twelve Debug/Release observations retained in
`verification/apple-appearance-font-profile/type-profiles.json`. Root accepted
those reference tables in `verification/apple-appearance-font-profile-root-review/acceptance.json`.
Section-header headline is the shared authored role supported by the bounded
contextual font comparisons; equivalence in every native context is not claimed.

`UISharedTextProfileSelectionV1.nearest(preferredBodySize64:)` accepts a converted
body preference in logical 1/64 point/dp units. It chooses the nearest body anchor,
with exact midpoint ties going upward. The supported interval is 14 through 53
points, inclusive. Values outside it throw `unsupportedBodySize`; there is no
silent cap. A selected profile resolves every role together. An adapter must
perform its separately verified native preference conversion before selection,
then apply the resulting size once. Native density is a separate conversion.

Metrics deliberately contain no universal line height or clipping box. The
observed first-line box and repeated-line advance are distinct and depend on
native shaping. Content must retain room for script/emoji fallback and wrapping.
The existing explicit system-sans policy does not redistribute Apple fonts.

This additive data API does not modify the closed appearance-v1 descriptor,
canonical default bytes or resolver behavior. It does not install a measured
recipe in either renderer. Versioned descriptor integration, Android preference
conversion, shared control/group shapes and paints, native input/accessibility,
physical side-by-side review, signed presentation and all GA gates remain open.
