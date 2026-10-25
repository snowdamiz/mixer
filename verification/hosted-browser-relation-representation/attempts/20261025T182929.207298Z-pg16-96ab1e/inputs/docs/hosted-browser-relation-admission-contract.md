# Browser relation admission: exact source contract

Document revision 2, 2026-10-25, still describing catalog manifest version 1.
This is the bounded next implementation contract for
the relation portion of [the lifecycle runtime contract](hosted-browser-lifecycle-runtime-contract.md),
not a runtime implementation or security acceptance. The base revision is
`4492bbc74c47c77514951ae49b0fe418c7873db8`; exact input SHA-256 values are in
[source-bindings.json](../verification/hosted-browser-relation-admission-contract/source-bindings.json).
The live working tree also contains independently reviewed, **partial**
`browser_auth/catalog.ex` and `catalog_manifest.ex`. They are read-only context
for this contract and cannot establish relation admission, trusted Store ownership
or browser readiness. The binding product plan remains complete in scope.

The owned files are this document and
`verification/hosted-browser-relation-admission-contract/`. No migration,
provisioning, credential, grant, application, route or provider changes occur here.
No database, native runtime, phone, computer-use or capture process is started.
Frozen catalog-inspector/authority-driver and rejected Worker V2 source is neither
read nor reused. Production qualification and GA gates remain pending.

The first frozen packet was **incomplete and unaccepted**: its source allowlist
omitted migration 00005's delegated ordinary artifact DDL and therefore missed
the customer-idempotency incoming FK. Its exact files, prior receipt, positive
source-check output and blocking review are preserved under
[history/incomplete-v1](../verification/hosted-browser-relation-admission-contract/history/incomplete-v1/receipt.json).
Those twelve positive methods did not establish completeness. This correction
expands the source closure and adds an executable omission control; it claims no
PostgreSQL runtime acceptance.

## Additive private interface and prerequisites

The proposed next producer owns a new module, without changing the existing
partial function prerequisite:

```elixir
MixerHosted.BrowserAuth.RelationCatalog.check_relation_surface!(
  repo, expected_roles, original_monotonic_deadline_ms
) # => :relation_surface_verified
```

`repo` is the fixed trusted LifecycleRepo supplied inside a Store-owned checked-out
transaction. `expected_roles` is the exact RuntimeConfig map with only
`lifecycle_login`, `writer`, `relation_owner`, `ordinary_runtime_login`, with four
distinct restricted names. Neither is request-selected. `in_transaction?/0`
alone proves neither Store ownership nor Repo/configuration provenance. The
future trusted owner join must establish those facts separately.

Before this check, the same transaction must successfully run the current
function/type prerequisite, including current login/session equality, role
flags/reachability/isolation, explicit relation-owner expectation, schema escape
denial, function/type manifests and ACLs, application SECURITY DEFINER escape
denial and transaction policy. Its current result
`:function_surface_verified` must never be treated as a complete catalog pass.
The relation check must revalidate its own role-map shape, transaction presence,
current user/session identity and original deadline; a caller-supplied boolean
or cached prerequisite result is inadmissible. The future trusted Store calls
both fixed checks itself on the same checkout before its fixed helper call.

The original monotonic deadline covers checkout, **both** prerequisites, Store
SQL, decoding, final checks and commit. Every query uses remaining positive
milliseconds, `queue: false`, no retry, and no timeout/deadline reset. Check time
before/after each query, during bounded decoding/comparison and just before
return. READ COMMITTED and the admitted transaction-local timeout/JIT/bytea/search
path policy remain in effect. Raise a single redacted private unavailable failure
on any discrepancy; it must escape/rescue into rollback, never be converted to a
successful transaction value. Return only `:relation_surface_verified`; it is a
private prerequisite, not an authority receipt or an owner/storage/readiness claim.

The function and relation OIDs are installation-local linkage identifiers. In the
same transaction, resolve each expected function's qualified name and exact
signature, verify its admitted body/configuration/owner/ACL, then require each
trigger `tgfoid` to equal that OID. No hardcoded database OID or name-only match.
Owner-level coherent rewriting is outside this boundary. Per-operation observed
drift checks require serialized operator schema changes; they do not create an
atomic DDL shield across several READ COMMITTED catalog queries.

## Source oracle and completeness matrix

