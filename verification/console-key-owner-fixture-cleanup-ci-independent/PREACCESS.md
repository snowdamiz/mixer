# Independent CI fixture-cleanup preaccess expectations

Prepared before reading the active canonical test or correction lane. The
committed fd92138 test source equals the preserved original test SHA-256
b31c249da0fc37743afe328e0232a0c347e8489094fbaaf50b9c813b9e368e33.
The retained remote log is
7862767965b6263a5dcc8e2b3c4b119c398eda37e7961897e151aada2ee398f2;
the failed receipt is
089f8f7a1ed250bbceb00464444d932b3458be106d96caa8d44c96e9492e678a.

The six retained failures are existing KeyOwnerTest on_exit callbacks calling
GenServer.stop: K01 manifest limits, K08 cold storm, K08b eight profiles, K09
rotation, K01b versioned replacement, and K01 lifetime history. They fail with
no-process or concurrent sys.terminate shutdown exits after their test bodies.
The remote log records all seven new lifecycle tests passing and ends with
684/690 passed, two skipped, six failed. This is a failed full CI run.

The source-grounded diagnosis is a lifecycle ownership race. start_owner starts
the worker supervisor through ExUnit, then starts KeyOwner.start_fixture directly
linked to the test process and adds an alive-check/on_exit stop callback. With
the accepted shared initializer now trapping parent exits, test-parent shutdown
can terminate the owner concurrently with the separately running callback.
Process.alive? followed by GenServer.stop is not an atomic ownership operation.
Logs identify the cleanup failure; they do not independently trace every
parent-exit scheduling event. Do not relax production exit trapping or hide the
race with broad catch/rescue, sleeps, retry, or a name-only registry erase.

The minimal correction should put the fixture owner under the same ExUnit test
supervisor as the already-started DynamicSupervisor. Add the owner after workers
so reverse shutdown stops/drains it first while workers remain available. Use an
explicit KeyOwner.start_fixture MFA, a unique exact child id, restart: :temporary
and shutdown: :infinity. Remove the independently racing manual on_exit stop.
Preserve options, endpoint seam, test bodies and production sources. In
particular K07g intentionally stops its owner and must not cause a replacement;
a permanent/restarting child would silently change that test.

Retain exact owned owner/worker names, PIDs and admission/table cleanup evidence,
without broad process inventories, global term erasure or touching other lanes.
The test helper must still allow one owner per exact name and preserve suspended
TLS-controller resume/final resource assertions in K07g. Existing run-local
MIXER_TEST_IDENTITY_EVIDENCE behavior must remain; accepted evidence is never
overwritten. Compile against the immutable prepared-3 eighteen-source product
closure, excluding active inflight-supervisor edits.

The future exact run selects the six full failed test names plus K07g: seven
existing methods. Keep their assertions and the same test module. Report its
registered total, exactly seven selected/running names, exclusions and skips
honestly; a targeted pass is not a full KeyOwnerTest or Phoenix suite pass.
Compiler warnings, missing terminal counts, wrong selected roster, teardown
callback exits, uncertain cleanup or stale source pins fail acceptance. The old
remote failure remains retained. No new product behavior or GA gate is covered.

This packet authorizes no compiler, formatter, OpenSSL, TLS or test replay and
contains no product edits. A frozen exact patch/runner/plan must be reviewed and
separately released by root. Native/UI/capture/devices, global inventory and all
paused lanes remain paused.
