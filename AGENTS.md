# mixer implementation rules

The binding product scope is `mixer-product-plan.md`. `PLAN.md` indexes execution;
it does not replace or narrow that scope. Keep `STATUS.md`, `work-graph.json`,
`gates/`, and `verification/` current with observed evidence.

## Ownership and execution

- Independently implement all product engine code. No Patch/Skip implementation,
  generated source, tests, fixtures, or dependencies. Official specifications and
  platform tools are permitted. Record general-purpose dependencies in THIRD_PARTY.yml.
- The plan explicitly requests parallel agents: use `gpt-6.1-sol`, `xhigh`, fresh
  context with bounded ownership for ordinary work. Escalate stalled blockers,
  competing experiments and difficult review to fresh `gpt-6-astra`, `xhigh`
  agents (Astra 6 Extra High), following product-plan sections 20.3 and 24.4.
  The main controlling model is selected by the user; do not claim to change it
  via a child agent.
- Aggressively test competing blocker hypotheses within finite resource/run bounds.
  Treat experimental numeric limits as hypotheses; preserve baseline failures,
  validation/capability safeguards and all active native/process/custody holds.
  After two failed approaches or two preparation-only cycles, launch the bounded
  escalation campaign. Each prerequisite must unlock a named executable test or
  integration; avoid endless accounting/review preparation without a decision.
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

Record command, tool version, source revision/tree digest, output, and scope.
Mac unit tests are not physical iOS/Android receipts. FieldLog must eventually
consume immutable published packages from a separate repository. Local checkout
debugging is not dogfood release qualification. Never mark a GA gate verified
without its specified evidence and accountable reviewer.
