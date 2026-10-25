# Protected customer artifact HTTP contract

This is the coordinated implementation contract for the first ordinary Phoenix
customer artifact routes. It records source-derived compatibility and explicit
new transport choices; it is not a claim that the routes have shipped or passed
integration. `mixer-product-plan.md` remains binding, including W11 Go-contract
parity and G24. The accepted application facade and transaction/storage contract
remain authoritative for authorization and effects.

## Routes and compatibility

Use these existing Go v3 paths, without a second convenience route family:

| Method | Path | Success |
| --- | --- | --- |
| PUT | `/v3/orgs/:organization/projects/:project/artifacts/:manifest_sha256` | 201 when created; 200 when identical content already exists under a new key; original status on an authorized same-key retry |
| GET | `/v3/orgs/:organization/projects/:project/artifacts/:manifest_sha256` | 200 with the exact retained artifact envelope bytes |
| GET | `/v3/orgs/:organization/projects/:project/audit` | 200 with a bounded page |

Upload success has exactly `artifact_sha256` and `immutable`, with the signed
manifest digest and literal `true`. Map the facade's `manifest_sha256` to
`artifact_sha256`; its payload digest/event sequence are internal to this
response. Preserve the original status on a same-key retry, including 201.

The read representation is the original JSON envelope containing exactly
`signed_manifest` and `payload`. Return `envelope_bytes` directly with
`application/json`; do not decode/re-encode it, wrap it, expose internal retained
columns, or return only the raw payload. This preserves the Go semantic envelope
and strengthens byte preservation beyond Go's reconstruction of a typed value.

Audit success has exactly `events` and `next`; map `next_after_sequence` to
`next`. Events are the validated schema-2 display maps described below. The
current Swift CLI source has no hosted HTTP client; Go service tests and Python
release-workflow clients are the existing wire consumers/reference evidence.

The path digest is exactly 64 lowercase hexadecimal bytes. Route organization
and project use Go's exact 1..128-byte ASCII `[A-Za-z0-9._-]` identifier alphabet.
Only two route fields become the closed internal map `organization_id` and
`project_id`. The internal `Authorization.Scope.identifier?/1` API is broader;
HTTP intentionally retains the narrower existing Go alphabet. Signed v3 manifest
scope must still match the configured host. Percent-escaped separators, malformed escapes,
ambiguous path normalization, extra path segments and invalid digests do not
select an alternate resource. No platform/runtime/application/environment comes
from headers, unsigned query data or guessed defaults.

HEAD is an explicit additive capability relative to the Go reference. It must
perform the same identity, action scope, tenant and current authorization checks
as GET. The actual HTTP wire contains no response body for either success or
error. The existing endpoint's `Plug.Head` rewrites the method to GET; it does
not itself erase the Plug response body, so verify the actual Bandit wire.
Unsupported methods do not invoke a mutation or gain a GET authorization bypass.

## Authentication and request ordering

Run the accepted `BearerIdentity` plug before fetching query/body parameters or
reading a body. Its bounded raw query-name and Content-Type policy intentionally
can reject malformed/alternative credential input before invoking the verifier.
It accepts only one bounded Authorization Bearer value and supplies only a
verified identity, never a principal, tenant membership or actor authority.

After identity verification, require the exact action scope before body work:
`mixer.artifact.upload`, `mixer.artifact.read`, or `mixer.audit.read`. Unsupported
identity classes fail closed. Do not use the presence of a token or this early
scope check as current database authorization. The existing facade still owns
the fresh policy, metadata-resolution and authorization transaction, including
effect-time checks and commit. Never return success, read bytes or audit results
before its owning commit succeeds.

The route/controller never accepts a Repo, root set, host policy, clock,
callback, actor, principal, role, membership, audit request ID or write authority
from HTTP. Trusted application configuration remains the only source of those
dependencies. No parser, multipart handler or automatic decompressor may run
upstream of identity admission.

## Request bytes, media and metadata

