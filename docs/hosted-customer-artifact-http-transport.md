# Customer artifact HTTP transport

The Phoenix router now exposes protected customer artifact PUT/GET routes at
`/v3/orgs/:organization_id/projects/:project_id/artifacts/:manifest_sha256` and
project audit GET at `/v3/orgs/:organization_id/projects/:project_id/audit`.
The coordinated wire contract is
[hosted-customer-artifact-http-contract.md](hosted-customer-artifact-http-contract.md).
These routes are private customer operations; their existence is not publication,
OTA release approval, deployment, or GA qualification.

## Composition and authority

The router matches a known method/action before running its customer-artifact
pipeline. The existing `BearerIdentity` plug runs with its unchanged production
`ConfiguredVerifier` and clock defaults. It reads only bounded credential/media
headers and raw query names. No upstream body parser or query-parameter map is
introduced. The controller is a plain Plug; it does not invoke Phoenix controller
parameter fetching.

`CustomerArtifactRequest` next requires a verified human identity and the exact
operation token scope: `mixer.artifact.upload`, `mixer.artifact.read`, or
`mixer.audit.read`. That check precedes route/query/media/body work. It is only
transport admission. The real `CustomerArtifacts` facade still owns current
membership, credential and tenant authorization, signed admission, transaction
commit, and effect-time checks. The transport has no success path around it.

Production controller atom initialization fixes the real facade and the system
monotonic clock. Validated keyword initialization can supply a facade module and
clock MFA for standalone tests. HTTP input never reaches those options. No Repo,
root set, host policy, actor, principal, role, membership or audit request ID is
accepted from HTTP.

## Bounded requests and representations

Organization/project IDs and the upload idempotency key contain 1..128 ASCII
bytes from `[A-Za-z0-9._-]`, excluding colon. The route digest is exactly 64
lowercase hexadecimal bytes. Only organization/project become the closed facade
route map. After identity/scope and bounded decoded-field admission, the request's
raw `request_path` must exactly equal the reconstructed operation-specific path.
Encoded static segments/IDs/digests and repeated/trailing slash aliases return
400 `invalid_path` before query/body/facade work, even if Phoenix routes them.
The raw comparison is limited to 512 bytes. This matches Go's encoded RawPath
rejection; Phoenix-routed extra-slash aliases consistently return 400 rather than
Go's possible 404 route miss. PUT requires one exact `application/json`
Content-Type and one key;
identical duplicate headers remain invalid. A single optional UTF-8 reason is at
most 512 bytes. Missing/empty reason becomes exactly
`local development operation`. Read/audit ignore reason headers and use empty
reason metadata.

PUT and artifact read accept no query. Audit accepts only one `after` and one
`limit`, with absence or empty value defaulting to 0 and 100. It validates the raw
fields before constructing a page, percent-decodes exactly once, rejects unknown
or duplicate keys including encoded duplicates, and accepts only at most 16
ASCII decimal digits. `after` is at most 9,007,199,254,740,991; `limit` is 1..100.
Signs, spaces, fractions, nested names, malformed escaping, empty fields and
extra segments fail closed. The identity plug retains its earlier raw-query
ceiling and alternative-token-name rejection.

Any present Content-Encoding returns 415 `unsupported_content_encoding`,
including `identity`, empty or duplicate declarations. GET/HEAD media is absent
or one exact JSON type. After identity/scope checks, read/audit actively read to
confirm an empty body; neither an absent nor a zero Content-Length bypasses that
check.

The raw upload document limit is inclusive at 6,291,456 bytes. Reads request at
most 65,536 bytes, have a fixed total 15,000 ms monotonic deadline, and permit at
most 128 adapter reads. The deadline is recomputed from the original deadline,
never extended per chunk, and checked after reads. Overflow returns 413
`body_too_large`; body errors, throws, exceptions, timeout or exhausted read
count return 400 `malformed_body`. Nonempty read/audit bodies return 400
`invalid_request`.

