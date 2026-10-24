# Shared-target contamination correction

Candidate 4's post-metadata `all-features-full-debug` and
`all-features-full-release` results cannot qualify the unmodified product
archive. The earlier source library matrix lists 151 tests. Metadata and later
full-source commands use the same unit executable pathname in each profile;
the later full commands execute 152 library tests, including the derived-only
`experimental_swift_reactor::execution::frozen_construction_metadata`.

`observations.json` binds the old receipt/archive/log hashes and read-only
runtime `--list` output from both retained contaminated binaries. Correct cwd,
explicit manifest, unchanged input hashes and a Cargo `Compiling ...source/vm`
line proved insufficient. The shared target directory allowed metadata test
artifacts to remain in the later product run. No claim about a deeper Cargo
internal mechanism is needed, and subtracting one test cannot repair provenance.
The pre-metadata library matrix is a separate observed scope; it does not
validate the contaminated full regression.

All 47 candidate 4 non-build evidence files, including its source archive,
receipt, logs and document, remain unchanged. The product source and its
algorithm/API/layout/accounting remain unchanged. Root owns a supplemental
fresh-target full product regression and the resulting executable/test-list
binding. This producer did not repeat that regression.

The unexecuted future `../collect_candidate5.py` uses
`../target_isolation.py`. Product commands use only `build/product-target`;
metadata commands use only `build/metadata-target`. Both roots must be fresh
and disjoint. Each subprocess gets a matching explicit `--target-dir`,
`CARGO_TARGET_DIR`, snapshot cwd and manifest. Every unit-test command records
the executable hash and runs that exact binary with `--list`. Product lists
must omit the derived-only metadata probe, while metadata lists must contain
it. A failed binary witness is recorded and stops qualification. The future
collector has not produced a candidate 5 receipt and is not replacement product
evidence.

`synthetic/receipt.json` records six Cargo commands against tiny independently
authored tooling fixtures: product, metadata, then product again in Debug and
Release. Each product binary retains its exact hash and one-test runtime list;
the metadata binary has its separate two-test list. Deliberately copying that
metadata fixture binary into the product target is rejected in both profiles,
and reused target roots are rejected. This verifies the collector correction,
without running VM tests, a Wasm target or any device.

All original full-executor, interpreter, initialize/invoke, growth/unwind,
target, physical-device, published FieldLog, signing/store/customer/operational
and GA limitations remain pending.
