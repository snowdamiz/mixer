# Stage 4 native join admission after a Swift fault

This addendum clarifies section 4 of `android-binding-stage4-seams.md` after
independent finding S4R-03. The original contract and candidate-2 failure evidence
remain immutable. This is a required implementation correction, not acceptance of
candidate 2 or an expansion of the host-only stage.

The successful, unique `beginJoin` decision under the lifetime control lock is
the native-join admission point. It must validate the exact Task-return key,
one-shot state, successful terminal RETIRE, and absence of any already-latched
Swift fault. An already-latched fault returns quarantine before
`mxuit_consumer_joined`, preserving uncertain endpoint and resource ownership.

A fault that wins the lock after this admission cannot retroactively invalidate
the actual Task return or the successful RETIRE. The already-admitted call may
record that genuine consumer-joined fact in C. It grants no retirement evidence,
reclaim permission, facade cleanup receipt, or capacity release by itself. The
later fault must still quarantine progress and prevent successful retirement and
reclaim. Do not hold the Swift control lock across C operations or callbacks.

Verification must exercise a real completed nonfinal RETIRE, a subsequent real
Swift progress fault and fanout, then the common final-finish path. With the fault
latched before admission, C's consumer-joined marker must remain zero, the result
must be quarantined, and resources/capacity must remain retained. The opposite
ordering must be reviewed separately: a genuine admitted join followed by a fault
cannot produce successful retirement or release uncertain ownership.
