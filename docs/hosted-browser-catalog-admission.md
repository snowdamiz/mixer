# Browser function capability prerequisite

This is a named partial implementation of the accepted
[runtime contract](hosted-browser-lifecycle-runtime-contract.md). It cannot admit
the complete storage catalog and is not wired to an owner, pool, Store, HTTP
facade, Application or readiness response.

The exact internal interface is
`Catalog.check_function_surface!(repo, expected_roles, monotonic_deadline_ms)`.
It returns only `:function_surface_verified` or raises the fixed redacted
`Catalog.Unavailable`. It has no `admit!/0` API. The trusted future owner adapter
supplies its checked-out transaction Repo and the constructor's exact trusted
`%{lifecycle_login: login, writer: writer, relation_owner: owner,
ordinary_runtime_login: ordinary}` expectations. This is not a request-selected
Repo or generic SQL callback; `repo.in_transaction?()` proves transaction checkout,
not ownership by the future Store. There are no callers in this slice.

The supplied monotonic deadline must still be positive and at most 5,000 ms away.
Each fixed catalog query uses `queue: false`, `log: false` and a positive timeout
of `min(original_deadline - current_monotonic_time, 5000)`. A check after each
query and before success prevents a late result from passing. No query changes
GUCs, refreshes the deadline or starts a transaction. The exact current session
must be the expected lifecycle login with READ COMMITTED, search_path pg_catalog,
statement/idle timeouts 5s, lock timeout 500ms, JIT off and bytea output hex. The
future owner still must prove original budget provenance and transaction
ownership; this internal function cannot attest either by its argument shape.

Catalog results are bounded before wire transfer. Role, membership and distinct
ownership sets use a 4,096-row ceiling; SQL fetches at most 4,097 rows and rejects
the extra row, never truncating and accepting. Graph traversal checks the original
deadline per edge and round. Functions, fields, types and ACL queries similarly
use their exact expected size plus one. Function source is limited to 65,536
bytes in SQL; oversize returns an invalid NULL marker. Signature/result text is
bounded to 4,096/1,024 bytes, configuration to exactly five entries/512 bytes,
and parameter names to sixteen entries/1,024 bytes. Non-null unaccepted optional
catalog fields return fixed invalid markers. These bounds preserve exact expected
bytes; they never truncate an accepted value. The 4,096-role/edge ceiling is a
component limit, not a qualified Neon fleet/catalog capacity claim. Larger
installations fail closed and require a separately reviewed design.

The manifest freezes function source/configuration from the accepted ordinary
StorageSchema at compilation. Typed returns and all three ordered composite
field/type lists are independently specified. Argument names come from accepted
installation source at compilation because changing an argument name can change
what an unchanged PL/pgSQL body binds. No observed catalog state becomes an
expected answer. Function checks require all eighteen exact typed signatures,
results, PL/pgSQL, SECURITY DEFINER, writer owner, source bytes, exact settings,
ordinary volatile/non-strict/non-leakproof/unsafe/non-set semantics, no defaults,
variadics or support handler, and exact expanded EXECUTE ACLs without grant
options. Lifecycle can execute only the nine public helpers, writer all eighteen,
ordinary none. Missing, extra or overloaded browser functions fail.

The three composite types require the expected non-login relation owner, ordered
fields and types, default collations, no dropped/defaulted/generated fields, exact
USAGE ACLs for owner/writer/lifecycle and no PUBLIC/ordinary usage. Role names and
shape are closed. Named role flags, all incoming/outgoing lifecycle/writer
membership edges, ordinary recursive privilege/ownership paths, named owner's
recursive privilege paths, effective schema CREATE and database CREATE are
checked. Callable unreviewed application SECURITY DEFINER functions fail for both
lifecycle and writer. Direct lifecycle table/column privileges and direct ordinary
browser table/column privileges fail; these are escape denials, not positive
relation admission.

Complete admission remains mandatory and unimplemented: all nine accepted
relations' exact columns, constraints, FKs, indexes, enabled integrity/audit
triggers and functions, full writer effective table/column grant matrix, and
complete policy commands/roles/permissiveness/predicates. In particular the
accepted scoped/directory policies intentionally target PUBLIC and must retain
their exact baseline predicates. This slice does not compare or repair them.
Tests deliberately demonstrate that RLS/constraint drift still yields only the
named function-surface result. No consumer may treat that result as
`:storage_ready`, browser readiness, a full catalog admission or GA evidence.
The new preparation helper and composite require independently reviewed combined
manifest v2 later; this baseline accepts exactly eighteen functions/three types.

Run the selected host evidence with
`python3 verification/hosted-browser-catalog-admission/run.py`. It reads only the
three explicitly named ordinary modules, accepted migrations 3/4/6/7, the
existing storage fixture's provisioning helpers and dependency beams excluding
the application's beams. It never runs Mix discovery or a broad hosted harness.
One owned loopback PostgreSQL instance is stopped and its scratch removed even
after failure; immutable per-attempt receipts retain commands, versions, revision,
source/dependency hashes, output and cleanup. No simulator, emulator, capture,
UI, phone or production process is started or modified. Native checks remain
paused. Production pool/Store/readiness, Neon/operator/TLS/custody, immutable
FieldLog dogfood, customer and GA qualification remain pending.
