# Customer artifact transaction contract

Status: proposed next development slice, reviewed against ordinary source at
`d385adf3dd110da44ba290a7221278c48e39b882`. This document is not implementation
or release acceptance. `mixer-product-plan.md` remains binding in full. This
slice is a local PostgreSQL protected upload, private read and upload-audit read;
HTTP/provider login, deployment, R2/CDN, publication, jobs, service/CI principals,
native qualification and published separate-repository FieldLog remain pending.

## Existing components and the required seam

`Protocol.ArtifactAdmission` already verifies a bounded signed v3 envelope and
retains exact envelope, signed document, canonical manifest CBOR, signature and
payload. Its `Checked` struct is forgeable data, not authorization. Re-run
`recheck/4` inside the protected transaction with current server-owned host,
roots and time; compare every retained field. No caller selects roots/host or
changes target fields after checking.

`Authorization.Repository.evaluate/5` and `PostgresRepository` return a pure
evaluation after their own transaction has ended. Domain stores must reject
that value as authority. The new transaction facade must own the actual Repo
transaction containing authorization, callback, domain rows and commit. Keep
the existing evaluation API separate. Root coordinates this facade before
dependent implementation. Suggested public domain API:

```elixir
CustomerArtifacts.upload(identity, route_tenant, key, envelope, request_metadata)
CustomerArtifacts.read(identity, route_tenant, manifest_sha256, request_metadata)
CustomerArtifacts.audit(identity, route_tenant, after_sequence, limit, request_metadata)
```

Server configuration supplies Repo/trust/clock. `route_tenant` contains exactly
organization/project. Request metadata is bounded server request UUID, trusted
ingress IP or absent, and a UTF-8 reason of at most 512 bytes. Metadata is never
actor authority. Initial audit pages use `after_sequence >= 0`, `limit=1..100`.
Only the three already supported human actions are accepted. No runtime
bootstrap, write-authority callback from HTTP, arbitrary Repo or clock argument
is public. Public success returns only after the owning commit succeeds.

The internal facade's context is bound to owning process, Repo, checked-out
connection/transaction, request reference, exact action and target. It cannot be
serialized or retained as a ticket. Reject a `Decision`, lookalike map, missing
callback, callback invoked zero/two times, foreign request/Repo/process,
reentrant transaction, changed target/action, and use after commit/rollback.
Domain SQL must still require `repo.in_transaction?()` and matching internal
context. This protects trusted application composition, not malicious BEAM code
or arbitrary SQL executed with the application's credentials.

## Locked operation and time

Use READ COMMITTED, `queue: false`, 5-second total transaction/statement/idle
bounds and 500-ms lock timeout. Preserve the current six shared lock classes:
profile, principal, family, credential, organization head, project head. Reads
also use them. Every policy/state query used for authorization occurs after the
last wait, with fresh wall time, rather than the caller's pre-lock `now`.

1. Verify access-token identity before private body work. For upload, admit
   bounded exact envelope outside locks and require signed organization/project
   to equal the route tenant. Never infer platform/runtime from request headers.
2. Start the protected transaction and take canonical authorization locks. For
   upload, resolve current target ancestry from the checked signed manifest.
   For read, begin with the project-only route and a narrow membership-aware
   metadata resolver. It returns only stored signed manifest bytes and normalized
   target/digest to trusted code; it returns no payload to the caller and does
   not require a guessed application/environment setting. Parse/reconstruct the
   stored manifest, verify normalized columns match its canonical signed scope,
   derive full target, then evaluate `artifact.read` for that exact environment.
   The current `Session.prepare!/2` assumes a full artifact target; this resolver
   requires an explicit new staged path, not a guessed environment bypass.
3. Upload takes the new per-project domain head `FOR UPDATE` **after** all six
   authorization locks and before inspecting idempotency/domain state. Read and
   audit do not take this mutation lock. After any wait, re-load policy evidence,
   re-evaluate token/family/credential/membership windows and perform current
   artifact recheck. Re-read the stored target for reads before returning bytes.
4. Immediately before the first insert/update or private-byte/result return,
   check fresh time again: no acceptance at/after token `exp`, credential/family
   end, or selected membership end; `iat` fences and current root validity also
   apply. Re-evaluate membership selection at that time. Record this effect
   snapshot. No external call, task, signer, provider fetch or customer code may
   run while locks are held. A bounded commit can finish just after expiry;
   this contract does not promise wall-clock atomicity with a token deadline.
