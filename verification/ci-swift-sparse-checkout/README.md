# Swift checkout input closure

This slice changes only the `swift` job checkout `with` block in
`.github/workflows/verify.yml`. It preserves `fetch-depth: 0`, every command and
artifact step, all toolchain pins, job/step limits, triggers and other jobs.
It does not skip tests. The source reviewed here is canonical revision
`114a2632fd58076574bd5b2444c511861c3b30d4`; its Git tree and every selected blob
identity are retained in the receipts and inventories.

The rule set retains every non-`verification/` file recursively. Inside
`verification/`, it retains the five complete consumed packets, four exact
external data files, and every basename scanned by `scripts/check-policy.py`.
Keeping all non-verification source avoids changing dynamic source inventories,
resource packaging, generated consumer snapshots or local package resolution.
The anchored `/verification/**/Package.swift` rule matches a filename at any
depth; there is no standalone `/verification/**/` directory inclusion.

## Per-step closure

| Existing Swift job step | Source/input closure retained |
| --- | --- |
| Verify and record pinned Apple toolchain | Complete `scripts/ci/`, including the Apple toolchain verifier; runner toolchain paths are unchanged. |
| CI selection regression tests | All five `scripts/ci/tests` modules and imported CI runners. Framing controls invoke the real collector with synthetic failing compilers and consume its two frozen packets; envelope controls consume the entire exact envelope pack. Dependency policy controls copy `scripts/check-policy.py`, `gates/ga.json`, `work-graph.json` and `dogfood/receipts/milestones.json`. Android binding controls reject supplied invalid native receipts before source staging; they do not execute the binding job's separate positive native closure. |
| Policy and acceptance integrity | The complete policy script and three JSON gate/milestone/work-graph inputs. Python AST inspection confirms all eleven policy manifest basenames. Every tracked instance anywhere in the canonical tree remains present, including the 609 manifest inputs outside the explicitly consumed verification packets. The basename patterns also cover future manifests at arbitrary verification depth. Policy-excluded directories remain a safe included superset; no basename inspection scope is removed. |
| Accepted standalone analyzer fixture framing | Complete `verification/swift-ordered-retention-analyzer-library/` and `verification/swift-ordered-retention-analyzer-library-review/`, including both seals/sidecars, all 270 and 624 sealed members, historical inputs, and selected source. The two additional sealed documents in `docs/` remain present through the non-verification inclusion. Member paths come from parsed seal JSON; all sealed byte sizes and SHA-256 values were checked after actual sparse materialization. |
| Accepted standalone analyzer fixture envelope | Complete `verification/swift-envelope-ci-pack/`: manifest plus all 86 members, including source, relative include files, historical data, oracle inputs, API negatives and inventory/provenance files. The runner inventories this entire packet and refuses unexpected or missing members; no narrow source-only substitution is made. |
| Generated capability schema and host lifecycle | Complete `capabilities/`, `sdk/` and `contracts/`. Generator input `capabilities/schema/v1.json` and every checked output remain present. Capability package local dependency `../sdk` and all its products, source, NativeIO C target and tests remain present. |
| Guest transport raw byte corpus | Complete `verification/guest-capability-contract/`; parsed `cases.json` references all 90 raw byte fixtures, individually size/hash checked after materialization. The frozen transport contract in `contracts/`, schema and probe package/source remain present. Both debug/release commands remain unchanged. |
| Native HTTP, deadlines and exit ownership under TSAN | The complete capabilities and SDK package closures, including resources and NativeIO source. The existing TSAN filter and scratch path are unchanged. |
| Swift SDK, update verifier and CLI | Root `Package.swift` and complete `sdk/`, `updates/`, `cli/`, `native/`, `runtime-identity/`, `activation/`, `contracts/` and `vm/`. Root SDK package maps targets into `sdk/Sources` and tests into `sdk/Tests`. CLI local dependencies are SDK and updates; updates' exact Swift Crypto dependency/resolution files remain unchanged. Android engine depends on SDK. Runtime identity depends on updates; its build-tools imports and synthesized snapshot/embedding packages consume retained source, activation fixtures, contract/schema and VM headers. Full `cli` resource/fixture directories remain present. |
| SDK appearance golden/corpus data | Exact `verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json`, `verification/ui-shared-appearance-contract/v2/mixer-default-appearance-v1.json` and `verification/ui-appearance-foundation/design-corpus.json`. Manual inspection of the Swift file-relative fixture readers confirms the V1, V2 and fifty-case corpus inputs. |
| CLI build-test compatibility fixture | Exact `verification/android-default-appearance-packaging/run-2/created-descriptor.json`. The parsed committed compatibility profile selects SDK/native adapter files, all retained recursively. The staging/appearance controls also retain their imported Python driver and fixture helper. |
| Statically linked owned VM and signed startup | Complete `runtime/`, `vm/`, `contracts/`, `activation/`, `updates/`, `runtime-identity/` and `verification/runtime-review/`. Runtime has local C/Swift targets; activation depends on runtime, updates and runtime identity; the review package depends on `../../runtime`. `runtime/build-vm.py` archives committed `vm` and `contracts/vm-session-v1.json` at `$GITHUB_SHA` and compares its header to the working runtime header. That exact archive/header read was exercised offline without invoking Cargo. |
| Generated consumer integration | Complete CLI plus SDK source snapshot and resource templates, including `SourceDigest`'s entire SDK traversal. Generated iOS project/package dependencies resolve inside the created temporary app and SDK snapshot. All create/test/iOS build commands and pins remain unchanged; none was run locally for this checkout slice. |
| Artifact preservation steps | Their paths read generated `$RUNNER_TEMP` outputs, with no additional checkout inputs. Their names, inclusion rules and retention settings are byte-identical. |

