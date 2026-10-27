# Independent retained-profile stdio correction review

This closed evidence packet reviews the frozen659-member raw-stdio correction
`01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2`.
Read findings.md for the required R03 read-completion failure and the separately
positive C01 ownership assessment. Complete composition remains unaccepted.

Final recorded executions:77 commands, including63 new independent cases
(61 behavior passes and2 required R03 failures), two exact26-method producer
suites and12 exact prior independent case invocations. Each producer suite also
checks307 snapshot-leaf mutations. The literal old C01 failure and new unused-hook
fixture mismatch both remain exit1 and neither is called a behavior pass.

preliminary/ retains the earlier75-command run and exact test sources. Its third
claimed R03 failure was a mistaken child-report expectation, corrected explicitly
in disposition-correction.json and findings.md. An early direct tool probe of the
32-short-read defect was subsequently rerun with retained streams; it is excluded
from these77 final recorded-command counts.

Scripts operate only inside this review directory. verify_inputs.py verifies all
immutable input members. prepare_replay.py copies exact sources; it is not a
producer prepare/freeze script. run_review.py runs bounded case subprocesses;
run_supplement.py appends the nested real-child cleanup join. No uncertain saved
number is retried and no uncertainty ledger is erased. Fixture-directory deletion
and terminal process containment do not retire modeled uncertainty.

No native runtime, devices, simulators/emulators, UI, capture, process inventory,
prohibited hosted harness, canonical source/index edit, commit, push or publication
was used. Real Rust binding/context/accounting/native/OTA/GA remain pending.
