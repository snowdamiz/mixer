# Dispatcher dead-admission CI setup correction

The retained Phoenix run `40570933769` passed formatting and compilation, then
reported `677/683 passed, 2 skipped` with all six dispatcher tests failing at the
same setup assertion. The registered `KeyOwner` was absent, but its
`persistent_term` value still held an ETS reference. `Admission.acquire/2`
already converts failed lookup of a dead table to `identity_unavailable`; this
packet does not establish a product defect.

The canonical change is confined to
`hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs`. Setup now
accepts an absent pointer or an ETS reference for which `:ets.info/1` returns
`:undefined`. It still refuses a registered `KeyOwner`, any live table, every
other pointer shape, and a nondefault dynamic Repo. It explicitly checks that
admission fails closed. Setup neither erases nor repairs the pointer.

The exact original test bytes are retained in
`browser_workspace_dispatcher_test.before.exs.txt`. Original remote receipt,
format, compile and test logs are copied under `ci-beforeimage/`; hashes and the
observed failure classification are in `ci-failure-preserved.json`.

`execution-plan-v2.json` binds all 35 current ordinary/product/test sources,
dependency and tool bytes, exact runner/child arguments, and `bootstrap.exs.in`.
The current source closure rebinds the four files changed by formatting and this
setup correction since the earlier fixed-dispatcher packet. The Python runner
has passed static AST parsing; `git diff --check` passed. No Elixir compilation
or regression phase has run at preparation time.

The proposed six sequential private BEAM phases are:

1. Check formatting of the three canonical selected tests and compile the 32
   ordinary/product source files with zero compile/runtime warnings.
2. Execute the exact original six dispatcher tests with a synthetic dead table:
   expect six setup assertion failures and zero dispatch calls.
3. Execute the three corrected suites with no pointer: expect 19 passing tests.
4. Execute the corrected six dispatcher tests with a synthetic dead table:
   expect six passing tests.
5. Execute the corrected six dispatcher tests with a live synthetic table and
   no registered KeyOwner: expect six setup assertion failures, zero dispatch
   calls, and no admission reservation slots added.
6. Execute the corrected six dispatcher tests with a fixed malformed pointer:
   expect six setup assertion failures and zero dispatch calls.

An ExUnit formatter counts actual setup AssertionError stack frames. Erlang call
tracing records `Dispatcher.dispatch/3`, with trace-delivery acknowledgement
before count retrieval. Each private BEAM starts without a pointer, registered
KeyOwner or Repo. Its synthetic owner uses canonical `Admission.new/3` to
publish an ETS reference, then exits normally for the dead-table cases. The
live-table case keeps that process alive until assertions finish. Only this
isolated BEAM's own pointer is closed after pointer-preservation assertions.

The runner requires a root-written `host-execution-release-v2.json` binding the
exact execution-plan hash. The global wall budget is 55 seconds, including
48 seconds maximum work, owned cleanup, hashes and scratch deletion. Output is
capped at 98,304 bytes. Each sequential child has a fresh session with its PID as
PGID; cleanup signals and checks only that exact owned group, reaps its direct
child, and verifies group absence. Explicit owned `mkdtemp` scratch is removed
only after every created child is reaped and every owned group is absent; it is
retained if cleanup cannot be proved. Handles remain available to outer cleanup
even if selector setup or inner cleanup throws. No global process
inventory, DB, HTTP, JWKS, real KeyOwner, browser, UI/capture, native runtime or
phone work is authorized by this packet.

After release, exact rendered bootstraps, arguments, output, actual tools,
PID/PGID cleanup and source rechecks will be retained without overwriting earlier
evidence. This bounded host correction does not replace corrected remote CI,
configured identity/database/session integration, operational qualification,
published FieldLog dogfooding, native/device acceptance or GA gate evidence.

The unexecuted first runner/plan/template are retained under
`unexecuted-pre-review/` and byte-identically at their first frozen paths.
`run_regression_v2.py` reads only `execution-plan-v2.json` and requires its path
and hash in the v2 release. Root review requested explicit process-before-scratch
cleanup ordering; execution-plan revision 2 implements that requirement.

## Observed terminal result

The single root-released v2 run completed all six phases in 5.844 seconds with
21,813 bytes of bounded output. Elixir 1.20.4 / OTP 29 compiled the 32 source files
into 35 modules with zero compile/runtime warnings; every phase's test compile
also had zero warnings. All three selected test files passed formatting.

The exact original dead-pointer case reproduced six setup failures with zero
dispatch calls. Corrected absent-pointer tests passed 19/19; corrected dead-pointer
dispatcher tests passed 6/6, each observing 31 dispatch calls. Corrected live-table
and malformed-pointer controls each produced six expected setup AssertionErrors
and zero dispatch calls. Pointer preservation, no registered KeyOwner, no Repo
startup and the unchanged default dynamic Repo were asserted throughout.

All six direct children were reaped; exact owned PGIDs 81740, 81787, 81837, 81891,
81937 and 81983 were absent after cleanup and in terminal checks. Owned scratch
was removed. All 988 original inputs rechecked unchanged; 559 copied inputs were
verified. `terminal-analysis.json`, `regression-v2-receipt.json`, retained stdout
and six rendered bootstraps contain the exact evidence. The expected rejection
runs are recorded as rejected test setups, not as passing dispatcher tests.

This packet is frozen after terminal analysis. Corrected broad Phoenix CI and
all integration/operational/native/device/customer/GA gates listed above remain
pending. Root owns central metadata, commit/push and remote follow-up.
