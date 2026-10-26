# Independent correction 1 control results

The exact admitted correction passes the previously frozen guard witnesses:
seven cases in each of default and optimized builds, all 14 observations matching
every expected word and guard result. The unchanged public runner also passes
all 39 four-File basics and all 15 attributed API compile dispositions. This
closes the two reproduced Q9/Q10 examples from the initial review. It does not
accept the implementation, accounting, complete terminal matrix or GA gates.

Root public admission is
`3230858dae7a43050c03f06c89202447f27627554302b6709df9c8f70b38f559`;
the private rebind admission is
`5f7c86575d45090dd73fb42b6312335ce6123f17c3ddd1c98b9e49a071f628cb`.
The corrected seal is
`b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6`:
814 members and 15,587,024 bytes, all independently verified and copied into an
owned snapshot. The public runner verified all members and staged the exact
three Rust sources before execution; the full snapshot preceded substantive
review of the correction. The initial review's 899 members and external document
were reverified unchanged.

The independent production diff confirms the only source change is `shape_q`.
Both old library files are byte-identical, and the cache-state source prefix and
suffix outside that function are unchanged. Planned masks/feasibility are now
read only in stages 6–10. Stages 7/8 require feasible=true before reading pending.
The accepted machine table, seven full32 expected records, Rust private glue and
append-only delta remain byte-identical to the initial sealed proposal. Only
admission paths, output paths and corrected baseline hashes were mechanically
rebound. The retained tooling diff makes that rebind reviewable.

Public results are retained in [public-summary.json](../verification/swift-cache-state-independent-review/implementation-review-2/public-summary.json)
and [api-compile-summary.json](../verification/swift-cache-state-independent-review/implementation-review-2/api-compile-summary.json).
The private [summary](../verification/swift-cache-state-independent-review/implementation-review-2/private-guard-run-1/summary.json)
retains every expected/actual word and guard comparison, alongside exact overlay
sources, commands, raw compiler/program output, source hashes and cleanup. The
compiler remains the root-bound Rust 1.99.0 Apple arm binary, SHA
`dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0`.
No `cfg(test)`, producer harness, producer test or producer model was executed.
All owned public/private binary products were hashed and removed after commands
returned; exact source and raw evidence remain.

Private deliberately seeded snapshots remain distinct from public from-empty
File construction. Passing these witnesses does not establish public reachability
of their corrupt states, row semantics, fault recovery, debit bounds or lexical
owner bounds. Public word/transition/sequence batches, the remaining full32
terminal matrix and other private fault/layout/numeric/IO/budget controls remain
unrun. The three impossible partial-paid variants still receive zero runtime
pass credit.

The initial P01–P35 review remains the baseline. Its two demonstrated guard
examples are corrected; its coarse work/helper/loop/Result/Option/lifetime proof
gaps remain open, including accounting for the changed final guard. The declared
7680/8151/8192, setup512/finish256/guard128 and union29344 are not accepted by
these finite runs. No cap increase, spare-credit transfer or optimizer assumption
is introduced. The separately prepared content-dedup transport amendment must
be frozen and root-admitted before any bulk execution; it will preserve lossless
input bytes, per-case mappings, exact exit diagnostics and full32 expectations.
Native, device, capture, real-source, release and GA qualification remain pending.
