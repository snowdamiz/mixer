# mixer implementation rules

The binding product scope is `mixer-product-plan.md`. `PLAN.md` indexes execution;
it does not replace or narrow that scope. Keep `STATUS.md`, `work-graph.json`,
`gates/`, and `verification/` current with observed evidence.

## Ownership and execution

- Independently implement all product engine code. No Patch/Skip implementation,
  generated source, tests, fixtures, or dependencies. Official specifications and
  platform tools are permitted. Record general-purpose dependencies in THIRD_PARTY.yml.
- The user resumed work on November 8 and restricts subagents to `gpt-6.1-sol`
  and `grok-4.7`. Use Sol 6.1 at `xhigh` for implementation, difficult review
  and blocker campaigns. Use Grok 4.7 only for easier, nonvisual tasks and reviews.
  This explicit selection supersedes the earlier Astra escalation model; preserve
  the finite campaign and independent-review requirements. Do not use fast mode.
  The main controlling model is selected by the user; a child does not change it.
- Aggressively test competing blocker hypotheses within finite resource/run bounds.
  Treat experimental numeric limits as hypotheses; preserve baseline failures,
  validation/capability safeguards and all active native/process/custody holds.
  After two failed approaches or two preparation-only cycles, launch the bounded
  escalation campaign. Each prerequisite must unlock a named executable test or
  integration; avoid endless accounting/review preparation without a decision.
- The November 9 user instruction authorizes removing development bottlenecks.
  Apply product-plan section 24.5: use standard tools and compact raw evidence
  for bounded development diagnostics. Do not require a new generalized controller,
  transitive artifact seal, universal result parser, or recursive review before
  every test. Keep concrete isolation/cleanup safeguards and all explicit holds.
  After two preparation-only cycles, change the experiment or implementation and
  run the smallest permitted discriminating test; another preparation campaign
  does not reset that count. Local app integration can use pinned public SDK
  checkout inputs while immutable published-package qualification stays pending.
  Unrelated CI failures, VM completion and final GA requirements do not block
  dependency-ready development. One independent slice review is sufficient unless
  a concrete new defect or changed contract requires another.
- Coordinate public contracts before dependent changes. Never edit another active
  lane's files without coordination. Do not undo user work.
- Each meaningful slice needs executable tests and accurate limitations. A skipped
  device, compiler, signing, store, customer, or operational gate is not a pass.
- Never use regex/syntax analysis alone to authorize an OTA release. Unsupported
  instructions, capabilities, UI operations, or security contracts fail closed.
- Use standard cryptography. Keep signing keys out of source and build workers.
- No production publication, messages to customers, destructive migrations, or
  credential changes are implied by implementation work.

## Verification

The user authorized periodic commits and pushes to `snowdamiz/mixer`; see PLAN.md.
Root coordinates pushes of coherent validated slices to `origin/main`, without
force-pushing or sweeping other agents' unfinished files into commits. Inspect CI
after pushes. Phones are disconnected until further notice: do not attempt new
physical-device runs or ask to reconnect; keep those checks explicitly pending.
The user's October 23 instruction accepts simulator/emulator tests as sufficient
to accept development slices and continue dependent implementation. Do not block
that progress on phones. Run the physical-phone matrix at final acceptance and
correct any differences then; preserve the actual environment in every receipt.
Keep simulator/emulator use bounded: normally one active test instance per native
lane. Reuse it, retire an obsolete owned instance before booting its replacement,
and shut down disposable test instances after evidence collection, including
failed runs. Record cleanup; preserve other projects' active instances and their
data. The user explicitly requested cleanup of unused simulators.

