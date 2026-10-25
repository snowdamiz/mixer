# Fixture FSM preparatory contract packet

Owned document: `docs/swift-ordered-retention-analyzer-fsm-contract.md`.
Only this packet and that document are authored here. No commits/pushes.

`model.py` and `test_model.py` are an independently authored Python finite
fixture envelope, not Rust integration or semantic replay. `layout.rs` is a
standalone value-layout probe with no product imports or dependency. `verify.py`
checks the owned seal, all845 upstream members and final run5 source identities,
then executes only18 finite model methods and the retained standalone probe.
Use `python3 -B verification/swift-ordered-retention-analyzer-fsm-contract/verify.py`.

Run1 passed17 methods. Run2 is a preserved failed admission attempt: root's
concurrent PLAN.md change prevented reuse of the first source snapshot; no
tests/compile executed. Run3 fixed snapshots to be per-run and passed17 methods
plus layout. Run4 passed18 methods plus layout. Run5 is the final exact-source
replay after freezing reason IDs. Each executed run verifies845 upstream
members before and after; external snapshot/finite-source digests are separate.
Synchronous host children are reaped; no disposable scratch/bytecode/native
instance or capture is created. Retained layout binaries are evidence.

No supplied fixture digest or context qualifies real bindings.
`fullReplayAccepted`, `storedPrefixValidated`, semantic metric validity and
implementation selection remain false/unavailable. Existing report version,
validity mask and reserved fields are untouched. Separate contract review and
root selection are required before any implementation; complete Rust/composed
memory and debit qualification remain pending.
