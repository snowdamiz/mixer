# Root-bound layout probe v2: strict JSON and retained launch handles

This separately frozen correction addresses the two independent preaccess
findings before any compiler execution. The original 173-member packet and seal
remain byte- and membership-immutable. Original seal SHA256 is
`c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9`;
original plan SHA256 is
`b76ab36cf7bc1137842ec3bc63d64eb30594e53dfb76c93abdc06e15cb1ae04b`.
The independent preaccess oracle is unchanged. This packet starts no compiler,
version command, strategy probe, host/native/runtime, UI/capture, network or
phone work. It does not release the compiler slot.

## Correction R01: unambiguous JSON objects

The previous `json.loads` could silently take the last occurrence of a duplicate
object key. `strict_json.py` now rejects every duplicate, at every object depth,
including identical repeated values, and rejects non-finite constants.
`diagnostics.py` uses that loader for each complete raw diagnostic line;
`check.py` and the root-release read use it for custody JSON as well.

Raw conflicting-key synthetic controls cover the top-level diagnostic `level`,
nested diagnostic `code`, and nested source-span `file_name`. An additional raw
control rejects identical duplicate keys in a third-level object. These inputs
are constructed as raw bytes because a Python dict/json.dumps round trip would
already erase the duplicate. All earlier source, expansion, concrete size,
closure identity, cardinality and unexpected-diagnostic controls remain.

## Correction R02: no handler-raised exception before handle retention

The previous handlers could raise inside `Popen` or before assignment of its
returned handle. An outer cleanup seeing `process=None` could then miss a child.
`launch.py` supplies one `TrackedLaunch` object. Its launch-in-progress flag is
true from before the constructor call through assignment to `self.process`.
The outer runner's unconditional cleanup reads `launch.process` directly,
independently of the caller's subsequent assignment.

Catchable SIGALRM, SIGINT, SIGTERM and SIGHUP handlers now only append a pending
interruption record. Explicit protected work checkpoints before/after
preflight/launch and during capture raise that request. The launch checkpoint
after constructor return runs only after the handle is retained. Constructor
failure clears the flag in a finally block. This also closes the adjacent
cleanup-entry interval: a signal handler cannot raise out of cleanup or receipt
finalization. Pending signals observed during cleanup remain retained and are
added to failure classifications before acceptance/final receipt. Interrupted
work cannot yield an accepted observation.

No signal blocking/unblocking or `preexec_fn` is introduced. Immediately before
launch, an empty-set `pthread_sigmask(SIG_BLOCK, set())` query observes the parent
mask without changing it. A nonempty mask refuses launch. The compiler therefore
inherits an unblocked mask; no temporary blocked mask can escape into it.

Pure synthetic fake constructors call the real handler method while a fake
child exists but no handle has been returned. For each of the four signal
numbers, the handler returns, the handle is retained, the pending checkpoint
raises and fake exact-PID/group cleanup completes. Controls also cover
constructor failure/no child, immediate postlaunch interruption, cleanup-entry
and finalization interruption, and the failure guard after interrupted cleanup.
No actual signal is sent and no child is started by these controls. The mask
observation is an offline observation of this Python process only.

## Preserved source, command, deadlines and custody

Original146 remains
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`;
diagnostic146 remains
`2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e`.
The exact two named insertions and actual-closure expression replacement remain
the only three source edits. V2 references the original frozen diagnostic
source; it creates no new source edit or substitute closure. Named/closure query
rosters, expected 56 E0308 plus two E0512 errors, exact source/expansion binding,
strict warning rejection and unqualified diagnostic strategy are unchanged.

`plan.json` preserves the original argv, cwd, full environment, toolchain,
source/query data and one-command bounds exactly. Its explicit hashes and checker
compare these fields against the frozen original. The exact argv still writes
to the original packet's `build/layout-proposal.rmeta`. Root extended this lane's
ownership to that **transient build directory only after a later exact root
release**. It must be absent before launch. All command outputs, PID records,
cleanup receipts and observations belong to this v2 directory; none is written
into the original sealed packet. The original sealed source membership remains
unchanged even while a released transient build directory exists.

The existing partition remains work at 44 seconds, owned cleanup by 49 seconds,
posthash/parser/artifact handling by 53.5 seconds and final evidence before 55
seconds. Source/tool hashes check the deadline while streaming. Capture keeps
the original finite stdout/stderr caps. The parser now checks the 53.5-second
deadline before parsing, per raw line/diagnostic and before returning; the runner
checks again after return. Runtime JSON evidence is capped at 262,144 bytes and
the final publication checks the 55-second deadline. There is no retry, broad
MIR command or additional compiler invocation. Generated build files are still
removed only after exact child reaping and exact PID/group absence; ambiguity
preserves them. Intentional compiler exit 1 remains diagnostic evidence only.

`correction-delta.patch` is the complete code delta against original scripts.
`check.py` independently rehashes all original 173 members plus both source146
trees, replays the exact source edits, and pins v2 scripts and toolchain.
`verify_and_seal.py` runs the checker and 42 offline/synthetic controls in the
same Python process, then rechecks original membership before freezing this
separate packet. Its command, exact tool/version, source identities, stdout and
stderr are retained under `commands/final-offline/`.

Actual compiler diagnostic behavior and all actual layouts remain pending.
All work/storage prices, backing capacities, simultaneous peaks, root/child or
forgotten-result funding, complete ownership, native/device/FieldLog/OTA and GA
acceptance remain pending. No byte, price or funding claim follows from this
correction or its synthetic fixtures.
