# Preserved construction attempts

Every source-only Python run is retained under `attempts/`, with the exact
source_checks.py snapshot, command/tool context, raw stdout, raw stderr and
exit status. No failed run is removed or relabeled as a product failure/pass.

The first construction run failed its event-name uniqueness assertion because
two coherence events used the same label. The source sketch was unchanged;
the second label was made unique. The next run failed the assertion that the
finite sample attained321 comparisons: the chosen input families did not yet
contain a constructive worst case. A bit-reversal timestamp family was added,
which attains32/48/56/60/62/63 comparisons. Neither failure was a Rust execution.

Subsequent passing runs preserve the intermediate whole-byte proposal,
the G2 Candidate timestamp-view refinement, padding/address checks, explicit
group assignment and the deeper checked integer helper accounting. Their
counts are historical. `operation-ledger.json` and the last passing run describe
the final construction. No failed compiler/runtime/device attempt exists
because this lane was never authorized to run those surfaces.