The independent native builder pin is
`1adb25c48a8723f56ed2649712fe5e357920c53e`. Its nine header/contract/schema reads
were also exercised through the isolated sparse repository. The actual positive
builder fixture belongs to `swift-capability-native`, whose job is unchanged.
The `swift` job's current VM builder uses the CI revision. Full fetch depth is
retained for historical source availability; no shallow-history change is made.

## Offline observations

Commands use Python 3.14.8 and Git 2.56.0 on macOS; exact command arguments,
environment restrictions, revision/tree, collector digest, output digests and
owned-process cleanup are retained in each `receipt.json`.

| Canonical source inventory | Files | Uncompressed blob bytes |
| --- | ---: | ---: |
| Full tree | 330,288 | 17,638,540,012 |
| Selected checkout | 5,054 | 208,685,831 |
| Retained non-verification source/metadata | 3,353 | 61,837,858 |

The selected byte count is under the 250,000,000-byte materialization ceiling.
The workflow was edited only after tiny semantic controls, canonical rule
selection and actual materialized blob/content checks passed.

- `selection-plan-1`: failed before copying canonical source because Git's help
  advertised `--skip-checks` while rejecting the option. Stderr and cleanup remain.
- `selection-plan-2`: actual candidate matched the independent 5,054-file closure;
  a deliberately broad-directory negative was incorrectly expected to include
  root files as well as nested directories. That collector assertion failed and
  remains preserved.
- `selection-plan-3`: passed in 7.686255 seconds. Tiny nested/hidden controls and
  canonical Git rule selection match the independent closure predicate. Adding a
  standalone recursive directory rule selects 330,217 files / 17,637,785,449
  bytes and is rejected without materialization. Removing manifest rules omits
  609 policy inputs and is rejected.
- `materialization-1`: the bounded checkout/blob, seal, corpus and VM archive
  checks completed; the extra historical-pin AST reader failed on the explicit
  `*HEADER_HASHES` list expansion. The failed receipt is preserved and scratch
  removed. The reader was corrected without executing the builder module.
- `materialization-2`: passed in 13.140976 seconds. Actual sparse checkout equals
  all 5,054 canonical blobs. All sealed member contents, ninety corpus cases,
  policy manifest paths, the exact HEAD VM archive/header and all nine historical
  pin reads pass. The actual collector source is retained alongside its receipt.
- `workflow-delta-2.json`: the final workflow patterns equal the observed rules;
  removing only the new Swift checkout insertion recovers the exact canonical
  workflow bytes. This confirms commands, toolchain pins, timeouts, triggers,
  artifacts and other jobs are unchanged.

Each owned Git child uses a new process group with a bounded wait; receipts
confirm every owned group is gone. Scratch cleanup checks the exact owned inode
and nonce before removing it. No main index/refs or existing object files are
written, no remote is configured, and lazy fetching is disabled. No global
process inventory, browser/UI, capture, compiler, product test, native runtime,
BEAM or container command was started. Both failed and successful runs cleaned
their exact scratch directories; unrelated processes and instances were not
queried.

## Acceptance boundary

The evidence proves offline Git rule selection and canonical input preservation
for this revision. It does not measure GitHub network/fetch savings or qualify
runtime behavior. Remote checkout timing, all existing job commands and remote
CI acceptance remain pending. The previous slow checkout observation must not be
reported as a new terminal failure. Phone, simulator/emulator runtime, operational
and GA acceptance are outside this slice and remain pending under the pause.

Reproduce the source-only checks with a fresh output path in this owned directory:

```sh
python3 -B verification/ci-swift-sparse-checkout/offline_check.py --out verification/ci-swift-sparse-checkout/fresh-selection
python3 -B verification/ci-swift-sparse-checkout/offline_check.py --materialize --out verification/ci-swift-sparse-checkout/fresh-materialization
python3 -B verification/ci-swift-sparse-checkout/check_workflow_delta.py
```
