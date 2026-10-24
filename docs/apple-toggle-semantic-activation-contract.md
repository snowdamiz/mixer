# Private Apple toggle semantic activation contract

This follow-on uses the exact pan-origin candidate accepted for thirteen real
native interactions. It is a new private candidate, with no live adapter change
and no alteration of historical source, checks, or evidence.

The completed direct replay shows that `performPrimaryAction()` invokes one
primary target without toggling selection, and direct `accessibilityActivate()`
returns false without dispatch, in both the authored carrier and plain UIKit
reference. The actual native taps pass. The prior assumption that calling
`super.accessibilityActivate()` itself supplies a selected-state transition is
therefore not a qualified implementation boundary on this simulator. Original
19/12 suites remain failed with their exact results.

Apple's [accessibility activation contract](https://developer.apple.com/documentation/objectivec/nsobject-swift.class/accessibilityactivate())
requires the implementation to activate the element and report success. Its
[primary action API](https://developer.apple.com/documentation/uikit/uicontrol/performprimaryaction())
dispatches the control action. Retained source snapshots and actual direct
observations are in `verification/apple-toggle-pan-origin-root-review/`.

## Selected private implementation

Keep the public UIKit UIButton as the native input, focus, keyboard, touch
tracking and accessibility element. Keep the authored paths, theme, geometry,
native pan recognizer, corrected admission, and preview/release behavior.
Disable UIButton's automatic selected-state toggling for this candidate with
`changesSelectionAsPrimaryAction = false`. Mixer owns the toggle's semantic
selected-state transition in the existing primary target. No custom input
injection, recognizer state assignment, private API or alternate accessibility
element is introduced.

Every admitted primary action proposes the inverse of the current retained
binding. It cancels an outstanding authored interaction, checks the current
binding generation and input gate, and updates the retained value and public
native selected state together. It emits exactly one value event only for an
accepted transition. Programmatic binding writes remain silent. Rejected,
disabled, stale or reentrant activation emits no value event and preserves the
latest legitimate binding. A binding change during callbacks cannot be undone
by restoring an older value. An input gate invalidation before value dispatch
cannot publish a stale event.

Accessibility activation checks admission, invokes the same public primary
operation, and returns true only if that invocation committed one transition.
It must not call a speculative superclass fallback and then toggle again.
Native taps and keyboard activation continue to use the same primary target;
actual native input evidence remains separate from direct callback evidence.
A direct call or a manually sent action does not qualify real VoiceOver or
keyboard delivery.

## Required verification before carrier acceptance

Retain the thirteen passing native interactions and all their original strict
predicates on the new exact app. Collect both directional primary and accessible
activation from independently established on/off state. Require selected value,
retained value, exactly one primary target and exactly one value event, plus
true accessibility return. For disabled/stale gates, both starting states and
both entry points must preserve value and emit none; accessibility returns false.

Exercise reentrant primary/accessibility activation, a callback that changes the
binding, a callback that closes the input gate, and accessible activation during
a held pan followed by release. Each test records actual state/event ordering and
the latest binding. Verify silent binding writes, stable native identity, selected
and disabled accessibility traits and authored metadata. A lifecycle or event
ordering assertion may not be replaced by a source-text check.

Retain the original direct diagnostic/reference output without changing its
historical assertions or turning reference failures into passes. A new scoped
semantic verdict must name its own candidate and requirements explicitly.
Full native no-change, cancellation, disable/stale retirement, focus/keyboard,
compositor parity and renderer integration remain required after this slice.
Physical VoiceOver and final physical-phone matrix remain deferred. No full
carrier, public route, FieldLog, store or GA acceptance follows from preparation.
