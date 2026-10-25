# Standalone fixture framing CI evidence

The accepted framing foundation now has a narrow direct-`rustc` CI runner at
`scripts/ci/check-analyzer-framing.py`. It compiles the unchanged library with
`-Dwarnings`, then compiles and executes the exact frozen 20 producer plus 24
independent methods. It grants no semantic or release acceptance:
`storedPrefixValidated=false` and `fullReplayAccepted=false` remain unconditional.
The preparer creates CI evidence only; it is not a real analyzer source authority
adapter. The binding scope remains `mixer-product-plan.md`.

The runner pins producer seal
`777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63`
(270 members) and independent review seal
`a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e`
(624). It hashes all 894 sealed members and both seal sidecars before and after
execution. It copies only the four selected Rust sources and 17 historical
stream/sidecar pairs, plus its executed collector source. No old packet runner
is executed or changed, and the complete old packets are not copied into CI
output. Selected source and output snapshots are checked again after execution.

The unchanged analyzer source is
`ce8f3013f7ecc9ccdb5ca88db75b7019f6af24cff995907d5d95012edb5d1757`.
The independent test root and producer tests retain their reviewed relative
paths. A separate test-only `source/inputs/framing.rs` is the unchanged analyzer,
one LF, and the unchanged private review probes. Its hash remains
`7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747`,
matching frozen review run-2. Library compilation uses the unappended source.

Usage requires an existing output parent and a fresh output directory:

```sh
python3 -B scripts/ci/check-analyzer-framing.py --output /existing/parent/framing
python3 -B scripts/ci/check-analyzer-framing.py \
  --rustc /explicit/toolchain/bin/rustc --output /existing/parent/framing-explicit
```

There are no source, test, Cargo or arbitrary argument overrides. Default
`rustc` selection resolves the executable from PATH; a rustup shim is resolved
through its `which rustc` command in the repository's context. Both launcher and
selected compiler identities, hashes, verbose version and actual host are
recorded. Explicit compiler paths are supported. Output refuses symlink
ancestors, parent traversal, `.git` components, existing destinations and
destinations inside the frozen packets. These local path checks assume a
quiescent caller; they do not establish adversarial path custody.

Each command has raw stdout/stderr, exact argv/cwd/environment overrides, exit,
timeout, elapsed time, output hashes and child-return status. Version, revision
and listing commands have 15-second limits, each compile has 60 seconds and the
test execution has 120 seconds. Timeout kills only the owned process group and
waits for the child to return. Checks use explicit exceptions and remain active
under Python `-O`. Both the listed and executed method names must match the fixed
44-method inventory; an ignored, filtered, missing, substituted or failed method
cannot pass.

The output retains the complete selected source/fixture closure, appended test
source, collector, logs, receipt and surviving test-created inputs/reports.
All 17 original sidecars must still say `invalid`/failure 15 and match their
captured stream hashes. The independent footer observations remain seven refused
and ten observed; they never reclassify the historical sidecars. Compiler
products are hashed and removed with scratch. Cleanup requires the exact owned
scratch inode/marker and returned children, preserves failure files, and deletes
only that scratch tree. Large failed sparse fixtures are retained losslessly
with streaming gzip rather than a large raw artifact. Changed ownership or a
scratch link fails cleanup and retains the tree for inspection.

The existing macOS `swift` job runs this check immediately after policy integrity.
Its following `always()` artifact step uploads only the named receipt, ownership,
command logs, selected `.rs` files, collector, historical inputs and retained
test files from `$RUNNER_TEMP/analyzer-framing`. Every selected input is
nonhidden. Existing job timeouts, toolchains, commands and platform checks are
unchanged.

The initial proposed Linux placement was corrected before any Linux run: the
frozen producer and independent controls require Darwin `Metadata=144` and
`Result<Metadata>=152`. Those tests are unchanged. The runner's standard-library
orchestration is portable, but this selected closure is qualified only by its
observed Darwin environment. Linux remains unqualified and unselected; there is
no failed Linux run to report. Remote macOS CI remains pending root delivery and
inspection.

Local evidence in
`verification/swift-ordered-retention-analyzer-framing-ci/local-darwin-1/receipt.json`
records one actual selected execution at
`4af8b7e1e451077aefc5ffbb213f84bf1b3d02e2`: Rust 1.99.0,
`aarch64-apple-darwin`, Python 3.14.8, all 44 methods passed, no ignored/filtered
methods, all 894 frozen members unchanged, 17 unchanged sidecars and owned scratch
removed after children returned. Thirteen focused runner controls pass in
`commands/runner-tests-2/`; the earlier 11-control pass is retained in
`commands/runner-tests-1/`. The checks cover output safety, exact inventory,
optimization behavior, failed compiler receipts, explicit compiler/rustup
selection, partial logs, descendant timeout termination, retained failure bytes,
sparse compression and cleanup ownership. This is host evidence only.

No live VM, Cargo/dependency, source preparer, CLI, target driver, hosted harness,
authority driver or rejected worker is imported or executed. Computer use,
capture, native simulator/emulator runtime and phones remain paused; no native
or unrelated process or instance was started or queried. Semantic replay and
real adapters/custody, compiler/native/device/signing/store/customer/operations,
published-package FieldLog and GA remain withheld. Root owns integration,
execution metadata, commits/pushes and remote CI acceptance.
