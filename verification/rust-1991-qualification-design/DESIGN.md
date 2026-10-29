# Exact Rust 1.99.1 prospective qualification through ordinary CI

Status: **design recommendation only; no compiler selection, installation, execution, delivery or acceptance performed by this lane.** Parent assigned the fresh Astra 6 Extra High review/design role (`gpt-6-astra`, `xhigh`).

Use the next coherent ordinary push to run the existing full 40-command envelope with a new, sealed adoption derivative. Select only the observed Apple ARM64 Rust 1.99.1 compiler fingerprint, prospectively. Leave the original runner, partition runner, 86-member pack, prior compiler amendment and 17-member historical adoption packet byte-identical. No new manual workflow, installer, retry, fallback or local compilation is needed.

## Evidence and decision

The reviewed failure is run `40942282975`, attempt 1, job `123688487731`, at revision `2c751cbbc300efc9aa766b5d4add648610ca0341`, tree `f2df6833ee8e9ce85306210b63dc35d45747fa0d`. The failure packet reports 240 successful source/data assertions, 22 passing controls, five closed identity/Git/Python commands, all eight postflights, no scratch and the sole active error `Compiler host/release not selected`. This lane read its review and source and independently rehashed its archive; it did not repeat the artifact inspector or claim a new 240-assertion execution.

The exact 444,759-byte archive has SHA-256 `4bf8af7420033af59134305742ccfc6e125a5a09a4e4e4f9ee4720948d94ab0e`. The report's 139 ZIP members and 8,714,342 expanded bytes remain attributed to that prior bounded inspection.

The old amendment expressly permits prospective selection and requires reselection after drift. The current source allows 1.98.1 and 1.99.0; `test_adoption.py` deliberately rejects 1.99.1. Thus the evidence supports a new prospective selection, not changing the old rejection into a pass. It does not yet distinguish whether this exact compiler passes the full envelope. The next ordinary invocation is the discriminating test.

No fresh user permission is needed for root to select this host verification derivative and deliver it within the existing implementation/periodic-main-push authorization. That authorization does not grant release or GA acceptance. Root still owns the actual source selection, independent implementation review, coherent delivery and result acceptance.

## Fixed compiler profile

Admit the new branch only when the unchanged strict parser produces this complete identity and the original resolver records this exact resolved compiler digest:

| Field | Required value |
| --- | --- |
| binary | `rustc` |
| release | `1.99.1` |
| host | `aarch64-apple-darwin` |
| commit_hash | `58cf8f9c35b355199727627d07ae34a4e2846d67` |
| commit_date | `2026-10-13` |
| llvm_version | `23.1.1` |
| resolved compiler SHA-256 | `1ba7bb8e273bd64125f4048d2ecce530e0a6470e565ab1b3aecf0b82b532f7b1` |

This is a compiler fingerprint selection, not an allow-any-1.99.1 version rule. Preserve original launcher spelling, sysroot resolution, verbose parsing, actual path/hash capture, launcher target/hash capture and later identity checks. Do not pin an ephemeral runner-home path. Do not infer distribution provenance or hash all unobserved sysroot contents; those were not established by this failure packet.

The original 1.98.1/1.99.0 paths delegate to the unchanged historical selector and retain their prior semantics. Every other release/host remains refused, including 1.99.2, 1.100.0, nightly/beta/dev, other Apple architectures, Linux and malformed identities. The new branch also refuses coherent 1.99.1 with a different commit, date, LLVM version or compiler digest.

## Minimal implementation ownership

Assign one implementer the new directory `verification/envelope-rust-1991-default-ci-adoption/` only. Root alone installs the reviewed `.github/workflows/verify.yml` diff and updates execution/evidence metadata. Keep the ongoing canonical axis .6 files outside this ownership.

Prepare these concrete files in the new directory:

