# Combined browser function/type catalog version 2

The internal `Catalog.check_function_surface!/4` now selects one of two fixed,
compiled function/type expectations. The existing three-argument function keeps
version 1. The fourth argument accepts only the exact integers `1` or `2`; a
future trusted lifecycle owner must select it. Request data, supplied maps,
callbacks and modules cannot supply expectations. Both versions return only
`:function_surface_verified`, with the same fixed redacted exception on failure.
There is no application caller, `admit!/0`, Store ownership claim or readiness
consumer in this slice. The [lifecycle runtime contract](hosted-browser-lifecycle-runtime-contract.md)
remains binding. Producer verification is complete; separate independent version
2 review and root acceptance remain pending.

`CatalogManifestV2` combines the unchanged eighteen-function, three-composite
`CatalogManifest` with the accepted preparation helper and access-evidence type:
nineteen functions, four standalone composites, ten lifecycle EXECUTEs and
thirty-four composite fields. It binds the exact source bytes of the accepted
baseline schema/manifest, additive schema and decoder at compilation. Its
positive assertions compare the addition's signature, result, parameter names,
settings, fields, flags and decoder SHA and require the complete combined counts.
The expected source is never learned from the installed database. Compiled import
inspection confirms that pin I/O remains at build time; the selected modules have
no runtime `File`, `Code` or `Module` import.

| Accepted input | SHA-256 |
| --- | --- |
| `storage_schema.ex` | `676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd` |
| unchanged `catalog_manifest.ex` | `3508c85922a1a716d39eb61ecb5daa699d6141b1aeb88a9565512c78465d1269` |
| `activation_preparation_schema.ex` | `d58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8` |
| `activation_preparation.ex` decoder | `e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5` |

The shared reader deliberately has separate fixed count-plus-one SQL limits for
each version. Compile assertions check these limits against the compiled data.

| Projection | Version 1 expected / limit | Version 2 expected / limit |
| --- | --- | --- |
| Functions | 18 / 19 | 19 / 20 |
| Function ACL entries | 27 / 28 | 29 / 30 |
| Standalone type rows | 3 / 4 | 4 / 5 |
| Composite fields, including dropped entries | 25 / 26 | 34 / 35 |
| Type ACL entries | 9 / 10 | 12 / 13 |
| Callable application SECURITY DEFINER functions | 18 / 19 | 19 / 20 |

The existing transaction/session/strict-role checks, 4,096-row role/ownership
bounds, original monotonic deadline, `queue: false`, `log: false`, and remaining
query timeout remain in force. Query text is fixed apart from the two compiled
numeric limits; expected role/type names remain bound parameters. No operation
retries or resets its deadline.

The pre-change PostgreSQL 17 proof demonstrated three real gaps: version 1
accepted an extra closed standalone browser-prefixed composite, the added type
alone without its helper, and grantor-only function/type ACL drift. The immutable
[three-method proof receipt](../verification/hosted-browser-catalog-v2/attempts/pre-fix-proof-20261025T184132.590573Z-83f2faa1/receipt.json)
binds the original product bytes. Those proof assertions document the old
behavior and are not current regression expectations.

The repaired type discovery now rejects extra browser-prefixed standalone types
across every namespace, including standalone composites, enums and domains.
Ordinary table row types are excluded from this partial function/type surface;
the expected names are still included if replaced by a wrong kind. Both versions
require the exact expected name set, public schema, composite/relation kind,
owner, ordered fields and ACL. Function and type expanded ACLs now also compare
the grantor: writer for EXECUTE, relation owner for USAGE. Same grantee/privilege
with a changed grantor fails. Relation admission remains a separate requirement.

The final [version 2 receipt](../verification/hosted-browser-catalog-v2/attempts/v2-20261025T184749.843998Z-b581bc4a/receipt.json)
passes **30 methods, zero failures/skips/exclusions**, on PostgreSQL 17.11/macOS
arm64. Its selected `elixirc --warnings-as-errors` and actual projectless
`mix format --check-formatted` pass. Ten additional expected-failing selected
compile controls prove rejection of baseline schema/manifest, additive schema and
decoder source-pin drift, combined-count drift, and addition signature, result,
parameter-name, setting and field drift. These are ten compile controls, not ten
additional ExUnit methods.

The methods include actual raw nineteen-function and ACL projections; exact
nine-field type projection; all nineteen body-byte mutations; source/name/
attribute/settings/owner/ACL/grantor drift; extra overload/type/field count-plus-one
controls; retained dropped fields; cross-namespace standalone types; mixed
baseline/type-only/inert/upgraded deployments; invalid version values before any
Repo call; transaction/session/role/deadline denial; an actual catalog permission
error; cumulative original-budget consumption; and direct table/column escape
denial. A positive negative-scope control still admits only the partial marker
when relation FORCE RLS or writer DELETE grants drift. That documents why this
marker cannot authorize readiness.

The unchanged original catalog suite also passes **26 methods** through the
[updated current PostgreSQL 17 runner](../verification/hosted-browser-catalog-admission/attempts/20261025T184819.258088Z-139af3d4/receipt.json).
The unchanged preparation SQL suite passes **39 methods** through its
[updated current PostgreSQL 17 runner](../verification/hosted-browser-activation-preparation-sql/attempts/20261025T184849.346512Z-9f403f3d/receipt.json).
An earlier fresh copied-tree 26-method regression also passed; it is not added
to these counts. Suites have separate receipts and counts are not summed.
The four current selected runners were coordinated before editing and now
explicitly include the new manifest's compile closure. The independent SQL
runner preserves its existing identity encoding helper. Existing test sources,
immutable attempts and historical receipts were not rewritten. The two current
PostgreSQL 16 runner adaptations have not been replayed by this producer lane;
separate independent review remains required.

The new bounded runner is
`python3 verification/hosted-browser-catalog-v2/run.py`; it snapshots only named
ordinary sources, the accepted reused storage fixture/migrations 3/4/6/7, lockfile,
contract and selected tests, then loads seven explicitly named general-purpose
dependency beam directories. No whole hosted build/discovery or frozen inspector,
authority-driver or rejected Worker V2 source was read, imported or executed.
Each receipt records tool commands/versions, revision, source/tree/dependency
SHA bindings, output hashes and cleanup. All owned PostgreSQL scratch instances
were stopped and removed, and all selected/negative compiler products were
removed, including failed attempts. Retained failures include an initial test
format mismatch, two compile-assertion mistakes corrected before database tests,
a raw projection search-path oracle mismatch, and two import-observer harness
mistakes. They are not passing product receipts.

No migration, operator provisioning, runtime owner, dedicated pool, Store,
relation/index/constraint/trigger/policy/grant admission or startup/readmission is
enabled. Current Config/access/OIDC comparison and custody, provider/HTTP/console
composition, Neon/operator deployment, immutable separate-repository FieldLog
packages, customer and GA qualification remain pending. No new dependency was
introduced. Computer use, capture, native simulator/emulator runtime and physical
phone checks remain paused and were not attempted. No other project's process
or data was discovered, started, stopped or altered by this lane.
