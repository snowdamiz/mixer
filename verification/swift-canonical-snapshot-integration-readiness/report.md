# Canonical Swift component integration readiness

This source-only comparison identifies a concrete canonical integration slice. First adapt the accepted private codec/row/loader tests to ordinary Cargo execution and Linux compilation, then integrate their bounded components with fresh canonical evidence. Bring shared adoption and the pure guard-derived encoder forward with their complete common foundation and privacy constraints. Preserve the snapshot writer's `WorkAuditPending` refusal until the remaining complete floor, paid evaluator, caller work and cleanup contracts are selected. Copying the final 144-file tree wholesale is not an accepted component integration.

No engine, compiler, runtime, native/device, UI, capture or frozen runner was executed. This report is not operational acceptance and promotes no gate. Active owner storage/emission folders were not read.

## Exact source boundary

Canonical HEAD is `5b80a99aca2bee400786a71f033cc0fd928de89d`. The relevant canonical VM paths have no worktree difference from HEAD. The frozen authority candidate's seal hashes to `351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c`; its 144 source members exactly match its manifest and recompute to `575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896` using SHA256 of sorted-key compact JSON member records. The matching canonical 132-member source set hashes to `bd023840414d4850abffdc4758072b95f115059bb03ccb4ba37f9bdb7a608691`. This source-set digest excludes canonical documentation, tools, build output and historical receipts. No canonical src/test/include member is absent from the frozen roster.

There are **121 byte-identical members, 11 changed members and 12 new members**, with 8,276 added and 18 removed lines. Cargo.toml, Cargo.lock and every public C header are byte-identical. `source-roster.json` records every member's exact bytes/SHA256 on both sides, status, and changed/new line counts. `receipt.json` binds the read inputs and tool versions.

Paths below are relative to `vm/`; frozen line references use `verification/swift-guarded-snapshot-scope-authority-correction/source/vm/`.

| Production or mixed production/support path | Delta and dependency |
| --- | --- |
| `src/experimental/swift.rs` | Adds private `snapshot_encoder_v2` at 731, guard/provenance imports at 734, byte cursor/block semantics, test/layout seams, and preguard counts at 1698. Depends on the actual private `InitialProfileBorrowV1` and full loader provenance. |
| `src/experimental_swift_reactor/cache.rs` | Adds initial-profile module, wrapper floor, guard reexport and scope-consuming snapshot adapter at 4849 onward; pairs actual cache tickets with the same RuntimeControl and optional WASI. |
| `src/experimental_swift_reactor/control.rs` | Changes AdoptedProof from a bare proof to full AdoptionBodyV1; adds four common foundation terms; ordinary/selected common adoption; appends scope capability, snapshot result, pairing, debit/storage and conservative finalizer. |
| `src/experimental_swift_reactor/mod.rs` | Private diagnostic row/codec/loader modules and crate-private guard/provenance imports. No public runtime route. |
| `src/experimental_wasi/accounted.rs` | Adds configuration getter and actual five-ticket/capacity pairing at 432–449. |
| `src/experimental_wasi/mod.rs` | Adds borrowed configuration getter at 638. |
| New `src/experimental_swift_reactor/cache/initial_profile_v1.rs` | Finite eight-outcome wrapper, sole guard, common original/snapshot branch, ownership-gated writer composition and source-place proposals. This file mixes accepted prerequisites with unresolved full-writer composition. |
| New `.../cache/initial_profile_v1/header.rs` | Fixed private profile-header encoding. |
| New `.../cache/initial_profile_v1/local_structure.rs` | Exact local type/layout comparison. |
| New `.../cache/initial_profile_v1/selected.rs` | Literal complete budget and 201-layout selection. Its combined grant is 268,435,456, not 300,000. |
| New `src/experimental_swift_reactor/diagnostic_profile.rs` | Private finite row derivation and borrowed File writer. This existing original row writer is distinct from the blocked snapshot writer. |
| New `src/experimental_swift_reactor/diagnostic_result_v1.rs` | Private unverified typed-result codec; no authority, I/O or allocation. |
| New `src/experimental_swift_reactor/retained_profile_loader_v1.rs` | Private retained File loader/full provenance, ordinary and selected body/adoption capability, corrected final metadata roles, layout seams. Operational loader storage remains unaccepted. |

Ten other changed/new files are support-only or support-only deltas: `src/experimental/account.rs` adds `snapshot_inventory_v2`, used by the cfg(test/encoder-host) oracle; `src/experimental_swift_reactor/cache_tests.rs` adds four new wrapper floor terms; `control_tests.rs` adds those named terms; `execution.rs` adds three comment lines; `src/lib.rs` adds only the cfg(encoder-host && !test) host main; new `diagnostic_profile_tests.rs`, `diagnostic_result_v1_tests.rs`, `retained_profile_loader_v1_tests.rs`, `cache/initial_profile_v1/tests.rs`, and `cache/initial_profile_v1/compile_contracts.rs` are test/host support. Production/mixed files also contain cfg-gated measurement and host seams; these must retain separate attribution from engine behavior.

