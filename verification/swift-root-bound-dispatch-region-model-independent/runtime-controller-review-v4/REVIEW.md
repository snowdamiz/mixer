# V4 source review: recommend one separately released successor attempt

No blocking source finding remains for controller
`bc0806b2307ea2180cc7f99cac8cb30481a4077fec854154aea222ad351074ab`
(14,401 bytes) and successor host plan
`4e2959b148ec1ef4a48e708076ac28be2951b633ef5400c4d1be65cd7f8bec8a`.
Recommend one root-owned attempt with Python `-B` and assertions enabled: one
compile, then only on recorded compile success one 24-test invocation, no retry,
within the same cumulative 55-second bounds. This is source review, not an
execution release or passing result.

The completed-child branch now calls `reap_completed` without TERM/KILL. It
records the actual return code after waiting for that positively WNOWAIT-observed
child, then observes group absence read-only. A surviving/reappearing numeric
group does not authorize a post-reap signal. The separate running-child cleanup
branch retains original custody and rechecks completion before each signal.
EPERM sets a sticky permission-refusal flag; subsequent close calls stop before
further control probes, retries or escalation. Unknown closure continues to
prevent pass and owned artifact removal.

WNOWAIT/reap/active-signal/absence operations now retain an operation name,
errno and traceback on OSError. Completion observations retain PID/code/status;
successful reap retains the exit code. This improves a future receipt's
diagnostic precision. It does not identify the old failing syscall, establish
that unconditional signaling caused EPERM, or prove the successor will run.
Initial getpgid/getsid remain outside the named-call wrapper and share the outer
traceback line; they precede custody, so failure there grants no signal authority.

The plan preserves exactly the two reviewed Rust sources, 24-test roster,
toolchain/SDK/linker, full environment apart from fresh TMPDIR, resource caps and
30/45/49/53.5/55-second deadlines. Only output paths change in the two argv
arrays. `command-2`, v4 runtime output and v4 release paths are distinct from the
failed attempt and absent at this review. The controller verifies the new plan's
same memory bytes before parsing and includes that plan in pre/post pins. Whole
preparation/control/source pins, capped output, bounded pre-launch generated
inventory, binary/file equality, cleanup gates and finite signal cutoff remain.

The prior failed receipt and later cleanup are hash-bound provenance fields in
the successor plan and were independently verified here. The controller does
not add those two historical receipts to its runtime pre/post pin table, so do
not claim it runtime-rehashed them. Fresh paths prevent this controller from
writing the old packet. The original result remains failed, with one compiler
record, no recorded exit/reap result and zero tests. Later absence/removal does
not supply a missing original compiler success.

The complete diff reconstructs the successor; all unaffected plan fields were
compared with the original plan. This review checked 145 unique source,
evidence, plan and tool inputs before and after with equal hashes. No controller,
compiler, model or tests were imported or executed. No version, process, native,
UI/capture/device operation, canonical metadata edit, commit or push occurred.
Generated hash-row equality concerns regular files; empty-directory equality is
not asserted. Actual physical capacity, prices, grants, root funding, complete
ownership and GA remain pending. No child/build artifact was created here and
no cleanup is owed.
