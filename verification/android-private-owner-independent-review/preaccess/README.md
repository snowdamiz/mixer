# Independent review: preaccess packet

This packet seals the review design before candidate access. It is not a product
test or an implementation acceptance. The product implementation, producer tests,
ConcreteHostLeaves and probe were not read. All source snapshots are the accepted
git-object baseline, never mutable checkout Android source.

`input-custody.json` identifies the instruction/scope/contract and baseline inputs.
`site-input-map.json` preserves all 184 V2 anchors and five V1 anchors, including
same-line calls and exact byte offsets. Candidate bindings and new-call inventory
remain unknown until root admission. `cases.json` contains 30 independent fault/
oracle families, 1,288 V2 baseline case rows and five separate V1 positives.
`packet-witness.json` is independently authored raw input; no decoder pass is
claimed. `clarification-opinion.json` records the additional contract review.
`commands.json` separates exact commands executable now from future command
templates requiring a literal-argv candidate addendum.

The design checker checks custody, roster anchors, row completeness and honest
status only. It does not run a product class. The exact-closure seal covers every
file below this directory except its manifest and deterministic manifest checksum
sidecar, plus `docs/android-private-owner-implementation-review-plan.md`. A later
candidate/addendum belongs outside this sealed directory. Handoff/check delivery
logs outside this directory are not extra sealed members.

All failed attempts are retained. An initial display helper assumed the frozen
amendment manifest's `files` was an array; it is a path-keyed object. That helper
failed before displaying its later multi-call summary. This was a reviewer data-
shape error, not a product finding. Its exact helper and observed failure are
retained under `attempts/001-roster-display.*`. Later design checks validate the
actual object shape and all 189 anchors independently.

No native/runtime/UI/capture/phone/process-discovery, network/install, frozen
hosted-lane access, product/profile/CI/root-metadata edit, commit/push or production
action occurred. All actual-subject tests, mechanical leaf audit/reuse admission,
candidate/new-call bindings, host regressions, SDK/D8/Swift-JNI and profile/consumer
qualification remain pending. No public V2, OTA or GA gate is promoted.
