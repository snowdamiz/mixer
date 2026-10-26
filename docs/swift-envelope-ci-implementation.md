# Standalone fixture-envelope pack and host runner

The selected standalone closure is in
`verification/swift-envelope-ci-pack/`. Its manifest SHA-256 is
`4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a`;
its 86 listed members total 8,330,464 bytes with tree SHA-256
`7a73ac6f477b6ac90db0be8444712bc195c184fb21239266c07601f9ea90ecee`.
The manifest excludes itself and is pinned separately in the runner. Root's
preflight independently verifies this materialization. The pack contains the
60 selected originals at 63 selected destinations, the two selected relative
test augmentations, fixed inventories, and immutable small provenance records.
The retained Python model is hashed as provenance; it is never imported or run.

`scripts/ci/check-analyzer-envelope.py` uses only Python's standard library and
direct official Rust compiler invocations. It needs the checkout, Python 3,
git, and an already installed selected Rust 1.99.0 or 1.98.1 compiler with host
`aarch64-apple-darwin`. Rust 1.98.1 is selected for prospective CI qualification;
its full envelope run remains pending. It performs no network or Cargo operation. For example,
with an existing output parent:

```sh
python3 -B scripts/ci/check-analyzer-envelope.py --out analyzer-envelope-ci
```

`--rustc` may select the original compiler launcher. The runner queries that
launcher using `--print sysroot` with `RUSTUP_AUTO_INSTALL=0` in repository
context, then executes the selected `sysroot/bin/rustc` directly. It records the
launcher target, executable hashes, sysroot, verbose identity, Python identity,
OS/machine, git revision and tree, actual argument arrays, fixed working
directories, allowlisted environment, timeouts, and raw command output. It
rejects a manager/installer identity and a compiler host/release outside the
selected combination. Future CI hosts must produce their own fresh receipt.

Before children run, the complete pack and its exact source/derived construction
are checked against the pinned manifest. Every member is copied into the fresh
output, checked, and made read only. Children read exclusively this snapshot.
The unchanged public library and independent source pair stay separate from
the producer test-only augmentation. Old absolute-path producer wrappers and
historical collectors are not runtime dependencies. Neither full historical
seals nor broader hosted code is read or executed by this runner.

The fixed run must list and execute the exact 78 producer methods and the exact
14 independent methods in separate serial binaries, with one test thread,
`--nocapture`, and no filters. Empty, changed, duplicate, ignored, or partial
inventories fail. The producer's two frozen-oracle counters must report 16,170
and 5,544 fresh candidate comparisons. All 32 complete selected layout values
are mapped by name from actual output, including Metadata 144 and its Result
152. The model/oracle generation remains historical evidence. The fresh public
library must first compile the positive external API probe, then each of eight
negative probes must return normal Rust compile error exit 1 with its intended
primary JSON diagnostic at the selected probe source. Missing/incompatible
libraries, unrelated error codes, crashes, signals, timeout, or unexpected
executables fail.

Each command owns one process group. Versions and listings have a 15-second
limit, compilers 60 seconds, and test binaries 120 seconds, within a 480-second
active deadline. Retention and cleanup have a further 60-second allowance.
Timeout and interruption terminate only the owned group, reap the direct child,
and check that group identity has gone before scratch removal. No unrelated
process or native runtime discovery occurs. Caller compiler, test, dynamic
loader, and Python injection variables do not enter the allowlisted environment.

Output must be new and cannot traverse symlinks, `.git`, the immutable pack,
or historical evidence. Every pack member must be a canonical relative regular
file with no symlink ancestor. A failed phase leaves a failed receipt and raw
logs. Postflight rechecks the complete original pack, snapshot, runner, Python,
launcher, and compiler even on failure. Cleanup checks exact scratch
device/inode/uid and its exclusive-create marker. Changed identity, marker,
symlink, special member, or outstanding child preserves scratch for inspection.
Test input/report/failure files are retained first, including independent
actual-File reports; compiler products are hashed before deletion. Large sparse
fixtures are compressed streamingly and verified against their original byte
length and SHA-256. A retention manifest is durable before scratch removal.
An interrupted retention leaves source scratch recoverable. This is local
custody evidence in a trusted quiescent checkout, not adversarial filesystem
custody certification.

