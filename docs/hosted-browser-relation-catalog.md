# Bounded browser relation prerequisite

`MixerHosted.BrowserAuth.RelationCatalog.check_relation_surface!/3` now implements
the private relation prerequisite against the accepted version-1 nine-table
surface. It returns only `:relation_surface_verified` or raises
`RelationCatalog.Unavailable` with `browser storage unavailable`. This is a
component candidate awaiting independent review. It neither installs a runtime
owner nor enables storage, routes, providers or readiness.

The trusted future Store supplies its fixed Repo, exact four-role map and the
original monotonic deadline. The checker independently verifies transaction
presence, all four restricted distinct role names, current/session login,
restricted role flags and absence of membership edges, transaction settings and
remaining positive time under the original 5,000 ms cap. Every fixed SELECT uses
`queue: false`, `log: false` and its current remaining timeout, with no retry or
deadline reset. Every query must return a typed Postgrex SELECT result without
diagnostic messages and with the same positive backend PID. Time is checked
before and after queries, each decoded row, each comparison row and final return.
A same-backend observation does not prove trusted Store or Repo provenance.

The fixed families resolve all nine relations, 124 ordered columns, 109 boundary
constraints (80 CHECK, nine PK, four UNIQUE, twelve FK and four user-trigger
constraints), fourteen indexes, 53 triggers, 32 policies and exact raw/effective
ACLs. Numeric OIDs link both FK endpoints, ordered keys, equality operators,
referenced key indexes, all 48 builtin RI triggers and the five explicit user
triggers. Builtin type, equality operator, opclass/family and collation identities
are qualified; index collation OIDs must equal admitted column collation OIDs.
Each user trigger joins its exact no-argument function OID, trigger return type,
language, writer owner, SECURITY DEFINER flag, five settings, execution denial
and every source byte. The complete function/type prerequisite remains separate.

The handwritten source-contract structure and reviewed per-major deparse
literals live in the two new `hosted/priv/browser_auth/relation_surface_v1_pg*.json`
files. The only static representation allowances are generated constraint/index/
RI names and the two reviewed bigint fast-default forms. The partial-index and
five user-trigger names remain exact. CHECK dependency-column vectors come from
the reviewed clean source installation, matched to the independent source-compiled
expression multiset before selection. Expressions and function sources are never
whitespace-, cast-, alias- or regex-normalized. Runtime rows cannot supply an
expected value; production code reads no verification file or filesystem path.

`RelationManifest` checks the two fixed JSON digests at compile time. Every
accepted DDL source, delegated schema, ordinary authorization Session, exact
nine migration entrypoints, `mix.lock` and the sixteen-source pinned Oban migration
closure is checked against its embedded digest and declared `@external_resource`.
A changed or missing source fails compilation. The build must retain the locked
Oban package sources; compilation from beams alone is unqualified. There is no
new dependency. A separately reviewed helper/type-only additive migration is
outside this explicit original-nine installer and changes no relation expectation.

Every family has its contract sentinel LIMIT, including 110 constraints, 54
triggers and 513 expanded ACL rows. Typed decoders check identifiers, OIDs,
nullable scalars and bounded vectors and enforce at most 2 MiB of decoded wire.
ACL arrays must pass both 64-entry and 16 KiB scalar guards before expansion.
Expression nodes pass a 32 KiB guard before deparsing; deparse output is limited
to 8 KiB with a distinct failure marker, preserving expected NULL values.
Function sources are independently bounded at 65,536 bytes. No application row,
SELECT-star, unbounded aggregate, repair, grant, migration or provider operation
is performed by this checker. Bounded EXISTS checks deny inheritance, rules,
foreign definitions and all writer/lifecycle table, column, sequence and schema
ownership/CREATE escape rights outside the exact nine, including memberships,
views and foreign tables. Complete SECURITY DEFINER/type/schema/role-topology
closure still requires the separate function prerequisite.

Only PostgreSQL majors 16 and 17 with C/libc (`c`), UTF8, origin replication,
default text collation, NULL locale versions and the reviewed fresh index-health
state are admitted. PG17 owner MAINTAIN ACL entries are selected explicitly;
all application MAINTAIN is denied. Other majors, locales/providers/versions,
Neon and index-health transitions require separate qualification. Multiple
READ COMMITTED observations cannot prevent coherent owner rewriting; serialized
operator schema changes remain an external requirement.

The final standalone fixtures passed 233 methods/65 live mutations on PG16.15
and 234 methods/66 live mutations on PG17.11. These overlapping counts are
component methods, **not 48 completed runtime-contract cases**. Every mutation
asserts its independently named catalog fact before invoking the product checker.
An unchanged catalog passes the identical admin transaction with local session
authorization; a genuine lifecycle-login baseline is tested separately. Mutation
fixtures roll back and the genuine baseline passes again. Automatic generated-name
renaming and real fast-default rewrites remain accepted. Actual scalar/node/
deparse caps, FK/RI/opclass/ACL corruption and external escape grants are exercised.
The test-only Ecto seam captures clean actual Postgrex results and replays each
family's overrun, NULL, shape, result-kind/backend/message, driver-error and
cancellation controls; this seam never supplies product expectations. Original
deadline expiry is forced after each of twelve query boundaries, positive timeouts
decrease without reset and injected errors/cancellations are not retried. A
synthetic individually bounded result exceeding the aggregate 2 MiB budget denies.

The [receipt](../verification/hosted-browser-relation-catalog/receipt.json) seals
commands, versions, source/dependency/output hashes and exact selected attempts.
[coverage.json](../verification/hosted-browser-relation-catalog/coverage.json)
maps every original contract case to named methods and explicit gaps.
The projectless actual Mix formatter and selected `elixirc --warnings-as-errors`
pass. Early warning-bearing compilation, a formatting edit failure and seven
non-selected fixture attempts remain retained; their owned cleanup passed.

Independent review, complete function/type conjunction through the trusted
Store, checkout/role-map provenance, nested/foreign Store rejection, original
checkout-to-commit budget and rollback, real pool-pressure/cancellation and
separately timed decoder/final-return expiry probes remain pending. The existing
fake wire cancellation is not a real server-cancellation receipt. Serialized
operator DDL policy, lifecycle/provider/HTTP/console/Neon readiness, separate-repo
immutable FieldLog packages, customer acceptance and all GA gates remain pending.
No metadata, caller, migration, route, provisioning or production operation was
changed by this lane. No native/simulator/emulator/phone, UI/capture or broad
process-discovery work occurred. All owned PostgreSQL servers/containers,
formatter/compiler scratch and temporary paths were removed; other projects'
processes and data were preserved.
