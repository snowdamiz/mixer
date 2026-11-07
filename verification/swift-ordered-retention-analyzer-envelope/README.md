# Fixture envelope producer candidate

This packet adds `analyze_fixture_envelope_v1` as a separate safe-existing-File
fixture boundary, preserving the accepted framing source/API/ABI/report and its
44 exact tests. No semantic replay, binding/custody, live VM or target authority
is implemented. Both acceptance fields remain false.

Read the root-selected immutable preparation2 and addenda under `inputs/`,
`source-accounting.md`, actual `logical-inventory.json`, `step-inventory.json`
and `final-receipt.json`. The preparation1/2 directories retain their original
bytes, and every failed attempt is retained. Producer authored bounds still
require independent review; passed fixture tests do not accept numeric proof.

The final exact source is frozen under `seal.json`/`seal.sha256`. Use
`python3 -B verification/swift-ordered-retention-analyzer-envelope/verify.py`
for a read-only member check. A reviewer should copy the selected sources into
its own bounded owned packet before reproduction, and preserve this freeze.

Before freezing, `run_checks.py run-N` creates a fresh run directory, snapshots
the exact source/tests/inputs, rehashes all2512 upstream sealed members and68
preparation files, compiles only direct std-only Rust with -Dwarnings, executes
bounded host tests and archives/removes owned scratch after synchronous children
exit. It never restores a VM, uses Cargo, queries processes/devices or starts
native/capture/UI/phone execution. Do not rerun it inside a frozen producer.

`generate_oracle.py` imports only this packet's exact copy of the frozen finite
Python contract model. Its16,170 cases are finite differential fixtures, not
source-applicability evidence, runtime integration or real diagnostic input.
The historical17 sidecars retain their invalid/failure15 classifications.

Source/FD/CLI, real adapters/cryptography/custody, token/resident/victim/plan/
metrics semantics, writer repair, full Swift target, compiler/native/device/
signing/store/customer/operations, published-package FieldLog and GA remain
pending. No deployment, message, credential or destructive action is selected.
