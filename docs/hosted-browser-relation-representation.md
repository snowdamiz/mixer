# Browser relation representations on PostgreSQL 16 and 17

The corrected [source contract](hosted-browser-relation-admission-contract.md)
now has bounded actual representation evidence on PostgreSQL **16.15** and
**17.11**. Both clean fixtures match its complete counts and semantics. This
packet supplies a reviewed source oracle plus per-major clean representations
for a future RelationCatalog implementation. It implements no product admission,
Store ownership, startup, readiness, route or release authority.

The final [receipt](../verification/hosted-browser-relation-representation/receipt.json)
indexes the immutable attempts and exact hashes. Each fixture installed all nine
ordinary migrations, ending at `20261025000007`, using Ecto's actual migrator
and the pinned ordinary StorageSchema and CustomerArtifacts.Schema delegates.
The separate uncommitted activation-preparation helper is outside this v1
installation. No Mixer application or broad hosted harness was loaded.
The existing approved StorageFixture helper was inspected, but its four-migration
allowlist is insufficient for this qualification, so it was not used to install.
Only the eight explicitly allowlisted locked dependency beam directories were
loaded; the ordinary Oban version-14 migration chain is pinned too.

The source revision was `0a6f110d8857b3732ce40b56aad33b006a187138`; exact
working-tree inputs, not that commit alone, bind the result. The shared source
manifest tree is
`d22a9fb6f442207f0e78c2ce83c1c0386d26ba3966817fb6e50eb655b9987cf5`.
Each attempt retains input copies, the source/beam manifests, tool/server
versions, command arguments, SQL stdin, stdout, stderr and cleanup evidence.
Only this document and `verification/hosted-browser-relation-representation/`
are owned. No product source, migration, metadata or other lane was edited;
no commit or push occurred.

## Expected representations and derivation

The independent source contract and its corrected review supply the source
matrix. Before taking each baseline, the fixture independently constructs
TEMP tables from that matrix's ordered names/types, compiles all **80 original
CHECKs**, **32 policy expressions**, **three defaults**, and the partial-index
predicate with that server, and compares the actual installed forms with these
source-compiled forms. The TEMP definitions never copy an observed target's
CHECK/default/policy expression. Policy subqueries keep their explicit ordinary
public-relation dependencies, while their local table names match the source.
The clean source install is therefore checked against approved DDL semantics
before its complete representation is frozen.

Each attempt's `frozen-expectation.json` is frozen once, **before** the first
mutation. Mutated catalog output never updates it. Generated constraint names,
generated index names and RI trigger names are diagnostic only; canonical
comparison removes them and resolves admitted index links by relation, ordered
keys and predicate. The explicit partial-index and five user-trigger names
remain exact. Installation-local numeric OIDs are not cross-installation
expectations. Product code must independently derive its source expectations and
resolve role/OID links in its checked-out transaction; fixture role names and
these fixture SQL collectors are not a production admission implementation.

| Exact surface | PostgreSQL 16.15 | PostgreSQL 17.11 |
| --- | ---: | ---: |
| Relations / ordered columns | 9 / 124 | 9 / 124 |
| CHECK / PK / UNIQUE | 80 / 9 / 4 | 80 / 9 / 4 |
| Outgoing / incoming FK | 10 / 2 | 10 / 2 |
| Boundary constraints, including four user constraint-trigger rows | 109 | 109 |
| Indexes | 14 | 14 |
| FK groups / internal RI triggers / all triggers | 12 / 48 / 53 | 12 / 48 / 53 |
| Policies: ordinary PUBLIC / writer | 10 / 22 | 10 / 22 |
| Expanded raw ACL rows | 123 | 132 |
| Effective table / column privilege rows | 27 / 372 | 27 / 372 |
| Source/structural semantic checks | 82 | 82 |
| Actual mutation controls detected | 23 | 24 |

All family collectors use the source contract's sentinel caps; clean output is
296,068 bytes on PG16 and 298,350 bytes on PG17, below 2 MiB. No application
rows are selected. These are fixture collectors and comparators, without the
future runtime decoder's transaction provenance, redacted failures, original
monotonic deadline and per-query/result admission guarantees.

## Observed forms

All three defaults deparse exactly as `1`. On a fresh install,
`profiles.state_revision` and `bindings.revision` have
`atthasmissing=true, attmissingval='{1}'`, with exact `pg_catalog.int8` type.
`oidc_attempts.ciphertext_version` has its ordinary int4 default but no missing
value. All other columns have neither default nor missing value. A real table
rewrite of both ALTER-added columns clears their missing metadata on both
majors; the source-approved absent form remains equivalent. A catalog mutation
substituting a genuine bigint `{2}` missing value from an owned dummy table is
detected. No arbitrary missing value is normalized away.

