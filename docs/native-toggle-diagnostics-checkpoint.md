# Native toggle diagnostics checkpoint

The original Android pointer matrix still passes all 429 assertions across twenty
actions. The additional component suite remains failed. Its repaired fixture now
preserves the original main-thread assertion instead of losing the process:
seventeen cases complete before `actual native ScrollView interception and CANCEL`
fails. The assertion counter is 85 including that failure, not 85 passes. Four
preview images, the result export and original stack are hash-bound. The cause of
the earlier crash remains unknown. A separate diagnostic candidate is investigating
delivery, scroll extent, timing and cancellation without changing product code or
weakening the original assertion.

The exact Apple candidate runs on iOS26.5. Coordinate taps reverse its selected
state once per event, and the simulator's exposed accessibility element activates
it correctly. Native held-touch state is observed. Explicit cancellation,
disabling and expiring the input gate during a hold prevent a release event;
disabled and stale fresh taps are also rejected. A dark RTL tap preserves authored
accessibility metadata and selected state. These are partial prototype results.

Two direct programmatic activation checks fail, and the subsequent deselection
check is vacuous because the first activation never selected. A horizontal CUA
drag follows the primary-action path without pan acceptance. The vertical probe
at scroll-top supplies no positive scroll evidence; Tab does not establish native
keyboard focus. Pressed-state screenshots serialize after release, so pressed
compositor paint remains unqualified. Static images were inspected in the
conversation, without a local numerical pixel comparison. A matched-toolchain
reference and diagnostic candidate are being prepared to distinguish runtime,
fixture and input-delivery effects.

Both owned native instances are stopped. The Apple simulator is deleted, its
owned frontend is absent and all four original device states are preserved. The
first cleanup poll rejected a transitional frontend identity after SIGTERM;
the original wrapper's retry verified absence. Android's owned process group and
ports are empty, and 184 extracted files totaling 172,984,832 bytes are removed.

No live native adapter is changed or newly accepted here. Full gesture, keyboard,
accessibility, compositor and adapter parity, physical phones, immutable FieldLog
releases and GA remain pending. Root receipts:
`verification/apple-authored-toggle-native-root-review/receipt.json` and
`verification/android-authored-toggle-supplement-root-review/runtime-review.json`.
