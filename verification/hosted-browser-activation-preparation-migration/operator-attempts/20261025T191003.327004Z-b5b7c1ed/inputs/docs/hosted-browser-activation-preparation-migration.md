# Inert activation-preparation migration and operator plan

Migration `20261025000008_add_browser_activation_preparation.exs` delegates `up/0`
only to the accepted `ActivationPreparationSchema.statements/0` and `down/0`
only to its `rollback_statements/0`. It installs the access-evidence composite
and preparation helper, then revokes PUBLIC execution and type usage. The
original nine migration files, StorageSchema, preparation SQL/decoder and both
catalog versions are unchanged. No role, credential, policy, application caller,
startup, grant to a lifecycle login or code version selection is installed.
The [accepted SQL](hosted-browser-activation-preparation-sql.md) and
[versioned catalog](hosted-browser-catalog-v2-review.md) retain their independent
component boundaries. Catalog success is only `:function_surface_verified`;
it cannot authorize readiness or full relation correctness.

The future operator rollout has four separate changes. This document records a
local synthetic rehearsal, not authorization to run production commands.

1. Stop new browser-session admission and drain in-flight lifecycle operations
   before making an operator/schema/version change. Keep admission closed on any
   unexpected state. An already consumed callback claim cannot resume or be
   retried after failure; a fresh login is required. There is no automatic V1
   fallback, claim replay or retry of a partial provisioning plan.
2. Apply the ordinary inert migration under the established schema/relation
   owner. The ten-migration runner proves no new role and no runtime execution,
   table privilege or type usage. Before separately provisioning this addition,
   both fixed catalog versions deny the mixed deployment. This denial is expected
   and must keep admission closed. V1 accepts only the original baseline.
3. A separately authorized privileged operator obtains the existing explicit
   isolated writer, lifecycle-login and relation-owner names, then executes the
   entire `ActivationPreparationSchema.provisioning_statements/3` list, in order,
   on one dedicated connection. It already contains BEGIN and COMMIT. Do not
   route statements independently through a pooled Repo. At the first error,
   roll back that same connection and discard the entire plan. Never replay
   initial `StorageSchema.provisioning_statements/2` on an existing installation,
   create replacement roles, change credentials or loosen runtime privileges to
   make the upgrade work. The accepted preflight rejects malformed names, unsafe
   role topology and unexpected initial helper/type ACLs, including third-party
   default grants. Provisioning transfers only the new helper to the writer and
   new type to the relation owner, grants their selected EXECUTE/USAGE, and revokes
   its temporary writer schema CREATE before commit. It does not change baseline
   functions, relations, policies or data. The actual operator authority must be
   separately qualified on Neon; local superuser evidence does not prove that.
4. A separate trusted application release explicitly selects exact integer V2
   and all remaining readiness checks before admission may reopen. This slice
   wires no caller or readiness consumer. V2 admits the provisioned combined
   surface; V1 and the legacy three-argument call deny it. No installed-database
   expectation learning or fallback is permitted.

For rollback, stop admission and drain again, then coordinate the application
version with the fixed schema expectation while admission remains closed. An
operator with sufficient existing object/schema authority runs only migration
00008 `down`; no earlier migration or baseline provisioning is replayed. The
function's new writer owner alone does not determine DROP authority: an existing
database/public-schema owner can still remove it in the local PostgreSQL fixture.
Production operator authority must be qualified directly; do not add runtime-role
membership or grants to make rollback work. The helper is dropped before its access-evidence type. V1 and the legacy
three-argument check accept the unchanged baseline again; V2 denies it. A later
00008 reapply is inert again and requires its own complete operator upgrade.
Consumed claims remain consumed throughout; no stale operation may resume.

The operator rehearsal uses `browser_admin`, the superuser of one owned isolated
loopback PostgreSQL 17 cluster. Its migration Repo executes `SET ROLE
browser_schema_owner`, an isolated NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT
relation owner. The ordinary ten-migration check separately connects as restricted
LOGIN `migration_owner`, with no superuser or role-creation privileges. Existing
roles `browser_writer` (NOLOGIN), `browser_lifecycle` and `browser_ordinary` (LOGIN)
retain restricted flags and no memberships. Synthetic `browser_admin` executes only the additive down successfully.
The separate `browser_schema_owner` role also successfully performs post-provision
down using its pre-existing database/public-schema ownership, observed directly
on PostgreSQL 17; neither function ownership transfer nor the fixture's NOLOGIN
flag removes that authority. Actual lifecycle and ordinary runtime logins fail
fixed helper/type DROP attempts in separately rolled-back transactions, and V2
and the baseline remain unchanged. No new runtime privilege or role membership
is granted for rollback. These synthetic names and identities are evidence, not deployment
configuration.

Run the two bounded checks from the repository root:

```sh
python3 hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py --output verification/hosted-browser-activation-preparation-migration/migration-attempts
python3 verification/hosted-browser-activation-preparation-migration/run.py
```

The first uses ten explicit filenames and the two existing delegate schemas plus
the preparation schema and its exact external decoder source. It checks full
apply/no-op, additive-only down/up preserving baseline object OIDs/source/ACLs,
relations/policies/constraints/data, seven-step down/reapply preserving existing
build data, and full rollback/reapply. The second exercises the real additive
Ecto migration against an already provisioned V1 baseline, both fixed catalog
versions, one-connection upgrade, actual claimed-session preparation, operator
rollback, malformed/unsafe roles, unexpected direct/default grants and an
interruption after ownership transfer followed by rollback. Actual runtime
helper/type teardown denial and existing schema-owner DROP authority are checked.
Baseline data and
catalog snapshots are compared exactly. The original nine migration bytes are
retained and hashed in both source snapshots.

Both runners snapshot named ordinary sources and load exactly eight locked
Ecto/Postgrex/Jason/Oban dependency beam directories, including application files.
They perform selected `elixirc --warnings-as-errors` and actual projectless
`mix format --check-formatted`. Each immutable attempt retains exact commands,
versions, revision, source/dependency/output hashes and all failures. Owned
PostgreSQL clusters, scratch and selected compiler products are removed even on
failure. No hosted application, broad Mix discovery/harness, frozen inspector,
authority-driver or rejected Worker transport is loaded.

Independent migration review, full relation admission, trusted Store transaction
and original deadline ownership, runtime pool/custody/current access/OIDC joins,
provider/HTTP/console, Neon/operator deployment, customer/FieldLog and all GA
qualification remain pending. Computer use, capture, native simulator/emulator
runtime tests and the final physical-phone matrix remain paused and were not
attempted. No production publication, customer message, migration, credential
change or other project's process was performed.
