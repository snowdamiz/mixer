# Protected customer artifact PostgreSQL storage

`mixer-product-plan.md` remains binding in full. This is ordinary local domain
storage inside the transaction owned by `Authorization`, with a restricted SQL
runtime role. It does not qualify a deployed API, Neon, Cloudflare, provider login,
R2/CDN delivery, publication, workers, phones, customer operations or FieldLog.

`PostgresStorage.upload/4`, `read/3` and `audit/4` accept a live transaction Context
and a closed trusted server configuration `%{repo: module, host: ArtifactV3Policy
host map, roots: bounded public-root list}`. No method opens, nests, retains or
commits a transaction. Context owner/process/Repo/connection/action/target checks
precede SQL. Upload command is exactly `%{key: text, reason: text, source_ip: text
or nil}`. The request ID always comes from the server-generated snapshot.

Upload locks `mixer_customer_artifact_heads` after all six authorization locks,
then checks fresh policy/time and re-admits every Checked field against current
host and roots. Every new key writes one artifact or preserves an identical
existing artifact, one v2 event, one principal-bound success, and one sequential
head transition. Deferred constraints run inside the protected effect before
returning to the transaction owner. Errors, including rescued topology failures,
latch the Context. Outer callback failure still rolls back successful storage
writes. No external effect runs under these locks.

The result is exactly
`{:ok, %{status: 201 | 200, manifest_sha256: digest, payload_sha256: digest,
event_sequence: positive_integer}}`. A current-authorized retry of the same key,
principal, target and exact request hash returns its original status/sequence and
actor without a new event. Refreshed credentials may retry for the same principal.
A conflicting principal or request receives `:idempotency_conflict` without a
cached result. The fixed key-existence helper returns only a boolean. A new key
with the same canonical manifest CBOR, decoded signature and raw payload returns
200 and adds an `unchanged` event. It preserves the first exact envelope/signed
bytes and creating event. Changed immutable content returns `:immutable_conflict`.

Private read requires the exact resolved environment Context. It re-admits the
stored envelope at fresh time, compares all retained signed bytes, signature,
payload, CBOR, digests and normalized target columns, and re-reads the same row
before returning exact original bytes. Its result is exactly
`{:ok, %{envelope_bytes: binary, manifest_sha256: digest, payload_sha256: digest}}`.
Audit requires a project-only `audit.read` Context. Pages have 1–100 records,
start after a nonnegative sequence, and validate every closed v2 projection,
canonical CBOR/hash and predecessor edge. The result is exactly
`{:ok, %{events: [display], next_after_sequence: integer}}`; an empty page preserves
the requested cursor. Missing predecessors or corrupt rows fail closed.

Migration `20261025000005` adds four FORCE RLS tables. Composite ancestry and
cross-table FKs, immutable triggers and deferred integrity triggers reject partial
writes, changed retained fields, changed projections/actor/policy evidence,
missing dedup/events, sequence gaps, broken predecessor/state edges and head-only
changes. SQL independently reconstructs canonical CBOR under depth 16, 4096 items,
256 entries/container and 65536 output bytes, with unsigned 64-bit integer
encoding. It validates exact nested signed JSON bytes, duplicate-free bounded
signed JSON, signature/payload base64, retained hashes, and current identity and
selected authorization snapshots. Standard PostgreSQL SHA-256 implements the
same versioned event, state, request and external-reference domains as Elixir.
SQL does not replace current-root Ed25519 admission in the protected API.

The metadata function is exactly
`public.mixer_customer_artifact_metadata(digest text)`, returning only text
organization/project/application/environment/platform/runtime/manifest columns and
`signed_manifest_bytes bytea`. A fixed SECURITY DEFINER function with
`search_path=pg_catalog` checks the metadata phase, project-only GUCs, exact read
scope, verified token bounds, current active linkage, credential/family/member
windows and read-role project visibility. A distinct relation-owner-only policy
allows that fixed helper to read its narrow projection under FORCE RLS. The
runtime cannot directly SELECT payload or envelope during metadata resolution.
Full target active ancestry and action authorization precede private-byte access.

Provisioning creates sequence-zero heads with the v2 tenant genesis; runtime
cannot create/delete them. Runtime has SELECT/INSERT on artifacts/events/dedup,
SELECT and UPDATE only of `sequence,event_sha256,state_sha256` on heads, existing
authz SELECT, six fixed lock-helper EXECUTEs, and EXECUTE only on the new allowed,
metadata and key-existence functions. Other new functions have no runtime or
PUBLIC EXECUTE. Owners must be non-login, non-superuser, non-BYPASSRLS and
unreachable by runtime membership, including indirect NOINHERIT paths.

`PostgresStorage.check_topology!/1` checks exact source bodies/signatures/results,
security/search paths, function owners, table owners/RLS, grants, column grants,
constraints, policies and immutable/deferred trigger definitions. The fixed
catalog SHA-256 is
`ff576c90a10e0bc098f3c7b593640f508aa676a166b8e2123257501f50eb375e`.
Unexpected overloads, writable views, executable unreviewed SECURITY DEFINER or
VOLATILE user functions, schema CREATE, PUBLIC grants and elevated roles reject.
Runtime and session users must match. This is trusted application composition,
not a sandbox against malicious BEAM code or arbitrary identity-GUC SQL by an
application credential holder. A privileged owner can coherently rewrite history;
independent audit checkpoints and retention/privacy remain separate work.

The selected-source collector is
`verification/hosted-customer-artifact-storage/run.py`. It copies named ordinary
source/fixture inputs, compiles those copies with pinned dependency BEAMs, records
command arguments, versions, exact inputs/dependencies and tree digest, starts a
disposable loopback PostgreSQL cluster, runs the real restricted-role ExUnit
suite, then stops the cluster and removes owned scratch. Failed runs remain
failure evidence. No full Mix application/shared harness or frozen catalog,
authority-driver or rejected outbound Worker sources are read or executed.

The development tests cover actual uploads/private reads/audit, exact retained
bytes, retry/conflict principals, root/token expiry after domain-lock waiting,
revocation ordering, concurrent same-key/new-key no-op operations, callback
rollback, contextual metadata projection, independent SQL/Elixir CBOR boundaries,
restricted SQL privileges, catalog tampering, twenty-one adversarial partial/corrupt
runtime writes and a valid direct-SQL control, a creating-event piggyback rejection, and the
maximum admitted 4 MiB payload under unchanged production bounds. Physical phones remain deferred.
Root coordinates independent review, final combined fixture/standard CI and
tracker updates; this producer packet does not promote any GA gate.
