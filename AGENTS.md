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

Latest direct user instruction on November 7 — “you can do native stuff, update
agents file” — resumes native simulator/emulator tests and related UI verification
and screen capture, superseding the previously supplied pause. Fresh bounded
owned builds and runtime attempts may proceed under the one-instance-per-lane and cleanup
rules above. Preserve other projects' processes, devices and data, and keep
physical phones disconnected. This does not authorize probing, signalling or
retrying the specifically held historical processes, the held v5 startup, or
frozen hosted lanes. The October 24 shutdown and pause remain historical evidence.
Record fresh attempts separately in
verification/plan-continuation-2026-11-07/native-resumption.json.

Record command, tool version, source revision/tree digest, output, and scope.
Mac unit tests are not physical iOS/Android receipts. FieldLog must eventually
consume immutable published packages from a separate repository. Local checkout
debugging is not dogfood release qualification. Never mark a GA gate verified
without its specified evidence and accountable reviewer.