- `adopt_envelope.py`: derive from the historical adapter, preserving its source checks, output ownership, single invocation, snapshots, finally-postflight and terminal replay. Add only the prospective compiler selection below and accurate receipt attribution.
- `test_adoption.py`: derive the existing 22 guarded controls and extend the selection/refusal coverage. Keep the old packet's controls unchanged.
- `offline_guard.py`, `terminal_replay.py`: byte-identical copies of the historical versions. The replay takes the newly loaded runner, so it can apply the new selected target without changing its 40-command or evidence checks.
- `compiler-selection.json`: root's fixed prospective selection, based on the inert template in this design directory. It is not a caller-supplied list or override. The proposal template is never runnable authority.
- `dependencies.json`, `seal.json`: exact new closure and own-source seal, following the existing sorted member/path/bytes/SHA/tree format.
- `workflow/original-verify.yml`, `workflow/swift-job.yml`, `workflow/envelope-steps.yml`, `workflow/changes.json`, `workflow.diff`: current whole-workflow baseline and exact proposed replacement, using the existing adoption pattern.
- `README.md`, `checks.json`, `pure-controls.stdout`, `pure-controls.stderr`, `.gitignore`: concise scope/result and actual guarded-control evidence. Only logs, control scratch and bytecode remain excluded from the sealed shipping closure, as before.

The implementer may copy the current adapter rather than introducing an inheritance or plugin framework. Its `load_runner()` should still verify that all three historical policy definitions match between the ordinary and partition runner, then install those original function objects with their original globals. Keep the original `rustc_identity` function object. Replace only the two runtime call sites described next with narrow wrappers. Do not change `candidate_runner.py`, `overlay.json`, `producer-partition.json` or `scripts/ci/check-analyzer-envelope.py`.

### Preserve failure/postflight ordering

The partition runner assigns `compiler, receipt['rustc'] = select_compiler(...)`, then calls `select_host_target(...)`, and only then creates scratch. Enforce the new pin at that second boundary.

1. Each `load_runner()` creates a fresh observation holder scoped to that runner instance and its single fixture invocation. The resolver wrapper clears the holder, calls the unchanged original resolver exactly once, and captures an immutable fingerprint tuple from its returned identity, resolved path and SHA-256. It returns the original values without editing the identity schema or rejecting the new pin yet.
2. The target wrapper delegates old releases and all unselected releases to the original target selector. For release 1.99.1, require a captured observation, require the supplied complete identity to match that observation, and require the fixed complete identity and SHA above. Return target metadata referring to the new sealed `compiler-selection.json` and its digest, with `prospective` scope and no inferred other-target qualification.
3. The captured observation must not be caller-provided, a module-wide shared cache, an environment override or a previous runner instance's state. If resolution fails, no stale observation survives. The guarded tests must prove these properties.
4. On terminal success, independently compare `receipt['rustc']` with the same fixed profile before calling the unchanged replay. Require the returned target-selection object to equal `receipt['compiler_target_selection']`; the old replay calls the selector but does not compare this recorded object. Compare the parser's output from the retained verbose bytes with the receipt identity as well.

Checking the pin inside the resolver before it returns would leave the unchanged runner's `compiler` and `receipt['rustc']` unset on coherent wrong-pin refusal and suppress its compiler/launcher postflight. The ordering above preserves all eight postflights while still refusing before scratch or fixture compilation. It adds no child command and no additional compiler invocation.

The adapter receipt must truthfully distinguish `rustc_identity` reused exactly, original resolver delegated exactly once, original selector delegated for historical targets, and the new exact-profile selector. Do not retain the old claim that all three installed function objects are unchanged. The candidate's own source hash remains its historical hash; snapshots of the executed adapter and selection explain its intentionally substituted policy globals.

## Schema and hash closure

Require a fixed schema, exact field sets/types and exact literal profile values in `compiler-selection.json`. Reject duplicate JSON keys, missing/extra fields, a proposal/pending status, altered compiler fields and arbitrary allowlist additions. Root authors the selected file only after deciding to adopt this design. The selection remains permanently prospective history; later qualification is recorded in a separate actual-result receipt.

