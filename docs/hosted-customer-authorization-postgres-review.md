# Customer authorization PostgreSQL review

**Accepted as a finite local durable lookup prerequisite and selected fixture /
migration integration.** No unresolved finding remains in the reviewed source.
This result is still a pure policy evaluation. It does not authorize a domain
operation, complete customer authorization, qualify a deployment or pass a GA gate.

The producer's current [final seal](../verification/hosted-customer-authorization-postgres/final-seal.json)
is SHA-256 `61c25aad3dc31050f6a196950a7a51fc21bad158f9f8936e884f568a36b8b6ff`.
Exact executed inputs, commands, versions, output, independent probes and cleanup
are retained in the [review packet](../verification/hosted-customer-authorization-postgres-review/).
Revision `cb56d4b9d979ffc02554be991466a180e7882cd3` is root-supplied context;
the byte manifests identify the actual sources executed.

## Finding closure

**AUTHZ-PG-REVIEW-001 / P2 is closed.** Original `run-3` passed all 23 producer
methods and 15 of 16 independent probes. Its sole failure reproduced admission
after separately granting `pg_read_server_files`, `pg_write_server_files` and
`pg_execute_server_program`. Those roles confer privileged host capabilities
without the elevated attributes checked by the original guard. PostgreSQL
documents their possible superuser-level authority in its
[predefined-role reference](https://www.postgresql.org/docs/17/predefined-roles.html).

The root-selected correction rejects every reachable role whose literal prefix
is `pg_`, retaining all prior owner, attribute, DML, helper and FORCE RLS checks.
Independent real-catalog probes reject each grantable predefined role directly
and through a non-inherited intermediary with `MEMBER=true`, `USAGE=false` and
`SET=true`. An unprivileged intermediary alone and the restored runtime pass.
`pg_database_owner` is implicit and cannot be directly granted: the prefix guard
covers it, but grant-only probes do not change database ownership to exercise
that case. No privileged file or program capability was invoked. The original
[finding](../verification/hosted-customer-authorization-postgres-review/finding-001.json)
and [closure](../verification/hosted-customer-authorization-postgres-review/finding-001-closure.json)
remain separate records.

## Executed evidence

Final standalone and selected shared-fixture modes each pass **42/42 methods**:
25 producer and 17 independent, with warnings-as-errors source compilation and
format checks. The selected shared-fixture mode executes only the unique named
AST FunctionDef from the actual ordinary harness; its main body is not imported
or run. Its helper hash is
`648bd53e0b94641cd5764486b28e7c99e2687447cccf59ecdba1005ec323ed3b`.
Migration compilation is deliberately omitted in that mode, so the focused test
actually executes its new migration-loading path.

The producer and independent methods verify canonical real lock waits in both
directions, membership insertion and physical deletion after head waits, a newly
committed family valid-after fence, exact identity/target RLS, SELECT-only runtime
and fixed-helper grants/ownership, family/credential window intersection without
invented revisions, 64/65 overflow including ineligible rows, indirect owner
rejection, immediate `queue: false` exhaustion, same-connection cleanup of every
GUC after exceptions/throws/exits/SQL errors, and the five-second transaction
limit. The intentional timeout emits an expected Postgrex disconnect log and
then a new authorized transaction succeeds.

A separate disposable migration smoke applies all five ordinary migrations,
confirms an empty rerun, rolls back `[00003, 00002]`, checks their tables are
absent, reapplies `[00002, 00003]`, and confirms another empty rerun. Independent
before/after reconstruction matches the exact allowed integration patch. All
five ordinary test files retain `all: true`; their migration expectations and
the aggregate rollback step are updated while worker-preservation assertions
remain unchanged. The new down-migration removes only its owned policies before
table drops, fixing the dependency found by the producer smoke without CASCADE
or an `up` authority change.

The final selected-fixture input digest is
`d04ddfb0488be193a2cfd9e42390e8ac4f2b92bda2d1bf816ac713cf4680da9a`;
the standalone digest is
`bb5e183d44275cf53565b28021b54eb2fefa59833634b01b26fd1cc8b3c65d89`.
Environment: Darwin arm64, Elixir 1.20.4, OTP 29 / ERTS 17.1, PostgreSQL 17.11,
Python 3.14.8 and `ERL_FLAGS='+S 2:2'`. Current inputs match both final runs.

All six review attempts stopped their owned cluster and removed scratch roots.
Earlier review-only pool-size and regclass-encoding errors remain recorded. The
transitional archive audit caught a rewritten sealed collector; it was restored
byte for byte and the expanded collector moved to a new path. Baseline 208,
correction 30 and integration 194 sealed entries match. Initial read-only Git
discovery commands are retained in
[discovery-commands.json](../verification/hosted-customer-authorization-postgres-review/discovery-commands.json);
no Git mutation occurred.

## Acceptance boundary

The facade captures caller-supplied `now` before database admission. Real
credential/family expiry during a lock wait can still pass at that captured
instant; a fresh current-time evaluation rejects. Membership RLS separately
uses the database statement clock and can deny more conservatively. No fresh
trusted-clock check before an effect, TTL/grace extension, positive cache or
reusable domain authority is supplied. The pure projection still lacks binding,
family and individual membership revisions required for immutable audit.

PostgreSQL 16, full standard CI and runtime execution of the five changed
ordinary suites, including held-worker assertions, remain pending. Also pending:
audited provisioning/non-recycling and writer enforcement, transaction-bound
domain authority, immutable content binding, complete audit and principal-bound
idempotency/Oban atomicity, protected customer routes/console, provider/service/CI
identity, deployed role topology/Neon/TLS/operations, published FieldLog packages
and accountable GA review. RLS remains the trusted-API defense boundary; identity
GUCs are not cryptographic proof against a hostile API or compromised credentials.
No broad harness, frozen lane, production, native/UI or device execution occurred.
