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