## The 300,000 versus 366,896 question

The concrete defaults in canonical and frozen `control.rs:40–65` are identical: `combined_bytes = 256 * MIB` (268,435,456), `state_bytes = 128 * MIB`, `cache_work = 64,000,000`, and `execution_work = 1,000,000,000`. Frozen `selected.rs:4–22` copies those complete literals. No default is 300,000.

The 300,000 grant is an explicit unit fixture in `cache/initial_profile_v1/tests.rs:948`. It calls **ordinary** `RuntimeControl::adopt`, then asserts `CategoryExhausted`, Construction, Adoption stage, limit 300,000, attempted foundation, zero remaining reservations/tickets and no wrapper entry. Lines 956 onward separately use 400,000 to reach a later preparation refusal. That second case never raises the first grant or the product ceilings.

The 366,896 unit foundation is a retained measurement from the accepted adoption correction, not a new measurement in this pass. The common formula at frozen `control.rs:552–586` includes full body/provenance owner sizes and the four named entry/move/cleanup/wrapper floors. Ordinary `adopt` at 595–602 creates `AdoptionBodyV1::ordinary`, then calls `adopt_body` and the same core; `OriginalAdoptionV1::foundation` at 1839 returns the enlarged common formula. Selected ordinary-carrier adoption at loader:163–166 calls that same method. Consequently the refusal is **not a selected-only bypass or isolated alternate ledger**: sufficiently narrow ordinary explicit grants also bear the increased common admission cost. That is an intentional real private-admission behavior change requiring canonical regression coverage.

There is no source evidence of a default/customer runtime regression. Cargo's `default = []`; `lib.rs:16` gates reactor exposure on `experimental-swift-reactor`; `experimental/mod.rs:6–7` also gates the Swift validator implementation. RuntimeControl is crate-private, the control module is crate-private, cache/execution modules are private, and the actual reactor instance remains crate-private. The canonical CLI/C ABI/session entry files contain no RuntimeControl/SwiftRunBudget route. `runtime/build-vm.py:46` builds without reactor features; `experimental-capability-runtime/build-vm.py:33,417` selects only capability-native and its dependency chain. A successful default full workload is **not** established by this inspection: source-level headroom over one retained unit foundation cannot prove complete runtime admission, physical memory or customer behavior.

The selected snapshot scope adds further proposed common/scope/outer floors in `control.rs:2072–2098`. Its full operational floor is unselected. Do not substitute 366,896 for that unresolved snapshot total.

## Concrete canonical integration obstacles

1. **Linux unit compilation needs an actual target boundary.** Loader `identity` (579), `retained` (599), `platform` (652), and `final_metadata_recheck_v1` (1165) exist only on macOS. Its tests module at 1292 is enabled for every test target. The new test file references those helpers without matching target gates at 309/317, 573–577, 631–641 and 711/735. Ubuntu `vm` CI enables reactor and compiles that module even if a test later returns for a missing environment variable. A safe integration must retain portable parser/codec/non-mac refusal tests and place actual macOS helper/entry tests under their real supported target. This is a source finding; no compiler failure was run or claimed.

2. **Frozen command-specific evidence tests are not ordinary Cargo tests yet.** `diagnostic_profile_tests.rs:169` requires `MIXER_PROFILE_EVIDENCE_DIR`; loader test:565 requires `MIXER_LOADER_HELPER_DIR`; initial-profile tests:27 require `MIXER_INITIAL_PROFILE_EVIDENCE_DIR` and use create_new fixed names. Unfiltered Cargo CI does not establish these environments or method-specific scratch ownership. Some genuine loader/encoder entry tests return early without variables, which must not be counted as genuine execution. Adapt these to owned self-contained fixtures or explicit separately selected host tests with honest pending status; do not paper over them by pretending a skipped body executed. Retain original frozen command evidence separately.

3. **Cargo warning/configuration qualification remains missing.** The frozen tree introduces custom cfg names `mixer_initial_profile_component_host`, `mixer_snapshot_encoder_host`, and `mixer_snapshot_composition_layout`, while Cargo.toml is unchanged and the repository has no root Cargo config declaring them. Existing CI runs reactor-only `cargo clippy --lib ... -- -D warnings`. Direct rustc metadata commands in authority `check.py:66–73` are not that Cargo/Clippy context. Integrate narrow cfg declarations or move host-only seams into explicit test support; check visibility/dead-code/lint results rather than assuming direct-rustc acceptance covers them. The newly unconditionally declared Buffer inventory helper is oracle-only and also needs its correct support boundary. These are required checks, not claimed diagnostics.

4. **Loader scope is macOS/trusted/quiescent, not a package authentication route.** Loader non-mac branch at 1211 returns UnsupportedScope. Its five `option_env!` build identities at 32–37 are absent under ordinary Cargo unless explicitly supplied, and load_inner at 979–986 refuses UnsupportedBuild when missing. The retained macOS path calls standard System SHA256/process APIs; it does not add a Rust dependency. Final role correction is present at 1166–1177, so do not reintroduce predecessor R1. None of these private identities can stand in for signed package provenance or hostile-parent protection.

