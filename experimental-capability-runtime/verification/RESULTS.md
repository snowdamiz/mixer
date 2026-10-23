# Experimental Swift bridge qualification

Final candidate5 is the separate development bridge over native revision
`b25e3b7de2391a80d12e7fd75e60903495bec120`. Its55-file source manifest is
`070f626acd4cfc99ec2bdeb9b1e1dc45da228548d3f6458fb8fbe1b7bbca4b4d`.
The implementation receipt is [candidate5](2026-10-23-candidate-5/receipt.json);
root's combined audit is
[integration evidence](../../verification/capability-bridge-integration-2026-10-23.json).

The implementer suite passes16 tests each in debug, release and Swift Thread
Sanitizer, plus a separate idle observation. Actual guest storage round trips,
strict transport decoding, dispatch limits, cancellation and retained exit
ownership execute on the host. Three actual loopback TLS fixtures observe normal
trust rejection, with no application request or trust change. The public consumer
links on macOS, iOS, simulator and Android; only the macOS empty-module rejection
is executed. Mobile results are compilation and linking only.

Independent review passes10 unmodified public tests and14 separately instrumented
ordering tests in debug, release and Swift/C-shim TSan. Separate metadata and
construction fault tests run in isolated debug/release processes:76 total test
case executions. Review found an ordinary close race that reported invalid
arguments despite successful cleanup. The correction treats checked closed-handle
status3 as expected at take/wake/deadline-query boundaries while keeping failed
acknowledgement, malformed metadata and invariant failures fatal. Four controlled
close races pass on final5. Failed prior probes and their inputs remain recorded.
The [independent receipt](../../verification/capability-bridge-review/final-receipt.json)
binds42 review files,131 evidence files and163 owner source/log/artifact checks.

[Active payload observation4](2026-10-23-active-payload-4/receipt.json) runs the same
final5 production sources in two debug and two release processes. Each executes
eight overlapping real storage gets of49,152 decoded bytes, with525,976 total
wrapper bytes, eight exit acknowledgements and complete drain. Debug maximum
batches are9.261–9.801ms, exceeding the cooperative8ms target by1.261–1.801ms.
Release samples are3.882–4.122ms. The1ms allocator sampler includes the probe,
runtime, frameworks and native work; it is not an exact codec-copy peak or RSS
bound. The original receipt's scope sentence still says candidate3; its explicit
base receipt and all55 matching source hashes establish that this replay is
candidate5. Those original receipt bytes are preserved.

The Rust archive and system frameworks are not instrumented by Swift TSan.
Logical payload/worker counts do not prove allocator capacity, Task destruction,
kernel cleanup, rollback, recoverable OOM or hard scheduling deadlines. The
bridge supplies development APIs, not signed release authority. Complete
validation-only and typed native failure classification, verified installed
material, identity2/release3 activation, successful provisioned HTTPS, full Swift
and UI execution, published FieldLog consumption and physical-device gates remain
open. Phones remain disconnected. GitHub CI integration is pending its own run.
