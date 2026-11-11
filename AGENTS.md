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
- The November 10 user instruction requires maximum useful parallel work across
  ready product domains, not only the current platform. Apply product-plan
  section 25.3: refill free agent slots at completion or a blocker, isolate file
  ownership/output/cache paths, and serialize only actual shared-resource or
  dependency conflicts. Do not impose an arbitrary small agent count or blanket
  two-job compiler limit. Fit concurrent agents and builds to aggregate provider
  and host capacity. Root retains native-device ownership and all explicit holds.
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

Direct user instruction on November 10 — “you are allowed to use computer use and screen capture again” — resumes computer interaction, UI automation and screen capture for implementation and verification. Earlier general computer-use or capture pauses are historical. Apply the existing owned-device, Accessibility preflight and cleanup rules below; physical-phone restrictions and all specifically held processes, scratch and frozen lanes remain in force.

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

The root R118 broad VM regression timed out and then received EPERM while observing
process-group absence. PGID4463 remains UNKNOWN. Preserve the exact group and
`/Users/andreyyurlov/.t3/userdata/mixer-owned-command-r118-q3pzd_gl`, including its
retained target/scratch, without probing, signalling, waiting, retry or cleanup.
The direct Cargo exit -15 does not establish descendant absence. Its raw command
outputs remain preserved; only copied top-level command/HOLD metadata may guide
new work. See verification/plan-continuation-2026-11-07/owned-taskeditor-command-integration-r118/HOLD.json.
Static canonical VM source is outside this scoped hold; independent fresh tests
and app work remain authorized.

The root R125 worktree-add timed out before recording a reliable process-group
identity. Preserve `/Users/andreyyurlov/.t3/userdata/mixer-owned-command-delivery-r125-svgl7xu3`
and its incomplete worktree registration/locks in the R104 delivery bare database.
Do not probe, retry, delete locks or clean this exact chain. The short launcher
reaped its direct child after timeout; descendant custody remains unobserved.
Use the copied metadata in owned-taskeditor-focused-integration-r124/git-delivery-timeout.json.
This does not hold static canonical source or revision-pinned GitHub API delivery.

The separate FieldLog Pair18 consumer full checkout failed while persisting its final command receipt after a no-space error. Preserve PID/PGID 73726 and the entire `/Users/andreyyurlov/.t3/userdata/fieldlog-pair18-r184-l5oi5a4t/public-mixer` checkout chain without inspection, enumeration, probing, signalling, waiting, retry or cleanup. Read only the copied top-level `verification/plan-continuation-2026-11-07/fieldlog-public-pair18-consumer-r184/HOLD.json` and report as historical metadata. Available disk space or a terminal outer result does not release this hold. Fresh sparse public checkouts in separate namespaces remain permitted.

The hosted Swift Python controls in run 42833959617, job 129891063070, recorded UNKNOWN terminal custody for `javap-budget-overflow` in the javap stdout-ceiling control. Root has no reliable inner PID/PGID. Preserve that exact hosted command group and retained unit-worker scratch without inspection, probing, signalling, waiting, retry or cleanup. Only the copied top-level log/hold summary in `verification/plan-continuation-2026-11-07/swift-javap-overflow-hosted-hold-r190/HOLD.json` is a reference. A completed GitHub job does not establish inner absence. This hold does not block fresh isolated source controls or independent application/native work.

The R248 callback-matrix JVM timed out with UNKNOWN custody for PID/PGID 93286. Preserve the entire `/Users/andreyyurlov/.t3/userdata/mixer-root-screen-r248-ksv0fdtm` scratch and the R248 outputs `full-189-callback-matrix.stdout`, `observed-sites.txt`, and `barrier-cases.json` without inspection, enumeration, probing, signalling, waiting, retry or cleanup. Only the top-level `verification/plan-continuation-2026-11-07/owned-root-screen-removal-r248/HOLD.json` and separately delivered source patch/result metadata are references. A terminal outer result does not release this hold. Fresh source builds and native development in distinct namespaces remain authorized.

The fresh hosted cache job in run 42883750881, job 130066539843, recorded UNKNOWN custody for PID/PGID 1143 after PermissionError/EPERM in the descendant control. Preserve that exact hosted group and its recorded scratch without inspection, probing, signalling, waiting, retry or cleanup. Read only the copied top-level summaries and hold reference in verification/plan-continuation-2026-11-07/current-cache-ci-top-level-diagnosis-r310/REPORT.md. Child return and later GitHub job cleanup do not establish absence. The exact failing operation remains unproven; this scoped hold does not pause independent app/native work or fresh isolated source checks.

