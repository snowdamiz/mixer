# Durable authorization runtime-role correction

The current candidate rejects every reserved PostgreSQL `pg_` role reachable
from the runtime login, including indirect, non-inherited paths permitting
`SET ROLE`. It retains the existing owner-chain, privileged-attribute,
authorization DML, helper and FORCE RLS checks. A minimally privileged application
authorization role needs none of these predefined roles in this slice.

This corrects the runtime guard in the
[baseline lookup prerequisite](hosted-customer-authorization-postgres.md).
That sealed report and its original source, results and seal remain historical
evidence. Its enumerated role checks omitted predefined server-file/program
capabilities. Independent review reproduced a Decision after separately granting
`pg_read_server_files`, `pg_write_server_files` and
`pg_execute_server_program`. The reproduction used only synthetic role grants,
policy evaluation and revocation; no server program or server-file capability
was executed. The original review result remains retained under
`verification/hosted-customer-authorization-postgres-review/run-3/`.

Root froze the correction before editing. Only the current
`authorization/postgres/session.ex` and producer test changed. The guard uses
literal `pg_catalog.substr(rolname::text, 1, 3) = 'pg_'`, avoiding SQL LIKE's
underscore wildcard. The reachable-role check includes direct and transitive
membership independently of inherited privilege availability. Switched sessions
already reject. There is no monitor/read-all exception, dependency change,
shared API/default change, activated route, production role provisioning or
deployment.

Producer `correction-run-1` compiles the selected sources with warnings as errors,
passes formatting and **25/25 methods** against a new disposable PostgreSQL
cluster. The two added methods grant/evaluate/revoke every grantable predefined
`pg_` role and four indirect, explicitly non-inherited `SET ROLE` paths through
a benign intermediary. The unprivileged intermediary by itself remains allowed.
`pg_database_owner` is implicit and cannot be directly granted; the guard's
literal prefix still covers it, and existing owner-role checks remain.
All original lock, revocation, identity, RLS, scope, window, ceiling, overflow,
timeout and cleanup tests pass unchanged.

The current executed input-tree digest is
`60a70bd97bdb61c892b290a573ca2b11e1a3c18281eb9c6177702b4268ac4d17`.
Revision `cb56d4b9d979ffc02554be991466a180e7882cd3` is supplied root context;
no Git ran. Exact commands, tool versions, source copies, output and cleanup are
in
[`correction-run-1/receipt.json`](../verification/hosted-customer-authorization-postgres/correction-run-1/receipt.json).
The environment remains Darwin arm64, Elixir 1.20.4, OTP 29 / ERTS 17.1,
PostgreSQL 17.11, Python 3.14.8 and `ERL_FLAGS='+S 2:2'`. The owned cluster stopped
and its temporary root was removed. Independent correction review is pending.

The corrected result remains a durable read-only evidence lookup feeding a pure
policy callback. It is not transaction-bound domain authority. Existing
caller-captured time and 30-second issued-at skew semantics remain; trusted-clock
recheck before persistence is still required. Separate family/binding/membership
audit revisions, immutable domain/audit/idempotency/Oban composition, protected
customer routes/console, audited membership administration, real provider,
deployed role topology/Neon/TLS/operations, native/device/FieldLog and GA
qualification remain pending. The earlier baseline's full scope limitations
continue to apply.
