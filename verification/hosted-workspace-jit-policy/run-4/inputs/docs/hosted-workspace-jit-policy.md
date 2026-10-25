# Bounded authorization transaction JIT policy

The shared `MixerHosted.Authorization.Postgres.Session` sets `SET LOCAL jit = off`
after its existing local time bounds and verifies the effective value before
any authorization topology or identity query. It first requires an active owner
transaction. A setting error or an effective value other than `off` fails closed.
This includes workspace directory reads and ordinary artifact authorization.
All request, checkout, transaction, statement and lock budgets remain unchanged:
5 seconds for each existing total/checkout/SQL boundary and 500 ms for locks.

The bounded RLS-expanded directory plans have compilation overhead even when
little data is returned. The prior paired local diagnostic measured 631 JIT
functions and a 201.041 ms organization query versus 5.886 ms with JIT disabled.
That evidence supports this narrow policy; it does not establish the cause of
the Ubuntu CI transaction deadline. PostgreSQL documents that JIT often costs
more than it saves for short queries, and `jit = off` applies at both planning
and execution, including prepared statements. See [JIT decisions](https://www.postgresql.org/docs/16/jit-decision.html).
`SET LOCAL` restores the previous session value after commit and rollback; no
pool or server setting is changed. See [SET](https://www.postgresql.org/docs/16/sql-set.html).

## Focused verification

Run only the selected collector, with an explicit source revision:

```sh
python3 verification/hosted-workspace-jit-policy/run.py \
  --output verification/hosted-workspace-jit-policy/run-1 \
  --source-revision <current-head>
```

It snapshots only its explicit ordinary module, migration, test and signed-vector
allowlist; compiles those copies against hashed pinned dependency BEAMs; starts
one disposable PostgreSQL 16.15 Linux arm64 container; runs the 24 workspace,
20 transaction, 15 artifact-read and 19 artifact-storage regressions plus eight
new JIT controls; and stops/removes its own container and scratch. The dedicated
`jit_policy_spec.exs` remains outside ordinary discovery and requires the existing
transaction fixture. It uses a separate disposable database with that fixture's
restricted runtime role and applies only its required migrations. This is not
the broad hosted harness or complete-migration acceptance.

The new controls cover inherited `on` and `off` restoration after success and
explicit rollback, SQL-error rollback and connection reuse, workspace success
and failed identity rollback, unchanged effective bounds, restricted-role
admission, unsafe-role rejection, outside-transaction rejection, and an actual
SQL fault that changes JIT back on before the effective-value check for both
workspace and artifact owners. The observer records the first ordinary workspace
transaction and nonexecuting organization EXPLAIN, without changing the policy.
The saved organization query timing excludes its following observer work; the
observed transaction includes that work and is not a production latency result.

Execution results, exact input hashes and limitations will be recorded with the
collector receipt. Exact-push PostgreSQL16 Ubuntu CI remains required to evaluate
the previously observed CI failure. Native runtime and capture checks remain
paused; phones remain disconnected. No provider, deployment, customer, FieldLog
or GA qualification is claimed.
