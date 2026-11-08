# Ordinary fixture mocked-clock correction

This is a thin, uninstalled sibling for the ordinary `swift-cache-state-fixture`
job. Root owns `.github/workflows/verify.yml`, integration, Git delivery and host
selection. This packet selects no dispatch or retry.

Engine run 40810235312 at the supplied `836fc67b` revision passed the 16 adoption
and nine materializer controls, then ran all 36 runner controls with 32 passes
and four errors. The complete 103-command fixture never started. The exact
retained artifact's runner, test and adapter sources match the frozen checkout
sources. The actual host monotonic origin was not retained. Source and guarded
counterexamples establish a clock-domain defect: `mocked_command()` sets a
deadline from the host clock plus 20 seconds before `accounting_row()` substitutes
a fixed 100-second clock. A host origin below 80 seconds exhausts that synthetic
deadline before creating a command receipt; the success control raises the
deadline error and the other three controls then index an empty command list.

`control_source.py` requires the exact 27,413-byte frozen test preimage at SHA-256
`e7ce50d89ef974d26d8c7a449f84964d6df36d7a279df6013dba932937f4e257`.
It inserts only `c.deadline=clock.monotonic()+20` immediately after the test's
fixed-clock construction and before the original timeout side-effect sequence
is assigned. The allowance remains 20 seconds. The timeout's original
`[100.0, 101.0, 101.0]` sequence and all four accounting/custody assertions remain
unchanged. `controls.diff` is the complete effective source difference. No
runner, pack, compiler validator, runtime deadline or production source changes.

The new `test_runner.py` verifies the sealed source closure, compiles the exact
effective test source using the frozen filename, and executes it in the actual
main module's globals. The original `unittest.main()` therefore discovers all
36 original test methods. The original `HERE`, optimized-child working
directory, frozen runner imports, evidence retention destinations and teardown
semantics stay at frozen v2. The source contract tests exercise actual-main
discovery with only `unittest.main` intercepted; no original method runs during
that discovery check.

`adopt_fixture.py`, `test_adoption.py` and `offline_guard.py` are byte-identical
copies of the frozen ordinary adoption packet. The adapter's original exact
function/globals reuse of the ordinary compiler validator, one-invocation policy,
installed-job equality, source pre/postflight and source retention remain
unchanged. `dependencies.json` retains all original 123 dependency rows and adds
the 14-file frozen adoption closure, for 137 exact bindings. It preserves the
original compiler-policy and fixture-source objects. No second fixture pack or
runner ships here.

`workflow/original-job.yml` is the exact frozen ordinary job preimage. The minimal
`workflow.diff` changes only the adapter sibling path, routes the runner-control
command through this wrapper, and adds this packet to sparse checkout and the
existing 14-day hidden-file-inclusive archive. All 16 adoption, nine materializer
and 36 runner controls remain required before the sole complete 103-command
fixture. Rust selection, `RUSTUP_AUTO_INSTALL=0`, existing two-release ARM64
allowlist, per-child 60 seconds, active 600 seconds, cleanup 60 seconds, per-stream
8 MiB, always-run source postflight and archive remain unchanged. The old packet
stays in sparse checkout and archive because its closure is now also bound.

Local checks use Python 3.14.8 and install operation guards before subject imports.
The unchanged adoption guard and supplemental guard deny actual process,
session/group, signal/timer, wait and socket APIs. Only the selected four fully
mocked CPU controls execute locally. The unmodified source is reproduced at
synthetic host-clock origins 0 and 1000; the corrected source is tested at both
origins. The low-origin baseline's four expected errors are retained only under
ignored `logs/local/`. The high-origin baseline and both corrected origins must
pass all four original assertions. Source/contract checks also verify all 36
unchanged names/bodies, actual-main discovery, exact one-line replacement,
unchanged compiler/fixture policy and exact job routing. The 16 copied adoption
controls remain pure and guarded. `checks.json` records actual results.

Commands from repository root:

```sh
/opt/homebrew/bin/python3 -B verification/shared-fixture-clock-controls-correction/test_clock_controls.py
/opt/homebrew/bin/python3 -B verification/shared-fixture-clock-controls-correction/test_adoption.py -v
/opt/homebrew/bin/python3 -B verification/shared-fixture-clock-controls-correction/adopt_fixture.py verify
```

The full 36 runner controls and 103-command fixture are unrun locally and remain
pending on a fresh remote ordinary job. No compiler, Rust/Swift/Elixir/product
runtime, native instance, UI/capture, process inventory or held-process probe was
started by this lane. Native/UI/capture and all physical-phone, local custody,
Unit A, hosted and GA holds remain. FieldLog run 40802230894, PGID 2424/PID 2621,
protected dirty hosted sources and `.wrangler` remain untouched. Raw logs and
failed counterexamples remain local. This evidence grants no release, signed
authority, published-package dogfood or GA acceptance.
