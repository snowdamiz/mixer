# Retention candidate rejected after full workload comparison

The isolated segmented-LRU candidate is rejected for live integration. One
original-harness run under unchanged work, memory, ticket and time limits reaches
CacheWork 64,000,001 / 64,000,000 after **8,746,437 instructions**, versus
**23,358,291** for the current engine with the same target/harness/budgets.
This is 37.44% of the baseline instruction progress.
Validation and Initialize pass, Corpus 1 fails and Corpus 2 is never started.
Neither run completes the workload. No rerun or source integration is selected.

The failed phase records 73,511 completed decodes and 134,721 hits,
compared with 61,627 decodes and 537,576 hits at the baseline failure.
These are observations at different progress points, not a fixed-trace hit-rate
benchmark or a new causal attribution breakdown. Together with the finite
resident-hit regression, they reject this candidate's expected benefit; the next
retention design needs a cheaper hit path and better behavior on the actual call
pattern. No budget is raised and no native or end-to-end product claim follows.

The finalized candidate, seven-method independent finite review and original
harness preparation each have exact source/binary seals. A separate preparation
review accepted the 15 unchanged driver functions, exact harness/parser and
one-attempt guards. Root restored only the packet's source and executable, wrote
a fresh selection after both reviews, then invoked exactly the proposed command.
The selected candidate closure remains d840933a706131e64c50b74812af771ead622912d57575336770434387f5b99d;
the live 132-file closure remains 16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd.
The prepared copied-source manifest, tool identities, exact argv and environment,
exclusive attempt marker, raw streams, events and original result are retained.

The outer exit is 1 and the libtest exit is 101. The child ran 2.992
seconds with no timeout or cleanup signal. The original failure remains intact,
including the legacy false cleanup_empty flag. The final consuming usage is
separately verified: all current reservation categories, live counters and live
tickets are zero, with no cleanup invariant. Historical nested WASI observations
remain visible and are not rewritten as final reservation accounting.

Root copied the attempt evidence into verification/swift-retention-runtime/ and
used only its new finish.py for scoped cleanup. Owned process group absence,
empty holder checks and stable device/inode identities preceded retirement of
the restored scratch and executable: **78,039,492 logical bytes** removed. The
original prepared gzip and every sealed preparation member are unchanged.
No inherited preparation cleanup, compiler rerun, native instance or other
project process was used. Physical-phone and all accountable GA gates remain
pending. Independent audit of this retained failed result is pending.
