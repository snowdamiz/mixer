# Stage 4 native join admission after a Swift fault

This addendum clarifies section 4 of `android-binding-stage4-seams.md` after
independent finding S4R-03. The original contract and candidate-2 failure evidence
remain immutable. This is a required implementation correction, not acceptance of
candidate 2 or an expansion of the host-only stage.

The successful, unique `beginJoin` decision under the lifetime control lock is
the native-join admission point. It must validate the exact Task-return key,
one-shot state, successful terminal RETIRE, and absence of any fault already
latched in that lifetime control. Such a control fault returns quarantine before
`mxuit_consumer_joined`, preserving uncertain endpoint and resource ownership.

A fault that wins the control lock after this admission cannot retroactively
invalidate the actual Task return or successful RETIRE. The admitted call may
record that genuine consumer-joined fact in C. This bookkeeping grants no
retirement evidence, reclaim permission, facade cleanup receipt, or capacity
release by itself. Do not hold the Swift control lock across C operations or
callbacks.

Global fault publication has a separate admission mutex. `quarantineAll` latches
the registry fault before fanout reaches each lifetime control. During that
interval a control without a local fault can still admit the genuine joined
bookkeeping. This explicitly supersedes section 4's unqualified statement that
any fault prevents that assertion: failed RETIRE and a previously latched local
control fault prevent it; a registry-only fault prevents native reclaim instead.
An unsynchronized extra registry read would not close the publication race.

Successful actual `mxuit_try_reclaim` while holding the registry admission mutex
is the endpoint-retirement point. A registry fault published before that point
prevents reclaim and therefore endpoint retirement evidence. A fault published
after real successful C reclaim cannot undo that completed retirement: the exact
immutable endpoint fact may be published afterward and its Swift endpoint record
removed. This grants no successful facade finalization. The separately guarded
facade reclaim and cleanup stages must retain uncertain resources and capacity
when the registry/facade is quarantined. Historical success is not retroactively
rewritten; future work remains closed.

Verification must exercise a real completed nonfinal RETIRE, a subsequent real
Swift progress fault and fanout, then the common final-finish path. With the fault
latched in the control before admission, C's consumer-joined marker must remain
zero, the result must be quarantined, and resources/capacity must remain retained.
The registry-before-reclaim and registry-after-actual-reclaim orderings require
separate checks. The latter may publish only the completed endpoint fact while
the facade/resources/capacity remain pinned. No fault injector may fabricate a C
success, Task-return witness, callback fence, or cleanup evidence.
