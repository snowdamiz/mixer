# Isolated test-only Swift release observer repair

Root selected this bounded repair after the exact retained full Swift diagnostic
stopped at the cfg(test) release observer's `ordinal < 64` assertion. That failed
target remains sealed in `verification/swift-exact-reactor-diagnostic/`; this
packet does not edit it, reread the full reactor or run another target attempt.
No live VM source, production budget/accounting, public API, native instance,
service, provider, credential, Git or shared tracker is changed here.

The selected baseline has 132 files and closure
`6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8`.
The complete original source is copied into this packet and an owned scratch
checkout. The candidate changes only
`src/experimental_swift_reactor/frame_operations_tests.rs`. No dependency is added.

The observer previously recorded every release into its fixed 64-entry array,
even with the default zero fault mask. Long ordinary executions therefore
panicked at the 65th release before producing an engine result. The candidate
adds only this early guard before recording:

```rust
if hooks.release_mask == 0 {
    return false;
}
```

The nonzero-mask recording, original assertion, 64-slot bound, bit positions,
foreign-header fault injection and restoration remain byte-identical. Source
inspection found that every existing release count/order assertion selects a
nonzero mask, including the control-operation tests. The observer is reachable
only through the existing cfg(test) module. This fixes test observation, and
grants no production runtime or accounting credit.

Three independent regressions use actual completely validated synthetic owners,
original frame admission, real cache pins, entry, finish and consuming cleanup:

| Regression | Required evidence |
| --- | --- |
| Default zero-mask state | 130 serial real entry/finish releases on one original owner; each barrier has no live frame/value/control/pin; no release recording. |
| Enabled bit 63 | First 63 releases record without fault; release 64 rejects the actual pin through a real foreign header; all 64 recorded function indices remain exact; reset and original retained cleanup drain that pin. |
| Return to default | Seventeen enabled records, then ordinary zero reset and 130 further real releases without recording. |

The accepted baseline plus the same new regression reproduced the original
`ordinal < 64` panic after 64 successful releases, exit 101. Its exact source,
toolchain, command, raw output and failed executable are retained before any
candidate rebuild. No partial observation is relabeled a production failure.

The isolated candidate closure is
`f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c`.
Qualification completed on macOS arm64 with the pinned Rust/Cargo 1.99.0
toolchain. The packet collector `verification/swift-release-observer-repair/run.py`
uses one owned target, offline locked builds, no incremental compilation, a
180 s per-command limit and a 900 s aggregate command budget.
Owned process groups receive finite TERM/KILL cleanup, including descendants
after a direct child exits. Exact baseline/candidate/per-command manifests,
source snapshots, compiler/proxy/sysroot hashes and versions, environments,
commands, outputs, timings, terminal group states and compressed executables
are retained.

The first complete Swift Debug library run was serial. It reached its 180 s
timeout path after partial passes, then the collector raised EPERM while probing
the owned group after TERM. Its original failure receipt, script, partial output,
source and executable remain. The missing per-command terminal receipt stays
explicitly incomplete: neither exact child exit nor actual duration is invented.
A fresh read-only process inventory found the selected PGID absent, and empty
lsof-holder/inode checks permitted scratch removal. This is a collector/host
observation, not an engine defect or a passing test result.

Root then approved a bounded four-libtest-thread continuation, preserving all
tests, runtime/fixture budgets, and the same command/aggregate limits. The
collector records exact selected PGID rows on an EPERM liveness probe, with
distinct absent/present/unknown outcomes; it never signals broader processes.
The new `resume.py` records the continuation separately. Its complete results are:

| Configuration | Complete library | Ordinary production check |
| --- | ---: | --- |
| Swift-only Debug | 364 passed, 0 failed, 0 ignored | Passed |
| Swift-only Release | 364 passed, 0 failed, 0 ignored | Passed |
| All-feature Debug | 394 passed, 0 failed, 0 ignored | Passed |
| All-feature Release | 394 passed, 0 failed, 0 ignored | Passed |

That is 1,516 passing identity executions, including all twelve executions of
the three new regressions. Old identities remain and none are ignored. A separate
ordinary same-module caller of `tests::Hooks` failed solely with E0433 in each of
the four production contexts, as required. Exact negative source and compiler
output remain. The normal candidate was restored exactly after those checks;
all production source bytes are unchanged in that candidate and the live VM.

The packet has 24 complete command receipts plus the separately retained
incomplete serial attempt. Known complete command time is 188.825 s. The serial
attempt is conservatively charged its entire 180+5+5 s envelope rather than
inventing actual elapsed time, making the aggregate charged budget 378.825 s of
900 s. Every completed command's owned process group is observed empty. The
partial serial cleanup removed 187,831,317 logical bytes; final continuation
cleanup removed 426,682,510 bytes after empty-holder/inode checks. No owned scratch
remains. All six exact compiled executables, including the failing baseline and
interrupted serial candidate, are retained compressed with uncompressed hashes.
No native instance or unrelated process was changed.

After sealing, `python3 -B verification/swift-release-observer-repair/verify.py`
checks source isolation, exact guard removal, complete command evidence,
production-negative diagnostics, archived binaries, preserved serial failure and
cleanup without compiling or executing any guest. The producer qualification is
ready for independent/root review; it does not itself integrate or accept a
live source change.

This packet accepts no full-reactor parity, production accounting, full SL row
or matrix, table mutation, public/signed/native entry, performance/size/memory,
immutable published FieldLog packages, physical phones, store/customer/
operational or GA gate. A fresh exact target diagnostic requires separate root
review and selection after this repair is accepted.
