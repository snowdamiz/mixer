# Control-test observer isolation repair

Hosted VM CI for 6172e65 failed five of the six new control tests under the
normal concurrent Rust test harness. The original collector used one thread
and --nocapture; its scoped executable receipts remain valid, but they did not
qualify the default CI harness.

The original class of failures reproduces locally with the retained exact
Debug test binary. Running that same binary with captured output and one thread
also reproduces a second failure: libtest's growing output Vec is owned by the
test observer and appears as a leak across a cold fault check. These two failed
replays and the hosted decoded log are preserved.

The repair changes only span_control_extraction.rs. Each of its six tests takes
one mutex before creating Ownership or Background. Reverse local destruction
ends ownership and joins the noise worker before releasing the mutex. Trace
diagnostics use direct locked stdout writes, initialized before ownership, so
libtest's captured-output Vec no longer contaminates the live-byte assertions.
Every fixture, assertion and measured allocation interval is unchanged. Neither
the common allocation observer nor any VM production source changes.

Candidate1 builds fresh archived source for span/all features and Debug/Release.
All six tests run with six harness threads and default capture, both with and
without background noise: eight runs. Every run reproduces all795 complete
control observation rows from the accepted sequential source packet, compared
as a multiset because scheduling changes test order. All tests and fmt pass.
The root receipt audits all retained artifacts and 428 tracked VM inputs; a
separate read-only agent review found no source defect. Hosted Linux CI must
still recheck the repair. No native, physical or GA acceptance follows.