The R442 separate Apple consumer recorded three new UNKNOWN custody chains.
Preserve PID/PGID 22837, the entire
`verification/plan-continuation-2026-11-07/fieldlog-delivered416-apple-consumer-r442/work`
tree and its `public-identity.log`; read only the top-level `HOLD.json`.
Preserve PID/PGID 45310, the entire R442 `work-r2` tree, its
`r2-generic-ios-build.log`, and
`/var/folders/w6/vbftz74j4jzb2t9ry9r724g00000gn/T/ResultBundle_2026-10-11_17-22-0037.xcresult`;
read only top-level `HOLD-r2.json`. Preserve PID/PGID 64890 and the entire
R442 `work-r3` chain, including its bare repository, launch/result and raw
`r3-bare-init` outputs; read only top-level `HOLD-r3.json`.
Do not enumerate, inspect, probe, signal, wait on, retry or clean any of those
held chains. Direct child exits and unavailable process observers do not prove
absence. Existing copied host-test observations remain scoped evidence;
generic iOS build/resolution is incomplete. Independent source, Android and
other fresh work remain authorized; no historical hold is released.

The R492 pinned public-checkout Git archive timed out with UNKNOWN custody for
PID/PGID33305. Preserve that exact command, its retained
`verification/plan-continuation-2026-11-07/fieldlog-v4-system-bar-restore-r492/work-r2`
and `public-java.tar`, and the command's source-checkout chain
`verification/plan-continuation-2026-11-07/fieldlog-delivered416-android-consumer-r444/work/public-mixer`
without inspection, enumeration, probing, signalling, waiting, retry or cleanup.
Read only R492's top-level `HOLD.json` and separately delivered static artifact
metadata. The successful R492 build is in the separate `afterimage-build` namespace;
its terminal custody does not release the archive hold. Root's new native test
may use the exact delivered APK/source ZIP without accessing this held chain.

The R494 owned AVD cleanup timed out during avdmanager deletion after its cold-boot
preparation failed. The deletion child's identity was not persisted before the
30-second wait timeout; custody is UNKNOWN. Preserve the entire exact
`/Users/andreyyurlov/.t3/userdata/mixer-fieldlog-api36-r494-kbha57n_` target and
`verification/plan-continuation-2026-11-07/fieldlog-public-v4-os-ime-r494/delete-owned-avd.stdout`
and `.stderr` deletion outputs without inspection, enumeration, process operations,
waiting, retry or cleanup. Read only that campaign's top-level HOLD/ownership/result
metadata and static source. Emulator exit0 does not establish deletion-child absence.
No app installation or OS-IME payload ran. Fresh distinct namespaces remain permitted.

The R506 independent GuestUI review has UNKNOWN compiler custody for PID/PGID76976
and uncollected inner compiler resources despite terminal outer exec38931/exit74.
Preserve `verification/plan-continuation-2026-11-07/guest-ui-v2-independent-review-r506/source`,
its `scratch/candidate`, and `logs/candidate-build.stdout`/`.stderr` without
inspection, enumeration, probing, signalling, waiting, retry or cleanup. Read only
its supplied top-level HOLD.json, REPORT.md, receipt.json and logs/candidate-build.json.
No review test ran. Build-complete output, direct baseline return or elapsed time
releases neither this hold nor any older one. Fresh independent review may use
unchanged R486 inputs in a separate namespace.


The R580 local callback matrix timed out with UNKNOWN custody for PID/PGID45848. Preserve the entire `verification/plan-continuation-2026-11-07/native-editor-opacity-source-compose-r580/native-work`, `logs/B-matrix.stdout`, `logs/B-matrix.stderr`, `observed-sites.txt`, `barrier-cases.json`, and `helper-boundaries.jsonl` without inspection, enumeration, probing, signalling, waiting, retry or cleanup. Read only the top-level HOLD.json, callback-matrix-custody-hold.json, REPORT.md and delivered static application packet. The separately captured immutable afterimages and completed binding-preflight metadata are outside that mutable held chain. Root R598 native acceptance and independent R578 source review do not release it.

The R580 optimized source worker timed out with UNKNOWN custody for PID/PGID48537. Preserve `verification/plan-continuation-2026-11-07/native-editor-opacity-source-compose-r580/overlay/verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/control-scratch` and `logs/optimized-test_source113.py.stdout`/`.stderr` without inspection, enumeration, process operations, waiting, retry or cleanup. Top-level HOLD-source.json and source-worker-custody-hold.json are the custody references. A later fresh optimized-source pass does not release this worker; static inputs and separately captured afterimages remain available for fresh independent work. All older holds remain in force.

## Verification artifact retention

New build outputs, APKs, compiler dumps, copied checkouts and dependency trees
belong in ignored `verification/local/` or an owned external scratch directory.
Write new compact receipts under `verification/receipts/`. Existing tracked
fixtures and all custody holds remain protected. Historical reports may refer
to archived inputs: use `verification/README.md` to restore the corresponding
campaign before replaying an old driver.

