# Independent transaction JIT review

The scoped Session correction passes independent development review. No product
repair was required. The product source matches the retained PostgreSQL 16.15
producer run; six additional independent groups pass against a separate
restricted login on the same server version. Exact-push Ubuntu CI remains
pending, and these results do not establish the cause of the earlier CI timeout.

The review examined only the Session policy change, its selected JIT tests and
collector, and the retained run-4 evidence. The source diff adds an active-
transaction guard, `SET LOCAL jit = off`, and an exact effective-value check
before topology and identity queries. Existing transaction isolation, five-second
statement/idle/query budgets, 500-ms lock timeout and `queue: false` remain
unchanged. A mismatched setting rolls back as authorization unavailable. The
change does not alter grants, RLS, identity mapping, domain decisions or clocks.

The [producer evidence integrity check](../verification/hosted-workspace-jit-review/producer-run4-integrity.json)
verifies every retained input and output hash in run 4, all 86 recorded selected
methods with no failure/skip/exclusion, and complete owned cleanup. Current
Session, selected JIT spec and collector bytes match their tested snapshot.
Those 86 methods are audited producer results; they are not represented as newly
independent execution. The organization query's recorded JIT-off plan and timing
support the scoped policy, without proving production latency or Ubuntu CI.

## Independent execution

Run from the repository root:

```sh
python3 verification/hosted-workspace-jit-review/run.py
```

The [accepted immutable attempt](../verification/hosted-workspace-jit-review/attempts/20261025T161255.730119Z-a62e2766/receipt.json)
passes six groups, with zero failures, skipped or excluded methods:

| Independent group | Actual database assertion |
| --- | --- |
| Successful preparation | Prior session JIT `on` and `off` each become `off` inside the transaction; the same backend restores the exact prior JIT and nondefault timeouts afterward. |
| Explicit owner rollback | Both prior JIT values and every nondefault setting are restored on the same backend after an intentional rollback. |
| Identity denial and reuse | A missing credential denies, restores the same backend settings, and permits a subsequent valid preparation on that connection. |
| SQL error abort | Real PostgreSQL division-by-zero after successful preparation aborts the transaction and restores the exact prior settings/backend. |
| Effective-setting fault | A SQL telemetry fault sets JIT back on immediately after the local setting. The actual effective-value query denies before any topology query; the connection is restored. |
| Outside transaction | A direct preparation call fails before changing session policy or bounds. |

Every group checks the restricted non-superuser/non-BYPASSRLS login has no owner
role path. Before each test checkout, inherited statement/idle timeouts are
4,321 ms and the lock timeout is 321 ms. Inside successful preparation they are
exactly 5 seconds/500 ms/5 seconds with READ COMMITTED; afterward the full settings
row, including backend PID, equals the original. Pool size one plus a single
explicit checkout prevents accidental restoration assertions on another
connection. Settings observations are retained as JSONL in the attempt.

This fixture was independently authored and imports no producer test fixture.
It compiles only Session and ordinary authorization migrations 3/4, against
explicit hashed existing dependency beams. It starts one named disposable pinned
PostgreSQL 16.15 Debian Linux arm64 container on loopback. Source snapshots,
source-tree/dependency digests, exact commands, tool versions, outputs, result
and cleanup are bound in the receipt. Session SHA-256 is
`8ae27291a2e0777dfde6f995cf8c1a64c6ac8e2e7b0e7660afdb7cac76382727`.

The [first independent collector attempt](../verification/hosted-workspace-jit-review/attempts/20261025T161147.971667Z-3229e578/receipt.json)
is retained as an invalid fixture attempt, not a product failure. Its readiness
probe accepted Docker's temporary initialization Unix-socket server, which
stopped before role creation. The collector now requires the final TCP listener.
Both attempts stopped/removed their owned PostgreSQL container and scratch;
the successful run reports no source changes during execution.

The top-level [review acceptance](../verification/hosted-workspace-jit-review/review.json)
binds the final receipt, current tested sources, outputs, producer integrity and
cleanup. No broad hosted harness, complete application compilation, frozen lane,
provider, production migration/deployment/credential action, browser, capture,
native runtime or physical phone was used. Other projects' processes/data were
preserved. Provider, Neon operations, customer, FieldLog and GA qualification
remain outside this development review.
