# Fixture-envelope CI runner parser correction

This is the bounded parser correction selected by root in
`verification/swift-envelope-ci-root-review/runner-correction-1-selection.json`
(SHA-256 `376589fa85f8da663e1f2ae4232ee28471e86cf9603a55ef0bb912381fb9bd7c`).
Independent round 1 withheld acceptance of runner
`4f5c6d64cb821b3fc1984794c96f81c8610c441ec47e3ff37cabb95b01fb43f1`:
compiler identity fields could overwrite duplicates or omit commit identity,
and a negative API diagnostic could use an unrelated in-range primary span.
Those findings and the original producer and review packets remain unchanged.
The corrected implementation requires root's fresh independent review before
workflow delivery or acceptance.

The runner now requires one complete, duplicate-free verbose compiler identity:
binary, release, host, full 40-character hexadecimal commit hash, valid Gregorian
commit date, and LLVM version. Malformed lines and values fail. The header's
release, abbreviated commit, and date must agree with those fields before the
fixed host/release selection. The only selected tuples remain Rust 1.99.0 or
1.98.1 on `aarch64-apple-darwin`. The local run below qualifies only actual
1.99.0 for this host fixture scope; a complete actual 1.98.1 envelope CI run
remains pending.

Each negative probe is bound to its fixed source length and SHA-256 and the
exact operation, item, or field byte ranges and text selected by root in
`api-span-correction-targets.json` (SHA-256
`24c4d9f7bea9e863a4af917c9ea422005448b39521d14672b3e56349c32a9852`).
All 23 primary targets across eight probes are encoded inside the runner.
Every coded error must have the intended code and identifying message terms,
at least one selected primary span in the exact selected source file, and no
wrong or duplicate primary span. The complete selected set must be observed.
This also applies to errors nested in diagnostic children. Message prose is
not pinned byte for byte across compiler versions. JSON duplicate keys at any
level, non-finite constants, malformed diagnostic structures, boolean or other
non-integer offsets, and mixed correct/wrong spans fail closed. The runner has
no caller map override or additional runtime dependency.

The pack remains exactly 86 members, 8,330,464 member bytes, manifest SHA-256
`4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a`,
and tree SHA-256
`7a73ac6f477b6ac90db0be8444712bc195c184fb21239266c07601f9ea90ecee`.
Product source, API, inventories, numeric contracts, compiler selection and
independent-test-only lint allowance did not change. The existing 480-second
active budget, 60-second retention allowance, command budgets, postflight checks,
owned process group handling, output protection, and lossless retention remain.

`verification/swift-envelope-ci-runner-correction/freeze.json` freezes the exact
executed runner and tests plus the complete unchanged pack before the full run.
Its SHA-256 is
`55a32bf6ea9d792ce52917354e50178d992998712a0c676cf9cdcb191d1eb003`.
The frozen runner is
`4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c`;
the frozen tests are
`95adb99fd9f4dff39cf732414e8a287a5f301fe5860aa504e2ba394ccf33a8f1`.
Both final control commands pass all 32 methods under ordinary Python and
`python3 -O -B`. All 25 previous method names remain covered. New controls
include complete/duplicate/missing/incoherent identity, all eight actual
unmodified compiler diagnostic streams, all eight unrelated and shifted primary
spans, mixed spans/errors, incomplete constructor targets, nested errors, JSON
duplicates, and invalid offset/primary-flag types. Literal actual diagnostic
streams inside the tests avoid a historical fixture dependency. Synthetic
controls establish runner refusal behavior, not product semantics.

The fresh complete invocation used Python 3.14.8 and the already installed
Rust 1.99.0 compiler, commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, date `2026-09-28`, LLVM 23.1.1,
on macOS 27.0.1 arm64. Its source revision is
`4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d`; exact dirty source bytes are
identified by the freeze, pack digest, and executed-runner snapshot. It passed
78 producer and 14 independent methods from both listing and execution, API
1+8, all 23 primary targets, 21,714 fresh comparisons against reused frozen
oracles, and 32 layouts in 54.709605 seconds. All 23 commands returned within
their budgets, all eight postflight scopes passed, and the receipt has no errors.
The independent compilation alone retains its fixed `non_snake_case` allowance.

The runner used a new owned temporary output outside the historical packets.
All 252 output files, totaling 63,660,987 bytes, were retained unchanged in the
new packet's `host-run-1/`. `full-run-state.json` records the original paths,
complete inventory, SHA-256 identities and exact prefix mapping to the retained
paths. Both inventories and every retained byte were verified before removing
the exact owned temporary parent. The runner first retained 92 test files,
54,911,744 original bytes, including 79 independent actual-File files, recorded
four compiler product identities, and removed only its exact owned scratch.
`audit.json` reconciles all command streams, listings/execution, selected API
spans, pack/freeze identities, retained original bytes and cleanup. The caller
PATH initially lacked `rustc`; that discovery command returned 127 and did not
start qualification. The successful run selected the existing compiler by its
explicit absolute path. No compiler was installed and no network was used.

No workflow, execution metadata, commit, push, hosted authority, rejected worker,
callback retry, native runtime, simulator/emulator, capture, UI, phone, or
unrelated process discovery was used. Root owns independent replay and delivery.
`storedPrefixValidated`, `fullReplayAccepted`, `semanticMetricsValid`,
`model_imported_or_evaluated`, and `GA_qualified` remain false. Semantic/full
replay, target/native/device, signing/store, separate-repository immutable
published-package FieldLog, customer/operational and accountable GA qualification
remain pending. Computer use and native runtime checks remain paused.
