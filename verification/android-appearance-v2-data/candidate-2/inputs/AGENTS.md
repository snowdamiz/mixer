# mixer implementation rules

The binding product scope is `mixer-product-plan.md`. `PLAN.md` indexes execution;
it does not replace or narrow that scope. Keep `STATUS.md`, `work-graph.json`,
`gates/`, and `verification/` current with observed evidence.

## Ownership and execution

- Independently implement all product engine code. No Patch/Skip implementation,
  generated source, tests, fixtures, or dependencies. Official specifications and
  platform tools are permitted. Record general-purpose dependencies in THIRD_PARTY.yml.
- The plan explicitly requests parallel agents: use `gpt-6.1-sol`, `xhigh`, fresh
  context with bounded ownership. The main controlling model is selected by the user;
  do not claim to change it via a child agent.
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

Record command, tool version, source revision/tree digest, output, and scope.
Mac unit tests are not physical iOS/Android receipts. FieldLog must eventually
consume immutable published packages from a separate repository. Local checkout
debugging is not dogfood release qualification. Never mark a GA gate verified
without its specified evidence and accountable reviewer.