Before frontend-dependent Simulator tests, verify macOS Accessibility access
before creating or booting a device. On this macOS 27 host the pane is named
Device Control and Data Access; the requesting helpers are attributed to
`/Users/andreyyurlov/Applications/Acid.app`. Re-adding that exact app resolved
the observed denial; see verification/plan-continuation-2026-11-07/apple-accessibility-after-readd/receipt.json.
Fresh public trust checks remain required. If access is unavailable, keep that test
pending. Never quit or terminate Simulator.app while unrelated devices are
booted: even a newly owned frontend can shut them down. Use exact owned-device
UUIDs and individually owned windows for cleanup. A changed external baseline
is a cleanup failure; record it and coordinate recovery before further actions.

Direct user instruction on November 7 — “you can do native stuff, update
agents file” — resumes native simulator/emulator tests and related UI verification
and screen capture, superseding the previously supplied pause. Fresh bounded
owned builds and runtime attempts may proceed under the one-instance-per-lane and cleanup
rules above. Preserve other projects' processes, devices and data, and keep
physical phones disconnected. This does not authorize probing, signalling or
retrying the specifically held historical processes, the held v5 startup, or
frozen hosted lanes. The October 24 shutdown and pause remain historical evidence.
Record fresh attempts separately in
verification/plan-continuation-2026-11-07/native-resumption.json.

The user subsequently resolved the conflicting pasted pause with “Keep native
testing resumed.” That explicit clarification governs new bounded native/UI/capture
attempts. Preserve the one-instance-per-lane, exact owned-device cleanup and
Accessibility preflight rules above. It does not release any specific historical
process, custody, v5, frozen-hosted-lane or physical-phone hold.

The cache deadline control's optimized run left unresolved custody for PGID
23663. Preserve that group and its retained scratch; do not probe, signal, or
retry it, and do not infer absence from the direct child's return or elapsed
time. See verification/plan-continuation-2026-11-07/cache-deadline-custody-hold/receipt.json.
The Android controller host controls also left PGIDs 40708, 40709, and 40711
with unresolved custody. Preserve both retained scratch directories; do not
probe, signal, or retry these groups. The receipt is
verification/plan-continuation-2026-11-07/android-controller-custody-holds/receipt.json.
All earlier process and custody holds remain in force.

The cache R4 test adapter stopped with UNKNOWN during launch/pipe setup before
recording any inner PID or PGID. Preserve its direct-control scratch without
inspection, cleanup or retry; no process absence is inferred. The exact held path
and launch record are in
verification/plan-continuation-2026-11-07/cache-custody-actual-controls-fix-r4/HOLD.json.
Outer command custody does not release this inner hold.


The fresh iOS setup and adoption failures remain preserved. Root's separately
selected recovery positively observed owned simulator
`4CE0ECC9-1EDA-4543-80FF-9B011DF9044F` Shutdown, deleted only that disposable
device, and verified the external device baseline unchanged with both protected
devices Booted. See verification/plan-continuation-2026-11-07/apple-adoption-recovery/attempt-1/result.json.
No iOS test instance remains owned by that experiment. Do not resume either old
one-use reservation or quit the shared Simulator frontend. The keyboard-readiness
successor owns preparation for the one remaining original XCTest attempt; root
coordinates any newly reviewed disposable instance. The failed setup/adoption
receipts remain historical failures; all earlier process holds remain active.

Record command, tool version, source revision/tree digest, output, and scope.
Mac unit tests are not physical iOS/Android receipts. FieldLog must eventually
consume immutable published packages from a separate repository. Local checkout
debugging is not dogfood release qualification. Never mark a GA gate verified
without its specified evidence and accountable reviewer.

The resumed root repository-observation wrapper failed while persisting its log
directory, before a reliable inner identity/scratch receipt was saved. Preserve
the uninspected `/tmp/mixer-resume-inspect-*` namespace; do not enumerate, probe,
signal, clean up, or retry it. See
verification/plan-continuation-2026-11-07/resumption-2026-11-08/inspection-HOLD.json.
The later explicit resume does not release this or any historical custody hold.

