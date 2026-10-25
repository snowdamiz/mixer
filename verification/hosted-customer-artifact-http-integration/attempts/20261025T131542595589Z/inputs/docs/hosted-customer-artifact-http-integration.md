# Customer artifact HTTP integration evidence

This selected-source host test exercises the actual ordinary
`MixerHostedWeb.Endpoint`, including RequestId/Head and the production Router,
over its loopback Bandit TCP listener. The production route
initializers use the default `BearerIdentity`, `ConfiguredVerifier`, and real
`CustomerArtifacts` facade. There is no controller facade replacement or
caller-supplied verified identity in this test.

The first successful HTTP request performs cold JWT/JWKS admission; a preceding
missing-bearer HTTP request makes no JWKS fetch. The named production `KeyOwner` receives a test-only TLS/JWKS transport fixture
for `jwks.fixture.invalid`, fresh RS256 access tokens, and a synthetic profile and
credential registry. Each test independently generates an Ed25519 artifact key,
signs the owned protocol-only payload, and installs a short-lived public trust
root in the trusted application fixture configuration. Private keys remain in
process memory; the TLS helper removes its temporary certificate/key directory.
This proves the host composition with synthetic identity data. It does not
qualify a production identity provider, public DNS, or deployed trust registry.

`mixer_customer_artifact_http` belongs to a disposable loopback PostgreSQL
cluster. Separate fixture-admin, no-login owner, and restricted runtime roles run
the real authorization and artifact migrations, current grants, RLS, integrity
constraints, retained byte checks, and schema-2 audit storage. Synthetic registry
mutations are made only through the test admin connection.

The executable matrix checks:

- Initial creation, authorized same-key retry preserving 201, and a new key
  preserving the first artifact bytes while appending an `unchanged` event.
- Exact retained envelope bytes including whitespace, bounded schema-2 audit
  pages, terminal cursors, socket peer IP instead of forwarded claims, and an
  internal domain request ID independent of an HTTP correlation header.
- Actual HEAD requests with empty wire bodies on artifact, audit, and missing
  authentication responses.
- Missing/expired bearer and exact upload scope, including headers declaring an
  upload body that is deliberately withheld: rejection completes before body
  bytes arrive.
- Digest mismatch before mutation and before an existing idempotency receipt,
  with unchanged artifact/event/key/head counts and the same unreserved key
  available afterward.
- Current viewer/billing roles, credential revocation, removed membership,
  foreign tenant reads, and another principal attempting to reuse a key.
- Empty Content-Encoding, exact media, duplicate/extra JSON fields, signed
  admission failure, duplicate/unknown/overflow audit queries, and both fixed
  and chunked nonempty GET bodies.
- A fixture-only PostgreSQL backend termination after the upload's writes and
  deferred checks but before final authorization completion and commit. The
  response must be 503, all four committed counts remain zero, and a subsequent
  retry can create with the original key. This checks a concrete pre-commit
  failure; it does not model every uncertain commit outcome.

Run from the repository root:

```sh
python3 verification/hosted-customer-artifact-http-integration/run.py --list-sources
python3 verification/hosted-customer-artifact-http-integration/run.py
```

Each run creates a fresh UTC-named attempt directory and preserves source
snapshots, the dynamic Git revision, selected-tree SHA-256, dependency BEAM
hashes, tool versions, exact commands/output, sanitized public request/response
observations, and cleanup. The collector compiles only the listed ordinary
sources with existing pinned general-purpose dependency BEAMs, excluding the
`mixer_hosted` application. It extracts only the named safe database provision
helper with its owned tuple; it neither imports nor executes the shared
collector's main body. It never imports frozen catalog/authority, rejected
Worker transport, native, UI, or device lanes.

Request records retain method/path, body lengths and SHA-256, header names,
bearer presence, public response data, and committed table counts. They omit
access tokens, private keys, and idempotency header values. Setup/configuration
is restored and owned Bandit, JWKS workers, TLS sockets, PostgreSQL, and scratch
files are stopped/removed even when a command fails.

This is local host HTTP/storage integration evidence. PostgreSQL transport has
no TLS in the disposable cluster. Neon, R2/CDN, Cloudflare deployment, production
identity/login, abuse quotas, full W11 wire parity, Go audit-history migration,
compiler/runtime execution, native/store/physical-device behavior, published
separate-repository FieldLog, accountable operational review, and GA acceptance
remain separate gates.
