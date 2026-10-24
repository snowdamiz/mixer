# Configured identity startup

This is the root-selected implementation contract for the next W11/W16 slice.
The accepted key-owner component at `dd604eca` is not yet started by the hosted
application. This slice connects explicit operator configuration to that existing
component. It adds no authenticated HTTP route, membership, permission, provider
selection, durable identity registry or GA acceptance.

## Configuration

`MIXER_IDENTITY_MODE` accepts exactly `disabled` or `configured`. Absence means
`disabled`, preserving the present liveness-only foundation. An invalid supplied
value fails startup. `MIXER_IDENTITY_CONFIG` is forbidden when disabled, including
when the mode is absent. A future protected route must fail unavailable when no
owner exists; disabled mode is never anonymous authorization.

Only the API role accepts configured identity. The processor must be disabled
and rejects supplied identity configuration. Configuration is loaded once before
application children start. Changes require a process restart; this slice exposes
no reload endpoint and does not read mutable environment settings per request.

Configured mode requires a JSON object in `MIXER_IDENTITY_CONFIG`, at most 65,536
UTF-8 bytes. It has exactly these fields:

| Field | Contract |
| --- | --- |
| `version` | Integer `1`. |
| `generation` | Integer `1...2147483647`; operator configuration revision, not token authority. |
| `binding` | Exact configured profile ID present in `profiles`. |
| `profiles` | One through eight complete entries, with no duplicate IDs. |
| `resolvers` | One through three distinct canonical IP address strings; port 53 is fixed. No hostnames, ports, search expansion or resolver discovery. |

Each profile entry has exactly `profile`, `jwks_endpoint`, `transport`. The
profile has the seven exact fields accepted by `Identity.Manifest`:
`profile_id`, `profile_version`, `issuer`, `audience`, `client_id`, `identity_class`
and `enabled`. The endpoint has exactly `host`, `port`, `path`; port is integer
443. Transport is literal `hosted_https`; identity class is `human` or `service`.
Map these known strings to already declared atoms with explicit clauses. Never
intern a configuration key or value. Apply the existing complete manifest
validation and limits after conversion. Unknown, missing, duplicate or escaped
duplicate JSON fields fail the whole configuration. Numbers must be integers;
no floating point coercion. Use the existing bounded JSON decoder; its decoded
depth/container checks are not a claim of streaming preallocation enforcement.

Resolver addresses must parse as an IPv4 or IPv6 tuple and round-trip exactly
through the platform address formatter. Explicit trusted recursive resolvers may
be private/loopback: their addresses are infrastructure configuration, distinct
from the JWKS endpoint. Existing production DNS and global-peer checks remain
mandatory for every JWKS connection. This slice does not expand their policy.

CA roots come from the same standard OTP CA source already loaded for verified
database TLS. Require a nonempty list of valid DER certificates; use ordinary
chain and hostname validation. No configuration field permits custom code,
module names, a test transport, disabling TLS checks, an injected snapshot, a
token-supplied issuer, or implicit OIDC discovery. The test harness may provide
synthetic roots to the pure configuration constructor; production runtime obtains
them only from the existing OTP source.

All configuration errors are fixed, bounded categories and do not interpolate
the JSON, profile data, paths, certificate bytes, environment map or secrets.
The resulting settings' Inspect representation must omit configuration contents.
There is no production log of bearer material or trust payloads.

## Application integration

Add a small `Identity.StartupConfig` module, a field on `RuntimeConfig`, its runtime
configuration binding and a third argument to the application child-selection
helper. Preserve the existing two-argument helper as an explicit disabled-mode
compatibility wrapper for existing callers. `Application.start/2` must use the
validated configured value, never that wrapper or a silent fallback.

In configured API mode, start the existing `KeyOwnerSupervisor` under its fixed
production owner name before the HTTP endpoint. Keep the accepted worker/owner
supervision, constructor validation, shutdown ownership and final verification
fences unchanged. Disabled API and processor modes start no identity child. A
bad required configuration or child startup fails the application before its
endpoint starts. An empty key cache is valid startup state; liveness remains
available, while identity remains unavailable until an admitted fetch installs
valid keys. This slice does not add proactive or unbounded refresh. The existing
configured adapter uses the existing owner and binding; it receives no route or
token-selected profile.

## Executable acceptance

| Case | Required observed evidence |
| --- | --- |
| IS01 | Existing defaults/role separation and missing foundation configuration behavior remain; disabled starts no owner and rejects stray identity configuration. |
| IS02 | Exact complete JSON conversion, both classes, IPv4/IPv6, disabled bound profile, one/eight profiles and one/three resolvers. Reject malformed, duplicate/escaped duplicate, missing/extra, wrong type, over-limit, absent binding, invalid endpoint and nonexistent/empty CA inputs without leaking values. |
| IS03 | Configured child ordering and actual supervised startup, owner registration, bounded empty initial state and zero startup fetches. Invalid required configuration cannot expose the endpoint. Production constructor rejects test-only options. |
| IS04 | Existing public `ConfiguredVerifier.authenticate/2` reaches the started configured owner. Disabled profile denies without transport. An isolated Linux namespace uses production DNS/HTTPS paths and synthetic CA material to exercise cold fetch and actual signed-token admission through the configured startup options. No real identity provider is contacted. |
| IS05 | Component shutdown/restart clears authority and retains accepted transport cleanup semantics. Any reused constructor/cleanup evidence is identified as reused; changed application wiring needs actual lifecycle checks. |
| IS06 | Full hosted tests, production release build, missing-config rejection, test-only export exclusion and exact source/dependency/output bindings. Preserve original failed attempts and clean only owned fixtures/containers/databases. |

Implement and test in an isolated overlay first. Root reviews the exact patch and
evidence before applying it. Existing accepted identity source and transport
policies, dependency pins, HTTP routes and migrations are outside this lane's
ownership. This contract does not accept startup behavior merely because a
child-spec list or configuration parser test passes.
