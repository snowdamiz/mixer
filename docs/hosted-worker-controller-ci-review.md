# Worker controller CI integration review

The final reviewed integration has no open findings within this review's scope.
This is local development evidence; Linux CI, a production provider, devices and
GA acceptance were not qualified.

The review is bound to HEAD `855942a472357cdce7662b4e950bb56d46196954` plus the
working-tree hashes in
[`final/snapshot.json`](../verification/hosted-worker-controller-ci-review/final/snapshot.json).
The final `test/check.mjs` SHA-256 is
`bb331e5b4b477c6f5a625dca41f4e3525346c5d77982631bc7731aaa75f42d58`.
The environment was macOS arm64, Node `v22.23.3`, npm `10.9.9`.

Scope covered the new runner, the `npm test` script, audit report routing, README
and `.github/workflows/worker-controller.yml`. The independently accepted V2
engine, ledger, schema and test worker were not reopened. No production or
shared files, Git state, native/UI/cloud services, catalog/authority driver or
interrupted transport V2 lane were changed by this reviewer. Original transport
vectors were consumed only as test data.

## Findings and repairs

| ID | Observed problem | Final verification |
| --- | --- | --- |
| R1, P2 | Initial source digest omitted the contract acceptance file, three consumed vector files and both external fixture sources. | All six now occur in the source manifest and immutable run snapshots. All 25 manifest entries match their snapshots and current files; the final rehash rejects persistent input drift. |
| R2, P2 | An EOF timeout threw before stdout, stderr and command metadata were retained. Open reader streams could retain the event loop. | An escaped pipe holder now produces `eofObserved:false`, an EOF error, partial output and a command receipt, preserves scratch and fails. Reader streams are destroyed. |
| R3, P2 | A naturally occurring `kill(-pgid, 0)` EPERM after TERM threw before command evidence was written. This reproduced twice. | Both injected and naturally reproduced EPERM now retain output and command evidence, record unknown group state and process-management errors, preserve scratch and fail. EPERM is never accepted as an empty group. |
| R4, P2 | A live child could retain the event loop after the new terminal-observation ceiling. | With group signals deliberately denied, a bounded control wrote a failure receipt with `directChildTerminal:false` and `directChildUnrefOnFailure:true`. The wrapper exited before the independent supervisor retired its exact owned child group. |

The initial runner was
`2bf5bf923a5b97717cc96335d06c2b8d8aebd1be4a5a7ae2da2a3d392e26ba0f`.
The first repair was
`8e7202ed9fd316ca8e42bfef532cb2678795ef5305071741dceec99ca4d62068`.
Their snapshots, failed/incomplete attempts and negative-path results remain
under the review directory. Passing later controls do not replace those records.

## Preserved suites and integration checks

| Suite | Unchanged source SHA-256 | Preservation evidence |
| --- | --- | --- |
| Original 28 groups | `389500f0e5593e2487f1bc713f732d93bf674880abb1e090abc8dac1c71c53f3` | Matches HEAD and accepted V2 input/candidate copies. |
| Seven independent regressions | `b4757bb866c4fbc38ceff105246e4cfcb120fe5ed9e8503fa3dcd2e17a60a8b0` | Matches original independent regression source. |
| 36 focused repair groups | `619b93a562462363a9d8936c09b1a793d88eee13c2c581afd1dc233329d416a4` | Matches the accepted independent review fixture manifest. |

The root's final `check-4` receipt records all 71 groups passing against the final
runner, with source digest
`1be6500ebb140b468130d9eb8c0b02de9a1ab1f92b0bd69832b30c08d39deec8`.
This reviewer inspected its reports, source snapshots, command output hashes,
EOF, direct-child termination, empty-group and scratch-cleanup records without
repeating the full suite.

`npm test` invokes the integrated runner. Fresh output creation rejects an
existing destination; fixture copies and environment-selected report paths
preserve historical evidence. Nonzero exit, timeout, missing EOF, unknown/live
group state and process-management errors block success. Group grace periods
use monotonic time. Audit routing changes only the optional report destination;
its static-production-closure limitation remains explicit.

The workflow's push and pull-request paths cover controller files and every
external acceptance/vector/fixture input used by these suites. It pins Node,
installs the lockfile with `npm ci --ignore-scripts --no-audit --no-fund`, runs the
same test script and requests evidence upload on failure. The lock includes
optional Linux workerd binaries and the installed loader resolves the selected
platform package without requiring postinstall. These are source/lock checks,
not a claim that Linux CI executed successfully. Runtime/dependency versions,
source digest and host scope are retained in runner receipts.

## Executed controls and cleanup

Exact commands and outcomes are in
[`commands.json`](../verification/hosted-worker-controller-ci-review/commands.json).
The final controls exercised ordinary nonzero exit, same-group inherited pipes,
an escaped pipe holder, an ignored TERM requiring KILL, injected probe EPERM,
natural post-TERM EPERM, and a denied-termination observation ceiling. The
timeout controls scaled timer scheduling; they did not wait out the production
five-minute timeout. The helper bodies were extracted unchanged from each bound
runner snapshot.

Only exact review-owned groups were signalled. The final read-only inventory
found all 18 known toy PIDs absent, and the supervisor removed leftover owned
scratch after terminal inventory. Negative-path receipts preserve their original
unknown-group or retained-scratch observations. See
[`cleanup-final.json`](../verification/hosted-worker-controller-ci-review/cleanup-final.json).

The compact decision and evidence index are in
[`receipt.json`](../verification/hosted-worker-controller-ci-review/receipt.json).
Physical phones, native runtime gates, cloud/provider operation, Linux CI and GA
remain outside this review's evidence.
