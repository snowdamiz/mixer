# Independent review of the pending-registry corrections

Outcome: **no actionable findings in the two selected component corrections**.
The previous `audit_missing_schema_meta` defect is repaired in the exact frozen
candidate, and permanent terminal tracking now accepts the selected newer-version
replay without changing terminal evidence or delivery history. Root may select
these component sources; Engine integration and its separate controls remain an
independent acceptance boundary.

This review binds derivative receipt SHA-256
`6ea785b91c6c34e77a5c03bbfa4cd131ac969e59fcd7cd08787cab9a8c816106`,
audit source SHA-256
`8120ebd4786005b263264c1162fa5a6ed0a7a0347d235aa5b6c4e984b076e38d`,
registry source SHA-256
`99d8a5dc4e2e9b8875c262ae44d2f1307d3107d3bc48c4300e981f68ec12b428`,
and terminal contract selection SHA-256
`141f32609d338647687d8f49c63d4add83d395c4cb833173204dcb80d37ffd38`.
Only `pending-audit.ts` and `pending-registry.ts` differ from the original producer
production candidate. The public interface, SQL schema, dependency pins and
remaining production files are unchanged. The original changes-required review
remains preserved evidence about its older source.

The source assessment checks the exact changes in `corrections.diff`. The audit
constructor tests bounded table existence inside the transaction before running
schema creation or seeding metadata. An absent metadata table with either safety
table surviving, including an empty safety table, leaves the coordinator
unavailable. The existing exact-one-row metadata validation also remains intact.
Fresh installation still proceeds when all audit tables are absent.

The registry normalizes and validates a closed projection before the transaction.
For a permanent terminal row, a greater canonical int64 TEXT version is accepted
only when that terminal projection is byte-identical to the stored canonical
projection. That equality requires the same phase, digest and null next-due.
The new SQL updates only `state_version`; allocation, identity, terminal bytes,
quiescence, failures, skip visits, attention, attempt/run/visit fields and ticket/
disposition history remain unchanged. Equal versions still compare projection
bytes, older versions remain stale, and invalid, reopening or different-terminal
projections conflict without a write.

Five independent actual workerd/SQLite controls passed. They use a fresh excluded
review adapter extending the exact copied production sources, a different identity
population and new orchestration; they do not invoke the producer test runner.

| Independent control | Observed result |
| --- | --- |
| Fresh installation and scheduled progress after SIGKILL | Initial sequence `"0"`, sixteen empty completion slots and normal sequence `"2"` after a real restart. |
| Empty surviving completion table with metadata and summary absent | Startup and audit remain unavailable; exact schema and empty surviving table remain unchanged. This verifies existence rather than row-count gating. |
| Retained late unavailable completion and summary, then metadata removal | Actual held recovery times out, audit remains busy until settlement, and the exact late `unavailable` ticket is durably retained. After two SIGKILL/restarts, audit returns unavailable with null run ID; surviving schema/rows and registry bytes are identical, and recovery calls remain one. |
| Completed terminal, newer watermark and lost acknowledgement | Eight failures, attention, skip-seven and attempt-eight history are retained. The newer commit is observed while its acknowledgement is held; SIGKILL makes the request reject, exact retry returns duplicate after restart, the receipt is stable, the old ticket is stale, and no row becomes due. Every registry/meta field is compared with only `state_version` changed. |
| Stopped terminal, concurrent watermark requests and int64 boundary | Concurrent exact updates converge to the greatest version; older and equal replay semantics hold. Reopening, phase/digest changes, non-null next-due and an extra field conflict without mutation. Int64 maximum persists as TEXT across restart; overflow conflicts. A subsequent sixteen-page audit examines no records and starts zero recoveries. |

Reproduce from the repository root:

```sh
node verification/hosted-worker-pending-registry-corrections-review/run-review.mjs
node verification/hosted-worker-pending-registry-corrections-review/verify-packet.mjs
```

The selected independent run is
[`runs/20261025T045244777Z`](../verification/hosted-worker-pending-registry-corrections-review/runs/20261025T045244777Z/).
Its reviewed source digest is
`fab192d6cf29db11d5473f7c9557d330fb264403154d1fd7ac6fc2fa2c4daddb`;
observed Git revision is `29b33e40c51450b7ea143d52bbe9e4eb502e9bce`.
The runner binds sixteen source/helper/dependency files, exact compiled output,
argv/cwd/environment overrides, versions, output streams and source copies. It
verifies 165 frozen producer, earlier-review and derivative file bindings before
and after execution. All are unchanged.

The independent receipt records five disposed owned SQLite stores, six
identity-checked SIGKILL boundaries and eleven observed owned workerd identities.
All eleven PIDs and both command process groups are absent; both stdout/stderr
streams reached EOF; both direct children closed; all owned storage and scratch
paths were removed. No remote recovery cancellation is claimed. The environment
was Darwin arm64, Node v22.23.3, TypeScript 5.9.3, workerd 2026-07-30,
Miniflare 4.20260730.0 and workers-types 5.20260730.1. A reviewer hash-literal typo
failed preflight before starting a build child, runtime child or owned store; its corrected
bookkeeping is preserved in `preflight-correction.json` and is not a product
finding.

The producer's eight schema controls and four terminal controls remain existing,
separately source-bound evidence; they were not rerun here. This narrow review
does not replace the full component matrix, Engine cross-DO replay/entry/barrier
acceptance, controller regressions or any deployed qualification. No live source,
producer packet, Engine file, root tracker, Git state, device, cloud service,
credential or publication was changed. No excluded catalog-inspector,
authority-driver or rejected outbound-transport lane was read, imported or run.
Physical-phone and every final/native/signing/store/FieldLog/operational/GA gate
remain outside this component review and are not marked passed.