[expectations.py](../verification/hosted-browser-relation-admission-contract/expectations.py)
is a handwritten transcription from accepted ordinary migrations,
`StorageSchema` and ordinary `Authorization.Postgres.Session`; its exported
[relation-matrix.json](../verification/hosted-browser-relation-admission-contract/relation-matrix.json)
contains every ordered column, original-source CHECK expression, FK, unique key,
extra index, grant and complete policy expression. It is never generated from
the database being admitted. The offline command capturer evaluates only
allowlisted accepted source with an inert `Ecto.Migration.execute/1` stub; it loads
no Ecto application, Repo or Postgrex. It compares the accepted source SQL against
the independent transcription. Its syntax checks are documentation evidence only.

Below, `B.` abbreviates `public.mixer_browser_` and `A.` abbreviates
`public.mixer_authz_`. The catalog must contain each qualified name exactly once.

| Relation | Columns | CHECKs | PK | UNIQUE | Outgoing FK | Indexes | User triggers | Policies | Exact source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| B.sessions | 22 | 17 | 1 | 1 | 2 | 2 | 1 | 3 | StorageSchema:302–324 |
| B.session_vault | 10 | 6 | 1 | 0 | 1 | 1 | 1 | 3 | StorageSchema:327–337 |
| B.oidc_attempts | 26 | 20 | 1 | 0 | 1 | 2 | 1 | 3 | StorageSchema:340–369 |
| B.session_events | 30 | 17 | 1 | 0 | 1 | 1 | 2 | 2 | StorageSchema:371–400 |
| A.profiles | 7 | 6 | 1 | 1 | 0 | 2 | 0 | 4 | migration 00003:8–16; 00004:8–10 |
| A.principals | 5 | 4 | 1 | 1 | 0 | 2 | 0 | 4 | migration 00003:17–24 |
| A.bindings | 7 | 2 | 1 | 0 | 2 | 1 | 0 | 3 | migration 00003:25–35; 00004:14–16 |
| A.families | 8 | 4 | 1 | 1 | 2 | 2 | 0 | 5 | migration 00003:36–46 |
| A.credentials | 9 | 4 | 1 | 0 | 1 | 1 | 0 | 5 | migration 00003:47–58 |
| Total | 124 | 80 | 9 | 4 | 10 | 14 | 5 | 32 | full sets, not minimum counts |

Paths are pinned in source-bindings.json: StorageSchema means
`hosted/lib/mixer_hosted/browser_auth/storage_schema.ex`; migrations are
`hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs`,
`20261025000004_add_authorization_state_revisions.exs` and
`20261025000006_add_customer_workspace_discovery.exs`. Migration
`20261025000007_add_browser_sessions.exs:5–8` installs the inert StorageSchema
statements. Ordinary Session is
`hosted/lib/mixer_hosted/authorization/postgres/session.ex:113–171`.

Two incoming FKs cross the exact-nine boundary:
`A.memberships(principal_id) -> A.principals(id)`, migration 00003:91–104, and
`public.mixer_customer_idempotency(principal_id) -> A.principals(id)`,
`hosted/lib/mixer_hosted/customer_artifacts/schema.ex:64–83` (the inline FK is
at line 67), installed by migration 00005:3–5. Both use default nondeferrable
MATCH SIMPLE / UPDATE NO ACTION / DELETE NO ACTION. Inspect and compare both
boundary FKs plus their RI triggers, without claiming full memberships or
customer-idempotency relation admission. The full accepted source audit below
finds no third incoming FK.
Thus there are **12 FK groups**, including both boundary FKs, and **48 internal RI
triggers across both endpoints**. Include both sides of those twelve groups,
including the four referencing-side triggers outside the nine. With five user
triggers the bounded extraction contains 53 triggers. The exact-nine
`pg_constraint` set contains 80 CHECK + 9 PK + 4 UNIQUE + 10 FK + 4 constraint-trigger
rows = 107; adding both incoming FKs makes the boundary extraction 109. Do not
mistake `contype='t'` for an extra CHECK or silently filter these rows away.

## Complete accepted DDL source closure

[accepted-ddl-source-audit.json](../verification/hosted-browser-relation-admission-contract/accepted-ddl-source-audit.json)
records every accepted migration entrypoint, exact delegate, source digest,
classification and all 27 raw-SQL FKs (13 ordinary authz, 9 customer artifact,
5 browser). The earlier build migrations have three additional build-only FK
routes, all outside the exact-nine target. All **nine** migration filenames are
explicitly allowlisted, and the checker rejects a missing/new migration or an
omitted SQL delegate rather than claiming completeness from selected positive
comparisons. No broad hosted harness is used.