Start the new dependency manifest from the existing 93 runtime/control inputs, unchanged. Include the old adoption's 17 sealed members and `seal.json` as 18 additional preservation bindings: 111 distinct dependencies in total, absent any explicitly justified new external input. This preserves the original packet without editing or resealing it. Include the new selection in the new own-source seal. Verify the closure before subject imports, before fixture invocation, in the adapter's finally path and in the workflow's always-run postflight.

Do not make a manifest contain its own digest. `compiler-selection.json` binds historical inputs and observed evidence; the new seal binds that selection and all new sources. Root's later installation/acceptance record can bind the completed new seal and delivered commit. Do not put a future commit SHA inside the commit whose SHA it would need to predict.

The historical adapter's `verify(installed=True)` expects its old Swift job and would correctly reject the new job. The new adapter must validate its own sealed Swift job. Historical-source validation may use its old data-only closure semantics; do not weaken or mutate the old installed-job guard. Do not claim that the old sealed job remains installed.

Snapshot and retain the new adapter, selection, dependency manifest, own seal and unchanged replay, in addition to the existing executed ordinary policy and partition runner. Freeze the full proposed job bytes and verify them before and after execution. Preserve the whole-workflow baseline/diff to prove all jobs and all non-envelope Swift steps stay byte-identical.

## Ordinary workflow delta

Use `.github/workflows/verify.yml` only; do not add `workflow_dispatch` or a separate workflow.

1. Add `/verification/envelope-rust-1991-default-ci-adoption/` to the Swift job's sparse checkout. Keep the old adoption path and all 93 existing dependency paths.
2. In the existing envelope group only, point its preflight, controls, one fixture invocation and postflight to the new adapter directory. Name the step `Standalone analyzer envelope with prospectively selected compiler` so the UI does not announce an unqualified compiler as accepted.
3. Keep `RUSTUP_AUTO_INSTALL=0`, `command -v rustc`, current artifact location, 2/3/12/2/5-minute step limits, 30-minute enclosing job, and both `if: always()` steps. Add the new directory to artifact upload and retain the old packet and workflow. Do not use `continue-on-error`, toolchain installation, fallback or automatic retries.
4. The ordinary next push supplies `GITHUB_SHA`; preserve its exact revision checks and tree-before/tree-after equality. Root binds the first resulting run ID and attempt to that actual delivered SHA after delivery. No local or additional manual qualification attempt is selected by this plan.

The new policy remains a prospective selection until actual independent review. A subsequent ordinary job can enforce the same source-bound policy, but root must inspect this first result before treating the compiler as qualified or deliberately scheduling another diagnostic. A first-run identity refusal or workload failure is a result, not permission to loosen the profile or replay an unchanged failure.

## Required bounded controls and executable prerequisites

Run only guarded Python controls locally, with the existing runtime/process/signal/network deny guard installed before any subject import and writes confined to the new packet. Preserve all 22 historical control behaviors except the deliberately changed derivative identity assertions and workflow binding. The historical packet still rejects 1.99.1 in its own unchanged test.

Add the following behavioral cases to the new derivative's tests:

| Control | What it unlocks |
| --- | --- |
| Complete coherent observed identity and exact hash; original parser/resolver delegation; old pairs unchanged | Admits only the intended next-host compiler |
| One-field mutations, malformed/duplicate/missing/incoherent verbose fields, other hosts/releases and wrong hash | Proves the prospective exception cannot widen silently |
| No observation, stale observation after failed resolution, cross-instance observation, identity/observation mismatch | Proves the narrow wrapper cannot reuse stale compiler state |
| Actual adapter/runner orchestration with fake children for the exact 1.99.1 profile | Proves ordered 40-command success and unchanged roster/layout/API/capture/retention behavior before hosted execution |
| Coherent wrong hash and wrong complete identity through that orchestration | Proves five commands only, no fixture scratch/compile, retained compiler identity, all eight postflights and failed adapter result |
| Historical 1.98.1 synthetic full run | Preserves the existing selected path |
| Changed selection source, dependency, installed job, compiler pin or recorded selection metadata; failed/raising fixture | Preserves source/postflight failure propagation and prevents retrospective receipt relabeling |
| Exact sparse closure and whole-workflow minimal diff | Unlocks the root-owned ordinary workflow installation |
| Existing wrong oracle, command/receipt/custody/capture/cleanup refusal controls | Keeps unchanged acceptance boundaries under the new adapter |

