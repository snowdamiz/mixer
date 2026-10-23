# Baseline observations and design review boundary

The producing agent inspected the eight original PNGs with `view_image` after
native simulator capture. Tool previews were reduced to 942×2048 for display;
the retained native PNGs remain unchanged at 1206×2622. This is agent visual QA,
not accountable human acceptance or a numeric extraction of SwiftUI metrics.
All four fixture pairs show readable content within the initial portrait view.
The typography fixture's last row intentionally has `maxLines=2` and shows native
ellipsis. The ZStack uses a base VStack with a blank text row and an overlaid
caption so the two children remain legible; it is not a general overlay test.

Observed baseline features in this exact simulator/runtime:

- Native navigation presents a large bold title. Native List presents rounded
  grouped surfaces, row separators, and prominent section headings.
- Normal and cancel button labels appear blue, destructive appears red, and the
  disabled button is visibly dimmed. This records roles in a List context.
- Native checked toggles appear green; unchecked/disabled switches preserve the
  current toolkit appearance. Native field placeholder and value are distinct.
- Body/headline/title/caption have visibly different native semantic hierarchy.
  The `.disabled` text row remains ordinary-looking; this is current output,
  not evidence for a desired shared disabled-text recipe.
- The Arabic fixture reads from the right, its title/section/content align right,
  and its switch is at the left of the Arabic label. Accessibility-medium is
  observed as SwiftUI `accessibility1` and native category
  `UICTContentSizeCategoryAccessibilityM`. The larger content remains visible.

These observations differ from proposed `sharedCandidate1` choices in ways that
need explicit root token review: the proposal uses accent for a checked toggle,
caption for section headings, a fixed title recipe for app navigation, and
explicit list/control geometry. Those candidate recipes are design choices; they
were not measured from this Apple output, and this reference does not approve
them as an existing iOS match. No RGB, type-size, corner, row-height, padding,
hit-target or node-position measurement is claimed. Labels mentioning gaps 8/16
describe explicit fixture document properties, not measured pixel distances.

The eventual Apple and Android adapters must both consume the same explicit app
theme. Capturing today's implicit Apple appearance establishes a review baseline;
it neither authorizes platform defaults as the shared solution nor qualifies a
candidate renderer. Accountable root/human design review is pending, as are
physical iOS/Android side-by-side parity and every specified native, signing,
store, customer, operational and GA gate.
