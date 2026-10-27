# Swift host CI-selection group cleanup regression

The Swift job in run `40507305688`, attempt 1, failed its Python CI-selection
step at source `c4d04e56d0175f4c036c878db5ccb7bd9c7b30f0`.
Of 63 tests, only `test_descendant_timeout_return_and_group_identity` failed:
its command timed out and its direct child returned, but the command group
remained visible. The full raw job log and job metadata are retained here.
Downstream Swift steps were skipped; this packet does not claim they passed.

The old fixture killed a command and its concurrent grandchild together, then
required the host's init process to reap the orphan before the group poll expired.
The source therefore depended on reaping outside the fixture's ownership. The
remote process table and per-command temporary receipt were not retained by the
failed test, so this diagnosis does not claim to have directly observed a remote
zombie. The same unchanged test passed locally in 0.262 seconds; that receipt is
retained as corroboration of environment-dependent behavior, not a CI pass.

The test-only repair creates two real directly waitable children in a fresh
process group and explicitly waits both handles after the runner's real SIGKILL.
The test factory asserts that the runner requested `start_new_session=True`,
then creates a fresh group in the test session so the second owned child can
join. This qualifies whole-group termination and direct-child waits. It does
not qualify new-session creation or orphan-reaping behavior. The production
runner and its fail-closed policy are unchanged; the real timed wait stays 0.2s.

Validation:

- Both focused controls passed. The positive receipt records two exact child
  waits returning `-SIGKILL` and confirmed group disappearance.
- A leader-only SIGKILL mutation caused the real second member to survive and
  the repaired control to error on its wait. Fixture cleanup then killed and
  waited both exact handles. `negative-direct-child-only.json` records this
  expected failure and all waits.
- A deterministic group-visibility control confirms that even an exit-0 direct
  child remains refused when owned-group disappearance cannot be confirmed.
- The complete Python host CI-selection suite passed 64/64 in 7.251s. No native
  runtime, simulator/emulator, physical-device, screen-capture, or UI runs occurred.

`checks.py` reproduces the focused positive, leader-only mutation, and host
suite with commands recorded in `receipt.json`. `test-source.patch` binds the
single source change; source hashes and the base Git tree are retained in the
receipt. `freeze.json` hashes this evidence packet. This packet is frozen for
independent review; delivery and fresh pushed CI remain root-owned and pending.
