The root-selected V3 lifecycle implementation is integrated into the live VM as
three exact files: `lifecycle.rs`, `lifecycle_tests.rs`, and
`memory_growth_operations.rs` beneath `vm/src/experimental_swift_reactor/`.
Every other file in the accepted VM scope is unchanged. Both Cargo files and
all files beneath `include/`, `src/`, and `tests/` match the complete 132-file
candidate manifest, with SHA-256 closure
`93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38`.
VM tooling and temporary targets are outside that source-manifest scope.

The integration follows root's exact runtime acceptance
`verification/swift-reactor-lifecycle-runtime-v3-root-review/runtime-acceptance.json`
(SHA-256 `4ab6960d7e0bf99d94db569bc8d29a7a62bab53a9f3bd8d9fcef6c8799222c2e`).
Before copying, the two lifecycle files were absent and memory growth matched
its selected prior hash. The packet records those preimages, the exact selected
changes, and full before/after/final manifests. The accepted source bytes were
copied without modification; historical candidate-stage comments in those
immutable files do not describe the later integration receipt.

The implemented entry is private to the experimental Swift reactor. It uses
the existing original reactor owner and the fixed initializer function 35 and
corpus function 62. An uninitialized owner permits initialization; a ready owner
permits corpus invocation. Calling the corpus before initialization or
initializing an already ready owner produces an ordinary refusal before
preparation. A terminal owner blocks further requests. This introduces no
public lifecycle API or signed/public execution entry.

Accepted execution enters the existing growth-capable frame dispatcher. The
initializer must return no value, and the corpus must return exactly an i32.
The result remains local until consuming completion has reconciled the original
owners and clean frame barrier. Initialization publishes ready only after that
completion succeeds. The final checkpoint observes cancellation and deadlines
while the admitted phase still exists. Failure terminalizes the original owner,
releases pending growth, drains active frames, and retains actual cleanup
authority when completion cannot finish. Repeated calls use the same remaining
fuel, accounting, WASI state, memory, globals, and table reads. Guest table
mutation remains unsupported.

Root previously accepted the exact candidate's selected 30-row host matrix:
1,602 passing test identity executions, four Cargo checks, two qualified Node
oracle rows, and removal of all 30 owned targets. This integration retains that
evidence through the exact source closure and the 978-file final seal
`027d3895f69f3f6c92638c44e7304fa2f65e34075f564e388c8751e3ea133d27`.
All 978 pins were checked again before integration and by the additive replay.
The 1,602 executions were not repeated. The existing full raw compiler/MIR
proof and its finite representation selections remain in the selected packet;
this integration grants no additional accounting credit.

A fresh macOS arm64 host build of the live Swift-only library produced a fresh
test executable. Its filtered list exactly matched the accepted 23 lifecycle
test identities, and all 23 passed with zero failures or ignored tests. The
required command from `.github/workflows/verify.yml` also passed:

```sh
cargo clippy --locked --manifest-path vm/Cargo.toml --lib \
  --features experimental-swift-reactor -- -D warnings
```

Rust 1.99.0 (`b940084d7`, host `aarch64-apple-darwin`) and Cargo 1.99.0
(`5f94df478`) were used through the selected stable toolchain. Before and after
each live command, the Rust proxies, actual compiler, and every qualified
sysroot `bin/` and `lib/` file matched the prior evidence. Actual commands,
restricted environment, versions, source identity, stdout/stderr, test
identities, executable bytes and process-group checks are retained in
`verification/swift-reactor-lifecycle-v3-integration/`. All four commands used
one fresh owned target with incremental compilation disabled. The target was
removed after an empty `lsof` holder check; no native instances were created
and no other project's processes were changed.

These are host synthetic tests and a private implementation integration.
They do not complete any original SL row's full authored matrix. The complete
failure/checkpoint/budget/WASI permutations, SL12 guest table mutation, real
full 53 MB Swift reactor, public/signed execution, native simulator/emulator
matrix, final physical-phone matrix, immutable published packages consumed by
FieldLog from a separate repository, store/customer/operational evidence, and
GA gates remain pending. No shared tracker, Git, public release, signing,
credential, customer or native-runtime operation was performed by this lane.

The additive packet can be checked without running a compiler or test:

```sh
python3 -B verification/swift-reactor-lifecycle-v3-integration/verify.py
```

Its seal covers this document and all retained integration evidence. The
one-shot `integrate.py` records the actual mutation and host commands; it must
not be rerun against an already integrated tree. Root remains responsible for
acceptance, shared trackers, commits, pushes and CI review.