| Accepted entrypoint | Reviewed DDL source | Incoming FK into exact-nine |
| --- | --- | --- |
| 20261024000000_add_oban.exs:4 | installed approved Oban.Migration.up(version:14); PostgreSQL dispatcher and exact v01–v14 source chain, static only | none; Oban-only objects |
| 20261025000000_add_build_journals.exs:4–57 | Ecto build journal/index/check DSL, static only | none |
| 20261025000001_add_build_admission.exs:4–72 | Ecto build DDL and raw ALTERs at 31–39; references(:mixer_build_reservations) at 50–59 | none; three build-only FK routes |
| 20261025000002_add_build_aggregate_limits.exs:4–62 | Ecto capacity/index DSL, static only | none |
| 20261025000003_add_customer_authorization.exs:8–108 | inert capture of ordinary SQL | memberships.principal_id → principals.id |
| 20261025000004_add_authorization_state_revisions.exs:7–17 | inert capture of two ADD COLUMN statements | none |
| 20261025000005_add_customer_artifact_storage.exs:3–5 | delegated ordinary CustomerArtifacts.Schema.statements/0; table DDL at schema.ex:8–85, including ALTER at 59–61 | customer_idempotency.principal_id → principals.id at schema.ex:67 |
| 20261025000006_add_customer_workspace_discovery.exs:4–93 | inert policy/display-name SQL capture | none |
| 20261025000007_add_browser_sessions.exs:3–8 | delegated ordinary StorageSchema.statements/0 | five FK groups wholly inside exact-nine |

The Oban boundary is source inspection of the already installed approved
general-purpose dependency, not imported product-engine implementation or a new
dependency. Its `hosted/deps/oban/lib/oban/migration.ex:268–275` dispatch selects
Postgres for the approved adapter; `migrations/postgres.ex:19–32,67–79` selects
v01–v14. The exact sixteen files and `hosted/mix.lock` are source-pinned. No
dependency/Ecto/Repo migration is executed. The two owned delegates and all
entrypoints are bound independently of the database being admitted.

The twelve source methods now assert this closure and the complete incoming FK
multiset. An explicit negative control removes migration 00005's captured output
and proves that the now-required second FK becomes missing. Future accepted
migrations/delegates require updating/reviewing this static closure before they
can be admitted; runtime catalog output still cannot supply its expected oracle.

## Relation and column contract

All nine are permanent, local, ordinary `relkind='r'` relations in `public`, with
ENABLE and FORCE RLS and exact configured `relation_owner`. They are not owned
by either application login or writer. Require no partition/inheritance edges,
partition bound, typed-table link, foreign-table definition or rewrite rule;
replica identity is the installed default. Extra browser-prefixed table/view/
foreign/partitioned/materialized relations in any namespace fail closed. Index
and row-type catalog objects are classified separately rather than counted as
additional ordinary relations.

