# Independent guarded snapshot funding source review

Accepted **bounded constants-only source integration evidence** for frozen
candidate source144 `7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
Complete funding, work admission, writer execution, production caller and GA
qualification remain pending.

The preaccess packet was frozen before candidate access. It verifies accepted
source144 and the frozen correction75/independent9 inputs, derives the C/S/A/H
recipe and passes 123 independent pure integer assertions. The released candidate
seal `e006b90b8c9e351e0d4dd504c6de309e2c7970b628fe9fc4f788cb30e77bedf7`
has 225 members and 20,037,475 bytes; all were independently checked.

The actual diff changes only `control.rs` and `cache/initial_profile_v1.rs`.
The unchanged 13-term Original F0 is charged once. C=78,240 is added once to
the common constant; S=941,467 once to selected; H=81,327 additionally in
cfg(test); A=430,175 replaces the phase placeholder amount. Placeholder structs
remain for historical/layout purposes. The old conservative 200-byte selected
formula-role charge and unused legacy charges remain; no optional 2,192-byte
credit is selected.

Both retained production/unit metadata-MIR commands succeeded under Rust1.99
on aarch64-apple-darwin. The raw funding-function MIR has only each function's
existing Option return place, with a constant copy and no runtime checked-add,
helper call, array or new local. Exact source inversions confirm unchanged
pair/preflight/work/commit/transfer order, WorkAuditPending, actual completion
forwarding, stop/error checks and the conservative finalizer. The 174 recorded
scalar controls pass in each production/unit/overflow context; an independent
integer oracle recounts those cases. These are scalar tests, not Mixer runtime
fixtures. The expected E0080 overflow diagnostic is retained and checked.

Two fresh, bounded, compile-only diagnostic seams measured the real source
constants without creating a Mixer executable. Each intentionally produces
three E0308 array-size diagnostics. The actual values differ by cfg context:

| Context | F0 | Common F0+C | Selected including applicable H | Admitted including A |
| --- | ---: | ---: | ---: | ---: |
| production | 366,312 | 444,552 | 1,386,019 | 1,816,194 |
| cfg(test) | 366,896 | 445,136 | 1,467,930 | 1,898,105 |

The scalar harness's F0=366,896 is synthetic; it happens to match cfg(test),
and is not the actual production F0. The first measurement driver's assumption
that both actual F0 values were equal failed after saving both valid compiler
receipts and removing scratch. That failed assumption is preserved in
`measurement-assumption-failure.txt`; the script now summarizes per context
without repeating the compilers. The review's initial MIR-name extractor was
also repaired to recognize the explicit `control::` prefix in cfg(test).

The final independent review passes 79 checks. This is a logical source-place
recipe on the measured compiler/target, not a physical stack/RSS or private
library bound. The unchanged 300,000/400,000 fixtures were not dispatched; the
400,000 common-floor fixture may now refuse earlier. The original 256MiB memory
and one-billion work policy literals are unchanged.

The current commit function returns the prior Construction amount. Completion
passes it to the unchanged drop-and-narrow helper. The report correctly leaves
the A producer/return/move/owned-backing retirement proof open even though S's
receiving diagnostic slots are charged. The alternative that returns the
already committed total is a proposal only and was not applied or accepted.
The cfg(test) H charge at selected admission does not establish reservation
for already-live ingress arguments or the independent external harness.
WorkAuditPending still blocks the actual conditional commit and writer path.

All recorded independent child groups were reaped and absent; owned compiler
scratch was removed. No Mixer VM/writer, native app, device, simulator,
emulator, UI automation, capture, global process inventory, canonical source,
Git, root metadata, hosted lane or unrelated project was run or changed.
Canonical Linux diagnostic CI remains separate evidence.

Recheck the read-only review with:

```sh
python3 verification/swift-guarded-snapshot-funding-independent/review.py
```

`measure_constants.py` creates bounded owned scratch and runs compile-only
diagnostics. Its existing saved receipts can be summarized without compilers:

```sh
python3 verification/swift-guarded-snapshot-funding-independent/measure_constants.py --summarize-existing
```
