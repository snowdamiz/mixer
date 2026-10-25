# Browser catalog function-surface review

Independent review accepts only the named prerequisite
`Catalog.check_function_surface!(repo, expected_roles, monotonic_deadline_ms)`
and `CatalogManifest`. The result is `:function_surface_verified`, never full
catalog admission, storage readiness or browser authorization. There is no
`Catalog.admit!/0`, application caller, pool, Store or readiness wiring in this
slice. The broader [runtime contract](hosted-browser-lifecycle-runtime-contract.md)
remains binding.

The final independent run passes **20 methods, zero failures/skips/exclusions**
on PostgreSQL 16.15 (Debian, Linux arm64), using pinned image
`postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97`.
The immutable [receipt](../verification/hosted-browser-catalog-surface-review/attempts/20261025T170142.998593Z-ec7ce7c3/receipt.json)
binds commands, versions, Git revision, input snapshot/tree digest, dependency
beams, outputs, unchanged source/dependency checks and owned-resource cleanup.
Producer's separate 26-method PostgreSQL 17.11 evidence is a distinct suite;
the counts are not summed.

Review used the existing accepted `storage_fixture.exs` installation and
provisioning helpers and migrations 3/4/6/7. That fixture is **reused**, not an
independent implementation. All test oracles and adversity controls in
[surface_review.exs](../verification/hosted-browser-catalog-surface-review/surface_review.exs)
are independently authored. The runner copies only the three ordinary source
modules, four accepted migrations, fixture helper, lockfile and review source,
then loads explicitly named locked dependency beams. It does not compile or
start the hosted application, run Mix discovery, or read/import/execute the
frozen inspector/authority driver or rejected WorkerV2 lane.

The positive raw PostgreSQL projections compare all eighteen functions against
authored `StorageSchema` SQL: source bytes, argument and result types, parameter
names, language, exact five settings, writer owner, SECURITY DEFINER, ordinary
volatile/non-strict/non-leakproof/unsafe/non-set attributes, no variadic/default/
mode/support/binary/SQL-body alternatives, and exact expanded EXECUTE ACLs. The
three composites independently match the authored SQL field order/types,
relation owner and expanded USAGE ACLs. Expected answers come from accepted
static source, never from the checked database.

Independent negative controls cover:

- Byte drift in every one of the eighteen bodies; unchanged body with altered
  argument names; optional catalog attribute drift; oversized source,
  configuration and argument-name arrays; an extra closed-ACL browser helper.
- All three composite owner/ACL changes; same-typed field reordering, changed
  collation, added fields and retained dropped fields. A few impossible-through-
  ordinary-DDL attributes use explicit test-only catalog corruption in the
  disposable fixture; restoration is checked before later controls.
- Multi-hop named-owner access to predefined/privileged roles; ordinary
  NOINHERIT ownership routes through two roles to functions and databases;
  extra SECURITY DEFINER execution via PUBLIC or writer in another schema;
  lifecycle view/foreign-table/column grants.
- More than 4,096 membership edges with fewer than 4,096 roles, proving the
  graph is rejected rather than accepted as a truncated prefix.
- One original 125-ms deadline consumed across successful queries by a
  synchronous telemetry observer. Telemetry query messages are checked for no
  repeated SELECT; a late intermediate result fails before success. This does not attest
  future checkout/commit or end-to-end provider deadlines.
- Foreign/outside transaction context, changed transaction-local settings and
  restoration after rollback; fixed redacted exception on an actual catalog
  permission error. Source review confirms every Catalog query uses
  `queue: false`, `log: false` and the remaining original deadline, with no
  application retry path or deadline reset.

The source freezes agreed with the producer and rechecked after the final run
are SHA-256:

| Input | SHA-256 |
| --- | --- |
| `catalog.ex` | `9ddb2adbf8820ca8ab13823eecb05f26ee0bc671f49da6728e63e36eb3cdd642` |
| `catalog_manifest.ex` | `4f336e460292e57a108fc1a5d9d7830cfedd9899ad72ea3ab0c3dc5c186dd918` |
| accepted `storage_schema.ex` | `676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd` |

No product correction was required by this review. Two retained review-only
attempt failures were corrected before final acceptance: a Postgrex regprocedure
parameter needed `text::regprocedure` rather than OID encoding; the new raw
composite projection initially sorted fields alphabetically instead of by the
declared ordinal. Each failed attempt stopped and removed its owned container.
An intermediate 18-method suite passed before the two direct raw projection
methods were added. The final 20-method suite and final handoff bind the final
review test bytes.

Full relation columns, RLS enablement, constraints, indexes, enabled triggers,
policy sets/predicates and exact writer table/column grants remain unimplemented
admission requirements. The suite deliberately shows that writer DELETE or a
widened policy can still produce only the partial function-surface result.
Trusted Store ownership, original deadline provenance, dedicated pool, startup/
re-admission, preparation manifest v2, current verifier/provider/HTTP composition,
Neon/operator/TLS/custody qualification and customer/GA acceptance remain pending.
No readiness consumer may use this result to enable auth or `storage_ready`.

Run with `python3 verification/hosted-browser-catalog-surface-review/run.py`.
One owned loopback PostgreSQL container was stopped and removed after each run;
other projects' processes/data were preserved. No native simulator/emulator,
physical phone, browser/UI, screen capture, provider or production action ran.
Those native/UI/physical checks remain paused or pending under AGENTS.md.
