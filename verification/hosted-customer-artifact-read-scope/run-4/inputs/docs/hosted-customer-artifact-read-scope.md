# Staged private artifact read authorization

`Authorization.with_artifact_read_transaction(identity, project, manifest_sha256,
callback, repo \\ MixerHosted.Repo)` owns a fresh five-second local transaction.
Its callback has arity two and receives `(context, metadata)`. The project is a
validated project-only `Scope`; no application/environment guess is accepted.
The digest is exactly 64 lowercase hexadecimal bytes. Verified human identity,
token window and `mixer.artifact.read` scope validation precede database work.
The optional Repo is trusted server configuration, never request data. There is
no caller clock or production route in this seam. The complete product plan
remains binding; this is a bounded development slice.

The new pure `Policy.metadata_request/3` and `metadata_evaluate/4` use the actual
`artifact.read` action, read roles and OAuth scope. They do not alias `audit.read`
permission, and do not weaken the existing artifact `request/4` requirement for
a complete environment. A metadata evaluation is data, never a transaction
Context. Missing read scope is rejected before lookup even if the supplied
project would be hidden. With that prerequisite satisfied, missing/nonvisible
projects return `not_found`; visible projects whose current role cannot read
return `permission_denied`.

The transaction uses `queue: false`, READ COMMITTED, the existing statement/idle
and 500 ms lock bounds, and all six canonical authorization locks. After the
last lock it loads current project evidence and freshly evaluates metadata read
permission. Only then does the coordinated `PostgresStorage.check_topology!/1`
verify the new schema, policies, triggers, privileges, owners and exact helper
definitions. An unexpected overload or modified helper is unavailable, rather
than trusted because its name matches.

The sole metadata query is
`SELECT * FROM public.mixer_customer_artifact_metadata($1)`. The helper is a
fixed-search-path SECURITY DEFINER function owned by a nonlogin/non-superuser/
non-BYPASSRLS role, with no PUBLIC execution. It requires the metadata phase,
artifact-read action/scope, current identity/role/windows and empty application/
environment settings. Its owner-only SELECT policy exposes exactly the
project-visible metadata projection; runtime base-table private SELECT remains
empty during this phase.

The result must have zero or one row and exactly these named columns in order:
organization, project, application and environment IDs, platform, runtime digest,
manifest digest and signed manifest bytes. Missing is `not_found`; multiple,
malformed or mismatched rows are `storage_unavailable`. The strict owned JSON
decoder, v3 manifest policy, canonical 64-byte signature spelling and bounded
CBOR encoder check the signed document, including every normalized column and
the canonical manifest digest. This stage does not verify a signature or claim
current trust. It never reads payload/envelope bytes.

The derived full target is set on the same connection, evidence is reloaded
under the held locks, current full `artifact.read` is evaluated, and Snapshot
loading and Context binding run through the existing exact-target contract.
The callback receives a closed bounded data map containing `target`, `platform`,
`runtime_sha256`, `manifest_sha256`, `signed_manifest_bytes`,
`canonical_manifest_cbor` and `manifest`. Retaining or constructing that map
cannot grant authority. Private storage must re-admit the exact envelope under
current server host/roots/time and compare retained fields before returning it.

Context binding now sets transaction-local `token_issued_at`, `token_expires_at`,
`required_scope` and `phase=effect` from verified identity and the exact action.
All four join the existing connection fingerprint. Changing any one fails a
checkpoint and latches rollback. Exact mappings are `mixer.artifact.read`,
`mixer.artifact.upload` and `mixer.audit.read`. These settings do not introduce a
bearer token or caller-controlled clock into SQL.

Fresh server time and the independent monotonic deadline are checked after
resolution, before callback entry, by every effect and as the final operation
before returning successful callback data for commit. Context ownership,
connection/transaction binding, nesting rejection, error sanitization and
cleanup preserve the ordinary transaction contract. The bounded conflict
reasons now also include `immutable_conflict` and `idempotency_conflict`; explicit
effect failures still latch rollback even if caught by the callback.

## Executable scope

```sh
python3 verification/hosted-customer-artifact-read-scope/run.py \
  --output verification/hosted-customer-artifact-read-scope/run-N \
  --source-revision ROOT_SUPPLIED_REVISION
```

The collector snapshots and hashes only named ordinary sources, the pinned
dependency BEAMs, this test, and the unchanged Policy/transaction regression
tests. It compiles those preserved inputs and runs them against a uniquely
owned loopback PostgreSQL cluster with restricted runtime roles. It records
commands, versions, selected tree digest, output and cleanup on every path.
It does not invoke shared Mix compilation/application startup or frozen lanes.

The resolver fixture applies the actual 003/004/005 product migrations and
uses their real helper, RLS and topology checker. A synthetic superuser seed
uses `session_replication_role=replica` solely to create stored artifact rows
without a successful upload ledger. The altered test manifest retains a test
signature for its shape, deliberately without a signature-validity claim. These
tests qualify metadata resolution and authorization behavior, not successful
mutation integrity, artifact admission or a dogfood release. The unchanged
transaction regression suite uses a separate disposable database/roles.

Focused cases cover project-only admission, all read roles, rejection before
metadata, empty app/environment settings and zero private base-table rows,
exact full-target binding, distinct environment digests, malformed and changed
normalized metadata, helper replacement, expiry during an observed profile
lock wait and immediately after metadata resolution, final expiry rollback,
four-setting tampering, bounded conflict latching, nested/malformed callbacks,
reuse after completion and connection cleanup. Earlier failed attempts remain
preserved beside subsequent receipts.

HTTP/console composition, production Neon/Cloudflare/TLS operation, independent
security acceptance, provider identity qualification, native devices, immutable
published FieldLog consumption and GA remain separate gates. No publication,
customer message, credential change, provider/native/UI run or Git operation is
performed by this lane.