All 80 CHECK rows have `connoinherit=false`; the 9 PK, 4 UNIQUE, 12 FK and 4
user constraint-trigger rows have `connoinherit=true`. This matches the
corrected kind-specific contract. Ordinary constraints are local, validated
and nondeferrable; only the four source user constraint triggers are deferred.
The two incoming FK groups include both memberships and customer idempotency,
without claiming admission of those complete external relations.

Every FK's three equality-operator vectors resolve to the builtin operand-type
identities. All 48 RI triggers have the four expected builtin functions, exact
child INSERT/UPDATE or parent DELETE/UPDATE event masks, opposite endpoint and
referenced admitted key-index link. Their rendered regprocedure names quote
the mixed-case builtin names, for example `"RI_FKey_check_ins"()`; their
namespace is separately `pg_catalog`. RI-generated names contain local OIDs
and carry no expected meaning. The five user triggers match their source event,
function, deferral and constraint-link shape.

All indexes use builtin btree opclasses with the source key types/collations.
`int4_ops` and `int8_ops` use the shared **pg_catalog.integer_ops** operator
family; `text_ops` and `bytea_ops` use their respective same-named families.
Keys are ASC NULLS LAST, valid/ready/live/immediate, with no INCLUDE,
NULLS-NOT-DISTINCT, expression, exclusion or inheritance additions. Fresh
`indcheckxmin` is false; other operational health transitions remain unqualified.

Both fixtures explicitly use libc provider `c`, C collation/ctype and UTF8,
with origin replication role. Text columns/index keys resolve to
`pg_catalog.default`; other types have zero/no collation. Stored and actual
libc collation versions are NULL in these C environments. PostgreSQL 17 locale
identity is read from `pg_database.datcollate/datctype`, not a nonexistent
`lc_collate` GUC. This does not qualify another locale/provider/version or Neon.

Expanded owner ACLs match each major's builtin table-owner default. PG17 adds
exactly nine owner MAINTAIN rows, explaining 132 versus 123 raw rows; application
MAINTAIN is false. All application table and effective column rights, explicit
writer UPDATE columns, grantors, grant options, PUBLIC and third-party-role
absence match the source matrix. Null column ACLs are distinguished from
effective access inherited from table SELECT/INSERT. After removing this
per-major MAINTAIN difference and its raw owner-ACL spelling, the two frozen
representation families are identical.

## Controls, retained failures and remaining scope

Both majors detect extra CHECK/column/index/incoming-FK/policy/browser-prefixed
objects; missing incoming FK/partial index; weakened CHECK/policy/default;
NO-INHERIT additions; disabled FORCE RLS; disabled user trigger; independently
disabled parent-side and child-side RI triggers; corrupt fast defaults; and
extra table/immutable-column/PUBLIC/third-party/grant-option privileges. PG17
also detects a real MAINTAIN grant. Every mutation runs inside an owned fixture
transaction and rolls back. A final fresh snapshot equals the frozen baseline.
Automatic PK/backing-index renaming is an explicit equivalence control, as is
the real rewritten fast-default form.

Earlier attempts are retained with failed receipts and their exact source
copies: the initial PG17 locale-GUC query, qualification-tool index-name handling,
a Python Counter misuse for RI group expectations, and an invalid direct
bigint-array assignment to pg_attribute.anyarray. These were fixture/tooling
failures, not accepted passes or contract changes. Their owned servers and
scratch were removed. The initial successful narrower runs are historical;
only the final two indexed attempts support the current counts.

Both final fixtures ran serially with distinct owned names. The native PG17
postmaster stopped, its pid file disappeared and its scratch directory was
removed; the exact PG16 container was stopped and inspection proves it absent.
Projectless formatter scratch was removed too. No native simulator/emulator,
physical-device, capture, computer-use/UI automation or process-discovery work
occurred. Other projects' processes and data were preserved.

No discrepancy in the corrected source contract was found. Independent review
of this packet, RelationCatalog implementation and its bounded decoder/query
adversity suite, trusted Store/Repo/original-budget composition, serialized
operator drift policy, lifecycle readiness, provider/HTTP/console/Neon, immutable
FieldLog packages, customer and GA gates remain pending. The paused native and
physical matrix remains pending as instructed.

Replay only the bounded host fixture with:

```sh
python3 verification/hosted-browser-relation-representation/qualify.py --major 17
python3 verification/hosted-browser-relation-representation/qualify.py --major 16
```
