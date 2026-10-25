# Independent combined browser catalog V2 review

The frozen candidate is accepted as the **partial function/type prerequisite**
for continued development. No blocking source-admission finding was established.
This acceptance authorizes only `:function_surface_verified`; it does not establish
relation admission, Store ownership, browser readiness, deployment or GA.

The reviewed product bytes are `catalog.ex`
`6d568887deabc3d573462b7ecd038444bc07e985ee4a9e1f32e6fb4a3ef268af`
and `catalog_manifest_v2.ex`
`0c4e4c0186a57979182b90eb4b6e852b8b2b40d9e894bede0e95e382dfc7a8ea`.
The producer's [frozen closure](../verification/hosted-browser-catalog-v2/handoff.json)
and the [lifecycle contract](hosted-browser-lifecycle-runtime-contract.md) were
reviewed alongside the binding product plan. No product source or existing test
oracle was changed by this review. Revision labels changed between early and
final attempts because root delivered another slice; the final receipt records
`53672fc12bae5d1ebd0ed0d1890f3926942d8402`, the named source-tree digest
`702fd44ac61a5a96e8e77ef7d02e3c3683a8922b45240a46656e111ce222e9de`,
and zero source, dependency or execution-metadata drift during that run.

The three-argument entry point selects V1. The fourth argument accepts only the
exact integers 1 and 2 before consulting the Repo; no supplied expectation map,
module or callback is accepted. Both versions use private compiled maps and
count-plus-one bounds. V2 combines the pinned baseline and additive schema with
nineteen functions, four standalone composites, ten lifecycle EXECUTEs and
thirty-four fields. The build-time assertions pin four accepted sources, check
the added signature/result/names/settings/flags/fields and combined counts, and
do not import `File`, `Code` or `Module` at runtime in either reviewed module.

Source inspection confirms a single supplied monotonic deadline, fixed qualified
catalog statements and bound role/type values. All queries disable queuing and
logging, use the remaining timeout and recheck expiry after execution. Role and
membership/ownership projections retain their 4,096-row bound. Function metadata,
source bytes, settings and exact ACL entries include the grantor. Standalone
browser-prefixed types are discovered across namespaces, including enums/domains;
expected names remain included when their kind changes. Composite field order,
types, dropped/default/generated/identity flags, collation, dimensions and ACL
entries are compared exactly. A single fixed redacted exception covers errors.

Fresh independently authored tests used one owned synthetic PostgreSQL **16.15**
arm64 Docker container at a time. The accepted storage fixture was reused only
for installation/provisioning; neither producer test suite supplied the new
attack oracles. The bounded host runner reuses the accepted named surface
review's process/container plumbing. It snapshots only explicit ordinary source
files and loads the seven named general-purpose dependency beam directories.
Elixir/Mix **1.20.4**, OTP **29**, Python **3.14.8**, Docker Engine **29.8.2** and
the immutable image digest are recorded with exact commands and outputs.

| Fresh check | Result | Receipt |
| --- | --- | --- |
| Independent V2 attacks | 19 methods; zero failures, skips or exclusions | [V2 receipt](../verification/hosted-browser-catalog-v2-review/attempts/20261025T185721.472085Z-c6ac7db1/receipt.json) |
| Additional selected compile controls | 12 expected rejections | Same V2 receipt |
| Current original V1 independent review | 20 methods; zero failures, skips or exclusions | [V1 receipt](../verification/hosted-browser-catalog-surface-review/attempts/20261025T185407.586027Z-c874ff60/receipt.json) |
| Current original preparation SQL independent review | 38 methods; zero failures, skips or exclusions | [SQL receipt](../verification/hosted-browser-activation-preparation-sql-review/attempts/20261025T185740.222738Z-429b7c31/receipt.json) |

Counts belong to separate suites and are not summed. The original V1 runner
loaded the current selected V2 compile closure successfully. The V2 and SQL
receipts also pass selected `elixirc --warnings-as-errors` and actual projectless
`mix format --check-formatted`; no broad hosted compile/test discovery ran.

New runtime attacks cover duplicate accepted type names in another namespace,
temporary browser types, closed cross-namespace enums/domains, an exact helper
moved to another namespace, duplicated otherwise-valid ACL entries, grantor-only
changes to a nonprivileged role while effective privileges remain true, optional
helper metadata, oversized parameter/settings arrays, a SQL-standard parsed body
attached to the PL/pgSQL helper, and generated/default/identity/multidimension
field metadata. Both compiled versions emitted their exact six count-plus-one
limits on the real server. An actual Ecto SQL call trace observed `queue: false`,
`log: false` and bounded remaining timeouts on every catalog query. A successful
query deliberately crossing the original deadline denied further admission.
Current role changes and catalog permission loss denied with the fixed error.
Exact version/deployment selection was checked independently.

The twelve negative compile controls append drift to each of the four pinned
sources, alter the additive baseline version and runtime-execute assertion, and
decrease each of the six V2 query bounds. All failed compilation for the expected
reason. Only temporary copies were altered and every compiler directory was
removed. Producer PostgreSQL 17 and producer compile-control counts remain
separate historical evidence; this review did not rerun or relabel them.

Four failed review-harness attempts remain immutable. The first invalidated all
eighteen then-defined methods because the migration pool had only one connection.
The second invalidated them because the initial no-queue probe raced connection
startup. The third passed one method and failed seventeen after review code sent
transactional provisioning through different pooled connections. It was corrected
to one dedicated connection, as the accepted fixture requires. The fourth passed
seventeen methods and failed only the review's query-observer filter, which had
omitted the escape projection because it contains no browser prefix literal.
The final suite corrected that oracle and added the runtime query-options trace.
None of these attempts is passing product evidence. Their receipts, inputs and
output are retained under the [review attempts](../verification/hosted-browser-catalog-v2-review/attempts/).

Positive negative-scope controls still accepted a browser-prefixed table row type,
a permissive relation policy and a writer DELETE grant. This is expected for this
partial API and demonstrates why its result cannot attest relation correctness.
Full relation/index/constraint/trigger/policy/exact writer-grant admission,
trusted Store transaction/deadline provenance, current custody/access/OIDC
composition, runtime owner/pool/readiness, migration/operator deployment, Neon,
provider/HTTP/customer/FieldLog and GA qualification remain pending. Native/UI,
capture, simulator/emulator and final physical-phone checks remain paused; none
was attempted. No frozen inspector, authority-driver or rejected Worker V2 source
was read, imported or executed. No production data, credentials, keys or another
project's processes were discovered or altered.

All seven owned PostgreSQL containers from the five V2 attempts and two original
regression runs were stopped and removed. All owned selected/negative compiler
products and temporary compile scratch were removed, including failed attempts.
The review's [handoff](../verification/hosted-browser-catalog-v2-review/handoff.json)
enumerates exact new attempt paths and the SQL runner's changed mutable
`latest.json` pointer for root delivery. The two preexisting runners and historical
attempts were not edited by this lane. Root owns status/gate integration and any
commit/push; this review made no delivery or release claim.
