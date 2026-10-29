# Exact compiler admission v3 — source candidate

This thin candidate addresses the missing explicit provisioning witnessed in v2 run [40793279678](https://github.com/snowdamiz/mixer/actions/runs/40793279678). All 36 runner and nine materializer controls passed there; its only fixture command failed because the declared toolchain was absent. No Rust compilation, tests, metrics, or speedup were observed.

Official [release notes](https://doc.rust-lang.org/releases.html#version-1981-2026-09-03) and the [September 3 release announcement](https://blog.rust-lang.org/2026/09/03/Rust-1.98.1/) confirm Rust 1.98.1 was published. The distribution-manifest URL was inaccessible through the web tool; this is not evidence that the macOS ARM64 artifact is unavailable. The candidate preserves 1.98.1-aarch64-apple-darwin with no replacement or fallback.

Root may install the sole workflow candidate at .github/workflows/cache-fixture-compiler-admission-v3.yml after review and select one future invocation. This packet does not dispatch, install, compile or run a fixture. It reuses the sealed v2 runner, tests, materializer, accepted Rust overlay, source review and frozen base by hash; it contains no duplicate pack.

## Executable decision

The remote sequence is source binding/materialization, admission pure controls, the unchanged nine materializer and 36 runner controls, one explicit official Rustup install, a one-shot admission claim, then the unchanged complete fixture. The frozen v2 workflow remains included solely for its existing verifier's source binding. The new workflow's bytes are independently bound before provisioning and again at postflight.

Provisioning has its own two-minute GitHub step. It explicitly runs rustup toolchain install 1.98.1-aarch64-apple-darwin --profile minimal --no-self-update exactly once, using official distribution endpoints and a fresh job-specific RUSTUP_HOME. RUSTUP_AUTO_INSTALL stays 0. The small file-only admission helper cannot spawn processes. It rejects local/non-ARM64 contexts, attempt 2, a reused home, missing/failed/interrupted results, altered output and duplicate fixture claims. Its begin/finish/claim records are admission evidence, not proof of compilation or complete descendant custody. The workflow invokes Rustup directly; no process discovery or custom signaling is added.

If installation succeeds, the named executable test unlocked is the original 103-command fixture. Its existing first two child commands still establish sysroot and exact compiler identity. The 60-second child, 600-second active, 60-second cleanup and 8 MiB per-stream fixture limits, all 1,003 context vectors, assertions and memory safeguards remain unchanged. Any provisioning failure is terminal for this run; there is no automatic retry or compiler fallback. A successful installation alone accepts no fixture behavior.

## Evidence and cleanup limits

Pure controls execute actual admission functions against synthetic files under this sibling. A guard denies nested process creation, session/group access, signals, waits, sockets and sleeps, and restricts writes to this sibling. They exercise success/failure/order/no-retry and source mutation, but do not validate Rustup, Bash execution, GitHub scheduling or installation. The workflow ordering check is a fixed-source check, not a complete YAML interpreter. Remote syntax/execution, installation, the real compiler and fixture remain pending.

Rustup version, install stdout/stderr and shell exit are retained. If the two-minute step is interrupted, the result receipt stays absent and the fixture is skipped; the start receipt and partial logs remain uploadable. No claim is made that every Rustup descendant was reaped. The dedicated RUSTUP_HOME is retained for the disposable GitHub runner's normal disposal, whose completion is not independently verified. It is excluded from artifact upload. There is deliberately no recursive deletion while installer custody could be unknown. The unchanged fixture still owns its normal scratch cleanup, reap/group facts and holds. Pure control scratch is removed after each test.

This is a bounded diagnostic preparation, with no runtime release, default-pack promotion, native/device, performance, customer or GA acceptance. Existing native/UI/capture pauses, disconnected phones, process/custody holds, old FieldLog fetch and UnitA remain untouched. Only root selects delivery and the single remote invocation.
