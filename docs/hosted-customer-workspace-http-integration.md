# Customer workspace production HTTP integration

The focused collector is
`verification/hosted-customer-workspace-http-integration/run.py`. It stages an
explicit ordinary source allowlist, dependency BEAM hashes, exact console client
and parser sources, installed TypeScript runtime hashes, tool versions, commands,
outputs, and a source-tree digest into a fresh attempt directory. It never imports
or executes the shared hosted collector, compiles the full application, or starts
native/capture processes.

The integration fixture starts the actual `MixerHostedWeb.Endpoint` and production
router on an ephemeral loopback Bandit listener. Requests traverse the default
`BearerIdentity`, `ConfiguredVerifier`, and named `KeyOwner`, using an ephemeral
RS256 token and synthetic TLS JWKS fixture. The production controller calls the
actual `CustomerWorkspace.organizations/2` and `projects/3`; the default
`MixerHosted.Repo` connects as a separate non-superuser, non-bypass, non-role-creator
runtime login. No replacement facade or repository is injected into the controller.
Migrations 3, 4 and 6 run under a nonlogin database owner. Grants permit SELECT on
authorization tables and the six existing fixed head-lock helpers.

Eleven required tests cover exact GET/HEAD routes, identity and exact workspace scope
before withheld bodies, workspace-only tokens denied by artifact/audit routes, closed response envelopes, current nullable names, all six
role strings with distinct organization/project provenance, complete Scope IDs in
query values (dots, slash, Unicode, plus, percent and space), cursor pagination,
foreign/inactive/missing organization equivalence, revocation between requests,
metadata freshness, malformed and duplicate query rejection, encoded path aliases,
nonempty and chunked bodies, media/encoding policy, and unavailable responses for
invalid stored names or absent heads. A telemetry-only fixture terminates the actual
default repository backend after its final local read and before commit; the HTTP
response must be generic unavailable with no page, and a fresh retry must succeed. Every captured socket response must close,
carry one no-store header and a bounded request ID. HEAD must have no wire body.

The final test compiles the actual console API client and parser, then uses Node's
real global fetch against the same Phoenix listener. It traverses all organization
pages, round-trips dot/slash/Unicode/plus/percent IDs, reads billing-manager projects,
and rejects a foreign organization and missing local session. The token is passed
only through an ephemeral child environment; no token or private key enters the
receipt, command arguments or saved output.

For ordinary hosted CI, provide `MIXER_WORKSPACE_HTTP_TEST_PORT` using database
`mixer_customer_workspace_http` and roles `workspace_http_fixture_admin`,
`workspace_http_owner` and `workspace_http_runtime`. Compile
`console/src/api/workspace-client.ts` and
`console/src/domain/workspace-directory.ts` with ES2022 output into a fresh
directory; copy the versioned `node-client-driver.mjs` there as `driver.mjs` and
write `{"type":"module"}` to that directory's `package.json`. Set
`MIXER_WORKSPACE_HTTP_NODE_DRIVER` to its absolute `driver.mjs` path. Both inputs are
required; missing fixture configuration fails instead of silently skipping a gate.
The focused collector performs those steps itself.

Run the bounded host integration with:

```sh
python3 verification/hosted-customer-workspace-http-integration/run.py
```

The first attempt stopped on an unused-variable cold-compile warning before any
PostgreSQL/listener resources started. Attempt two found that the production JWT
verifier filtered out the new workspace scope: the actual console/Phoenix join
returned 403 for a workspace-scope-only signed bearer. That attempt also exposed a
fixture-only header-tuple evidence encoding failure. The identity owner added the
exact new scope to the existing allowlist and independently tested real signed
JWT positive/negative controls; the fixture now preserves headers as JSON pairs.
Each attempt retains its own failure or
success output and hashes; later success does not rewrite earlier evidence.
Cleanup requires the endpoint, default Repo, KeyOwner, JWKS worker supervisor,
TLS fixture and PostgreSQL to stop, both HTTP/TLS ports to close, application
environment restoration, TLS key-directory removal and scratch-directory removal.

This is host-only synthetic evidence. It does not qualify a production identity
provider, public DNS, TLS PostgreSQL/Neon, Cloudflare deployment, login, publication,
full artifact regression, native runtime/device/store/compiler behavior, GA, or
immutable published FieldLog packages from a separate repository. Native runtime
and capture tests remain paused; those checks remain pending.

## Observed host result

`verification/hosted-customer-workspace-http-integration/attempts/host-4/receipt.json`
is the successful receipt at source revision
`6ed7df4f147b3a3254dab91dd3224b9513f586a8` plus its explicitly staged working-tree
inputs, SHA-256
`aff0e5b7b3944804c8b5512ff6b453e222a79fe90f374deebe6ddca552b5d7e2`.
Elixir 1.20.4 / OTP 29, PostgreSQL 17.11, Node 22.23.3 and TypeScript 5.9.3 ran
11/11 tests with zero skips/exclusions and empty compile/runtime warning lists.
The fixture captured 65 complete socket requests: 25 success, 19 invalid request,
6 unauthenticated, 4 forbidden, 6 not found, 1 unsupported encoding and 4 unavailable.
The console client separately traversed four organization pages and three special-ID
project lookups, then rejected the foreign organization and absent local session.

Seven HEAD responses (200, 401, 404 and 503) had zero wire-body bytes. Workspace
scope alone received artifact/audit 403 responses in 2 ms and 0 ms respectively
with bodies withheld. The actual default Repo backend was terminated after the
final local read and before commit: the response was generic 503 with no page,
and a fresh request succeeded. The expected Postgrex disconnect appears in the
test log; it is the asserted fault injection.

All owned resource cleanup checks passed. The independent identity observation
records one TLS JWKS request with `jwks.fixture.invalid` SNI and `GET /keys`.
The cleanup callback's JWKS request count is null because ExUnit had already
stopped that supervised process; it is not interpreted as a zero-request result.
Attempt three stopped on formatting before resource startup. All earlier attempts
remain preserved. `verification/hosted-customer-workspace-http-integration/seal.json`
binds this final explanatory document and the complete attempt evidence; only the
document's result section was added after the successful runtime snapshot.