Ordered column notation below is `name:type`; `?` is nullable, and `=1` is the
only default expression. All unmarked columns are NOT NULL, including PK columns.
All columns have no identity/generation, `typmod=-1`, array dimensions 0, local
definition and inheritance count 0. Require contiguous `attnum=1..N`, no dropped
slot or extra attribute. Types are exact pg_catalog `bytea`, `text`, `int4`, `int8`
and `bool`, not user domains or types that merely format alike. Text has the
installed `pg_catalog.default` collation; other types have collation OID zero.
Column/index collation identity must agree. Default locale/provider/version
qualification belongs to the operator environment and is not supplied by this
role map. Physical placement, statistics and TOAST size are not authorization
expectations. Not-null/identity/generated/default are distinct catalog fields;
do not infer them from a CHECK. [PostgreSQL column catalog](https://www.postgresql.org/docs/17/catalog-pg-attribute.html)

```text
B.sessions:
 id:bytea cookie_digest:bytea status:text epoch:bigint revision:bigint generation:text
 csrf_digest:bytea created_at:bigint last_seen_at:bigint absolute_expires_at:bigint
 idle_expires_at:bigint expected_profile_id:text expected_profile_version:integer
 initial_config_digest:bytea config_digest:bytea profile_id:text? profile_version:integer?
 principal_id:text? family_id:text? credential_ref:text? credential_revision:bigint?
 audit_sequence:bigint
B.session_vault:
 browser_id:bytea epoch:bigint session_revision:bigint vault_generation:bigint
 ciphertext_version:integer envelope_kind:text key_id:text? iv:bytea? tag:bytea? ciphertext:bytea?
B.oidc_attempts:
 state_digest:bytea browser_id:bytea browser_epoch:bigint browser_revision:bigint cookie_digest:bytea
 generation:text config_digest:bytea profile_id:text profile_version:integer issuer:text client_id:text
 redirect_uri:text return_route:text nonce_digest:bytea created_at:bigint expires_at:bigint status:text
 claim_digest:bytea? claimed_at:bigint? claim_expires_at:bigint? completion_reason:text?
 ciphertext_version:integer=1 key_id:text? iv:bytea? tag:bytea? ciphertext:bytea?
B.session_events:
 browser_id:bytea sequence:bigint audit_schema:integer operation:text outcome:text request_id:text
 recorded_at:bigint old_revision:bigint? new_revision:bigint old_epoch:bigint? new_epoch:bigint
 old_status:text? new_status:text config_digest:bytea attempt_state_digest:bytea?
 profile_id:text? profile_version:integer? principal_id:text? family_id:text?
 issuer_hash:bytea? subject_hash:bytea? client_hash:bytea? credential_hash:bytea?
 profile_revision:bigint? binding_revision:bigint? principal_revision:bigint? family_revision:bigint?
 credential_revision:bigint? token_issued_at:bigint? token_expires_at:bigint?
A.profiles:
 id:text version:integer issuer:text client_id:text identity_class:text active:boolean state_revision:bigint=1
A.principals:
 id:text identity_class:text active:boolean not_before:bigint revision:bigint
A.bindings:
 profile_id:text profile_version:integer subject:text identity_class:text principal_id:text active:boolean revision:bigint=1
A.families:
 id:text profile_id:text profile_version:integer principal_id:text active:boolean not_before:bigint expires_at:bigint? revision:bigint
A.credentials:
 profile_id:text profile_version:integer reference:text principal_id:text family_id:text active:boolean not_before:bigint expires_at:bigint? revision:bigint
```

Only attempts.ciphertext_version has an inline default; profiles.state_revision
and bindings.revision acquire default 1 through ALTER. Their fast-default missing
value may be absent after a physical rewrite or be one int8 value 1. All other
columns require no missing value; no arbitrary non-NULL `attmissingval` is accepted.
This representation must be reviewed on both selected majors before runtime use.
Fast defaults and ordinary defaults must not be conflated. [PostgreSQL 16 column metadata](https://www.postgresql.org/docs/16/catalog-pg-attribute.html)

## Constraints and indexes

Require the complete multiset of original-source expressions in
relation-matrix.json, not just the names/counts. This includes the compound
session linkage, erased/live vault, pending/claimed/terminal attempt, event
transition and token/audit shape checks in full, in addition to all lengths,
ranges, canonical generation/key/request patterns and enumerations. Nullable
CHECKs intentionally preserve SQL NULL semantics; never add implicit NOT NULL or
rewrite NULL into false. There are exactly 80 CHECK expressions.

All ordinary CHECK/PK/UNIQUE/FK constraints are local, validated, nondeferrable,
not initially deferred, with no inherited/parent/domain constraint or NO INHERIT
addition to a CHECK. Catalog `connoinherit` is false for these CHECKs and true
for local ordinary PK/UNIQUE/FK and user constraint-trigger rows. This
kind-specific flag must not be confused with an actual inheritance edge.
[PG16 key creation](https://raw.githubusercontent.com/postgres/postgres/REL_16_STABLE/src/backend/catalog/index.c),
[PG17 key creation](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/catalog/index.c),
[PG16 FK creation](https://raw.githubusercontent.com/postgres/postgres/REL_16_STABLE/src/backend/commands/tablecmds.c),
[PG17 FK creation](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/commands/tablecmds.c),
[constraint-trigger creation](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/commands/trigger.c)

Check exact keys, ordered referenced keys, referenced relation, and
the relation-local check expression. Every FK is MATCH SIMPLE, UPDATE NO ACTION,
DELETE NO ACTION (`s/a/a`). Match builtin equality operator identities/types in
`conpfeqop/conppeqop/conffeqop`; no same-named custom operator. PostgreSQL stores
relation NOT NULL in pg_attribute on both selected majors. User constraint
triggers have their own pg_constraint rows. [PostgreSQL 16 constraints](https://www.postgresql.org/docs/16/catalog-pg-constraint.html),
[PostgreSQL 17 constraints](https://www.postgresql.org/docs/17/catalog-pg-constraint.html)

| Relation | PK | Additional UNIQUE | Outgoing FK |
| --- | --- | --- | --- |
| B.sessions | id | cookie_digest | (profile_id,profile_version,credential_ref) → A.credentials(profile_id,profile_version,reference); (family_id,profile_id,profile_version,principal_id) → A.families(id,profile_id,profile_version,principal_id) |
| B.session_vault | browser_id | — | browser_id → B.sessions(id) |
| B.oidc_attempts | state_digest | — | browser_id → B.sessions(id) |
| B.session_events | (browser_id,sequence) | — | browser_id → B.sessions(id) |
| A.profiles | (id,version) | (id,version,identity_class) | — |
| A.principals | id | (id,identity_class) | — |
| A.bindings | (profile_id,profile_version,subject) | — | (profile_id,profile_version,identity_class) → A.profiles(id,version,identity_class); (principal_id,identity_class) → A.principals(id,identity_class) |
| A.families | id | (id,profile_id,profile_version,principal_id) | principal_id → A.principals(id); (profile_id,profile_version) → A.profiles(id,version) |
| A.credentials | (profile_id,profile_version,reference) | — | (family_id,profile_id,profile_version,principal_id) → A.families(id,profile_id,profile_version,principal_id) |

There are 13 constraint-backed btree indexes, one for every PK/UNIQUE key, plus
exactly `public.mixer_browser_one_attempt` on attempts `(browser_id,browser_epoch)`
with exact source predicate `status IN('pending','claimed')`. Every key is ASC
NULLS LAST, no INCLUDE, expression, exclusion or NULLS NOT DISTINCT addition.
Require `indisvalid/indisready/indislive/indimmediate=true`, correct
`indisunique/indisprimary`, `indisexclusion=false`, `indnullsnotdistinct=false`,
no partition/inheritance, expected index owner, exact relation backlink and
constraint `conindid` backlink. Keys resolve to default builtin `pg_catalog`
`bytea_ops/text_ops/int4_ops/int8_ops` btree operator classes according to exact
type, with text default collation and zero collation otherwise. Match operator
family and input type identity as well. [PostgreSQL index catalog](https://www.postgresql.org/docs/17/catalog-pg-index.html)

For PK/UNIQUE, conindid is that relation's own backing index; for FK, it is the
referenced key's admitted index. Both link directions must match, not merely a
same-shaped standalone index. A new incoming FK affecting any of the nine also
denies rather than being ignored as another relation's object.

Server-generated constraint/index names are diagnostic identifiers, not the
expected oracle. Compare a **multiset** keyed by relation, kind, ordered columns,
FK target/keys/actions, expression and complete enforcement flags. Never collapse
to a set or map before detecting duplicates. Explicit source names (the partial
index and five user trigger names) are exact. Arbitrary renaming of an automatic
name does not replace any structural match. This choice avoids inventing names
from live catalog output. Storage-derived index health such as `indcheckxmin`
must be decoded and handled using its documented snapshot restriction; it cannot
silently excuse an invalid key/enforcement definition. Fresh installation forms
and any operationally permitted health transitions need runtime review.

## Triggers and exact function-source join

| Relation | Name | Timing/events | Function | Constraint/deferred |
| --- | --- | --- | --- | --- |
| B.sessions | mixer_browser_integrity | AFTER INSERT OR UPDATE, ROW | public.mixer_browser_integrity() | yes / initially deferred |
| B.session_vault | mixer_browser_integrity | AFTER INSERT OR UPDATE, ROW | public.mixer_browser_integrity() | yes / initially deferred |
| B.oidc_attempts | mixer_browser_integrity | AFTER INSERT OR UPDATE, ROW | public.mixer_browser_attempt_integrity() | yes / initially deferred |
| B.session_events | mixer_browser_integrity | AFTER INSERT, ROW | public.mixer_browser_event_integrity() | yes / initially deferred |
| B.session_events | mixer_browser_immutable | BEFORE UPDATE OR DELETE, ROW | public.mixer_browser_event_immutable() | no |

All five require `tgenabled='O'`, no UPDATE OF filter, no WHEN, no arguments,
no transition table, no parent/clone. The four constraint triggers require exact
`tgconstraint` linkage and `tgdeferrable/tginitdeferred=true`; immutable has no
constraint linkage and both flags false. Require session replication role
`origin` during admission/operation; enabled mode O alone is insufficient when
the session is in replica mode. The five trigger SQL definitions are
StorageSchema:574–581. [PostgreSQL trigger catalog](https://www.postgresql.org/docs/17/catalog-pg-trigger.html)

Function identities/source ranges are StorageSchema:487–527 (integrity),
528–554 (attempt integrity), 555–557 (event immutable), 558–570 (event integrity).
[trigger-function-source-bindings.json](../verification/hosted-browser-relation-admission-contract/trigger-function-source-bindings.json)
pins exact compiled `prosrc` byte hashes/lengths from the accepted source,
including meaningful whitespace. The future relation prerequisite must join to
the independently admitted four no-argument PL/pgSQL trigger-returning SECURITY
DEFINER functions, exact writer owner and five helper-local settings, with no
PUBLIC/login execution. It must not locally bless a changed body or weaken the
existing eighteen-function prerequisite. A source hash is a source-binding aid;
the current function comparator still compares exact source bytes.

Internal RI triggers are separately classified, never skipped using
`tgisinternal=true`. Each of twelve exact FK groups has its four `O`-enabled
ROW triggers linked to that FK and correct referring/referenced endpoint:
`pg_catalog.RI_FKey_check_ins`, `RI_FKey_check_upd`, `RI_FKey_noaction_del`,
`RI_FKey_noaction_upd`. Specifically, check_ins/check_upd are AFTER ROW
INSERT/UPDATE on the referencing endpoint, and noaction_del/noaction_upd are
AFTER ROW DELETE/UPDATE on the referenced endpoint. Each has the exact FK's
tgconstraint, tgconstrrelid identifying the opposite endpoint, and the referenced
key index's tgconstrindid. Require nondeferrable/not-initially-deferred flags,
empty arguments/filter/WHEN/transition tables, no parent clone, and builtin
function identity; do not reuse local numeric
trigger OIDs or `RI_ConstraintTrigger_*` names as cross-installation expectations.
PG16/17 fixture review must confirm this full internal linkage shape, and must
exercise disabling a parent-side and a child-side trigger independently.

## Exact grants and complete policy sets

StorageSchema:227–289 defines new writer rights/policies; ordinary migration
00003:116–154 and 232–241 defines the existing policies. Ordinary
Session:125–143 requires ordinary table SELECT with no authz DML/column mutation.
New browser privileges do not alter the ordinary role's selected topology.

| Relation | Writer table privileges | Writer column UPDATE only |
| --- | --- | --- |
| B.sessions | SELECT, INSERT | cookie_digest,status,epoch,revision,generation,csrf_digest,last_seen_at,absolute_expires_at,idle_expires_at,profile_id,profile_version,principal_id,family_id,credential_ref,credential_revision,audit_sequence |
| B.session_vault | SELECT, INSERT | epoch,session_revision,vault_generation,ciphertext_version,envelope_kind,key_id,iv,tag,ciphertext |
| B.oidc_attempts | SELECT, INSERT | status,claim_digest,claimed_at,claim_expires_at,completion_reason,key_id,iv,tag,ciphertext |
| B.session_events | SELECT, INSERT | none |
| A.profiles | SELECT | state_revision |
| A.principals | SELECT | revision |
| A.bindings | SELECT | none |
| A.families | SELECT, INSERT | active,revision |
| A.credentials | SELECT, INSERT | active,revision |

Lifecycle and PUBLIC have no direct table/column privileges on any of the nine.
Ordinary runtime has table SELECT on the five authz relations, no browser
privileges and no authz mutation/REFERENCES/TRIGGER/TRUNCATE. Writer has exactly
the table and column rights above, no table-level UPDATE, no DELETE/TRUNCATE/
REFERENCES/TRIGGER, no immutable key or authz linkage UPDATE outside those exact
lists, and no grant option. Sessions intentionally permits the listed browser
profile/principal/family/credential linkage updates; its integrity trigger and
fixed helper transitions constrain them. PostgreSQL 17
MAINTAIN is additionally forbidden. Owner rights are handled separately, never
mistaken for application grants. Reject grants to unreviewed third-party roles
or grantors rather than quietly ignoring them; initial application ACL rows are
owner-granted, and explicit column ACL rows contain only the indicated writer
UPDATE entries. The owner ACL is compared as the selected major's builtin owner
default; no owner column grants are required. [PostgreSQL 17 GRANT](https://www.postgresql.org/docs/17/sql-grant.html)

Expand `COALESCE(relacl,acldefault('r',relowner))` and each explicit `attacl`
with `aclexplode`, preserving grantee/grantor/is_grantable. A NULL column ACL
means no explicit column grants, not no effective column access. Cross-check
effective table privileges individually and effective per-column SELECT/INSERT/
UPDATE/REFERENCES for lifecycle, writer and ordinary roles using `has_*` checks,
including PUBLIC/inheritance/default effects. Effective writer column SELECT/
INSERT legitimately follow table grants. Deny extra mutation authority rather
than counting only explicit narrow UPDATE rows. Existing role-topology admission
must close role SET/membership/ownership/predefined-role routes. Broader writer
grants on tenants/memberships/views/foreign tables must also be denied by the
composed catalog boundary, not inferred from this nine-relation table alone.

For each five authz relations preserve exactly `scoped_read` (SELECT,
USING=its complete ORDINARY_PREDICATES entry, WITH CHECK=NULL) and `scoped_lock`
(UPDATE, same USING, WITH CHECK=false). Both are **permissive PUBLIC-targeted**
policies (`polroles=[0]`); "scoped" does not mean SQL AS RESTRICTIVE. The exact
profile, subject/binding, principal-linked and family/credential current_setting
expressions are fully transcribed in relation-matrix.json. Do not replace them
with true or a broad identity-class check. [PostgreSQL policy catalog](https://www.postgresql.org/docs/17/catalog-pg-policy.html)

All new policies are permissive with exact singleton writer target:

| Tables | Additional exact policies |
| --- | --- |
| B.sessions, B.session_vault, B.oidc_attempts | mixer_browser_read: SELECT USING true / check NULL; mixer_browser_insert: INSERT USING NULL / check true; mixer_browser_update: UPDATE USING true / check true |
| B.session_events | mixer_browser_read and mixer_browser_insert only |
| A.profiles, A.principals | mixer_browser_read as above; mixer_browser_lock: UPDATE USING true / check false |
| A.bindings | mixer_browser_read only |
| A.families, A.credentials | mixer_browser_read, mixer_browser_insert, mixer_browser_update as above |

Thus 10 ordinary policies plus 22 new writer policies = 32, with no others.
`directory_read` does **not** exist on any exact-nine relation. Migration 00006
adds it only on memberships/organizations/projects and adjusts scoped_read only
on those same three; these changes do not rewrite the five identity relations'
ordinary policies. The offline checker explicitly verifies that boundary.
Do not widen this into acceptance of those three relations or the other ordinary
authz tables; ordinary authorization's current Session checks still apply.
Reject every missing/extra/duplicate policy, altered target/command/permissiveness
or expression, including an unexpected restrictive policy. Preserve NULL versus
false versus true and role OID zero. Additional permissive PUBLIC or ordinary-role
OR policies must fail even when all expected policies still exist.

## Bounded extraction shape for the future producer

Use fixed pg_catalog-qualified SELECT statements and bound trusted role values.
Expected relation names are compiled literals/arrays, never SQL identifiers from
request input. Do not SELECT application data. Resolve all expected names first,
then use those OIDs only as same-transaction joins; do not use live rows to populate
the expected manifest. Explicit result columns/tuple types only; no SELECT *,
unbounded JSON aggregation or unchecked Postgrex rows. Each family has sentinel
`LIMIT cap+1`, exact expected count/multiset validation and a total decoded-wire
budget of at most 2 MiB across this prerequisite. Row caps bound wire volume,
not arbitrary database planner memory; remaining driver/statement deadlines
also bound server work. Oversized input is unavailable, never truncation-success.

| Family | Fixed source/shape | Accepted max / sentinel |
| --- | --- | --- |
| Session/server | current/session user, server_version_num, transaction policy, session_replication_role | 1 / 2 |
| Relations | pg_class + namespace + owner; expected nine or unexpected browser-prefixed table-like object | 9 / 10 |
| Columns/defaults | pg_attribute positive attnum including dropped slots; pg_type/namespace/collation and pg_attrdef | 124 / 125 |
| Constraint boundary | pg_constraint where conrelid in nine OR confrelid in nine; complete flags/keys/operators/expression | 109 / 110 |
| Indexes | pg_index + index pg_class/namespace/access method/opclass/opfamily/collation; same fourteen only | 14 / 15 |
| User + FK triggers | triggers on nine OR tgconstraint in twelve exact FK groups; include other endpoint | 53 / 54 |
| Policies | pg_policy on exact nine; name/command/permissive/roles/using/check | 32 / 33 |
| Raw relation/column ACL expansion | pg_class/pg_attribute ACL arrays expanded only after scalar caps | 512 / 513 |
| Effective role/table rights | 3 application roles × 9 tables × per-major table privilege booleans | 27 / 28 |
| Effective role/column rights | 3 application roles × 124 columns × four privilege booleans | 372 / 373 |
| Forbidden rules/partitions/inheritance/foreign/extra escape objects | fixed EXISTS queries over catalog identities | zero / 1 |

Use at most 63-byte identifiers, four restricted role names, OIDs decoded as
nonnegative integer identities, at most 32 entries per key/operator/column vector
and no more than four role OIDs per policy (the actual exact sets have size one).
Each ACL array has a pre-expansion 64-entry cap and 16 KiB text-byte cap. A
malformed/NULL/missing catalog identity or cap breach fails closed. Store catalog
exception text nowhere in returned failures/receipts.

Guard expression node trees **before** deparsing: node text at most 32 KiB;
then each `pg_get_expr(..., false)`/constraint/index/trigger deparse output at
most 8 KiB, with a distinct failure marker. Do not substitute NULL for oversize
because NULL is an expected value for several fields. CASE-gate deparsing on the
node/array cap and validate the returned output byte length too. Required
function `prosrc` bytes are bounded by the already selected function prerequisite
(65,536 bytes/function), not silently omitted by the relation query. Check source
and helper OID joins without fetching application rows.

For example, the relation query has a static predicate of this shape; other
families join to its accepted exact OIDs and retain their own independent caps:

```sql
SELECT n.nspname::pg_catalog.text, c.relname::pg_catalog.text,
       c.oid::pg_catalog.int8, c.relkind::pg_catalog.text,
       c.relpersistence::pg_catalog.text, c.relowner::pg_catalog.int8,
       c.relrowsecurity, c.relforcerowsecurity, c.relispartition,
       c.reloftype::pg_catalog.int8, c.relreplident::pg_catalog.text
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE (n.nspname = 'public' AND c.relname = ANY($1::pg_catalog.text[]))
   OR (pg_catalog.left(c.relname::pg_catalog.text, 14) = 'mixer_browser_'
       AND c.relkind IN ('r','p','v','m','f'))
ORDER BY n.nspname, c.relname, c.oid
LIMIT 10
```

This illustrative SQL is not implemented or database-validated by this lane.
For effective-privilege rows use one bounded row per role/object with a fixed
boolean vector; query every privilege separately because comma-list `has_*`
tests answer whether **any** listed privilege exists. Include version-specific
MAINTAIN probing only in the PG17 fixed statement. Unexpected catalog server
major, query result shape or privilege token fails closed.

## PG16/17 canonicalization and acceptance gaps

Select explicit PG16 and PG17 decoders from numeric server_version_num; never
fall back to an unreviewed major. Numeric OIDs and raw pg_node_tree strings are
installation/version-local. Use qualified object/type/operator/opclass/collation
identity plus exact structural linkage. `pg_get_expr` and `pg_get_constraintdef`
are decompiled forms, not original SQL; disable pretty printing and keep
search_path=pg_catalog. Whitespace removal, alias removal, regular expressions,
sorted AND operands, removing casts/qualifiers or replacing IN with ANY are not
an authorization comparison strategy. [PostgreSQL deparse APIs](https://www.postgresql.org/docs/16/functions-info.html)

Before implementation acceptance, independently install the source-pinned
migrations and operator topology into **separate clean PG16 and PG17 fixtures**,
review deparsed representations for all 80 CHECKs, 32 policies, three defaults
and the partial-index predicate, and freeze exact per-major compile-time
expectations with source/tool/server bindings. Do not record an attacked live
catalog and then compare it with itself. New fixtures should prove equivalent
expected forms and exercise mutations against both majors. This documentation
lane intentionally provides no fabricated deparse strings or runtime pass.

Two concrete version differences require explicit handling. PG17 has table
MAINTAIN privileges; PG16 does not. Both raw ACL expansion and effective denial
must account for the selected major. [PG16 GRANT](https://www.postgresql.org/docs/16/sql-grant.html),
[PG17 GRANT](https://www.postgresql.org/docs/17/sql-grant.html)
PG16 uses `pg_collation.colliculocale` and database `daticulocale`; PG17 uses
`colllocale` and `datlocale`, and supports builtin locale-provider metadata.
Do not execute a query naming the other major's field or treat the rename as
permission to relax collation identity. [PG16 collation](https://www.postgresql.org/docs/16/catalog-pg-collation.html),
[PG17 collation](https://www.postgresql.org/docs/17/catalog-pg-collation.html),
[PG16 database](https://www.postgresql.org/docs/16/catalog-pg-database.html),
[PG17 database](https://www.postgresql.org/docs/17/catalog-pg-database.html)

The next producer still needs actual bounded SQL/comparison implementation,
independent review, both-major catalog/deparse/internal-RI fixtures, full effective
ACL escape closure, exact current transaction/owner composition, deadline/fault/
redaction checks and Store rollback integration. Function/type prerequisite
acceptance stays separate; the proposed v2 activation-preparation helper/type is
not in this version-1 surface. Mixed versions fail closed until explicitly
selected. Complete owner/Store/provider/HTTP/console/customer/Neon/operator/FieldLog
and GA acceptance remain pending.

[runtime-adversity-matrix.json](../verification/hosted-browser-relation-admission-contract/runtime-adversity-matrix.json)
lists 48 concrete transaction, relation, column, constraint, index, trigger,
policy, ACL, canonicalization and composition cases, all `pending_runtime`.
The corrected offline checker passes twelve source/structure methods, including
16 shape mutations, six policy mutations and the omitted-artifact-delegate
negative control; these are not PostgreSQL attack tests.
Command/tool/source/output scope and resource cleanup are recorded in
[receipt.json](../verification/hosted-browser-relation-admission-contract/receipt.json).
