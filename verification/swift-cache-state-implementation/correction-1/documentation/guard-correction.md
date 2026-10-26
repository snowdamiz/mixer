# Q9/Q10 private projection guard correction

This candidate corrects only `shape_q` in a fresh copied fixture-only library.
Root selected it in `guard-correction-selection.json`, SHA
`0f70d7f9ce793d710da4d1d3dc97debaf8474d8bfb9031f77fdd1af5ddbc22fe`.
Every original454 member, all original seals and the external implementation doc
remain byte-identical. The original candidate is retained evidence, not silently
rewritten. No independent raw fixture, expected case, glue or oracle was read,
imported or executed by this producer correction.

The accepted Q10 expression says that selected/taken/committed masks and feasible
are not read outside planned stages6..10. The original helper unconditionally
validated masks, causing arbitrary inactive storage to poison an otherwise
eligible private observation. The correction places all mask, feasibility and
destination validation inside the planned-stage branch. Inactive fields retain
the required projected zeros/MAX sentinels and never influence this guard.

Q9 additionally requires feasible=true for pending stages7/8. The previous helper
checked the pending slot and selected bit but allowed false feasibility. The
corrected pending condition checks feasibility first, then checks the pending
slot range before its shift/membership expression. Infeasible pending state
therefore becomes T09 poison with every state/coordinate word suppressed. False
feasibility at planned nonpending stages6/9/10 remains an observed obstruction;
its destination is ignored and projectsMAX. Pending storage outside7/8 remains
inactive. No terminal row, public enum/getter,32-word projection expression,
public API, report byte layout or constant resource ceiling changes.

Five producer-authored focused private methods exercise4,337 scenarios per mode:
33 baselines across every stage and slots1/3/64;3,000 inactive-field combinations;
144 planned-mask/boolean/destination boundaries;1,152 pending feasibility,
membership and destination combinations; and eight initial/precedence controls.
Every scenario checks the full32 projection, and applicable cases directly
check the actual `shape_q`. These deliberately seeded private states have zero
public-from-empty reachability credit. The22 prior cache-state methods and all
78 producer/14 independent inherited methods are separately rerun against the
new exact bytes, together with16 new and nine immutable old API compile controls.
All25 API dispositions are checked in each compiler mode.
Fresh layouts remain104/128/232,256/488 and complete Result488 on the recorded
Rust1.99.0 Apple arm host.

The source audit proves that `shape_q` is the only changed product function;
all semantic-leaf, sort, staging, commit,256-word clear,12-word restore, tail
induction, public return and error-partition source is byte-identical outside
that helper. The existing per-record471+7680=8151,8192 preflight, setup512,
finish256, guard128 and all memory roles stay unchanged. The correction adds
only the pending feasibility scalar predicate to a guard already owned by
finish256, moves the existing planned-range test to the enclosing branch and
removes the old repeated destination gating conjunction. It adds no array,
allocation, Result, callback, returned object or persistent state owner.

`proofs/correction-work-and-lifetime.md` names the changed scalar read/control
operations and conditional read sets. The inherited637 administrative/block
claim, complete source-work partition and caller/lifetime reconciliation are
still producer claims awaiting independent review; the guard correction does
not mark them endorsed or raise a cap. Actual helper layouts are evidence of
representation only, not proof of physical stack, RSS or complete source work.

Commands retain exact source hashes, tool identity, PID/PGID, separate per-command
deadlines and output caps, raw stdout/stderr and observed parent exits. Outer
orchestration yields while the serial suite runs and imposes no aggregate60s
deadline. Fresh raw File evidence is isolated from prior attempts. Owned host
executables, archives, bytecode and scratch are removed after terminal receipt.
No process inventory, live VM, CLI, native, simulator/emulator, phone, UI or
capture work occurs. Real adapters, release/device/operational/FieldLog/GA and
independent implementation acceptance remain pending; root owns admission and
delivery.

The first host run is preserved under `evidence/attempts/initial-host-run` with
zero final-command pass credit. The final full suite used artifact-hash cleanup;
the earlier preliminary binaries had already been removed before that
instrumentation and their binary hashes were not retained. The original
single-mode API raw logs are also retained with zero final API credit; the
supplementary 25 dispositions per mode provide the final API evidence.
