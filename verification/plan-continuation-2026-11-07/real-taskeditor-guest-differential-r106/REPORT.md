# FieldLogTaskEditorBurstAndSaveDifferential — R106

The actual unmodified shared TaskEditor compiled and executed natively and as a
full Swift Wasm guest. Their complete JSON outputs are byte-identical. The current
owned VM refused this module before execution. Independent review is pending.

The fixture imports the public MixerCore package product, the exact R90
TaskEditor and the complete Workspace source. It preserves MainActor isolation,
FeatureStore state/effect dispatch, async save execution and `waitForSave()`.
The injected app-owned actor records the save arguments after an asynchronous
yield and returns `.saved`; it performs no application network or filesystem
operation. This exercises the save-completion contract, without qualifying
storage durability.

The burst covers Arabic, Chinese, emoji, decomposed accents, internal newlines and
leading/trailing whitespace. The expected save values are literal test inputs,
not values derived from an earlier run. Assertions cover empty-submit rejection,
last-edit preservation, ignored changes and duplicate submit while saving, one
save callback, one saving-to-saved transition, ignored edits/resubmit after save,
and submit rejection after closing. Effect count is observed through the public
save callback and state transitions; no private-store instrumentation is added.

Both actual runtime payloads emitted:

```json
{"closedSubmitRejected":true,"completionTransitions":1,"finalState":{"canSubmit":false,"responsible":" Zoë\n李 · مسؤول ","saved":true,"saving":false,"title":" \nInspect 🛠️ gate\nبوابة · café\n "},"observerDeliveries":17,"saveCount":1,"saves":[{"responsible":" Zoë\n李 · مسؤول ","title":" \nInspect 🛠️ gate\nبوابة · café\n "}],"status":"passed","test":"FieldLogTaskEditorBurstAndSaveDifferential"}
```

`failure == nil` is asserted by the fixture; synthesized optional Codable fields
are omitted when nil. The Node diagnostic uses the installed Node 22.23.3 WASI
preview1 implementation, empty environment, no filesystem preopens, and platform
randomness. It reported exit 0 and 34 declared WASI imports. Called imports and
the official experimental-WASI warning remain in the raw stderr. Node is the
development oracle; `ownedVMExecution` remains false.

The Wasm artifact is 60,877,726 bytes, SHA256
`24c0fb1bb38f64ad254ca89543b7ca1328bc8bdf83d198c9e84ba127d9fb7d85`.
Current unmodified VM source was built offline as a dependency of the small
admission executable. Its actual output includes:

```text
strict_table_memory_v3={"code":"limit","message":"module byte limit exceeded","function":null,"offset":0}
experimental_swift_reactor=SwiftValidationFailure { kind: ResourceExhausted, code: "profile_vector_limit", function: None, offset: 7205, resource: Some(StaticPolicy), attempted: 80514, limit: 79966, ... }
ownedVMExecution=false; no invocation performed without module/profile admission
```

The complete unabridged failure, including resource usage, is retained in
`commands/owned-vm-admission.stdout`. The first experimental refusal is the
defined-function count. Later validation, import, opcode and ABI checks have not
passed. Source inspection also shows that the experimental validator pins the
original reactor's `_initialize`/`mixer_fieldlog_corpus_v1` export ABI, whereas this
official async-main command exports `memory` and `_start`. Changing only a
numeric limit would not establish admission or execution.

Source provenance is recorded per file in `receipt.json`, including SDK
Package.swift and all five MixerCore files, the VM source set and official Wasm
SDK metadata. TaskEditor is pinned to
`ef5321a92467868227007b856aca5c7ed142e5337d8dbb20a07e0e3394335310`.
TaskEditor and Workspace match the supplied original R90 provenance checkout.
All 84 recorded inputs were rehashed after execution with no drift. The aggregate
source digest is
`0098f42d9667e12e51e51508495059c50e3a98b0705d0d611d446675b4f6eb52`.
The parent-supplied root revision is recorded as an assertion; no root Git
operation was attempted.

Exact argv, working directories, tool versions, exit codes, command times and
owned PGIDs are in `COMMANDS.txt` and `receipt.json`; raw stdout/stderr are in
`commands/`. The two reproduction phases are `python3 -B run.py` and
`python3 -B run.py --continue` from a fresh copy of this diagnostic directory.
There were three distinct build commands and two application runtime payloads.
Cargo's first invocation failed before executing `rustc -vV`; the same build argv
succeeded after adding the installed Rust bin directory to PATH. Both logs are
preserved, so four build-launch invocations are explicitly recorded. Builds used
two jobs. Total recorded command wall time was 18.175 seconds; this is diagnostic
accounting, not a performance measurement.

Every recorded owned command group was observed absent after its command.
The initial read-only inspection session was interrupted and collected with exit
130. Fresh userdata scratch is retained at
`/Users/andreyyurlov/.t3/userdata/mixer-taskeditor-r106-pferm211`.
No device, native-app lane, historical held resource, source baseline, Git state,
CI job, service or external account was changed.

Next decisive test: `FieldLogTaskEditorBurstAndSaveDifferentialOwnedVM`, reusing
this exact fixture and native JSON oracle after a separately owned, explicitly
admitted async-command execution path exists. It must validate the entire module,
imports and instructions under its explicit bounded policy and execute the real
`_start`/MainActor/effect path. Preserve the existing strict and fixed-reactor
policies. The test must compare the same complete JSON and save/completion counts
from the owned interpreter. It is blocked today by the concrete refusal above
and the absent public executable feature-command route.

This advances W07 feature-semantic development evidence beyond the old pure-model
corpus and gives W08 a real-feature admission failure. Native widgets, filesystem
persistence, published packages, physical devices, debugger/source-map coverage,
complete W07/W08 qualification and GA remain pending.