The initial runner-control run exposed an overly broad nonzero compiler-exit
check. Its source, tests, failure output, and analysis remain under
`verification/swift-envelope-ci-implementation/runner-controls-1/`. The final
25-method control suite passes both ordinary Python and `python3 -O`; it
exercises pack/overlay mutation, paths, links, output refusal, launcher selection,
missing/failed compilers, exact inventories, diagnostics, partial logs, owned
descendant timeout/reap, sparse retention, independent report retention,
changed scratch identity, interrupted retention, independent postflight continuation
after pack failure, partial snapshot custody, compiler launcher retargeting, and the exact selected compiler tuple policy. These are synthetic
runner controls and do not add product capabilities.

First host run evidence is retained under
`verification/swift-envelope-ci-implementation/run-1/`. Its producer executed
78/78 successfully, all 21,714 comparisons, and all 32 layouts. Independent
compilation failed because the selected unchanged method name
`independent_G_report_reservation_111_112_113_before_selected_cell_mutation`
triggers `non_snake_case` under `-Dwarnings`. The failed run remains failed;
its source snapshot, command logs, output/report bytes, and cleanup receipt are
preserved. Root selected the fixed independent-test-only arguments `-Dwarnings -A
non_snake_case` in amendment
`verification/swift-envelope-ci-root-review/test-lint-selection-amendment.json`
(SHA-256 `1684fb9a329809c8c5bb9a4af20bbceaa7e4d68123a77e54a1115e3534277e52`).
The pack and all source bytes remain unchanged. Library, producer, and API
compiles retain `-Dwarnings` without the exception. A control checks the exact
fixed lane arguments and rejects unknown lanes. No caller flags are accepted.

Run 2 completed the full fresh closure successfully. A final failure-path audit
then strengthened postflight so an invalid original pack cannot suppress checks
of copied inputs or tools; partial copied snapshots get an observed inventory,
and original compiler launcher retargeting fails. Run 3 passed the complete closure under that runner. Root then selected a
second exact prospective compiler tuple because the accepted framing CI receipt
observed Rust 1.98.1 on `aarch64-apple-darwin`. The selected amendment is
`verification/swift-envelope-ci-root-review/compiler-qualification-selection-amendment.json`
(SHA-256 `b7c482646943a34ffae810cfad38962a4b50a455b37d2deab7ea80e38d805e5b`).
The runner accepts only Apple arm64 Rust 1.99.0 or 1.98.1, records its actual
tuple and amendment, and executes the entire unchanged selected closure on that
actual toolchain. Other hosts/releases and malformed identities fail closed.
No caller target list or layout override is available. The pack's 1.99.0 layout
inventory remains historical evidence. A successful local 1.99.0 run gives no
qualification to 1.98.1; actual envelope CI evidence remains pending.

The final runner's complete fresh local qualification is retained under
`verification/swift-envelope-ci-implementation/run-4/`. No earlier producer,
independent, framing, or full-run success substitutes for this invocation. It
passed all 78 producer and 14 independent methods, 21,714 comparisons, all 32
layouts, and API 1+8 in 49.007 seconds
(48.787 seconds active). All eight postflight
scopes passed. It retained 92 test files totaling
54,911,744 bytes, including 79
independent actual-File files, then removed its exact owned scratch. The final
host artifact has 252 files totaling 63,653,797
bytes. Actual Rust 1.99.0 Apple arm64 is qualified only for this host fixture
scope; remote envelope CI remains pending.

Root owns independent review, workflow wiring, metadata, commits, pushes, and
inspection of actual remote CI. The existing framing runner and 44-method
workflow stay unchanged by this implementation. Uploads should use the new
output prefix and explicit pack/source/log/receipt/ownership/retained-byte
allowlist, never broad historical verification-tree wildcards.

Every receipt retains `storedPrefixValidated=false`, `fullReplayAccepted=false`,
and `semanticMetricsValid=false`. The source's public debit stays
`534*S_paid + 47*F_paid + 425*N_B`; selected425, W24, B471, G112, setup534,
finish47, T42/F42, Candidate2048, and parent framing API/report bounds stay
fixed. This check provides no semantic authority, arbitrary reply validation,
physical stack/RSS/CPU proof, or natural public File absence fault evidence.
Compiler targets, native runtimes/devices, signing/store, customer/operations,
separate-repository immutable published-package FieldLog, and accountable GA
acceptance remain pending. Native simulator/emulator runtimes, capture, UI,
and physical phones remain paused/disconnected; none were started or queried.
