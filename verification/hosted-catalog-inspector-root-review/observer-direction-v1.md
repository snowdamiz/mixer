# Catalog observer and runtime connection direction

Root selects an explicit private `verify(catalog_repo, runtime_repo)` seam for
the isolated hosted inspector. The first real Postgrex implementation of the
single-runtime-connection proposal could not reproduce the accepted selected
manifest: PostgreSQL's restricted `pg_settings` view omitted 21 setting rows.
The original accepted Python fixture captures legacy/enforcement catalogs through
its catalog/admin connection and captures fresh-session fields through runtime.
The failed single-repo attempt and actual differential output must remain evidence.
No role privilege or selected-manifest relaxation is authorized by that failure.

The new component uses a separately provisioned, dedicated catalog observer,
with `pg_read_all_settings` visibility and without superuser, create-role,
create-database, replication or bypass-RLS attributes. Its actual inspection runs
in an explicitly read-only, repeatable-read transaction. A disposable test fixture
may provision this observer to verify the seam; no live role, credential,
migration or production bootstrap change is part of this implementation.
Observer session/profile checks and actual capability failures must fail closed.

The existing restricted runtime role remains unchanged. The caller holds one
runtime checkout while recording its exact nine accepted fresh-session fields
and backend identity before and after catalog inspection. All catalog counts,
legacy observations and enforcement observations share one observer snapshot.
The two roles/connections are distinct. Existing transactions or checked-out
contexts, confused dynamic repositories and an identical underlying backend
reject. The caller supplies trusted, separately configured repositories and owns
fresh-connection provisioning; observed settings alone do not prove freshness.

The original fixed expected manifest remains
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
The added observer must first be shown not to change that selected authority
contract. No enrollment of observed drift, omitted hidden setting, runtime role
broadening, SQL-domain narrowing or caller-selected expectation is permitted.
Queue-free checkout and a single remaining absolute budget cover both acquisitions
and all operational queries. Cleanup has an explicit bounded rollback/connection
retirement disposition even after that operational budget has expired.

A successful result is only point-in-time diagnostic metadata. One catalog
snapshot does not make the two connections an atomic authorization operation,
prevent privileged DDL, qualify subsequent traffic, or accept a combined
Oban/domain schema. Production observer provisioning, bootstrap publication
coordination, current-authority/request integration and independent component
acceptance remain separate pending work. Native, physical and GA gates remain open.
