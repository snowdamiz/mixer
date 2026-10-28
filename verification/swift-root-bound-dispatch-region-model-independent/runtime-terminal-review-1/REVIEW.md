# Terminal review: failed attempt; later cleanup is separate

The original attempt remains failed. One compiler command was recorded for
PID/PGID/SID 89514, with matching planned argv/environment and initial custody.
Its recorded start/end interval is about 0.390 seconds. Both retained compiler
streams are empty. The bounded final inventory found a 2,195,320-byte binary,
SHA `ca8b7433ce7a409a9e2e01944154f56511577b3b0586864498ad3446ea562514`.
The binary was never executed.

No compiler return code or reap result was recorded. The artifact and empty
stderr do not establish successful compilation. The attempt contains no test
command or test result. Its two PermissionError records do not identify the
failing syscall. The original receipt's `owned_groups_closed=false` and
`generated_directory_removed=false` remain authoritative for that observation.
The receipt's observation hash, stream hashes, exact command/source binding and
later artifact hash were checked offline; the controller records its own
116-pin postcheck as complete.

Later exact read-only evidence reports both group and leader absent. A separate
later cleanup receipt records the same bounded binary hash and owned-directory
removal. The generated directory is also currently absent by a filesystem-only
check. This closes the later artifact-cleanup account; it does not reconstruct a
missing original exit/reap status, pass the original attempt or qualify tests.
No process query or signal was performed by this reviewer.

The proposed narrow source correction is justified: a positively
WNOWAIT-completed owned child should be reaped without unconditional TERM/KILL,
with its actual return code recorded, then group absence observed read-only.
Once reaped, never signal that numeric group to resolve an ambiguous/live probe;
fail and preserve artifacts. Signals belong only to failure/timeout cleanup of
a still-running owned child while original leader custody is retained. EPERM
must record a failed/unknown action without alternate kill methods or implicit
retry/escalation.

Unconditional normal-completion group signaling is a plausible EPERM site,
not an established diagnosis. The current source can also raise process-control
errors in WNOWAIT, identity, reap or absence operations. A successor needs
phase/syscall/arguments/errno and completion-status records around these steps.
Do not promote the hypothesis into an observed cause or call it a verified fix.
Six finite prospective expectations are retained in the JSON review; none ran.

Any future attempt requires root's separately selected successor plan,
reviewed controller and fresh output paths. Preserve the original failed packet
and maintain the one-compile/conditional-one-24-test ceiling, cumulative 55-second
budget, bounded inventories/output, binary/source/tool custody, exact owned
closure and finite signal cutoff. This review releases no new execution.

No compiler, controller, model, test, native/UI/capture/device operation,
version command, process inventory, canonical metadata edit, commit or push was
performed. Physical capacity, prices, grants, funding, complete ownership and GA
remain pending. The original compiler/test result is not accepted.
