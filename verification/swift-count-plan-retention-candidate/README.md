# Isolated count-plan Rust feasibility packet

Result: rejected for live integration and a full-target retry. Three actual
finite work traces and narrow memory admission regress. See
[`docs/swift-count-plan-retention-candidate.md`](../../docs/swift-count-plan-retention-candidate.md)
and `comparison.json`.

The source boundary is the exact 132-file live closure from
`verification/swift-cost-retention-candidate/live-baseline-source-manifest.json`,
resolved under `vm/`. No historical engine was restored. `baseline-source.tar.gz`
is pristine; `tested-baseline-source.tar.gz` includes selected host probes;
`candidate-source.tar.gz` includes the isolated seam and probes. Each has an
exact member manifest. Patches compare candidate with pristine and with the
instrumented baseline. No live VM edit or commit is included.

`proposed-seam.md` and its hash-bound `root-selection.json` freeze the reviewed
finite scope, named inventories and 41+16 debit blocks. `layout-probe.rs` is
layout-only prospective code retained separately from the executed candidate.
`inventory-probe.rs`, `inventory-fields.json`, `generic-differential.json` and
`hit-ledger-differential.json` distinguish full typed Results, measured layout,
generic behavior, hit work/allocations and the failed promise of hit-byte parity.

`commands/*` retains exact argv/environment/tool versions and executable hashes,
source manifests, raw stdout/stderr, source/input/stream hashes and exit status.
Initial compiler failures and the candidate's two original policy-assertion
failures remain intact. The new finite passes do not replace those failures.
`test-adapter-correction.json` and `probe-corrections.json` describe only the
test-interface repairs. No policy retuning followed observed results.

Reproduction uses `run.py prepare`, then `implement.py`, the existing-test adapter
correction, and `install-probes.py baseline candidate`. The copied original
Swift suite deliberately retains its two candidate policy-observation failures.
Selected generic suites, `count_candidate_` methods and unchanged
`cost_retention_common_` methods use the exact commands in their receipts.
`assess.py` derives reports from retained outputs. `finish.py` archives, audits,
cleans only the owned scratch tree and seals the packet. Reproduction must use
a new owned destination; these retained receipts must not be overwritten.

`ownership.json`, `cleanup-preflight.json` and `cleanup.json` bind exact scratch
device/inode identity. No compiler/native/UI/capture/background process was left
running. No full-target or broad hosted harness was executed. Paused native,
physical phone, signing/store, provider/operational, separate-repository published
FieldLog and GA gates remain pending. Independent result review is separate.