Use a non-executing pure fingerprint checker test for the actual compiler SHA. Fake test binaries cannot naturally hash to the observed compiler; the synthetic orchestration must stub only the compiler's fingerprint read/resolver result and label that result synthetic, without patching the validator under test or accepting a test-only profile in production.

Implementation evidence must state the actual test count, interpreter version, source/seal digests, command, exit status, no real runtime operations and scratch cleanup. Source tests prove the adapter and refusal behavior, not compiler qualification. One focused independent implementation review should verify the source substitution and control results. After that, proceed directly to the next authorized coherent push; no extra qualification framework or recursive review chain is required.

## First actual result and acceptance

Acquire the first ordinary result with existing root-owned delivery/custody tooling. Preserve the failed baseline archive and its review unchanged. Hash the new artifact and independently inspect its data without running its executable contents.

Qualification requires all of the following from that one exact run and new derivative:

- Exact delivered revision/tree, installed Swift job, source closure, prospective selection digest, compiler complete identity and compiler digest above.
- No error, timeout, output cap, descendant/owned-group hold or missing stream EOF; all 40 original commands in order and no added fixture child command.
- 78 producer methods across the same 18 disjoint groups; 14 independent methods; all original list/execute identities; 32 unchanged expected layouts; 16,170 + 5,544 comparisons; one positive and eight intended negative API checks with their original diagnostics.
- All 92 retained payload files and four compiler-product records, their digest checks, all eight source/tool postflights, the adapter and workflow source postflights, exact direct/group/pipe closure and scratch removal.
- Unchanged 480-second active budget, 60-second cleanup budget, 120-second per-producer-group limit, 8 MiB per stream and 64 MiB aggregate capture limits; original warnings policy and all authority flags remain false.

If these pass, root records a separate immutable actual-result acceptance linking run, revision/tree, artifact hash, source/selection seals, reviewer and the precise host-envelope scope. No source edit or second qualification run is required merely to change a label: the prospective selection stays historical, while the new receipt establishes its observed qualification. Update `PLAN.md`, `STATUS.md`, `work-graph.json` and relevant evidence references accurately; do not change any GA gate to verified.

If the host is different, the new exception refuses before fixture compile; record the actual identity and stop. If the exact compiler runs but a workload, capture, deadline or custody gate fails, preserve the full failure and use that concrete result for the next bounded decision. Do not weaken layout, API, warning or custody checks to secure green CI.

This qualifies only the existing standalone host envelope. It does not qualify all Rust releases, native runtime, OTA semantics, signing/store release, immutable-package FieldLog, the canonical axis .6 slice or GA. Other jobs retain their separate evidence attribution.

## Review operations and preserved boundaries

This lane used `cat`, bounded `sed`, `wc -l`, `rg` and `shasum -a 256` to inspect source/data; no repository helper or subject was imported or executed. `rg --version` reports 15.2.0, revision `e89fff89ac`, and `shasum -v` reports 6.02. `source-bindings.json` records the exact live bytes rehashed here and the parent-supplied revision/tree provenance. Those hashes do not claim the entire working tree is clean or unchanged.

Only this `verification/rust-1991-qualification-design/` directory was authored. No Git/gh, compiler/product/oracle/native/UI execution, network acquisition, workflow submission, process probe/signal, protected hosted source or `.wrangler` inspection occurred. FieldLog run 40802230894 / PGID 2424 / PID 2621, Unit A and every existing custody/process hold remain untouched. Phones, native UI and capture remain paused.
