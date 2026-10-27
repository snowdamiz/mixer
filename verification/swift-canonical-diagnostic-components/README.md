# Canonical private diagnostic components

Candidate implementation of the private unverified typed-result codec and finite original diagnostic row helper, based on canonical `5b80a99aca2bee400786a71f033cc0fd928de89d`. Independent review and canonical CI are still required.

Only five canonical paths change: `diagnostic_result_v1.rs`, `diagnostic_result_v1_tests.rs`, `diagnostic_profile.rs`, `diagnostic_profile_tests.rs`, and `experimental_swift_reactor/mod.rs`. The module declarations stay private and within the existing nondefault reactor feature. No dependency, public runtime route, loader, adoption, snapshot guard/writer or budget changes are included.

The two implementations and both original suites were copied from the accepted typed-result source142 (`58a90a1cec00fd3ffbe4d8bee90476f6e136114dbe3d506da8ab4bbd035b8ecd`). The row implementation also matches the independently accepted adapter SHA256 `7f4458ddadb0480fe48a5ec57cbc1a11bfa074037eb41eeeb5edd8465fff87d8`. Exact original/final hashes and separate acceptance inputs are retained.

The row tests replace their supervisor environment requirement with one fresh owned directory per file test. Atomic directory creation refuses collisions without removing existing entries; File values close before the guard removes its directory. The supervisor explicitly sets TMPDIR to this packet's `owned/tmp` and observes its entries after each command. Final cleanup verifies that directory is empty before removing owned build scratch. Fixture allocation occurs outside the existing allocation-observation intervals. Every original assertion remains.

The first production Clippy command found Rust1.99's `chunks_exact_to_as_chunks` lint in the copied codec. The disclosed one-line repair changes `chunks_exact_mut(8)` to `as_chunks_mut::<8>().0.iter_mut()`; both iterate the full eight-byte chunks in order and discard the same trailing remainder. The initial source manifest, supervisor, failed Clippy log and pre-repair passes remain separate. The final source is freshly tested in both modes; no old execution is relabeled as a final-source pass.

Final-source verification on Rust/Cargo1.99.0, Clippy0.1.99, aarch64-apple-darwin:

- 27 codec methods and 17 row methods pass in debug and release: 44 distinct methods, 88 final-source executions, zero failures or ignores.
- Row cases compare every byte of the 80,000-row (2,560,000-byte) File output, exact absolute offsets, the 79,966-definition boundary, refusal preservation, partial writes, interruption/short-write exhaustion and zero allocations in measured row/write operations.
- Codec cases cover actual typed fields/tags, exact extents and reserved bytes, 54 result combinations, borrowed unverified views, independent final observations, all fifteen ledger words and refusal-before-write behavior.
- Production reactor Clippy passes with `-D warnings`. Default and stream-only library checks pass, preserving feature isolation.
- Three fresh external metadata controls pass: the public validator type remains accessible; both new diagnostic entry modules refuse external imports with E0603.

Commands use a fresh owned Cargo home/target, offline locked resolution, two build jobs and new owned process groups. Each command has a fixed 180-second ceiling (privacy probes 30 seconds), exact source/tool/argv/environment/output hashes and actual child/group cleanup observations. All final test commands leave the owned TMPDIR empty. The default shell initially had no Cargo/Rust tools on PATH; the packet records that discovery failure and uses explicit existing toolchain paths.

The unit compile retains two inherited `dropping_copy_types` warnings in unchanged `control_operations_tests.rs:1619,1643`; they are outside this ownership. Production Clippy passes without suppressing them globally. Other existing unit methods, Linux execution, complete CI, operational storage/work admission, native/device/UI/capture, published FieldLog/package, OTA/store/customer and GA evidence remain pending. The original finite row helper performs acknowledged File writes only; it establishes no rollback, fsync, durability or artifact authority. Codec decoding establishes unverified data shape only.

`result.json` is the command/source/cleanup index; `canonical/` freezes only the five owned source files; `source-manifest*.json` binds the full canonical VM compilation inputs before and after the lint repair. `source-attribution.json`, `clippy-repair.json` and `test-fixture-adaptation.patch` disclose all departures from accepted inputs. `commands/` retains every attempt. `seal.json` closes this packet; no Git mutation or paused surface was used.
