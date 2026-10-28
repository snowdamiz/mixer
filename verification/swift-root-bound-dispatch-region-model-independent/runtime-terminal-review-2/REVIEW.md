# Terminal review: accept only the isolated synthetic host-model slice

Recommend root accept the reviewed model v2 source and its finite host tests
under exact v4 plan
`4e2959b148ec1ef4a48e708076ac28be2951b633ef5400c4d1be65cd7f8bec8a`
and controller
`bc0806b2307ea2180cc7f99cac8cb30481a4077fec854154aea222ad351074ab`.
Release SHA
`a56971cf26a81c5a871b95cd8b4e756845f1e56d88e816f81992e35cf4fbf9f1`
binds the exact reviewed source and execution. This is model-only acceptance.

The saved observation matches its receipt hash. Exactly one Debug
`aarch64-apple-darwin` compile returned zero with empty stdout/stderr. Exactly one
host-test command returned zero. Its 24 distinct passing names match every name
in the frozen roster; the final summary has zero failures, ignored, measured or
filtered tests. Full output lengths/hashes, argv, environment and cwd match the
plan. Source and tool identities remain pinned; the compiler version is reused
from the prior pinned tool receipt, not newly queried.

Compiler PID/group/session 99318 and host-test PID/group/session 99321 each have a
positive WNOWAIT exit-zero completion observation, recorded reap/return code,
`completed-child-no-signals` cleanup path and group absence. Neither record has
an active signal or syscall error. The reviewed code's normal-completion branch
has therefore been observed for both owned children. Failure/timeout/EPERM
branches are not qualified by this successful run, and no earlier EPERM cause
is diagnosed.

The 2,195,320-byte binary has the same
`ca8b7433ce7a409a9e2e01944154f56511577b3b0586864498ad3446ea562514`
hash in pre-run, post-run and final bounded inventories. The generated directory
was removed after owned closure and is currently absent by a filesystem-only
check. The controller reports all 117 runtime input pins rechecked and no
errors. This review independently reconstructed that exact finite pin roster,
verified its current expected values, and checked 163 total source/evidence/tool
inputs before and after with equal hashes. Historical runtime checks are
reported by the exact reviewed controller; these current checks do not pretend
to recreate past filesystem state.

The signal cutoff is 1.482063708 seconds, below the 53.5-second posthash and
55-second overall limits; observed signals are empty. The reviewed source places
all hashing and observation digest before the one-way cutoff/pending snapshot,
then publishes only the receipt. Recorded command intervals meet the 30/45-second
deadlines, and cleanup/posthash precede that cutoff. Generated row equality
concerns regular-file content; empty-directory identity is not asserted.

The original attempt remains failed, with missing exit/reap status and zero
tests. Its receipt and later cleanup hashes remain unchanged. Identical binary
bytes in the two attempts do not supply the original missing status or turn it
into a pass. The separately selected successor ran once without automatic retry.

The accepted boundary is the typed finite semantic/physical-declaration model,
checked synthetic capacities/unions, and its 24 finite tests. Fitting Synthetic
or ReviewedBound-looking input still yields only ModelOnly. No actual product
File, allocator, dispatch, error or destruction path ran, and no production
selector, quote, grant or refund became available.

The accepted contract explicitly permits preparing the next narrow
physical/capacity evidence plan after this host result. Focus that source-only
plan on the dispatch return boundary: complete AdmittedReturn (13,624 bytes),
separate Body frame, and ChildWrap (13,640 bytes). Select exact-toolchain region
evidence or a reviewed implementation making storage explicit; specify required
arena identity, offsets, alignment, capacity, liveness/aliasing and complete
backing evidence before authorizing another code slice. Unknown frame/backing
facts must still refuse. This receipt alone authorizes no further canonical
product implementation.

Actual physical capacity, backing upper bounds, numeric prices, complete quote,
root durable funding/custody, product integration, real File/error/drop behavior,
native/device qualification, FieldLog, OTA and GA remain pending. This reviewer
only parsed saved evidence and read source/hashes: no compiler, controller,
model/test replay, process query, signal, version/native/UI/capture/device action,
canonical metadata edit, commit or push. No child/build artifact was created by
the reviewer and no cleanup is owed.
