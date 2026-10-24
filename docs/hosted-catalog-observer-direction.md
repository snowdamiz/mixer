# Catalog observer and runtime connection direction

Revision 2: root selects an explicit private `verify(catalog_repo, runtime_repo)` seam for
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

The original fixed manifest
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`
remains immutable historical authority. It grants database CONNECT only to its
owner and runtime role, so a directly connected observer cannot satisfy it.
Root therefore explicitly selects a new, separately versioned isolated observer
profile. Its declarative baseline delta adds only CONNECT for the fixed
`catalog_inspector_observer` role to the fixture database ACL. The exact delta,
derivation, new expected hash and all otherwise unchanged selected bytes must be
reviewed. Never derive expectations from observed database state. The original
profile must continue rejecting the new grant, rather than being relabeled as a
pass. Any additional selected delta requires root coordination.

The observer uses its own direct connection with LOGIN in the isolated fixture.
The component must verify its selected membership options, absence of protected
role reachability/object ownership, restricted attributes and expected session.
Do not connect the inspector through an elevated owner login and then demote it.
The observer is not a runtime member and receives no data/writer permission.
Fresh negative cases must cover additional CONNECT subjects/grant option,
TEMP/CREATE/PUBLIC privileges, extra observer memberships or privilege flags,
and attempts to acquire protected runtime/writer/resolver/owner authority.
Original raw-model controls and exact unchanged authority SQL remain bound.
The new profile and component still require fresh independent review.
No enrollment of unrelated observed drift, omitted hidden setting, runtime role
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

The superseded unchanged-manifest proposal is preserved under
`verification/hosted-catalog-inspector-root-review/observer-direction-v1.md`.
The direct-login CONNECT requirement was found before observer implementation;
no production account or access policy was changed.
