# FieldLog task form accessibility

Apply `fieldlog-552559d2-task-form.patch` to a FieldLog checkout at `552559d2d3278abb9b1aa7dcf0288102c09a202b`. Build FieldLog against the Mixer SDK containing the native section-header change. Run `FieldLogUITests/FieldLogUITests/testTaskFormSelectsFieldsByIdentifierAndSaves` on an owned iOS Simulator.

The test creates a project, fills the task title and assignee using their accessibility identifiers, saves, and checks that the task appears. The macOS hierarchy checks and exact build inputs are in the [host receipt](../../../verification/receipts/apple-integrated-section-accessibility-root-cjmN9HqN.json).

## Consecutive edits in the same text field

FieldLog editors that synchronously install each accepted value can opt in to `MixerNativeView`’s `trackSynchronousTextChanges` initializer. When SwiftUI invokes the same binding twice before the next render, the second edit uses the next revision only if the first edit installed its exact value and the rest of the document stayed the same.

Run the host regression on macOS from the Mixer checkout with a local FieldLog Git checkout containing revision `552559d2`. The script applies the [consumer patch](typing/fieldlog-opt-in.patch) in scratch. Its accessibility checks use the public form’s `task-title` and `task.responsible` identifiers and require macOS Accessibility access.

```sh
tests/integration/fieldlog-apple-section-accessibility/typing/replay-host.sh "$FIELDLOG_CHECKOUT"
```

The regression sends two consecutive values through the same binding, taps Add through the editor model, then reopens the real workspace. The opt-in path saves `Night shift`. It also checks that an unrelated render expires the binding and that stale events preserve current validation errors.
