# Independent bounded RelationCatalog review

The frozen `RelationCatalog.check_relation_surface!/3` prerequisite has no
blocking findings within its original-nine PostgreSQL 16/17 scope. It returns
only `:relation_surface_verified` and raises the redacted private unavailable
exception on discrepancies. Root acceptance remains separate. This review does
not establish Store ownership, complete catalog admission, runtime readiness or
any GA gate.

The reviewed product hashes are `f71d79b9` for `relation_catalog.ex`,
`3f83abc9` for `relation_manifest.ex`, `f1a64cd8` for the PG16 manifest and
`d56f3935` for the PG17 manifest. The exact hashes and final producer seal
`3ecd63d6349f454a9029f0655c8a3b99af55df8c00cb24355698fcc2976e7a2d`
are bound in the [review receipt](../verification/hosted-browser-relation-catalog-review/receipt.json).
Changing execution metadata does not replace these semantic source bindings.

Source inspection covers all nine permanent local ordinary relations, 124
ordered columns, 80 CHECK expressions and dependency-column vectors, nine PKs,
four UNIQUE constraints, twelve FK groups, fourteen indexes, five user triggers,
48 internal RI triggers and 32 policies. Both incoming memberships and
customer-idempotency FKs are included; the 109-row constraint and 53-trigger
boundaries retain both endpoints without admitting either complete external
relation. FK key/index links and RI trigger function, constraint, opposite
endpoint and referenced-index links use installation-local numeric OIDs.
Types, equality operators, btree opclasses/families and collations resolve to
qualified builtin identities. Explicit partial-index and user-trigger names are
exact, while automatic constraint/index/RI names remain diagnostic.

The comparison retains full expression and function-source bytes, exact trigger
settings and writer ownership, raw ACL grantor/grantee/grant-option tuples,
NULL versus explicit column ACLs, effective table/column rights, default 1 and
the two reviewed bigint fast-default representations. PG17 selects owner
MAINTAIN rows explicitly and denies application MAINTAIN. External writer and
lifecycle table, column, view, foreign relation, sequence, schema, tenant and
membership escape authority is checked along with inheritance and rewrite rules.
Complete function/type and SECURITY DEFINER topology remains the separate
prerequisite's responsibility.

Each SQL family has its cap-plus-one sentinel. ACL arrays are checked at 64
entries and 16 KiB before expansion; expression nodes are checked at 32 KiB before
deparse and deparsed strings at 8 KiB. Function sources/settings and vectors have
separate finite bounds. Closed Postgrex SELECT decoding rejects diagnostic
messages, malformed scalars/rows, inconsistent counts and missing or changing
positive backend PIDs, and limits decoded wire to 2 MiB. Queries retain positive
remaining time under the original 5,000 ms ceiling with `queue: false`,
`log: false`, no retry and checks before/after SQL, during row reduction and
comparison, and before return. These checks do not prove trusted Repo ownership
or protect several READ COMMITTED observations against a coherent owner rewrite.

The [independent artifact audit](../verification/hosted-browser-relation-catalog-review/audit.py)
passes 491 assertions. It verifies the producer seal, both immutable selected
attempts and their observed mutation effects, original-source representation
lineage, CHECK-key literals, exact handwritten structure, trigger source bytes,
the explicit nine original migration names and all 29 compile-time semantic
bindings. The sixteen-file approved Oban migration closure is included. It also
verifies that every method named in the producer's 48-case mapping exists and
that all original requirements and limitations remain visible. These finite
source assertions overlap; they are not runtime test counts.

Fresh independent fixtures run **96 methods on PG16.15 and 96 on PG17.11**.
Each fixture installs the accepted explicit original nine migrations through the
reviewed standalone installer, then tests a genuine lifecycle login and an
unchanged admin checkout with local session authorization. A new direct census
confirms the complete expected boundary, and an independent SQL oracle resolves
all twelve FK groups' four exact numeric RI/function/index/endpoint links and
both external source identities. No attacked database supplies expected values.

Each major executes fourteen independently proved denied mutations: RI groups
cross-linked between the incoming FKs, missing child equality vectors, numeric
index/column collation disagreement, explicit empty immutable-column ACLs,
inconsistent missing-default metadata, identity metadata, owner ACL grant
options, PUBLIC read-only views, lifecycle sequence UPDATE, tenant column-only
SELECT, immediate integrity-trigger metadata, a same-body trigger function under
another identity, five policy roles and 33 trigger settings. Automatic CHECK and
RI-trigger renaming are two additional accepted equivalences. Every mutation
asserts its named effect independently, rolls back and passes the genuine login
baseline again. This fixture restoration is not trusted Store rollback evidence.

New clean-result adapter controls exercise all twelve families with missing
backend PID, noninteger row count, extra row scalars, thrown diagnostics and
driver errors, including redaction and no retry. Additional controls reject
unqualified locale/provider/version/replication environments, an out-of-range
OID, invalid UTF8, NULL key entries, duplicate policy roles, malformed effective
rights, oversized settings/source scalars and original-deadline expiry before
post-query decoding. They add to the audited producer's cap-plus-one, aggregate
wire overflow, scalar/node/ACL/deparse, cancellation and deadline controls. They
do not constitute real server cancellation or pool-pressure tests.

Actual projectless Mix formatting and selected `elixirc --warnings-as-errors`
pass. Independent copied-source compilation rejects changed delegated source,
a missing Oban v14 source and a changed PG17 manifest. A fresh VM then loads the
compiled manifests after all copied source/JSON/verification resources are
removed and confirms all 31 external-resource declarations. Production embeds
its oracle at compile time and imports no runtime verification fixture. Locked
Oban sources are still required during compilation; a beams-only build remains
unqualified.

Three early fixture failures are retained: an overbroad RI mutation, an
oidvector lower-bound mistake in the effect oracle and a mistaken assertion
about Ecto's added logging callback. The corrected suites pass. Initial review
formatting and external-resource keyword-count mistakes are also retained with
the successful replacements. Every owned PostgreSQL postmaster/container and
formatter/compiler scratch path is removed, including failed and superseded
attempts. Fresh exact-name/path absence checks are sealed; no broad process
discovery occurs and unrelated projects' resources are preserved.

The [48-case review mapping](../verification/hosted-browser-relation-catalog-review/coverage-review.json)
claims zero complete runtime cases. Trusted Store/Repo/checkout/role-map
provenance, complete function/type conjunction on the same checkout, nested or
foreign Store rejection, original checkout-through-commit budget and rollback,
separately timed row-decoder/final-return expiry, real pool pressure/cancellation,
serialized operator DDL, non-C/provider/version environments, operational index
health and Neon qualification remain pending. The actual fixtures are PG16
Linux Docker and PG17 native macOS, C/libc, UTF8, origin replication, default text
collation and NULL locale-version metadata. Lifecycle/provider/HTTP/console,
customer acceptance, separate-repository immutable FieldLog packages and all GA
gates remain pending. Native/UI/capture and final physical checks remain paused.
This review changes only its document and evidence directory; no product,
producer, migration, root metadata, credential, commit or push is changed.
