# Authorization fixture and migration integration

The ordinary local PostgreSQL harness now creates the authorization fixture
roles/database and supplies its port. The focused test supports both a
precompiled migration and test-side migration loading. The five existing
foundation/build suites retain `all: true` coverage with the fifth migration
included. This is a focused local integration receipt; PostgreSQL 16 and the
full ordinary CI suite remain pending.

This extends the
[durable lookup prerequisite](hosted-customer-authorization-postgres.md) and its
[runtime-role correction](hosted-customer-authorization-postgres-correction.md).
Both earlier sealed reports, original/intermediate attempts and original source
copies remain intact. The original top-level collector is restored byte for
byte. The expanded collector is new:
`verification/hosted-customer-authorization-postgres/ci-integration/run.py`.

Root froze the integration contract. The shared harness change is one unique
top-level synthetic fixture provisioning function plus one call after its owned
cluster starts. It creates only the separate test administrator, nonlogin owner,
nonprivileged runtime, disposable authorization database and required local
grants. The focused collector extracts and compiles only that exact named
FunctionDef through Python AST; it does not import or run the shared script's
main body. The real helper source is hashed in the receipt. No production
database, credential, role or service is selected.

Normal test discovery conditionally loads the exact migration file when it is
not already compiled. The selected CI mode deliberately omits migration
compilation to exercise this path. Foundation/storage expected lists append
`00003`; admission/aggregate/coordinator counts become five. Aggregate rollback
uses two migrations in descending order and reapplies them in ascending order.
All existing worker-preservation assertions remain unchanged. Their execution
is still pending because the broader suites were not run here.

The all-migration smoke found a genuine down-migration dependency: resource RLS
policies referenced membership tables being dropped. The new migration now
removes only its own two policies on each of its twelve tables before relation
drops, without `DROP CASCADE`. Authority policies and `up` behavior are unchanged.
The original failed smoke and cleanup remain retained.

The focused collector's final `ci-integration/run-3` passes source compilation
with warnings as errors, formatting, exact shared provisioning, test-side
migration loading and **25/25 authorization methods**. A separate process applies
all five ordinary migrations to a second empty disposable database, confirms an
empty idempotent rerun, reverts `[00003, 00002]`, checks their tables are absent,
reapplies `[00002, 00003]`, and confirms another empty rerun. The restored original
collector separately passes **25/25** in `standalone-run-2` with its precompiled
migration path. Each owned cluster stopped and temporary root was removed.

Current selected input-tree SHA-256:
`2d9f921e665f993592a74dc38c4fbe1836b8b1d7ddbf4dabc38e6fc95df53916`.
The new nested collector's explicit repository-root and hosted paths were
verified. Exact before/after bytes, allowed delta, commands, tool versions,
source/collector hashes and cleanup are retained in the
[integration packet](../verification/hosted-customer-authorization-postgres/ci-integration/report.md).
The current environment is Darwin arm64, Elixir 1.20.4, OTP 29 / ERTS 17.1 and
PostgreSQL 17.11. Revision `cb56d4b9d979ffc02554be991466a180e7882cd3` is supplied
root context, not a queried Git revision.

This remains read-only current policy evidence. It does not activate a protected
customer operation or domain authority. The trusted-clock before-effect check,
complete immutable audit evidence, atomic domain/audit/idempotency/Oban work,
customer HTTP/console workflows and deployed role/Neon/TLS/provider/operations/GA
qualification remain pending. No broad harness, frozen lane, native/UI/device,
production migration/deployment or customer communication occurred.