The resumed CLI containment probe disproved shared-group containment. Preserve
inner PGIDs 76556, 76573, 76598 and bootstrap PGIDs 54277, 76155 without
probing, signalling, retrying, or cleaning their retained scratch. Exact paths
and limitations are in
verification/plan-continuation-2026-11-07/store-full-suite-containment-r4/HOLD.json.
Full CLI87 remains unrun; outer custody does not release these holds.

FieldLog filtered transport R3 left UNKNOWN nested Git custody after Xcode
bypassed the adapter. Direct Xcode PID/PGID 52096 is recorded terminal, but no
inner Git identity or absence proof exists. Preserve the exact retained paths
and the uninspected automatic xcresult listed in
verification/plan-continuation-2026-11-07/fieldlog-filtered-transport-r3/HOLD.json.
Do not inspect, probe, signal, retry, or clean this held build namespace.

The profile10 host-entrypoint campaign was interrupted after its inner A/B
commands completed. Outer custody is UNKNOWN for PGID 87240. Preserve
verification/plan-continuation-2026-11-07/profile10-host-entrypoint-r1/outer-2/scratch
without inspection, probing, signalling, retry or deletion. See the exact
OUTER-HOLD.json in that campaign directory. Inner receipts do not release it.

The profile10 host-entrypoint review introduced UNKNOWN custody during a missing-executable launch before an inner identity was recorded. Preserve its workflow-files/scratch namespace without inspection or process operations; see verification/plan-continuation-2026-11-07/profile10-host-entrypoint-review-r1/REVIEW-HOLD.json.

The CF phase packaging continuation has UNKNOWN inner custody with no recorded identity. Preserve verification/plan-continuation-2026-11-07/mainactor-cf-phase-validation-package-r2/package-completion without inspection, probing, signalling, retry or cleanup. Its terminal outer PID/PGID1022 does not release the inner hold; see that campaign's HOLD.json and handoff.json.

The CF phase controller R4 validation was interrupted with UNKNOWN custody for
managed PID/PGID 35671 and uncollected primary exec session 87367 (primary PID
not recorded). Preserve both retained campaign namespaces without inspection,
probing, signalling, retry or cleanup:
verification/plan-continuation-2026-11-07/mainactor-cf-phase-controller-r4/campaign-1/scratch
and verification/plan-continuation-2026-11-07/mainactor-cf-phase-controller-r4/campaign-1/normal.
Do not poll session 87367 or reuse its campaign/deadline. See the exact
mainactor-cf-phase-controller-r4/interruption-HOLD.json and handoff. A later
receipt or terminal outer result does not release this hold. No native attempt
was consumed; fresh separate work does not authorize touching this chain.

The isolated CF R7 review supervisor blocked the pinned custodian’s DEVNULL setup and recorded UNKNOWN before an inner PID/PGID was saved. Preserve verification/plan-continuation-2026-11-07/mainactor-cf-r7-isolated-final-review/campaign/scratch without enumeration, stat, reads, probing, signalling, retry or cleanup. The exact record is that review’s campaign/HOLD.json. Its terminal outer transport does not release inner custody. A separately selected fresh root-owned review may use the unchanged pinned custodian, but must never resume or inspect this held chain.

Native CF R7 dispatch is blocked by the reproduced constructor-time CPython automatic-finalizer path after UNKNOWN. Its 336-test component passes and adopted host proof remain historical accepted host evidence, but the prospective root review is now REQUEST_CHANGES. See verification/plan-continuation-2026-11-07/native-custodian-finalizer-premise-r1/REPORT.md and cf-r7-composite-host-acceptance.json. Use only a fresh, independently reviewed explicit inert-finalizer process-adapter successor with the named constructor/unwind/exit control and fresh root admission. Do not consume or reuse the R7 one-use proposal. This does not pause other authorized native lanes or release any historical hold.


The root generated-Swift version control failed while flushing its command log after launching PID/PGID60657. Terminal custody is UNKNOWN. Preserve verification/plan-continuation-2026-11-07/generated-swift-version-control-r1 and its scratch without inspection, probing, signalling, retry or cleanup. No compiler-output or process-absence conclusion follows. See that namespace’s HOLD.json. The exact missing commands-directory preparation is a root wrapper defect; no historical hold is released.