## Components that can move before writer acceptance

The private typed-result codec and finite original row helper can be integrated and tested independently with module wiring plus adapted support; they do not require modifying the shared admission formula. The loader-only component can then retain its private safe-File/carrier boundary and macOS scope while receiving Linux refusal and Cargo fixture coverage. This does not authorize operational storage or selected execution.

Shared selected adoption changes the actual AdoptedProof layout and common ordinary admission path. Integrate its full accepted body, final-role repair, four common floors, ownership and original-control tests together. Do not cherry-pick a selected boolean/digest path, discard full provenance when None, or shift only the selected caller to a different ledger. Its original source closure, narrow/default grants and both independent refund/quarantine paths need canonical evidence.

The pure encoder additionally depends on the exact sole initial-profile guard, local/header/budget validation, full provenance and borrowed proof API. It may be compiled/tested as a private inert component before operational writing, retaining genuine guard byte comparisons and compiler privacy controls. Its view/cursor/block semantics do not authorize File custody or work/storage admission. The final authority tree differs from the accepted pure-encoder tree in six files (listed in source-roster.json), so its acceptance does not transfer wholesale to the appended writer composition. Before deriving a new component slice, bind unchanged encoder behavioral ranges and preserve source attribution for measurement-only additions.

The scope authority correction itself is a prerequisite when the eventual selected constructors are included: only SnapshotScopeV1:1937–1944 mints SnapshotScopeBorrowV1 from actual slots, and both cache wrapper and inner selected constructor consume it. It must not be replaced with a separately minted permit plus substitutable raw cache/control/proof parts.

## Full writer remains a separate required implementation

`initial_profile_v1.rs:378–383` unconditionally returns WorkAuditPending from proposed_emission_work_v1. The begin path at 385–405 pairs actual ownership, preflights storage, debits the old fixed 16,384 planning proposal, derives actual shape, then hits that refusal before emission debit, storage commit, transfer-buffer construction or snapshot File write. Keep that refusal. A speculative invocation could still spend the old planning proposal, so its presence is not a paid-evaluator/work acceptance claim.

`SnapshotScopeV1::construct_v1` owns the exact slots; `SnapshotRunV1::finish_v1` at control:1949–1973 retires the independent primary, adopted body, cache and WASI while preserving enlarged Construction charge. The finalizer explicitly leaves ConstructionBound rather than proving healthy zero-ticket cleanup. The cfg(test) future_genuine_composition_v1 helper has no test/CLI/export dispatch and expressly asserts retained charge; it is not writer execution evidence.

The accepted encoder work and original-composition writer work interfaces remain separate inputs. Required closure still includes actual count binding, native transfer term, full caller/control/stop/inherited work, the constructor's separately added actions, a funded checked evaluator, complete simultaneous common/selected/conditional source places, and retained outer/error/move/cleanup lifetimes. New owner storage and emission work were deliberately not inspected in this pass. Do not lower the inventory, omit old wrapper/eight-outcome semantics, bypass WorkAuditPending, discard outer.export/completion, or claim operational success from this report.

## Focused canonical qualification commands, not run here

These commands derive from vm/Cargo.toml and the current verify.yml VM job. Use fresh canonical receipts with revision/tree digest, actual tools/commands/output and bounded owned scratch. First repair the target/scratch/cfg issues above. Run both debug and release for selected tests and builds; repeat broad existing CI only once the coherent slice exists.

```sh
cargo test --locked --manifest-path vm/Cargo.toml
cargo test --locked --release --manifest-path vm/Cargo.toml
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor diagnostic_result_v1
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor diagnostic_profile
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor retained_profile_loader_v1
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor experimental_swift_reactor::control::tests
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor initial_profile_v1
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor snapshot_encoder_v2
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-swift-reactor
cargo test --locked --release --manifest-path vm/Cargo.toml --features experimental-swift-reactor
cargo clippy --locked --manifest-path vm/Cargo.toml --lib --features experimental-swift-reactor -- -D warnings
cargo test --locked --manifest-path vm/Cargo.toml --features experimental-stream-validation,experimental-function-cache,experimental-span-execution,experimental-swift-wasi,experimental-swift-reactor,experimental-capability-native
```

The current VM job additionally runs release and explicit `--ignored` full-feature variants. Default builds/tests prove feature isolation; reactor-only builds check absence of accidental legacy feature dependencies; the combined set checks interaction. None of those ordinary tests supplies genuine loader provenance fixtures by itself. A new bounded canonical host harness must establish fresh immutable preimages, actual genuine cases and privacy-negative compiler controls without invoking old frozen runners. Keep host-codec/pure-encoder checks distinct from the writer-positive tests, which remain unselected until full contracts close. Native/physical/FieldLog/package/OTA/store/customer/operational and GA evidence stays pending.
