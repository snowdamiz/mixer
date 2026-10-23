# Independent instruction/fuel observation review

Accepted only as the private two-file control prerequisite at
`3a1bb5a455973bde841a4b57993277fa2c054569`, over
`45852204fbcced037d8e530876b619d9ed1c2ce1`. No executor, cache implementation,
target instantiation/execution, physical device, compiler, signing, store,
published consumer or GA gate is accepted by this review.

`review.py` independently obtains the committed VM archive, proves its 417
files equal the producer's isolated source, audits all 853 root bindings and
the retained 319+9 and 72-minimal counts per Debug/Release, then runs only
bounded control tests. It never runs the producer collector or rewrites its
receipt/audit. The archive, source manifest, tool output, command logs and
`receipt.json` bind this review. Build output is in ignored `.build/`.

The original eleven-case test ran once per mode against the pristine archive.
Three independently authored probes then ran per mode against that archive plus
`boundary_probes.rs`: 11 None-wrapper parity cases; six actual-WASI combined
failure-order/immutable-first-fault cases; five zero-credit and two exact-u64
arithmetic cases. This covers cancellation before deadline before fuel/count
overflow, existing fault precedence, zero-credit checks, exact-limit success,
overflow attempted/limit reporting, no repeated effects and complete cleanup.
Actual WASI probes use the complete validator, one real accounted owner and an
actual ArgsSizesGet dispatch; they never instantiate or execute the target.

Both old methods are thin None wrappers. The observed methods retain identical
checked-add/filter/mutation ordering; instruction-count overflow still follows
the existing successful one-fuel charge. Observation changes no admission and
is passed into check, fuel rejection and instruction overflow before first-fault
latching. No struct, stored field, policy, public route or layout changes in
the delta. Candidate host measurements: RuntimeControl 1720, SwiftRunFailure
1096, SwiftRunUsage 504 bytes, matching the unchanged declarations.

The initial parity probe compared historical validation wall-clock duration
from separately validated fixtures. `probe-authoring-failure.log` preserves that
harness failure. The corrected comparison normalizes only elapsed/overshoot
measurements; all semantic counters, limits, reservations, failures and historical
validation work/allocation fields remain compared.

Reproduce with `python3 verification/swift-instruction-observation-review/review.py`.
Selected reviewer model is gpt-6.1-sol, xhigh, with bounded fresh context.
