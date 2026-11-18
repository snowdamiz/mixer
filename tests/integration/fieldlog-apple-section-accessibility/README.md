# FieldLog task form accessibility

Apply `fieldlog-552559d2-task-form.patch` to a FieldLog checkout at `552559d2d3278abb9b1aa7dcf0288102c09a202b`. Build FieldLog against the Mixer SDK containing the native section-header change. Run `FieldLogUITests/FieldLogUITests/testTaskFormSelectsFieldsByIdentifierAndSaves` on an owned iOS Simulator.

The test creates a project, fills the task title and assignee using their accessibility identifiers, saves, and checks that the task appears. The macOS hierarchy checks and exact build inputs are in the [host receipt](../../../verification/receipts/apple-integrated-section-accessibility-root-cjmN9HqN.json).
