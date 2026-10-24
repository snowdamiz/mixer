# Current-authority catalog correction selection

Root requires ASR01–ASR03 corrections from the
[independent authority review](hosted-authority-schema-review.md) before selecting
the final schema/catalog prerequisite. The frozen resolver's 128 cases replay,
and the reviewer adds 48 observations, including five successful reproductions
of missed deployment drift. Those five are failing completeness requirements.
Root verified all 97 review bindings and the review's 240 producer bindings.
No baseline runtime authorization bypass was demonstrated.

Keep the correction isolated. Preserve the existing tables, columns, types,
resolver algorithms, lock order, role boundaries and every original behavior
assertion. Extend the actual inspection and comparison machinery and add focused
real PostgreSQL drift tests. Do not edit prior packets or live hosted code. A new
candidate must fail closed for the selected state changes below without granting
new privileges or weakening the original resolver boundary.

1. Inspect all actual user and internal constraint triggers, including enabled
   state, relation/function/constraint associations, event/timing and deferred
   state. Selected authority triggers must retain their enabled origin state.
   Include exact constraint validation/deferrability and index
   validity/readiness/liveness/immediacy, preserving the baseline's observed
   definitions. Disabled lifecycle guards and disabled FK enforcement must be
   detected before protected admission. Do not normalize away enforcement flags.
2. Inspect relation kind, logged persistence and replica identity. These fourteen
   authority relations must remain ordinary permanent tables with the selected
   default replica identity. Reject a changed or missing relation. This checks
   deployment drift; it does not qualify logical replication or crash recovery.
3. Inspect effective privileged parameter SET/ALTER SYSTEM grants for runtime,
   including PUBLIC and any reachable role. Runtime must not acquire the ability
   to set `session_replication_role` or another selected superuser-only safety
   parameter, or ALTER SYSTEM. Capture applicable `pg_parameter_acl` entries,
   including parameter names outside the visible registered-setting inventory;
   a raw direct-grant list alone is insufficient. Retain the existing rejection
   of unsafe role reachability and role capabilities.
4. Select and inspect applicable role/database startup defaults and validate
   safety settings on an actual newly connected runtime session. At minimum bind
   the exact expected session/effective role, `session_replication_role=origin`,
   `row_security=on` and the selected READ COMMITTED transaction behavior. Inspect
   relevant `rolconfig`/`pg_db_role_setting` defaults rather than assuming a clean
   parameter ACL proves safe startup. Add real ALTER ROLE/ALTER DATABASE/default
   tests and restore them before the next fresh control connection. This expands
   the reviewer guidance; it was not a reproduced finding in the old packet.

Catalog comparison must remain stable across independently created owned
clusters. Resolve OIDs to schema-qualified identities; internally generated FK
trigger names may contain OIDs and cannot serve as portable identities. Preserve
all actual trigger entries and multiplicities, association and enforcement data.
Do not collapse unknown or duplicate entries into an accepted record. Retain both
raw actual inspection output and a deterministic selected comparison form, with
executable rejection for malformed, missing, extra or changed required entries.
Do not turn a mismatch into an automatic baseline update. Freeze the safe expected
manifest from the selected schema separately from candidate observations.

Reexecute all 128 original cases. Preserve the old review's five reproductions
and add corrected assertions requiring rejection of those same changes. Retain
its 43 positive controls, existing ten drift cases, actual 89 constraints,
26 indexes and 74 trigger baseline, with updated counts only if a documented
fixture adds test-only objects outside the protected schema. Exercise direct,
PUBLIC and reachable-role parameter grants and fresh-session unsafe defaults;
prove the original safe runtime still admits and denied operations remain denied.
Use ordinary DDL and real sessions; do not manufacture evidence by modifying
PostgreSQL system catalogs. If an invalid-index state cannot be reached safely
through ordinary fixture DDL, keep that runtime case explicit rather than calling
a source-only inspection an executed rejection.

Retain exact input/source/tool/command/output hashes, every failed attempt and
owned cleanup. Independently review the new frozen packet before root acceptance.
The formatter-only atomic-storage correction proceeds separately; it must retain
its old SQL/catalog bytes. Before product composition, the selected enforcement
properties must cover the combined authorization and domain schema, including
its deliberately deferred constraints. No live migration, BEAM coordinator,
authenticated HTTP, provider, operational or GA gate is accepted by this direction.