PUT requires exactly one `Content-Type: application/json` header and exactly one
`Idempotency-Key`. The key follows Go's 1..128 ASCII bytes from
`[A-Za-z0-9._-]`. The internal facade additionally permits colon, but this HTTP
contract does not expand the existing accepted key alphabet.
Reject duplicate headers even when values match; never select the first value
or comma-join multiple values. The reason is supplied only by an optional single
`X-Mixer-Reason` header. Absent or empty uses exactly
`local development operation`, matching Go. Otherwise it is valid UTF-8 of at
most 512 bytes. Do not trim it, read it from a query/body field, or let it choose
actor authority. GET/HEAD use server-owned empty reason metadata and do not
interpret this mutation header.

Content-Encoding must be absent. Reject any supplied encoding, including an
identity declaration, with 415 `unsupported_content_encoding`; do not decompress
before applying limits. GET/HEAD have no body; Content-Type may be absent or the
single exact `application/json` value. Apply their body/media checks only after
identity and exact action-scope admission. Malformed/form Content-Type may
already have been rejected by the identity plug. A nonempty GET/HEAD body is
400 `invalid_request`, including a chunked body. An absent or zero Content-Length
is not proof that a streaming request has no body.

Read PUT as bounded raw bytes with a finite total read deadline. The entire
document, including whitespace, is at most 6,291,456 bytes. Enforce the cumulative
bound while reading; neither Content-Length nor a per-read length alone is
sufficient. Read/timeout failures return 400 `malformed_body`; overflow returns
413 `body_too_large`. Never log the raw body or credential.

The admitted envelope remains closed and preserves exact bytes. Signed manifest
JSON is at most 65,536 bytes, decoded payload is 1..4,194,304 bytes, signature is
64 bytes, and canonical base64 plus the nested closed protocol shape are
mandatory. Use bounded `ArtifactJSON.decode/2` plus exact top-level envelope
shape to classify invalid JSON/UTF-8, duplicate keys and top-level
missing/null/extra/alternate fields as 400 `invalid_json`. Pass the original
raw bytes unchanged to the facade afterward; the transport decode result never
confers admission or authorization. `ArtifactJSON.preflight/2` alone does not
check duplicate keys or UTF-8. Deeper signed-policy/signature failures return
422 `artifact_invalid`. Go's typed signed-document decoder also classifies some
deeper missing/null/extra/alternate nested fields, base64 and typed-value failures
as 400 `invalid_json`; unless separately reproduced by the transport classifier,
that subset remains an explicit 422-versus-400 migration difference. Syntax
analysis alone never authorizes a release.

Root's additive `CustomerArtifacts.upload_at/6` seam receives the expected route
digest and validates it against admitted signed bytes before opening the domain
transaction. The existing `upload/5` API remains compatible. Valid signed bytes
with a different digest return 422 `digest_mismatch`; failed signed admission
returns 422 `artifact_invalid`. Never discover a route mismatch after calling a
successful upload: its effects would already have committed.

## Query contract

PUT and artifact GET/HEAD accept no query fields. Audit GET/HEAD accepts only
`after` and `limit`, each at most once. Absent or empty values default to 0 and
100, matching Go. Empty segments/names, duplicate or unknown fields,
bracket/nested forms, invalid escaping, signs, fractions, whitespace and overflow
reject. Values are bounded decimal integers after one decode. `after` is
0..9,007,199,254,740,991 and `limit` is 1..100. No automatic parameter map may
collapse duplicates before this validation. Retain the identity plug's earlier
8,192-byte/128-field raw query ceiling and alternative-token-name rejection.

Return events in increasing sequence strictly greater than `after`. An empty
page returns `events: []` and preserves `next == after`; otherwise `next` is the
last returned event sequence. Reads do not create upload audit events. These
strict parsing rules intentionally narrow Go's ignored unknown keys, first-value
duplicate handling and uint64 cursor range. Absent-or-empty defaults are retained.

## Error and response policy

Every protected response has one `Cache-Control: no-store` header, a bounded
`X-Request-ID`, JSON Content-Type where a representation is returned, and generic
bounded error text. The error envelope remains exactly
`{"error":{"code":"...","message":"..."},"request_id":"..."}`.
Remove duplicate/conflicting response challenge/retry/cache metadata before
writing the applicable value. Do not expose database, verifier, provider,
signature or exception details. HEAD preserves these headers without a wire
body. The HTTP correlation ID is not the independently generated domain audit
request ID and never becomes actor evidence.

