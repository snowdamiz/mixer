# Executable actual-source test plan (proposed, not run)

No implementation/test compilation was performed for this preparation. The
following is acceptance work for the separately selected candidate. Retain exact
argv, tool version/host, revision and full source closure digest, started/ended
times, exit/timeout, stdout/stderr, output lengths/hashes and cleanup. Run the
existing accepted compiler without installation/fallback. Preserve 60-second
per-command deadlines and owned temporary directories. A timeout remains failed.

## Compile and invoke the real private adapter

After defining the module in the copied actual VM crate, use bounded targeted
unit groups; do not execute the whole VM suite or a target harness:

```sh
cargo test --offline --manifest-path verification/swift-cache-state-profile-adapter/source/vm/Cargo.toml --features experimental-swift-reactor --lib diagnostic_profile_tests::rows_ -- --nocapture --test-threads=1
cargo test --offline --release --manifest-path verification/swift-cache-state-profile-adapter/source/vm/Cargo.toml --features experimental-swift-reactor --lib diagnostic_profile_tests::rows_ -- --nocapture --test-threads=1
```

The owned supervisor supplies `CARGO_TARGET_DIR`/temporary directories inside
the candidate packet. Partition into explicitly named groups only if necessary;
retain an original failed attempt and exact distinct-method inventory. Cargo
compilation failure is not a test pass, and grouped success is not performance
equivalence. No dependency fetch or cap increase is allowed. Changes to a copied
closure do not inherit exact-source acceptance from this preparation.

Required actual-source cases:

| Test group | Acceptance observation |
| --- | --- |
| Real complete validation | Independently encode the fixed 34-import ABI, mandatory memory/table/exports and small body set; call `validate_swift_reactor` with the current fixed policy. Malformed body/unsupported policy input produces no usable snapshot and therefore no row output. Do not bypass validation to seed a metadata struct. |
| Absolute indices | All 34 imported rows use exact undefined sentinels; first defined row is absolute 34; all defined rows map to the correct independently known original bytes/type. Include absolute index >=128 and repeated equal body bytes at different offsets. |
| Offset/length identity | Include a leading custom section and code-section/body lengths that cross LEB-width boundaries. Independently tracked encoder offsets match emitted absolute offsets and lengths. Equal bytes at two locations must keep separate offsets. No pointer subtraction recovers provenance. |
| Closed 80,000 rows | Parse the full emitted row body independently: exactly 80,000 rows, exact 2,560,000 length, all reserved words zero, imported/tail sentinels exact; defined count agrees with the validated snapshot. `absolute=80_000`/MAX32 is refused by the row helper. |
| Boundary and narrowing | Minimum accepted body set, multi-byte type/function indices and last admitted defined position where a genuinely valid fixed-policy module fits existing validation limits. If the actual validator cap prevents construction of a nominal boundary fixture, report it untested; do not fabricate a sealed snapshot. |
| Immutable owner | Repeated full row traversals leave `source()`, `usage()`, observations and body identities unchanged. Use the existing allocation observer to prove the row helper allocates zero requests; writer must not allocate a whole profile or row list. Count writer buffering and test support separately. |
| Fixed File boundary | Actual fresh regular output at offset zero succeeds; prefilled, nonzero-offset and nonregular output refuses before writing. Retain actual files and partial failed output; do not claim private mock tests alone exercise the public safe File path. |
| Bounded writer faults | Private injected short/Interrupted/zero/error/overreport and 31/32/33-attempt controls; exactly 32 is not assumed successful unless complete. Returned bytes/attempts match actual completed writes. Failure stops, retains partial bytes and makes no new output name. |
| Layout and complete source inventory | Measure row, observation, error and their full Result/argument/caller places in Debug/-O; inspect exact source transfer/loop/error paths, total work and simultaneous lifetimes. Reconcile full proof/source/metadata retention and writer buffer ownership without borrowing fixture G totals or increasing any cap. |

## Exact accepted analyzer bridge

Compile the unchanged closedpack library directly as a non-test library, so
inherited tests and the 103-command pack are not rerun:

```sh
rustc --edition=2021 -Dwarnings --crate-name mixer_cache_fixture --crate-type rlib verification/swift-cache-state-ci/pack/source/library/analyzer.rs -o verification/swift-cache-state-profile-adapter/products/libmixer_cache_fixture.rlib
```

Use an independently authored small actual-File driver linked to those exact
bytes. The producer should emit the compiler-selected Debug and `-O` variants
under the candidate packet, record hashes and invoke each through the bounded
supervisor. The unit adapter first emits actual small-module rows. The bridge
test supplies only a synthetic header/context and independently encoded stream.
Do not modify the canonical pack to add a seam or import its generator/model.

Required bridge outcomes:

- The derived rows parse under the exact `MIXPRF01` row rules. Synthetic closed
  phase-only and legal miss/build/publication/release fixtures exercise actual
  File admission and cache-state observation using the independently known
  defined body's absolute identity. A miss/build byte amount is a synthetic
  cache amount, never the real decoder's measured cost.
- Alter just type, absolute offset, length, defined flag, sentinel or reserved
  word in each applicable independent negative; the exact parser or subsequent
  body-bearing join refuses. Recompute fixture echoes if needed to prove that
  digest equality cannot repair the wrong semantic row.
- A body-bearing record naming an import or undefined tail refuses. A record
  with matching bytes but the other function's offset refuses. A real derived
  row does not make unsupported Failure14 applicability available.
- Every outcome keeps all four authority getters false; report remains exactly
  49,152 bytes with semantic regions/validity unavailable as before. CAP remains
  unknown tail; late framing/drift/output failure suppresses fixture extent.
- Capture source hashes before and after the bridge and prove the canonical
  runner/manifest/source triplet was unchanged. Do not use this bridge to claim
  arbitrary File admission or Rust 1.98.1 qualification of a different source.

## Required independent review and delivery boundary

Independently rerun the candidate's exact selected groups in both modes and add
new independently encoded offset/type/import/undefined and fault cases. Review
all added production source, not only generated expected rows. Verify the seal,
immutability and complete changed-file roster. Root decides development slice
acceptance and any later canonical integration. New CI coverage requires a
separate closed deterministic runner contract and compiler qualification.

Native simulator/emulator/UI/capture and physical-device work remains paused.
No test here qualifies native behavior, target runtime, release eligibility,
signing/store, immutable published-package FieldLog, customer operations or GA.