5. Callback error return, exception, exit, throw, malformed envelope or failed
   final invariant rolls back everything, including writes made earlier by the
   callback. A final `SELECT 1` alone cannot validate callback success. Commit
   uncertainty returns storage-unavailable, never a claimed durable success.

Revocation writers take conflicting locks in the same order before changing
state. Missing rows do not bypass locking. New requests after revocation success
cannot use the old state; an earlier admitted transaction may finish before
revocation returns. Test both orderings and reads as well as uploads.

## Additive schema and least privilege

Use coordinated new migrations after `20261025000003`; root's transaction-facade
lane owns `20261025000004` and the profile/binding revision additions below.
Initialize existing rows to revision 1 as a new baseline, never invented old
revision history. Storage follows that coordinated migration. Do not amend historical
migration checksums or reuse unqualified catalog/Worker authority lanes. Proposed
names below deliberately distinguish these tables from historical audit data.

| Table/change | Minimum exact invariant |
| --- | --- |
| `mixer_authz_profiles.state_revision` | Positive revision through the current 2^53−1 bound. Profile active-state changes increment it under the profile lock. Profile identity fields remain immutable for `(id,version)`; trust changes require a new version. |
| `mixer_authz_bindings.revision` | Positive revision; the existing composite `(profile_id,profile_version,subject)` is its stable identity. Principal/class linkage cannot be retargeted; disable/link migration is explicit and audited. Binding active changes increment revision under the profile lock. No invented UUID binding ID is required. |
| `mixer_customer_artifact_heads` | PK `(organization_id,project_id)` and FK to authz project; sequence 0..2^53−1, last event hash and state hash. Provision one row with project creation, by provisioning authority. Runtime cannot insert or delete a head; missing head fails unavailable. Head lock serializes uploads; next sequence is exactly old+1, checked against overflow. |
| `mixer_customer_artifacts` | PK `(organization_id,project_id,manifest_sha256)`, FK actual app/environment ancestry. Immutable exact envelope, signed-manifest JSON bytes, canonical manifest CBOR, 64-byte signature, raw payload, manifest/payload/envelope SHA-256, normalized signed scope/platform/runtime, creating event sequence. Admission bounds apply independently to each byte column. All hashes/column scope must match retained signed bytes, not supplied projections. |
| `mixer_customer_audit_events` | PK `(organization_id,project_id,sequence)`, FK to artifact; explicit `audit_schema=2`, closed event CBOR, event hash, predecessor hash, previous/current state hash and validated display projection. INSERT only; UPDATE/DELETE/TRUNCATE forbidden. |
| `mixer_customer_idempotency` | PK `(organization_id,project_id,key)`, immutable principal ID, action, exact target, request hash, creating event sequence and bounded success result. Composite FK to the same tenant event/artifact. Key is 1..128 ASCII bytes from `[A-Za-z0-9_.:-]`; no token-derived key. INSERT only. |

Head sequence zero has no event hash and a versioned tenant genesis state.
A newly keyed successful command atomically creates one event and one
idempotency result and advances one head; it either creates an artifact or
retains an identical existing artifact unchanged. A deferred database invariant
must reject an event without its matching artifact/dedup/head transition, a
changed retained byte/projection/hash, cross-tenant FK, broken predecessor, gap,
duplicate event or a head advanced alone. A successful app unit test does not
substitute for that real runtime-role adversarial test. If a database canonical
codec/check is introduced, independently compare its bytes with the Elixir codec;
do not trust a SQL function merely because it is called `validate`.

All four new tables require ENABLE + FORCE RLS and revoked PUBLIC privileges.
Keep runtime SELECT-only on authz tables and EXECUTE only on the six reviewed
lock helpers. Domain runtime may receive SELECT/INSERT on artifact/event/dedup
and SELECT plus UPDATE of only the head transition columns; no UPDATE/DELETE,
TRUNCATE, REFERENCES or TRIGGER privilege elsewhere. Runtime cannot create
schema objects, provision projects/heads, mutate memberships or SET ROLE into
an owner. Any new fixed helper uses non-login/non-super/non-bypass ownership,
fixed `search_path=pg_catalog`, no dynamic SQL, no PUBLIC execution, exact
argument/result bounds and specifically reviewed grants.

