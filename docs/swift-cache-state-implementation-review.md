# Independent initial cache-state implementation review

The original frozen candidate is **rejected** for two violations of the accepted
terminal guards. Public basics pass, but this is not implementation, source
accounting, full matrix, native, or GA acceptance. A corrected candidate requires
its own exact root admission; this review does not read the evolving correction.

The reviewed candidate seal is
`caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3`
(454 members, 15,362,764 bytes), admitted by root receipt
`c238edff3f5ef05a770640a0f67b2d748e6e95108dfe00d93e7d890e42333df0`.
The cache-state source is
`d0e2ec2998f70958e10a7dbf33742917ced66cd4559bafb88bcabe8b221a54db`.
The unchanged sealed runner first verified all candidate members and staged the
three Rust sources. The first header/index read preceded the separate full
454-member owned snapshot; [its manifest](../verification/swift-cache-state-independent-review/implementation-review-1/candidate-snapshot-manifest.json)
records this access order explicitly. Substantive source review uses that owned
snapshot. The immutable preaccess and execution-preparation seals remain
`1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c`
and `07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6`.

The unchanged public runner executed 39 basics with four ordinary distinct,
quiescent Files. All full 32-word observations, inherited report/diagnostic
assertions, input integrity assertions, false authority getters and public layout
bounds passed. Fifteen attributed API compile controls had the expected results:
one positive and fourteen negative. These are finite public controls, separately
recorded in [public-summary.json](../verification/swift-cache-state-independent-review/implementation-review-1/public-summary.json)
and [api-compile-summary.json](../verification/swift-cache-state-independent-review/implementation-review-1/api-compile-summary.json).
The compiler was the root-bound Apple arm Rust 1.99.0, binary SHA
`dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0`.
Fresh public sizes were 104/128/232/256/488 bytes, with complete new Result 488
bytes, within the 512-byte reservation. Private helper layouts were not measured
by this lane.

Two blocking findings were reproduced through separately admitted private
instrumentation. The exact accepted machine table is
`terminal-contract.json`, SHA
`766762e23f6c4dd548f375f81918540c26000a82efdec098f1130e74c4365161`,
retained in the [frozen proposal](../verification/swift-cache-state-independent-review/implementation-review-1/private-guard-proposal/accepted-terminal-contract.json).
Its Q9 and Q10 expressions, rather than an inferred public reachability rule,
are the authority for these findings.

| Finding | Original source | Exact accepted behavior | Observed private behavior |
| --- | --- | --- | --- |
| F01: inactive masks are read | `cache_state.rs` 210–214 | Q10 says outside planned stages the masks/feasible fields are not read. Idle projects the fixed inactive sentinels. | Both an out-of-range selected mask and a taken-not-selected mask in an otherwise valid Idle snapshot produce InternalPoisoned/16 instead of the exact T14 observation. |
| F02: pending feasibility is missing | `cache_state.rs` 216–219 | Q9 requires feasible=true in stages 7 and 8, in addition to selected/in-range pending victim. False feasibility must take T09 and suppress the extent. | Stages 7 and 8 with feasible=false pass `shape_q` and expose CapCutUnknownTail/Observed live fields instead of the exact T09 suppressed observation. |

Root admission
`d52cb249fff84ed893e0f919cefff9095288a725ada60fa06db64743e893a586`
authorized exactly seven seeded cases in default and optimized binary overlays.
Each mode compiled and ran successfully: three baselines passed, four witnesses
failed. There were 14 case observations, six passes and eight failures, with
identical results between modes. [The run summary](../verification/swift-cache-state-independent-review/implementation-review-1/private-guard-run-1/summary.json)
retains every expected and observed word and exact differences. Raw commands,
compiler output, program output, overlay source, exact append delta and expected
fixtures are preserved. The orchestrator returned exit 1 because the witnesses
failed, with no preflight/protocol error. Both returned owned binaries were
hashed and removed after their commands returned. Product source hashes were
unchanged before and after execution. The default binary crate did not enable
`cfg(test)` or execute any producer test, harness or model.

These are deliberately seeded private Progress/child/config states. They prove
observable guard defects at the admitted private seam. They do **not** establish
reachability through public from-empty construction, row semantics, corruption
recovery, work bounds or memory bounds. Public File controls and private seeded
controls receive separate counts.

[All P01–P35 dispositions](../verification/swift-cache-state-independent-review/implementation-review-1/source-proof-review.json)
are recorded, with [source hashes and excerpt consistency](../verification/swift-cache-state-independent-review/implementation-review-1/source-audit-independent.json).
Both old library prefixes are byte-identical to the accepted sources. Four copied
historical emission/cache sources and fourteen seam excerpts were independently
reverified as source data; no live VM relation or execution parity is claimed.
Source review supports the actual checked record loan, local transition design,
single shared Candidate, no early `?` inside the loan/cleanup scope, exact 256
zero-word stores and twelve direct byte restores, and poison disabling both
later leaves. The reserved tail is zero initially; the first envelope writes
only 888..984 exclusive, semantic scratch ends before 1944, and cleanup clears
all bytes before restoring that payload. A poisoned Candidate is never reused.

The private paid receipt has one product construction, literal 1/1/0 after both
propagating finish/setup reservations. Its record count increments only after a
successful 8151 charge, before read/field failure can occur. The sole product Ok
aggregate follows these reservations and successful output. Thus returned Ok
with paid flags 00/01/10 is unconstructible in the reviewed production source;
these three excluded cases have **zero runtime pass credit**. The semantic
payment equation remains 512*SS + 256*SF + 7680*NC, with inherited 425 record
debit separate. Output failures propagate the original outer Err with no
aggregate. Reasons 15/17 retain enum identities but are non-emitting on product
projection paths. All four authority getters remain literal false.

The independent [accounting review](../verification/swift-cache-state-independent-review/implementation-review-1/accounting-review.json)
reconciles each event's fixed copies/stores and the producer's group 6 arithmetic,
including the largest built-publication branch. It distinguishes `st`/`sq`
array-result conversions from direct already-LE copies. It also proves the
six-pass algorithmic maxima of 321 comparisons and 384 transfers. It does not
endorse the entire work ledger: the claimed 637/640 group has only three units
remaining, while exact named scalar blocks, helper movement, all administrative
tests and final loop tests are insufficiently enumerated. Broad whole-function
ledger rows do not close P23/P24/P25. This is an unresolved proof requirement,
not a demonstrated numeric cap overrun.

The production public body expands its macro directly, so the cfg(test)
forwarding core adds no production Result layer. Complete lifetime acceptance
nevertheless remains withheld. Producer Progress/Paid birth indices refer to
walk/inputs instead of their actual macro constructors; helper/Option buckets
and aggregate/Result moves need exact source/received/drop/coexistence mappings.
The correct arithmetic 29,344 does not alone prove that complete lexical union.
P28/P29 and private helper-layout portions of P30 remain open. No spare group,
global margin, cap increase or optimizer elision is accepted as a substitute.

The public words/transitions/sequences bulk matrices, other terminal cases,
private row/victim/numeric/IO/budget/commit/cleanup fault controls, and independent
old-API runtime regression suites were not executed in this phase. They receive
zero new pass credit. Future public batches must be at most 64 cases and use a
separately frozen lossless deduplicated transport before repeating large profile
bytes per mutation. Single-defect reasons and explicit overlap allowed sets
remain unchanged; source predicate ordering is documented as an implementation
choice, separate from fixed T00–T15 terminal precedence. A corrected freeze and
further root admission are required before dependent execution. Native, device,
capture, real-source, custody, release and GA checks remain unrun or pending.
