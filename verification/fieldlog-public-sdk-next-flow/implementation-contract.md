# Selected next FieldLog behavior

Implement a shared task-editor presentation owner in the separate FieldLog app.
The owner consumes only the existing immutable public MixerCore/MixerUI pin. It
authors the actual form document, accepts current validated UI events, preserves
exact input on validation/storage failure, disables edits/cancel during an
authorized save, and ends navigation only after confirmed durable save or an
unsaved cancellation. Replaying a stale render event or sending an event after
closure must reject before persistence.

The iOS app can immediately consume this shared owner while retaining its native
vertical title field. Replacing that field with the public single-line adapter
would reduce existing behavior. Public shared rendering requires a supported
multiline field and shared appearance integration; neither is silently replaced
by app-private engine access. The Android module/object build proves source
portability only. Android's current synchronous value-only reducer cannot host
the async fsynced repository, so native Android durable app integration requires
a public effect/persistence host seam.

## Canonical ownership requested

- `../fieldlog/Package.swift`
- `../fieldlog/Sources/FieldLogFeatures/TaskEditorPresentation.swift`
- `../fieldlog/Tests/FieldLogTests/TaskEditorPresentationTests.swift`
- `../fieldlog/ios/FieldLog/ProjectDetail.swift`
- `../fieldlog/README.md`

No Mixer engine source, generated JNI, private staging, schema, dependency pin,
storage schema, auth/backend, production publication or gate changes are needed
for this scoped behavior. Root selects the final file ownership before edits.

## Decisive executable checks

1. Real repository: empty valid project → routed Unicode/spacing-preserving form
   input → one authorized save → confirmed terminal navigation → close/reopen →
   exactly one task and pending local change, without fake network success.
2. Invalid title/responsible input: no repository callback, exact draft retained,
   field-correction/retry possible; the shared document shows validation failure.
3. Held save: disable title/responsible/save/cancel and reject a second submission
   from the current render; a storage failure restores editing and exact input.
4. Stale revision, stale identity, wrong event/value and closed owner: reject
   before mutation or save. Unsaved cancel never calls persistence.
5. Late result after close: no terminal-success/navigation update; no claim to
   roll back an already committed repository write.
6. Generic iOS source build and official Android arm64 module/object build only,
   serialized through root's shared compiler lane. No runtime, instances, UI
   automation, screen capture, physical devices or rejected v5 experiment.

## Acceptance boundary

This is native iOS app-source integration plus exact host behavior and Android
cross-compilation. It does not establish shared-rendered native Android behavior,
multiline adapter support, shared-theme/physical design parity, an immutable
release-package consumer run, any D0–D8 milestone, store/customer qualification,
interpreted/OTA parity or GA. Root must retain all those pending checks.