`ArtifactJSON.decode/2` bounds syntax, duplicate keys and UTF-8 before the facade.
The outer value must be exactly `signed_manifest` (an object) and `payload`
(a string); malformed or alternate outer shapes return 400 `invalid_json`.
The decoded value is discarded. The original raw bytes, including field order
and whitespace, reach `upload_at/6` unchanged; there is no re-encoding. This
transport check does not authorize an artifact. Signed protocol and signature
admission rejection returns 422 `artifact_invalid`; root's facade checks route
identity before mutation and returns 422 `digest_mismatch` on mismatch.

Upload returns only `{artifact_sha256, immutable: true}` using the signed manifest
digest and the facade's 201/200 status, including the original same-key status.
Read returns retained `envelope_bytes` directly as JSON. Audit maps the facade's
`{events, next_after_sequence}` to `{events, next}` and preserves its validated
schema-2 display maps; it does not fabricate legacy Go actor/event fields.

Only `conn.remote_ip` supplies canonical IPv4/IPv6 source metadata; an unavailable
adapter address becomes nil. Forwarded/X-Forwarded-For/CF-Connecting-IP and
actor/audit request-ID override headers do not enter facade metadata. The HTTP
correlation ID retains the accepted BearerIdentity policy and remains distinct
from the independently generated domain audit request ID.

Protected responses have one `Cache-Control: no-store`, one correlation-ID header,
and JSON media for representations. Admission clears stale challenge, retry and
Content-Type metadata on success and error paths. Error envelopes contain only
constant bounded code/message and matching request ID. Only 503 responses get
`Retry-After: 1`. Exceptions and unsupported facade results become generic 503
storage unavailability; database/provider/body details are not returned.

The existing endpoint's `Plug.Head` maps HEAD to GET while retaining equivalent
identity/scope/current authorization work. The actual adapter must remove the
body from HEAD success and error responses. Unsupported methods and unmatched
routes do not invoke domain operations.

## Verification and limits

Run the isolated unit/adapter suite with:

```sh
python3 verification/hosted-customer-artifact-http-transport/run.py
```

The collector copies an explicit allowlist of identity modules, ArtifactJSON,
accepted BearerIdentity, health/router, owned request/controller, and the one
transport test. It loads only explicitly named general-dependency ebins, checks
both lock and runtime versions, starts no Mixer application, and excludes the
application ebin and every catalog/authority/Worker source. It does not call the
main hosted test script. Each attempt preserves source hashes, aggregate tree
digest, exact command/runner, tool versions, output and receipt. Scratch is removed
on subprocess completion.

`verification/hosted-customer-artifact-http-transport/run-5/` passes all **32**
tests on Elixir 1.20.4 / Erlang OTP 29. The preserved `run-3` has 29 passing
original tests and predates independent discovery of raw-path alias acceptance.
The repaired suite adds actual Phoenix-router canonical controls, rejection of
encoded/repeated/trailing-slash aliases for all three operations, and authentication/
exact-scope ordering on aliases. The cases exercise authentication/body
ordering; exact scopes and human class; route/key/reason/media bounds and
ambiguity; encoded duplicate query keys and numeric boundaries; empty GET bodies;
IPv6 socket metadata; unchanged bytes; inclusive/overflow body limits; partial
chunks; fixed deadline/read-count/failure controls; schema-2 audit mapping;
constant error classification; duplicate response-header cleanup; supported
production-router missing-auth routes; unsupported paths; and HEAD using the
Plug test adapter. `run-1` preserves a collector startup failure (Mix state was
not initialized for the identity module's compile-time environment); `run-2`
preserves a test expectation error for a comma-joined Content-Type rejected early
by BearerIdentity. `run-4` preserves a repair-test fixture compilation failure:
its pipeline clock pointed to an outer test module before it was loaded. A
separate bounded fixture clock resolved that test-only dependency. All failures
remain preserved; the identity plug is unchanged.

These 32 tests use a trusted fixture verifier/facade and test adapter. They do not
prove real socket framing, default ConfiguredVerifier acceptance, PostgreSQL
commits or authorization freshness. A separate coordinated integration receipt
must establish those properties. No claim here covers Neon, trusted-proxy
original-client IP, rate/tenant admission quotas, production deployment, R2/CDN,
provider login, service principals, native/device testing, signing/store gates,
or immutable separately published FieldLog packages. Physical phones remain
deferred under repository instructions.
