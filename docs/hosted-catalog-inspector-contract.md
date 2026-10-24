# Isolated hosted catalog inspector contract

This lane implements a private Elixir/Ecto/Postgrex component under
`verification/hosted-catalog-inspector/component/`. It is not installed in the
hosted application. The selected authority-only comparator is the
[accepted catalog prerequisite](hosted-catalog-acceptance.md), including the
positive-OID literal `*` and raw trigger-name uniqueness corrections. The
original selected manifest bytes retain SHA-256
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`.
Observation never enrolls a new expected catalog.

Root selected a separate **isolated observer profile**, because the original
fixture database ACL permits only its owner and runtime login to connect. The
new trusted profile has SHA-256
`a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395`.
Its sole declarative structural delta adds
`catalog_inspector_observer=c/andreyyurlov` to that exact database ACL. The
generator consumes the pinned original manifest and declared delta, never
observed database state. The original comparator correctly rejects this added
CONNECT grant. The original baseline has not been accepted under a different
meaning; the new profile requires independent review and root acceptance.

## Private API and ownership

The coordinated API is `MixerHosted.CatalogInspector.verify(catalog_repo,
runtime_repo)`. Both arguments are trusted configured Ecto Postgres Repo modules,
not HTTP input, credentials, callbacks, SQL, a schema name or an expected
manifest. Existing transactions/checkouts, the same dynamic Repo or backend,
unsupported adapters and dynamic Repo substitution reject closed. One absolute
five-second monotonic deadline covers both pool acquisitions and all operational
queries; every acquisition and query uses `queue: false` and the remaining
budget. No query receives a renewed operational deadline.

Success is `{:ok, %{manifest_sha256: digest, snapshot_scope: :point_in_time}}`.
This metadata is diagnostic. It grants no request authority and cannot be used as
an admission token. Failures are finite closed atoms
`:catalog_unavailable`, `:catalog_mismatch` or `:malformed_catalog`; raw catalog
definitions, input strings and SQL errors are not returned to callers.

The runtime Repo is a caller-owned dedicated fresh runtime connection, with the
actual selected session/effective identity. Before the observer transaction and
after it completes, the same held runtime checkout must expose the exact nine
selected fresh-session fields and the original backend. Observed settings alone
cannot establish that a pooled connection has never been used. Bootstrap owns
freshness, credentials, lifecycle, startup publication and migration coordination.

The catalog Repo supplies a separately provisioned trusted observer. It needs
`pg_read_all_settings` visibility: actual limited-runtime observations omit 21
`pg_settings` rows and cannot equal the selected 379-row settings domain. This
was measured in retained attempt 4; it is not repaired by granting the runtime
extra privileges or omitting hidden rows. The observer must be a fixed dedicated
non-superuser, non-BYPASSRLS, non-createdb/createrole/replication role, with only
the selected settings-reader membership and no ownership/elevation path. All
observer catalog preflights, identity/capability assertions and legacy/enforcement
captures share one `REPEATABLE READ READ ONLY` transaction. The runtime retains
its original ordinary `read committed`/`off` session comparison domain; the
observer transaction's different execution state is checked separately.

This isolates an authority-only prerequisite. The selected fixture revokes PUBLIC
database CONNECT and names an exact runtime grant in the frozen database ACL;
provisioning a direct-login observer changes that selected manifest. The explicit
new isolated profile above permits its CONNECT grant without grant option,
CREATE, TEMP or PUBLIC access. Fixture bootstrap creates a LOGIN INHERIT observer
with only `pg_read_all_settings` membership: ADMIN false, INHERIT true, SET false.
Separate read-only assertions reject elevated role flags, extra/transitive
membership, different membership options, object ownership, schema CREATE,
protected-schema USAGE and protected table/column/function privileges. No
production observer credentials/provisioning, startup wiring, domain/Oban
composition or privileged repair is selected by this implementation.

## Comparison and transport

The accepted legacy/enforcement SQL resources are copied byte for byte. The
original runtime-session SQL is retained, and its separately bound derivative
qualifies only the three builtin function names with `pg_catalog`. Pre-search-path
backend queries likewise qualify `pg_backend_pid`; envelope casts explicitly use
`pg_catalog.text`. A hostile search_path fixture reproduces spoofed fields with
the old unqualified query and verifies that the new query observes true state.
The nine selected fields and their domain are unchanged; these different session
SQL bytes are not described as byte-identical to the original. Each SELECT is enclosed
in a separately bound materialized CTE/text envelope: return its JSON as text
only when the serialized result is at most 4 MiB; otherwise return NULL and fail
unavailable. Postgrex thus does not automatically decode an unbounded JSONB value
for this component. The envelope preserves the accepted query's result semantics
and is tested against the independent Python oracle on actual PostgreSQL output.
PostgreSQL still constructs the JSON and text before this size check. The
envelope does not prove bounded PostgreSQL allocation.

All complete raw fields are validated before normalization: legacy nested
objects, all nine enforcement groups and all nine runtime session fields; exact
keys, nullability, primitive types, unsigned 32-bit OIDs, positive required
associations, optional associations, enums, trigger bits/arguments, identifier
bytes, ACLs and settings. Zero startup-association OIDs require `*`; positive
OIDs can resolve to a literal `*` and retain the prior general text domain.
Every raw trigger `(relation_oid, name)` pair is unique before generated internal
names disappear. OID values remain portable; semantic multiplicity is preserved.

The component then applies the selected normalization exactly: remove OID-only
transport fields; remove internal trigger name/definition only after validation;
sort the same enforcement groups, ACL entries and legacy memberships using
Python-compatible canonical JSON bytes. DEL, non-ASCII BMP/non-BMP and control
escapes match Python `ensure_ascii=True`, including lowercase hex and surrogate
pairs. No other list is silently reordered or deduplicated. Compare strict typed
structure against the fixed selected manifest. Unknown shape and retained drift
fail closed.

## Finite resource envelope

The complete JSON text has a 4,194,304-byte ceiling per SELECT. A byte scan limits
nesting to 32 before Jason parsing. After parsing, ordered objects expose
duplicate keys (including escaped duplicates); keys stay strings and no input is
converted to an atom. Post-parse limits are 100,000 value nodes, 4,096 array items,
64 object keys and 1,048,576 bytes per string. The same envelope guards direct
typed model inputs. These node/container/string limits apply after parser
allocation; only total bytes and nesting are bounded before parsing. Opaque
oversize values produce finite diagnostics without being echoed.

Within the same observer snapshot, bounded `LIMIT ceiling+1` preflights check
global catalog cardinalities. Roles, memberships, namespaces, default ACLs,
databases, settings and parameter ACLs have ceilings of 4,096; relations,
functions, constraints and triggers 32,768; attributes 262,144. Each data query
has a decreasing server statement timeout and matching driver timeout. The
observer transaction has a 250 ms lock timeout and a five-second idle timeout.
These are resource rejection policies, not changes to the selected primitive
domains or proofs of universal server work/allocation bounds.

## Failure, cleanup and acceptance boundary

Timeout, pool occupancy, disconnect, bad observer access, session/backend drift,
unknown shape, oversize transport and selected mismatch cannot return success.
Ecto owns commit/rollback and connection retirement. Operational deadline expiry
does not authorize a success retry within that invocation. Cleanup is observed
separately on the original backend: either no open transaction/local settings
remain, or the failed driver connection has been retired. Any replacement must
undergo a new full inspection. No cleanup claim is inferred from a replacement
connection's state alone. The pinned DBConnection timeout path deletes the holder
before dispatching driver disconnect; missing/error/aborted holders cannot be
handed back as usable connections. Postgrex cancellation/socket closure then
retires the backend asynchronously. A near-deadline run observed the original
backend still `idle in transaction (aborted)` immediately after failure and
absent 10 ms later. This is not synchronous server cleanup on return. A separate
1,000 ms test observation budget records settlement and every original-PID sample;
it is neither an enforced component cleanup deadline nor a universal bound.
Bootstrap must keep protected traffic unpublished on failure; a deleted holder
cannot be relabeled verified, and any replacement needs full inspection. Production
pool/supervisor lifecycle ownership and independent provider review remain pending.

Executable differential models and targeted actual PostgreSQL cases must record
same-snapshot capture, runtime visibility rejection, observer baseline acceptance,
portable OIDs/internal names, ordinary drift/restoration, literal `*`, nested and
occupied pool rejection, unsafe sessions/observer authority, exact SQLSTATE for
lock timeout, absolute deadline expiry, backend termination, result/string/count
bounds, original backend transaction/settings cleanup and later fresh inspection.
Preserve failed attempts and exact source/dependency/tool/command/output bindings.
Original broad schema suites are reused byte-bound evidence, not new executions.

`REPEATABLE READ` and held checkouts are local execution properties. They do not
establish atomic cross-connection admission, exclusion of concurrent privileged
DDL, publication fencing or protection after return. PostgreSQL catalog helper
and configuration behavior must not be represented as a universal DDL snapshot
proof. Combined hosted schemas, actual bootstrap/provisioning, HTTP, authority
driver/domain writer, customer/provider operations, production, signing,
publication, native/physical phones and GA acceptance remain pending.