RLS must check actual row tenant/target and current authoritative linkage,
active state, role and windows under transaction-local exact action/target
context. Domain grants plus a caller-set tenant/role GUC are insufficient.
Metadata resolution gets its own narrow project-visibility policy; payload
SELECT is permitted only after full target action evaluation. Audit rows require
`audit.read`; idempotency SELECT additionally requires the current principal and
upload permission. Missing/malformed/foreign context denies. No delivery role
inherits private artifacts, identity, audit or dedup access.

Extend topology checks to exact new tables, RLS/policy and immutable/deferred
trigger definitions, column grants, table/function owners and expected helper
definitions. Check current/session user equality; reject every reachable owner,
elevated/predefined `pg_` role, BYPASSRLS and indirect NOINHERIT role path as today.
Also reject unsafe PUBLIC/schema CREATE, extra write functions, writable views,
unexpected overloads and column-level authz DML. Read-only authz checks must not
accidentally reject the newly intentional *domain* head update/insert grants.
Provisioning/migration owners never run in API/Oban pools. Every mutation writer
must participate in the same lock/revision protocol.

## New audit schema; no v1 compatibility claim

`Audit.UploadEvent` v1 is closed to 16 display keys and `artifact.upload`, uses
UUID principal/binding/family/member identities and ASCII scope IDs, records
only membership ID/role/revision, and requires an authentication-completion time
within decision−45/+30 seconds. Current authz IDs are bounded printable text,
bindings have neither ID nor revision, and `VerifiedIdentity` carries token
`issued_at/expires_at`, not authentication-completion time. The pure Decision
also drops family identity/revision, binding state, and individual membership
revisions. Coercing IDs or treating `iat` as authentication time is incorrect.
Preserve v1 bytes, hashes, tests and decoder unchanged. No v1 historical row is
assigned to today's principal or inserted into the new chain implicitly.

Introduce a separately named `CustomerArtifactEvent`, schema 2, whose closed
canonical value is the following fixed-position array. Use the existing owned
bounded deterministic ArtifactCBOR encoder with *text hex* digests, not an
unimplemented byte-string/null extension. All numeric values are integers up to
2^53−1; profile version remains positive 32-bit. Optional numeric ends use `[]`
or `[exclusive_end]`; optional IP uses `[]` or `[canonical_ip]`.

```text
[2, sequence, [organization,project],
 actor, authorization, target, "artifact.upload", outcome, reason,
 server_request_uuid, optional_trusted_ip, recorded_at,
 previous_state_sha256, current_state_sha256, previous_event_sha256,
 request_sha256, envelope_sha256]

actor = [principal_id,"human",profile_id,profile_version,
         binding_key_sha256,issuer_sha256,subject_sha256,client_sha256,
         credential_ref_sha256,family_id,token_issued_at,token_expires_at]
authorization = [locked_at,effect_checked_at,
  [profile_state_revision,true], [binding_revision,true],
  [principal_revision,true,principal_not_before],
  [credential_revision,true,credential_not_before,credential_end],
  [family_revision,true,family_not_before,family_end],
  organization_revision,project_revision,required_scope,selected_memberships]
selected_membership = [id,role,revision,organization,optional_project,
                       project_binding,true,not_before,optional_end]
target = [organization,project,app,environment,platform,runtime_sha256,
          manifest_sha256,payload_sha256]
```

Optional project is `[]` or `[project]`. Members are the 1..64 current eligible
memberships that supply the action, sorted uniquely by exact UTF-8 ID bytes;
roles must be owner/administrator/developer for upload, with exact scope/binding
and valid windows. Record the required exact OAuth scope; unknown token scopes
need not be retained. Full raw claims, bearer tokens, refresh tokens and external
identity strings are never audit fields. Hash each external reference with its
own `mixer.hosted.customer.<field>.v2\0` domain and exact UTF-8 bytes. Binding key
hash covers canonical `[profile_id,profile_version,subject]`. Internal IDs retain
the current bounded identifier grammar, rather than UUID coercion. Snapshot
fields come from post-lock stored rows and verified identity; caller maps cannot
construct them. Record selected allowed rows, not just deduplicated role names.