| Condition | HTTP/code |
| --- | --- |
| Missing bearer | 401 `unauthenticated`, `WWW-Authenticate: Bearer` |
| Malformed/ambiguous/alternative credential | 400 `invalid_request`, Bearer `invalid_request` challenge |
| Invalid/expired/revoked identity | 401 `unauthenticated`, Bearer `invalid_token` challenge |
| Identity verifier unavailable | 503 `identity_unavailable` |
| Missing/invalid upload key | 400 `idempotency_required` |
| Invalid reason | 400 `invalid_reason` |
| Unsupported/missing PUT media type | 400 `content_type` |
| Failed body read / oversized body / syntax failure | 400 `malformed_body` / 413 `body_too_large` / 400 `invalid_json` |
| Signed admission / route digest mismatch | 422 `artifact_invalid` / 422 `digest_mismatch` |
| Other invalid route/query/application input | 400 `invalid_request`, or a route miss 404 `not_found` |
| Current authorization denied | 403 `permission_denied` |
| Invisible/missing tenant or artifact | 404 `not_found` |
| Immutable/idempotency/domain conflict | 409 `immutable_conflict` / `idempotency_conflict` / `conflict` |
| Authorization/storage/commit unavailable | 503 `authorization_unavailable` / `storage_unavailable` |

503 responses contain `Retry-After: 1`; other rows do not inherit retry advice.
On unavailable upload, clients retry the same key, bytes, route and reason with
bounded backoff. Retries always reauthorize. Failed requests do not reserve keys.
Same-key requests from another principal or with changed reason/content conflict.
This deliberately strengthens Go's method/path/exact-body binding, which did not
bind principal or reason. The current HTTP upload path is bound by its exact
admitted digest before mutation; no alternative route aliases exist.

Do not translate authoritative membership errors into Go's static-token
`scope_denied`/`role_denied` without evidence: invisibility and denial have
distinct existing facade semantics. Retain the accepted BearerIdentity ordering
and response behavior. The old Go 128-handler and 120-request/minute direct-IP
limits are existing reference behavior; this contract does not claim those
limits are implemented in Phoenix. Transport/tenant abuse controls and exact
429 behavior need their own implementation/evidence before full W11 parity.

## Source IP, schema-2 audit and limits

Use only the actual socket peer `conn.remote_ip`, converted through
`:inet.ntoa/1` to canonical IPv4/IPv6 text, or `nil` if a trusted adapter cannot
establish it. Ignore `Forwarded`, `X-Forwarded-For`, `X-Real-IP`,
`CF-Connecting-IP` and other client assertions. There is currently no qualified
trusted-proxy adapter; do not call a Cloudflare proxy peer the original customer
IP. Source IP is audit metadata and never identity or tenant authority.

Each schema-2 event includes `audit_schema: 2`, `sequence`, `tenant`, structured
`actor`, `authorization`, `target`, action `artifact.upload`, `outcome`, reason,
the internally generated 32-hex request ID, optional source IP, `recorded_at`,
previous/current state hashes, previous/event hashes, request hash and envelope
hash. Preserve the validated display as returned by storage. It hashes external
identity references and does not disclose raw provider subjects or credentials.

This is an explicit event-schema migration: Go events had an actor string,
`id`, organization/project fields, an HTTP-method/path action, `previous/current`,
`created_at_unix`, `previous_hash` and `hash`. Do not fabricate those legacy
fields, recalculate the immutable chain, or claim schema-2 is byte-compatible.
This slice has only upload events; it does not migrate a preexisting Go history,
outbox or publish/validate/promote/rollback operations. Authenticated private
read/audit routes are not public delivery routes or OTA publication authority.

The configured facade currently has one captured host/trust configuration.
Provider login, console sessions, service/CI principals, trust lifecycle writers,
Neon, R2/CDN, deployment, operational quotas, physical/native qualification and
published separate-repository FieldLog remain separate evidence gates. No frozen
catalog/authority or rejected Worker transport is part of this contract.
