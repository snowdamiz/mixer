# Failed cache runner controls: current attempt

Run `40730444182`, job `122964999431`, commit
`0b99469dfbeb06ac53ad0223bd070a35f2a6a700` failed before the compiler fixture.
The current control stderr reports 29 tests in 2.264 seconds, 28 `ok` results,
and one error: `RunnerControls.test_owned_descendant_group_is_stopped`,
`test_runner.py:85`, `KeyError: 'owned_group_gone'`.

The `timed_out` assertion on that line completed. `RunnerControls.bad` accepts
and discards a `RuntimeError`, `OSError`, or `ValueError`. The command row does
not initialize `owned_group_gone`; `Commands.stop` writes it only after its
signal/wait/group probes. `Commands.run` finalization can itself raise while
closing streams or stopping the child, before terminal row/save. A primary
accepted error can therefore be replaced by this missing-key error. The exact
primary exception, failing syscall, and current descendant cleanup disposition
were not retained, and this review does not claim to have identified them.

The artifact's sole `runs/` receipt is copied historical evidence from October
27 at source revision `c4d04e56d0175f4c036c878db5ccb7bd9c7b30f0`: its 103 passing
commands are not observations from this failed CI attempt. Both current
`logs/deadline-*-control.json` files are deliberate negative controls, contain
zero child commands, and their test methods reported `ok`. The actual
`Closed cache-state fixture on the existing compiler` step was skipped.

Artifact `12834358283` matches its published 1,429,194-byte size and SHA-256
`6d6edf35c709025b769144bffa94e83040d82321b5d818c97ffd64a58666b85b`.
All 738 entries were streamed for CRC, exact size and SHA-256 checks; actual
expanded bytes were 46,092,520. ZIP and expanded caps remained 8 MiB and 64 MiB.
Only selected evidence was extracted after canonical-path, duplicate,
case-collision, encryption and file-type checks. Signed URLs and the full
download response were neither printed nor retained. A receipt-only repair was
needed after the initial verified transfer because `process` is unavailable
in the Node REPL; the archive was reverified without another download.

`source-bindings.json` binds both runner/control sources, pack manifest,
README, historical receipt, and workflow to the failed commit/tree.
`review.json` records limitations and a conservative diagnostic-correction
proposal. The first correction should retain the original exception and
terminal cleanup uncertainty in current uploaded evidence, while preserving
all existing positive group-disappearance and cleanup-success requirements.
Fully mocked no-child cleanup-error controls can validate that correction;
real custody behavior remains a separate gate for root review.

This reviewer did not import or execute the runner, execute tests or compilers,
probe PIDs/groups, enumerate processes, or start native/UI/Docker/Postgres/
hosted processes. Current failed-CI descendant cleanup is unverified. The
local custody and native/runtime holds remain in force.