`outcome` is exactly `"created"` or `"unchanged"`. Canonical event bound is
65,536 bytes, depth 16, 4,096 items and 256 entries per
container, with fixed schema checked before encoding. Reject oversized snapshots
before effects. Event hash is SHA-256 of
`mixer.hosted.customer.audit.v2\0 || event_cbor`; previous event hash is `""` only
at sequence 1, otherwise 64 lowercase hex. Genesis state hashes canonical
`[2,organization,project]` under `mixer.hosted.customer.state.v2\0`. Next state
hashes `[2,organization,project,previous_state,sequence,manifest_sha256,
envelope_sha256,payload_sha256]` under that state domain only for `"created"`.
For `"unchanged"`, next state equals previous state exactly. The state is this
append-only artifact ledger, not a claim to hash all database rows. Every audit
event still advances the event sequence and hash chain.

Display is a closed named projection of the same fields plus `event_sha256`;
validate schema, types, array lengths and exact canonical CBOR/hash reconstruction.
Persist display JSONB as a semantic projection, not a promised PostgreSQL text
serialization. This new schema deliberately makes no v1 `display_bytes`
compatibility promise. Immutable persistence and edge checks prove consistency;
they do not detect a coherent rewrite by a privileged database owner. Independent
audit checkpoints/retention/privacy remain separate product work.

## Idempotency, private reads and successful audit

Compute request hash under `mixer.hosted.customer.upload.request.v2\0` over
canonical `[2,"artifact.upload",target,envelope_sha256,reason]`. Exact envelope
spelling is significant; request UUID/IP/time/credential are not retry identity.
After current full upload authorization and the head lock, look up tenant/key:

- Same immutable principal, action, target and request hash returns the original
  success/event unchanged. A refreshed eligible credential may retry; this does
  not replace the original actor or append another event.
- Any mismatch returns `idempotency_conflict`, without another principal's
  cached result/body. Another principal never gains the original retry right.
- A new key with an existing manifest preserves ordinary Go v3 behavior:
  compare canonical manifest CBOR, decoded signature and raw payload. Equal
  immutable content returns 200 and records `outcome="unchanged"`, one new audit
  event and a new principal-bound success row; artifact bytes, creating event
  and domain state hash stay unchanged. Different immutable content returns
  `immutable_conflict`. JSON formatting-only differences can be semantically
  equal under a new key; retain the first artifact's exact bytes and audit the
  new request's exact envelope hash. A new artifact returns 201 with
  `outcome="created"`. No failed attempt consumes a sequence or dedup success.

This follows `services/release/server.go`'s existing-artifact upload branch,
`storage.go:immutableEqual`'s decoded signed-document/payload equality and
`postgres.go`'s event/dedup/head write even when no domain change exists. The new
request hash, actor, schema, names and principal binding are explicitly versioned
hosted behavior, not a claim of historical Go audit-byte compatibility.

For upload, receipt includes manifest/payload digest and original event sequence,
not raw actor evidence. A revoked caller cannot retrieve a cached success. On
ambiguous commit, retry the same key after fresh identity/policy checks.

Private read first parses bounded metadata without exposing payload, then, after
the exact target is authorized, runs `ArtifactAdmission.admit/4` over the stored
envelope with current server host/roots/time and compares every retained row
field. Complete envelope/signed-byte/payload/column equality is mandatory before
returning the exact stored envelope; changed bytes fail storage-unavailable.
Missing/foreign/nonvisible
artifact is not-found; a visible project lacking action scope is permission-denied.
No private response URL is introduced. Reads do not mutate this successful-upload
chain; a separately versioned read-observation stream, if required, needs its own
contract. Sanitized rejection observations are not successful upload events.
Audit read authorizes the explicit project-only target, returns bounded ordered
pages of immutable v2 events, and cannot supply an artifact context. It verifies
row/projection/edge consistency; missing predecessor or corruption fails closed.

## Verification and acceptance boundary

The machine-readable matrix and runner are in
`verification/hosted-customer-artifact-transaction-contract/`. The runner checks
this proposal's packet integrity and refuses to turn missing product tests into
a pass. Every implementation case remains pending until its exact ExUnit test
exists and passes against a disposable real PostgreSQL fixture and restricted
runtime role. Root owns coordinating subsequent source/migration/API changes.
No production route, provider/R2/dispatch, customer message, phone run or GA gate
is authorized or passed by this proposal.
