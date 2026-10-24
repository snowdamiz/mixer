# Isolated hosted catalog inspector implementation

The [private contract](hosted-catalog-inspector-contract.md) now has an executable
Elixir/Ecto/Postgrex implementation in
[`verification/hosted-catalog-inspector/component/`](../verification/hosted-catalog-inspector/component/).
It is ready for independent review, not installed in `hosted/`. No authority
driver, domain writer, HTTP path, startup publication, live database, dependency
inventory or root tracker was changed by this lane.

`MixerHosted.CatalogInspector.verify(catalog_repo, runtime_repo)` holds separate
trusted runtime and catalog checkouts under one five-second monotonic budget.
It checks runtime identity/settings/backend before and after the catalog
transaction. The observer's counts, capability assertions and both exact
accepted catalog captures run in one read-only repeatable-read transaction.
Complete typed validation precedes the original selected normalization and strict
comparison. Unknown values return finite closed atoms; JSON keys remain strings.
The original baseline, raw SQL, schema, functions and broad-suite evidence remain
immutable inputs. No observation can rewrite the expected manifest.

Actual runtime testing exposed that the limited runtime sees 358 settings while
the selected catalog observer sees 379. Retained attempt 4 records all 21 omitted
names and rejects the incomplete observation. Root consequently selected a
separate direct observer and a separately versioned isolated profile. Its only
declared catalog delta adds observer CONNECT to the fixed database ACL. Original
manifest SHA-256 is
`78c0c8a56c6d358eda1e8a183176d5fe7b7e67e9427bdeb4aa1bb308dfaa8e6e`;
new profile SHA-256 is
`a63e1af41935f1a283618d2601e1b072762355059ca25b3782df6518da02d395`.
The exact diff, generator and profile selection are in the packet. The old
comparator rejects the additive grant, as required. Production provisioning is
not selected by this isolated profile.

The final source snapshot is **attempt 7**, source digest
`64d8adf4930d91c75025630c5526b62da3b59c02412fb785784958db1b59fde2`.
It compiles with warnings treated as errors and passes four model test groups:
1,257 unique raw inputs differentially derived from the original 126/1,083-shape,
portability, independent-extra and focused matrices; 19 authored malformed
transport/resource cases plus three valid boundaries; 250 unknown-name atom
controls; and 19 Python canonical-byte vectors plus one full normalized-array
vector. Original matrix outputs and explicit deduplication are retained. These
are model-input results, not malformed actual PostgreSQL catalogs.

All **17 actual PostgreSQL test groups** pass on a fresh socket-only PostgreSQL
17.11 cluster with 173 padding tables and separately connected runtime/observer
Repos. Counts remain 14 relations, 89 constraints, 26 indexes and 74 triggers,
with different actual OIDs/generated internal names. Cases cover profile/oracle
equality, ordinary trigger drift/restoration, legal positive-OID literal `*`,
nested/occupied pool refusal, unsafe runtime state, SQLSTATE `55P03` lock timeout,
monotonic expiry, backend termination, independent string/result caps, an observed
concurrent role-default snapshot schedule, eight ACL drift variants, thirteen
observer capability/membership/ownership variants, three runtime `42501` denials,
runtime post-check/dynamic Repo confusion, actual 4,096-role cardinality overflow,
near-deadline SQLSTATE `57014`, and hostile search_path/function shadows.

The qualified session query observes the real runtime state where the retained
unqualified original can be made to report selected-safe fields. Catalog SQL
under explicit observer `search_path=pg_catalog` is unchanged. Canonical sorting
matches Python's default ASCII escaping, including DEL, BMP/non-BMP, escaped
controls and lowercase Unicode hex. The client text envelope suppresses outputs
over 4 MiB before Jason; PostgreSQL still constructs those outputs first. Node,
container and string bounds follow parsing, while byte/depth bounds precede it.
No universal PostgreSQL allocation or concurrent-DDL guarantee is claimed.

The expiry receipt preserves the original backend's immediate aborted state and
its absence 10 ms later. Pinned DBConnection holder deletion quarantines a timed
out checkout before asynchronous Postgrex disconnect. Pool-owned retirement,
actual original-PID settlement and replacement verification are separate facts.
No synchronous cleanup-on-return claim follows from the 1,000 ms test observation
budget. The source excerpts, dependency file hashes, exact logs and every sample
are retained for independent review.

All seven attempts are preserved. Attempt 1 caught a test atom-count warmup
issue; attempts 2 and 3 caught the canonical serializer's uppercase control hex;
attempt 4 measured the real visibility/API mismatch; attempt 5 caught the
oversized fixture's PUBLIC function grant before its intended size boundary;
attempt 6 caught an immediate-cleanup assertion that was stronger than observed
asynchronous retirement. These failed outcomes remain failures. Attempt 7 passes
the corrected assertions with the explicit cleanup limitation above. Two command
preflight mistakes are recorded separately; no attempt was discarded.

The original 128 schema cases, 43 prior controls, five historical observations,
67 catalog corrections and 19 ordinary-runtime cases are **reused byte-bound
evidence**, not freshly executed suites. The read-only upstream checker verifies
those bindings. Historical observations are not converted to security passes.

The packet binds exact source/dependency/tool versions and executable hashes,
commands, output, the immutable source/dependency archive and cleanup. Each owned
cluster was stopped and its unique scratch directory removed, including failed
runs. No TCP listener, other project's process/data, simulator, emulator or
physical phone was touched. Physical phones remain disconnected and pending.

This is a new isolated observer-profile prerequisite. Independent review and root
selection remain pending, as do actual bootstrap/provisioning, combined
domain/Oban schema, provider/HTTP behavior, current-authority/domain writer,
production operations, signing/publication, customer and GA acceptance. Snapshot
execution does not provide atomic cross-connection authorization or protect
against privileged DDL during or after inspection.
