# Independent browser authentication prerequisite review

Observed 2026-10-25. No actionable defect was found in the reviewed prerequisite
scope. This is acceptance evidence for the ordinary configuration/protocol helpers
and console transport refactor. It does not qualify a working browser login,
customer deployment, durable session, provider, native runtime or GA gate.

## Bound source and command

Run the isolated review with:

```sh
python3 verification/browser-auth-prerequisite-review/run.py
```

The passed attempt is
`verification/browser-auth-prerequisite-review/attempts/20261025T151247634284Z/receipt.json`.
Its revision is `f2aba240ebdecae1c810f50528f0ed4ed6245be1`; its selected source tree
digest is `f0dcca75a286d8dfba78408b1ea00c033aeb942f0143c05c18f154055576da01`.
The receipt records each exact argument vector, output digest, tool output and
dependency BEAM digest. It checks source and dependency stability before reporting
success and removes the owned compilation directory in `finally`.

| Frozen product source | SHA-256 |
| --- | --- |
| `console/src/api/cookie-workspace-client.ts` | `696a7598780736d23703adf2c1e9d182fd92227c18826c3198100700b131dff2` |
| `console/src/api/workspace-transport.ts` | `c349d8ec732e8f70c880619a0d512cf3987bdcd74167ccf9d1fd6beca1d29d2b` |
| `console/src/api/workspace-client.ts` | `3153e7cb96dc483acde37e80f9c640ed693eda7c9a892c49858689386099433e` |
| `console/src/domain/workspace-directory.ts` | `ee23d78e263ead8fe9d3c5b68c88f44e9a5d9a8b2a20fe709db9ab8fe6c8f4dc` |
| `hosted/lib/mixer_hosted/browser_auth/config.ex` | `9904a83c79c5de50ab800d1443fdb6ee1c5ed03eda981ea85852e8c65e9bd8d2` |
| `hosted/lib/mixer_hosted/browser_auth/protocol.ex` | `a569cabebfd905f1f717137b9180ff5ae47fffb747a9b5e45f049f03b3da3428` |

The Elixir compiler receives only those two browser modules and these four
explicit existing identity helpers: `Encoding`, `BoundedJSON`, `Manifest` and
`StartupConfig`. The existing pinned Jason BEAMs are the only external application
code loaded. No whole-app Mix compilation, application startup or broad hosted
runner is used. The frozen catalog-inspector, authority-driver and rejected
outbound Worker transport lanes were not read, imported, compiled or executed.

## Results

| Independent check | Observed result |
| --- | --- |
| Strict selected TypeScript compilation | Passed |
| Adversarial transport tests | 15 passed, 0 failures, 0 skips |
| Selected Elixir compilation with warnings as errors | Passed |
| Adversarial protocol/configuration tests | 15 passed, 0 failures, 0 skips/exclusions |
| Selected source/dependency stability | Passed |
| Owned temporary compilation cleanup | Removed |

These 30 independent tests are separate from the producer's 112 complete console
host tests/build and 39 protocol tests. Those producer counts are not rerun or
added to this independent count.

The transport probes cover mixed URL/query/fragment identifier attacks, endpoint
and credential option rejection before getter evaluation, configuration mutation,
concurrent tenant responses arriving out of order, mixed/duplicate foreign rows,
per-request cancellation isolation, reentrant abort inside fetch, late responses,
stalled bodies, noncooperative cancellation, status mapping, dishonest length
metadata, invalid UTF-8, stream read bounds and private thrown text. They confirm
that the cookie adapter uses fixed relative paths and `same-origin` credentials
without a bearer header. Shared error instances remain compatible with the
existing exported class. The bearer adapter still resolves the current token for
each request and uses `omit`; a token arriving after cancellation cannot reach
fetch.

The protocol probes cover exact trust-profile matching, malformed/duplicate owner
options, canonical endpoint aliases, duplicate/escaped JSON keys, unknown secret
or return-route choices, canonical token unused bits, the fixed authorization
query and independently derived SHA-256 PKCE, callback permutations, single form
decoding, duplicate/encoded parameter aliases, issuer mismatches, mixed code/error
callbacks, field/body limits, raw duplicate headers, header structure/aggregate
bounds, cookie ambiguity, exact Origin/CSRF and cookie lifetime/flags.

Provider-error callbacks retain the validated canonical state and exact configured
issuer and return only `{:error, :provider_rejected}` as the outcome. Arbitrary
provider metadata is discarded. This supports a future durable owner consuming
failed callbacks; the parser itself does not claim or consume them.

## Limits and continuation requirements

`Config` and `Protocol` take trusted restart-scoped configuration. Protocol callers
must pass the validated constructor output; an arbitrary caller-created struct
does not represent configuration validation. Endpoint syntax validation is not
DNS, peer-address, TLS or provider qualification. CSRF verification requires its
expected token to come from the current loaded server session; checking the
canonical cookie shape alone does not establish that session binding.

Browser HttpOnly/Secure/SameSite enforcement, Host/Origin ingress composition,
HTTP route/method/body/cache/logging behavior, provider transport and OIDC ID-token
verification, OIDC/API subject binding, durable one-use state and browser epochs,
replay/expiry/logout, encrypted credential custody and lifecycle writing remain
pending. No production routes or session integration were added by this review.
The fixed cookie transport is not installed into a live authenticated console.

Computer use, screen capture, browser automation, native simulators/emulators and
physical phones remained paused. No provider/database/network service, native
instance or capture process was started, and other projects' processes were not
changed. These host checks cannot satisfy their eventual device/browser or GA
acceptance requirements.

One initial read-only exploratory command used the nonexistent
`hosted/lib/mixer_hosted/authentication/startup_config.ex` path and exited 1. The
correct `identity/startup_config.ex` path was then used. The executable review had
no failed command or test. No producer source, commit or push was changed.
