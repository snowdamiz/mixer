REQUEST_CHANGES for the exact R416 combined nine-path candidate. One P2 defect was reproduced. Review stopped at that defect, as instructed.

At `candidate/verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py:314`, bootstrap sets `integration_started = True` before creating the optional diagnostic directory at line317. An OSError from that mkdir prevents the integration call at line320. The finally block then records nonterminal custody and retains the downloaded toolchain scratch, even though integration was never entered. Optional diagnostics therefore change both execution and cleanup behavior.

The controlled reproduction used the exact candidate bootstrap and its existing `PhaseActivationControls.check_main(False, None)` fixture. All downloads, official tool commands and integration execution were inert adapters. The fixture's temporary-directory root was redirected into R424; candidate files were not modified. A selective `Path.mkdir` adapter raised EACCES only for `inspection-phases`.

| Case | Integration calls | Exit | terminal_custody | owned_removed | Scratch at return | Parent environment restored |
| --- | ---: | ---: | --- | --- | --- | --- |
| Normal | 1 | 0 | true | true | absent | true |
| Diagnostic mkdir denied | 0 | 1 | false | false | present | true |

The existing success control fails with `1 != 0` under the injected diagnostic-only failure. The reproduction script exits0 only after asserting both observations. See `reproduce.py`, `reproduce.stdout`, empty `reproduce.stderr`, and `result.json`. Both inert temporary trees were subsequently removed by the fixture. No real integration child ran, and the simulated receipt does not establish a new real custody hold.

Root must not apply the exact combined candidate as accepted. Make sidecar-directory setup best effort, keep the diagnostic disabled when setup fails, and set `integration_started` only immediately before entering integration after preparation completes. Preserve the existing fail-closed treatment of an actual integration whose custody is unresolved. Add the directory-creation failure case beside the existing success/write-failure controls. This is a concrete slice correction; no controller, seal framework, or recursive review campaign is needed.

The reviewed identities are recorded for every candidate afterimage and canonical preimage in `result.json`. All nine matched `changed-files.json` during this review. Key SHA256 values are:

- Combined patch: `00dd11abe64a65ee1f040fbfa122502bb932253868efaccc771543ed18408f78`.
- Android inspection helper: `6889b75958fdc2d2f4894072d180c8aa377c040cc4b1b22b3a8e3dfeff357ca2`.
- Candidate bootstrap: `a27c6264130899d64787efa3541fbbc8974c3ec5e9e393209cb6949cfa164a59`.
- Candidate bootstrap controls: `78414f1fd653ec5395a9b60a9336d5187c9dec980089b873ab794492b6672840`.

The helper is byte-identical to the R406 candidate and the resource actually used by the R406 producer. Read-only comparison confirmed that direct inspection equals the packaged-create lock inventory. Each recorded phase file has62 entries and4898 bytes. The files begin at `probe.swift/begin` and end at `distribution.hash.jdk/end`. Both original outer receipts record exit0/group absence, and both copied nested receipts record terminal custody. These are reused historical observations, not new process probes. The evidence and exact phase-file hashes are in `r406-reuse.json`.

The source diff keeps phase JSONL separate from stdout/stderr and preserves the inspection return structure, tool/filter/hash operations and their ordering. `MAX_ENTRIES=64` and `MAX_BYTES=16384` remain in the helper. The CI directory is a sibling of `integration`, outside `integration/inner-cli` and the five hashed distributions. The unchanged workflow's artifact step uses `if: always()` and uploads the complete bootstrap output, so the sibling is selected for retention on failure. This was source inspection, not an actual upload. The helper's write-failure neutrality does not cover the reproduced bootstrap mkdir failure.

The fresh controlled checks established normal activation and full parent-environment restoration, plus the adverse mkdir behavior above. After the first concrete defect, no additional adversarial suite, guard execution, full source116 recomputation or patch replay was run. The broader64/16384 boundary and absent/write-failure claims therefore retain R416/R406 producer evidence rather than a complete independent R424 pass. No overall PASS is issued for stdout/stderr/schema, limits, filters, hashes, capabilities, custody, admission or retention.

The root-supplied installed floor is R388 source116 `de5ca08c37cdca5307808a6732ffcbbe9dbeeb8057ceaa11b40e19f0be06cc6a` with R394 backend185. R416 identifies the prospective source116 as `452ff6bb02012d0664e88288597996cf7dd859e37688b8f80d02b388e557322f`. Application remains a root action after the concrete defect is corrected and affected checks pass. Preserve existing source/caller bindings, Pair19, qualification flags and every historical hold; do not treat this review as application, publication, hosted success, or release approval.

The R396 nested inspection180s timeout remains a real historical failure with unproven cause. This review did not rerun CI, rebuild tools, use devices/signing, invoke root Git, touch remote state, delegate children, inspect held resources, or write outside R424. Unknown remains Unknown. Python3.14.8 and macOS27.0.1 arm64 were used. The exact command, tool version, source identities, raw observations and cleanup are retained in `result.json`.