The actual source113-da six-consumer run stopped at debug-create with UNKNOWN custody for PID/PGID96620 after the live receipt scanner raised Inner evidence entry limit. Preserve verification/plan-continuation-2026-11-07/source113-da-six-consumers-r1/generated-java-owned-st_rkc95 and verification/plan-continuation-2026-11-07/source113-da-six-consumers-r1/inner-cli/011-debug-create-kp8uqg95 (including tmp) without inspection, enumeration, stat, probing, signalling, waiting, retry or cleanup. Additional inner identities remain unobserved; do not read the held tree to recover them. Only the already persisted top-level run receipts/command metadata may be read. Outer terminal custody does not release this hold. See source113-da-six-consumers-custody-hold.json and source113-da-six-consumers-root-r1/HOLD.json.

The CLI receipt-layout R4 premise campaign stopped with UNKNOWN during Popen setup after its payload guard rejected /dev/null, before an inner PID/PGID was recorded. Preserve the entire verification/plan-continuation-2026-11-07/cli-receipt-layout-premise-r4 namespace without inspection, process operations, retry or cleanup. Only the explicitly supplied top-level HOLD.json custody metadata remains a permitted reference. Outer exit74 does not release this hold. A separately selected R5 campaign uses a new namespace and does not retry the held chain; see verification/plan-continuation-2026-11-07/cli-receipt-layout-root-selection-r5.json.

The CLI receipt-layout R5 independent review left UNKNOWN custody for PID/PGID81662 after its Node outer observer failed to establish group absence. Preserve the entire verification/plan-continuation-2026-11-07/cli-receipt-layout-review-r5 namespace and scratch without further inspection, process probing, signalling, waiting, retry or cleanup. Its delivered top-level final custody/review metadata is historical reference only; no test payload ran. Direct child exit1, both EOFs and closed descriptors do not establish group absence. See that campaign's delivered HOLD.json. Root review completion uses a separate R6 namespace and the admitted custodian directly, not the failed Node observer.


The root source0647 full Python CI validation exited 74 after installed source/entry admission passed. Outer PID/PGIDs 80712 and 80713 are recorded terminal, but the unit worker may have retained inner ownership without an identity recorded at root. Preserve verification/plan-continuation-2026-11-07/cli-source0647-canonical-adoption-r1/validation-r1 in full without inspection, probing, signalling, retry or cleanup. Its outer custody does not release the potential inner hold. Use only the copied top-level summary verification/plan-continuation-2026-11-07/cli-source0647-unit-validation-hold.json for fresh independent source-only diagnosis; no held log or scratch access is authorized.

The hosted source303 cache focused controls in run 42666503150, job 129331452787, recorded UNKNOWN descendant custody after EPERM, with owned_group_gone=false and incomplete pipe EOF facts. Preserve that exact hosted command group and its retained scratch; do not retry, probe, signal or clean it, and do not infer absence from the direct child return or later GitHub job cleanup. Root has only the copied top-level diagnosis in verification/plan-continuation-2026-11-07/source303-cache-ci-diagnosis-r1/REPORT.md; use that summary for fresh source-only work. This hold is scoped to that command/resources and does not pause unrelated jobs or new isolated native development.

The fresh hosted cache controls in run 42697826753, job 129434287580, recorded
UNKNOWN custody for descendant PGID 1222 after EPERM while observing group
absence. Preserve that exact hosted command group and its retained scratch;
do not retry, probe, signal, wait on or clean those resources. The direct child
return and later GitHub cleanup do not release custody. The copied source-only
diagnosis is verification/plan-continuation-2026-11-07/cache-current-hosted-diagnosis-r34/REPORT.md.
This scoped hold does not pause independent native, source or other CI work.