Run `python3 scripts/check-verification-artifacts.py` after staging verification
changes. It checks the index, including sparse paths. New canonical fixtures
outside `verification/receipts/` require explicit `git add -f`; generated or
large fixtures also require an exact blob/size/reason entry in
`scripts/verification-artifact-policy.json`. Keep the whole verification tree
within its 1 GiB budget. Do not loosen the budget to accommodate transient runs.
The archive tag preserves old evidence; this change releases no custody hold.
The private R684 build-admission integration left UNKNOWN PostgreSQL readiness
and custody for PID/PGID 80819. Preserve the entire
`verification/local/build-admission-coordinator-r684` namespace, including its
database, source, outputs and scratch, without inspection, enumeration, probing,
signals, waits, retries or cleanup. Use only the separately delivered compact
`verification/receipts/build-admission-coordinator-r684.json` as a reference.
The candidate is unaccepted: two of seven database tests passed and coordinator
persistence remained unresolved. Outer exit 74 does not release this hold.
Fresh work from canonical source in a distinct namespace remains authorized.

The hosted Swift job in run 42957152316, job 130314843007, reported UNKNOWN
terminal custody or cleanup failure for the `stderr-default` output-ceiling
control. No reliable inner PID/PGID was exposed. Preserve that exact hosted
command group and its test scratch without inspection, probing, signals, waits,
retries or cleanup. Only the copied top-level summary in
`verification/receipts/swift-stderr-custody-r710.json` is a reference. A completed
GitHub job or direct child does not establish inner absence. The underlying
operation and OS error remain unproven; this does not release earlier holds or
block new isolated source-only controls and independent product work.

The optimized cache descendant control in run 42961685092, job 130329446293,
left UNKNOWN custody for PID/PGID 5342. Preserve that exact hosted group and
`/Users/runner/work/mixer/mixer/verification/plan-continuation-2026-11-07/cache-refusal-cleanup-r8/evidence/original-optimized-hpojqy3z/scratch/mixer-cache-runner-controls-2ryg0h52`
in full, without inspection, probing, signals, waits, retries or cleanup. Read
only the copied top-level summary `verification/receipts/cache-observation-custody-r762.json`.
Its first PermissionError is now attributed to `commands.py:16`, function
`gone`, calling `os.killpg(pgid, 0)`; the underlying OS cause remains unproven.
Direct child return, successful signal dispatch or GitHub job cleanup do not
establish group absence. Unrelated isolated development remains authorized.

The R768 lookup diagnostic consumed its first runtime to fourteen zero currents
and zero tickets, then failed while constructing a second runtime in the same
process. That second runtime's consuming accounting is UNKNOWN. All three OS
command groups were positively observed absent; that does not prove ledger
cleanup. Preserve its `source`, `target-private`, `artifacts`, `logs` and `tmp`
under `verification/local/entryeditor-private-headhit-r768` without inspection,
retry or cleanup. Only its delivered top-level report, receipt, HOLD.json,
manifests, source proof and patch are references. Fresh separately selected work
must use an independent baseline and namespace, never the retained chain.

The R772 control grouped multiple rejection cases under one runtime. Its retained
self-cycle failure caused a later harness panic before consuming cleanup. Ledger
accounting remains UNKNOWN, although both managed process groups were positively
observed absent. Preserve `source`, `target-private`, `artifacts`, `logs` and `tmp`
under `verification/local/entryeditor-single-owner-r772` without inspection,
probing, retries or cleanup. Only its delivered top-level REPORT.md, HOLD.json
and compact receipt are references. A fresh separately selected application run
uses the independent R760 baseline; it does not release this chain.

The fresh CLI host suite in run 42967308165, job 130347402614, aborted in
MigrationPrecisionTests.swift:6 while tests ran concurrently. No reliable inner
PID/PGID or complete descendant-absence proof was exposed. Preserve that hosted
command and `/Users/runner/work/_temp/cli-host-swift-42967308165-1`, including its
tmp and store-children paths, without inspection, probing, signals, waits, retries
or cleanup. Only the copied top-level summary
`verification/receipts/cli-import-ci-first-failure-r800.json` is a reference.
The uploaded top-level SUITE-HOLD.json is absent; that is not absence evidence.
Fresh test-only work in separate namespaces remains authorized.

The fresh stderr-default control in run 42976700575, job 130377344219,
reported a denied SIGKILL for owned PID/PGID1637: PermissionError/EPERM at
signal-owned-group. Its top record reports direct reap, both EOFs and group
absence, but descriptors_closed=false and terminal_custody=false. Preserve the
exact command and `/private/var/folders/2s/vty41l455yv698g4xkgfv7z00000gn/T/generated-java-python-controls-bs1munr7`
without inspection, probing, signals, waits, retries or cleanup. Read only the
copied top-level `verification/receipts/stderr-signal-custody-r822.json`.
The OS permission cause is unproven; the recorded absence does not override
cleanup failure or release this or earlier holds. Independent work remains authorized.
