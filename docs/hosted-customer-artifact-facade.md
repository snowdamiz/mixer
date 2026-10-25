# Customer artifact application operations

`MixerHosted.CustomerArtifacts` composes verified identity, artifact admission,
current PostgreSQL authorization, immutable storage and schema-2 upload audit.
It is the internal application entry point for future protected customer routes.
No HTTP route or deployment is enabled by this implementation.

The API is `upload(identity, route_tenant, key, envelope, metadata)`,
`read(identity, route_tenant, manifest_sha256, metadata)` and
`audit(identity, route_tenant, after_sequence, limit, metadata)`.
The additive HTTP seam is `upload_at(identity, route_tenant, expected_digest,
key, envelope, metadata)`. It validates the lowercase manifest digest and
compares it with the admitted signed bytes before starting the authorization
transaction. A mismatch returns `digest_mismatch` without reserving a key,
writing an artifact/event or advancing the project head. Failed signed admission
returns `artifact_invalid` on this seam; the existing `upload/5` error behavior
is preserved. These two errors are input/admission results before transaction
effects, not new transaction callback result types.
The closed route map contains atom keys `organization_id` and `project_id`.
The closed metadata map contains `reason` (valid UTF-8, at most 512 bytes) and
`source_ip` (canonical IPv4/IPv6 or `nil`). The trusted ingress adapter, rather
than a forwarded request header, must supply the source IP. The owning
authorization transaction generates the audit request ID. Caller request IDs,
actors, callbacks, Repo modules, clocks, host policies and roots are rejected as
extra request fields.

Trusted application configuration under
`Application.fetch_env(:mixer_hosted, MixerHosted.CustomerArtifacts)` contains
exactly `%{repo: module, host: host_policy, roots: public_roots}`. No default
configuration is installed. This first composition supports one configured host
policy; a multi-tenant trust registry, rotation/revocation writer protocol and
deployed configuration remain pending. An in-flight operation uses the captured
server configuration and rechecks its validity windows at effect time; this is
not a claim of atomic visibility of concurrent application-environment changes.

Upload validates identity and the exact token scope before admitting the bounded
signed bytes. The signed scope must match the configured host and route tenant.
The authorization transaction owns the six shared authorization locks and all
storage effects. Storage rechecks signature, trust, bytes and policy after its
domain-head wait and before effects. A success includes `status` (201 for a new
artifact, 200 for unchanged content under a new key), `manifest_sha256`,
`payload_sha256` and `event_sequence`. Same-key retries return the original
receipt only after fresh authorization; another principal or changed request
returns `idempotency_conflict`.

Read begins with only the route project and manifest digest. The restricted
metadata resolver obtains signed manifest bytes without exposing payloads,
derives the actual application/environment, and evaluates exact read permission.
The facade checks that resolved target, platform and runtime match the configured
host. Storage then re-admits the retained envelope under current effect time and
compares immutable bytes and normalized columns. Success contains
`envelope_bytes`, `manifest_sha256` and `payload_sha256`.

Audit uses `audit.read` and a bounded project page (`after_sequence` in
0..2^53−1, `limit` in 1..100). Success contains `events` and
`next_after_sequence`; an empty page preserves the supplied cursor. Storage
validates row projections and predecessor edges before returning a page. Reads
and audit reads do not create upload events. All public success values are
returned only after the authorization-owned transaction commits.

The focused collector is
`verification/hosted-customer-artifact-facade/run.py`. It snapshots selected
ordinary sources and fixtures, compiles with warnings as errors, and exercises
the actual public functions against a disposable PostgreSQL instance with a
restricted runtime role. Test mutations and identities are isolated synthetic
fixtures; they do not establish provider authentication, R2/CDN delivery, store
publication, native validation, separate-repository FieldLog qualification,
operational readiness or a GA gate. Independent review and integration evidence
are recorded separately from this description.
