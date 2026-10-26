# Closed cache-state fixture

This directory contains the exact independently reviewed fixture runner and its
closed source pack. It qualifies the isolated cache-state host component; it does
not integrate that component into the live interpreter or admit arbitrary files.

Run the 29 focused runner controls with:

```sh
mkdir -p verification/swift-cache-state-ci/logs
python3 -B verification/swift-cache-state-ci/test_runner.py -v
```

For a full run, create the owned `runs/` directory if absent and pass an existing
compiler launcher plus a fresh immediate child of that directory:

```sh
mkdir -p verification/swift-cache-state-ci/runs
python3 -B verification/swift-cache-state-ci/check_cache_state.py \
  --rustc "$(command -v rustc)" \
  --out verification/swift-cache-state-ci/runs/local-1
```

Only stable Rust 1.99.0 or 1.98.1 on aarch64-apple-darwin is admitted. There is no
installation or compiler fallback. Active work is limited to 600 seconds, with a
separate 60-second cleanup deadline and 60 seconds per child. Every child receives
owned temporary directories. Expired cleanup fails and preserves recoverable
scratch. Avoid changing Git HEAD/tree during a full run; they are recorded as
context; hashes bind exact observed source/output identity in a quiescent trusted
checkout. They do not establish custody against an adversarial checkout writer.

The accepted local run uses Rust 1.99.0 and passes 103 commands. Each Debug and
optimized mode covers 384 method invocations representing 132 distinct methods,
25 API dispositions, 23 accounting layouts and 31 distinct File cases. Repeated
capture of a case is not an additional distinct case. Historical whole-suite
timeouts remain failed observations; partitioned coverage does not prove equal
performance. The pack manifest fixes all source and expected observation bytes.

The dedicated `swift-cache-state-fixture` Actions job runs focused controls and
the full fixture after a shallow sparse checkout, then retains the complete
directory, including hidden inputs and failure evidence. The dedicated job now passes on actual Rust 1.98.1 macOS arm64: all 103
commands and 29 focused controls pass within the unchanged deadlines. Source and
retained output evidence are verified in
`../swift-cache-state-ci-workflow-root-review/CI-1.98.1-qualification.json`.
This qualifies only the closed host fixture. See the root selection in
`../swift-cache-state-ci-workflow-root-review/selection.json` and independent
decision in `../swift-cache-state-ci-independent/corrected-review/final-decision.json`.

No native runtime, physical phone, simulator/emulator, public V2, signing/store,
published-package FieldLog, customer operations or GA acceptance is implied.
