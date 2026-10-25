# Swift lifecycle Linux fixture repair

The three lifecycle failures in GitHub run `40142506088`, VM job
`121016995851`, came from a test setup deadline. The unchanged runtime correctly
refused construction after 200 ms, before the tests reached their intended
lifecycle assertions. The repair changes two source files: one helper inside
the existing `#[cfg(test)]` control implementation, and three lifecycle tests.

The source revision is `ccd8e4c3d96f96876a1339a51dc4297f4175d4fc`. The accepted
132-file VM closure is
`64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de`;
the repaired closure is
`6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8`.
The immutable source snapshot, original two files, exact patch, command receipts,
raw outputs, and compressed test executables are under
`verification/swift-lifecycle-linux-fixture-repair/`.

## Observed failure

The recorded CI command was:

```sh
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi,experimental-swift-reactor,experimental-capability-native
```

It used rustc `1.99.0 (b940084d7 2026-09-28)` and Cargo
`1.99.0 (5f94df478 2026-08-27)` on an x86_64 Ubuntu runner. The debug library
result was **388 passed, 3 failed, 0 ignored**. Each failed at the constructor
unwrap in `lifecycle_tests.rs:264`, with `swift_run_deadline`, a 50,738,224-byte
state reservation, 38,319,741 execution work, and **zero guest instructions**.
SL01 and SL14 reported Run origin; SL10 reported Wasi origin. The raw log digest
and relevant lines are retained in `source.json` and `linux-ci-excerpt.txt`.

The validator requires exactly 584 initial memory pages and a 46,713-entry table
(`vm/src/experimental/swift.rs:541` onward). Reducing those would change the
sealed fixture contract. The failed tests had placed a 200 ms deadline around
that construction work, then slept until expiry. Linux debug exhausted that
allowance during setup.

## Repair and regression assertions

`RuntimeControl::test_expire_deadline` exists only in the existing `#[cfg(test)]`
implementation. It requires no earlier sticky failure and an active deadline,
then narrows that deadline to the current monotonic instant and returns it. It
changes only the deadline field. Origin, budgets, counters, cancellation,
reservation state, and sticky failure remain untouched. The subsequent real
lifecycle request performs the actual expiration check and creates the failure.

The three cases now construct successfully before injecting expiration:

| Test | Preserved and strengthened assertions |
| --- | --- |
| `swift_lifecycle_sl01_expired_and_missing_control_refusals_are_nonexecuting` | In both uninitialized and initialized states, expiration leaves normalized usage unchanged; ordinary misuse rejects without changing usage; the allowed request fails with Run origin and no new instruction or host call. |
| `swift_lifecycle_sl10_preentry_cancel_and_earliest_wasi_deadline` | The actual default 30 s Run deadline and 20 s WASI deadline share an explicit start. Construction carries exactly `started + 20 s`, earlier than the original Run deadline, with Wasi origin. Expiration preserves normalized usage and the allowed request fails with Wasi origin, zero instructions, and zero host calls. The pre-entry cancellation variant remains. |
| `swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset` | The absolute deadline is captured before actual initialization and is identical afterward. Expiration preserves normalized usage. The later corpus call fails with Run origin, retains the injected absolute deadline, and adds no instruction, execution work, cache work, or host call. Existing cumulative work/cache failures remain. |

These cases contain no deadline sleep. They use the normal construction
allowance to prepare the fixture, then deliberately expire it. Separate real
clock/deadline runtime tests remain in the 49-test lifecycle inventory. The
repair adds no test identities and skips none.

Removing the exact added helper from `control.rs` reproduces its baseline bytes.
Every other non-test production source file matches the accepted closure.
Production runtime interfaces, limits, deadline checks, and accounting are
unchanged.

## Verification and limits

On macOS 27.0.1 arm64 with the same Rust/Cargo versions, all **49 lifecycle
identities passed in each of four contexts**: Swift-only debug, Swift-only
Release, all-feature debug, and all-feature Release. Each executable used
libtest's default parallelism, with no `--test-threads` override or
`RUST_TEST_THREADS` environment variable. This is **196 passing identity
executions, zero failures, zero ignored tests**. Corresponding ordinary
`cargo check --lib` commands passed in all four contexts.

The builds and checks used `--locked --offline --no-default-features`, plus
`--features experimental-swift-reactor` or `--all-features`, and `--release`
where applicable. Exact commands, compiler/tool hashes, source closure, output
hashes, timestamps, and process-group cleanup observations are recorded for
every command. Recorded command time totals 38.06 s, within a 900 s aggregate
budget and a 180 s ceiling per command.

The broad initial rustfmt check reported existing formatting in the one-line
`host_test_counter` at the end of `control.rs` and in its child
`control_tests.rs`. That historical failure remains in the packet. The exact
added helper and the complete changed lifecycle source pass the scoped check;
unrelated source formatting was preserved.

The owned Cargo target had no live holders and was removed after archiving all
four exact executables. Cleanup reclaimed 183,478,160 logical bytes. No other
targets, processes, simulators, emulators, or device data were changed.

The original Linux failure is observed evidence; a repaired Linux CI run is
pending root review and push. Full all-feature library/integration/ignored,
Frozen/Node, full 53 MB reactor, native/device, signing, store, operational, and
published FieldLog qualification were not rerun. This repair adds no MIR/layout
or production accounting credit, completes no SL row, and grants no GA credit.
Independent reviewer and root acceptance remain separate.

After sealing, the packet can be checked without building or executing guests:

```sh
python3 -B verification/swift-lifecycle-linux-fixture-repair/verify.py
```
