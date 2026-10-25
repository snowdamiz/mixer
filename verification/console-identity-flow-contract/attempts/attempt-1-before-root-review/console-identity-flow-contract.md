# Proposed console login and session contract

Status: proposed contract pending root review. This W11/W14 dependency design
extends product-plan §§13 and 17; it is not an implemented login, provider choice,
deployment or GA pass. The initial executable product slice is interactive OIDC
code flow, a bounded session, workspace reads and local logout. It does not replace
the remaining smooth session, SSO, onboarding or commercial workflows.

## Current boundary and proposed decision

The ordinary API admits only an Authorization bearer through `BearerIdentity`.
`AccessTokenVerifier` currently accepts configured RS256 RFC 9068 access tokens,
maps `jti` to `VerifiedIdentity.credential_ref`, and caps human token lifetime at
900 seconds. `Session.prepare_identity!/2` locks profile → principal → family →
credential and resolves existing bindings; it creates no authorization Context.
Workspace facades then check current state and membership for every page. The
existing browser-compatible bearer `WorkspaceClient` resolves an in-memory token
per request and uses `credentials: "omit"`. Preserve those public contracts.

Propose a **same-origin Phoenix confidential OAuth client and browser session**.
The browser receives an opaque cookie, safe session metadata and a ready
`WorkspaceClient` capability. Provider tokens remain on the server. Add a distinct
cookie-session transport implementing the existing `WorkspaceClient` interface;
do not change the bearer client's cookie or token contract. App/controller code
receives `ready(client)`, `unauthenticated`, or `unavailable`; it never accepts raw
credentials. Root owns that integration and the session-change cancellation seam.

This custody choice is a Mixer design inference, not a claim that an OAuth standard
requires a server session. The standards require particular protocol protections:
use authorization code, exact registered redirects and PKCE rather than implicit
token delivery. Mixer requires S256 PKCE even for its confidential client.
[OAuth Security BCP §§2.1, 4.1, 4.5](https://www.rfc-editor.org/rfc/rfc9700.html),
[PKCE §§4, 7.1](https://www.rfc-editor.org/rfc/rfc7636.html).

## Origin, routes and ordinary API composition

Use one operator-configured HTTPS origin, illustrated only as
`https://console.example.invalid`. Static console assets remain on Workers Static
Assets. Ingress routes `/auth/*` and `/console-api/*` to Phoenix before SPA fallback;
it passes cookies only to those routes and never performs identity conversion.
The public API's `/v3/*` routes retain their existing header-only authentication.
No secret, session, response or Set-Cookie may enter the static/CDN cache.

The new server workspace adapter has exactly two fixed destinations:

| Browser route | Ordinary customer operation |
| --- | --- |
| `GET /console-api/v1/orgs` | `GET /v3/orgs` |
| `GET /console-api/v1/projects` | `GET /v3/projects` |

It rejects a browser Authorization header and any destination/actor/header override,
copies only the already bounded workspace query, obtains the session's stored
provider access token, and invokes the **ordinary protected request pipeline**
with exactly that bearer. A small internal dispatcher may reuse the ordinary Plug
pipeline without a network hop; tests must prove its path, method, verifier,
default Repo and response validation equal the real `/v3` route. It must not call a
facade using an ID-token identity, an earlier `VerifiedIdentity`, a cached role or
linkage returned by `prepare_identity!`. Do not add cookie handling to
`BearerIdentity`. If an internal dispatcher cannot preserve this boundary, use a
fixed trusted server-to-server origin with verified TLS and redirects forbidden;
that transport requires a separate bounded implementation/review, not a generic
HTTP proxy or reuse of frozen outbound lanes. All ordinary response limits,
no-store behavior, HEAD semantics and error categories remain applicable.

The browser adapter uses relative fixed URLs, `credentials: "same-origin"`,
`redirect: "error"`, `cache: "no-store"` and `referrerPolicy: "no-referrer"`.
It preserves the existing page parser, 256-KiB/4,096-chunk bounds, deadline and
cancellation semantics. A cross-origin API deployment is not selected here:
these cookie routes emit no Access-Control-Allow-Origin or credential permission.
Do not enable wildcard or reflected CORS to make a deployment work. A future
direct browser bearer deployment needs an explicit exact-origin preflight policy
and provider token-endpoint compatibility review. Origin means scheme, host and
port, not merely sibling domains. [RFC 6454 §§3–4](https://www.rfc-editor.org/rfc/rfc6454.html#section-3).

## Proposed closed HTTP contract

All JSON below is illustrative data with no real provider or credential.
Errors use fixed codes, sanitized request IDs and no provider response text.

| Endpoint | Request and result |
| --- | --- |
| `GET /auth/session` | Empty body/query. Creates or reuses a bounded pre-auth session when absent. `200 {"state":"unauthenticated","csrf_token":"…"}` or `200 {"state":"authenticated","generation":"…","expires_at":1234567890,"csrf_token":"…"}`. Closed keys, no bearer, ID/refresh token, issuer subject, principal ID, roles or membership. Readiness requires fresh current profile/principal/family/credential admission; never implies tenant access. Dependency failures return `503 identity_unavailable` or `authorization_unavailable`, distinct from sign-out. |
| `POST /auth/login` | Exact same-origin Origin plus synchronizer CSRF header; JSON exactly `{"return_route":"workspace"}`. Bounded authenticated/pre-auth session. Creates one transaction and returns `200 {"authorization_url":"https://configured-provider.invalid/…"}`; browser performs a top-level navigation. The URL contains only configured authorization parameters and transient state/nonce/challenge. Replaces any earlier pending login for that browser; no supplied URL, issuer, client, audience, scope, tenant or `return_to`. |
| `GET /auth/callback` | Top-level query-mode redirect to the exact registered URI. No body. Strictly parse one `state`, one `iss`, and either one `code` or one `error`; bounded optional `error_description`/`error_uri` are discarded. Duplicate/escaped-equivalent/unknown parameters reject. Require matching browser cookie, live transaction and expected issuer before exchange. Consume once, admit credentials and rotate session, then `303 /console/`. Failure redirects only to fixed `/console/login` with a bounded non-secret status; never copies provider query/text. |
| `POST /auth/logout` | Empty JSON object, exact Origin, session-bound CSRF. Atomically revoke the local browser session/family and invalidate pending callbacks/refreshes before success. Clear cookie; `204`. Repeating logout under a new valid pre-auth session is harmless. Database unavailability is `503`; client discards visible private state immediately and retains a visible pending/retry state until server revocation is confirmed. |
| `POST /auth/refresh` | Not registered in the initial product slice. No offline_access request or refresh token retention. Add only after the later refresh contract below is implemented and qualified. |

Every auth/session response and redirect carries `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`. Callback handling has no third-party assets;
ingress/application logs redact its query before recording a request. No error
includes the authorization URL, code, state, nonce, cookie or raw provider body.
All non-callback requests reject ambiguous content, duplicate session cookies,
unexpected query/body fields and alternate methods with bounded errors. Initial
limits: callback raw query 8,192 bytes, code 4,096 bytes, state/nonce 43 base64url
characters, CSRF 43 base64url characters, session JSON 4 KiB and response 8 KiB.
Use the ordinary duplicate-aware bounded JSON/query helpers where applicable.
Provider token response: maximum 32 KiB, bounded JSON/depth, 10-second total
deadline and no redirects/decompression; access token still fits the existing
4,089-byte admission limit. These are proposed Mixer limits and need real adapter
compatibility tests. A failure returns no authenticated cookie.

Rate-limit pre-auth creation, login starts, callback claims and failed CSRF by
bounded trusted-ingress/browser keys; do not retain attacker-controlled labels.
Expired/superseded transactions have a finite retention/cleanup bound. Pre-auth
cookies and pending sessions expire within 300 seconds; a successful session's
cookie lifetime cannot exceed the token-backed session deadline.

## Configuration and login transaction

Add separate API-role-only login configuration; do not widen the existing
`MIXER_IDENTITY_CONFIG` schema or infer endpoints by discovery per request.
Mode defaults to disabled and disabled plus stray settings rejects startup.
Public bundle configuration contains only the fixed relative route version and
safe enabled/disabled capability. No Vite environment variable contains a secret.

| Trusted server field | Proposed validation |
| --- | --- |
| `version`, `mode`, `public_origin` | Version 1, `disabled`/`configured`, one canonical HTTPS origin with no credentials/path/query/fragment; must match trusted ingress/Host allowlist. Never derive callbacks from request forwarding headers. |
| `profile_id`, `profile_version`, `issuer`, `client_id`, `api_audience` | Exact currently enabled human trust profile and configured identity binding. Initial slice supports one profile/client. The OAuth client must match the API token's configured client. |
| `authorization_endpoint`, `token_endpoint`, `id_token_jwks_endpoint` | Explicit reviewed HTTPS endpoints with exact host/port/path, no redirect or token-derived destination. Separate ID-token key/algorithm validation from RFC 9068 API access-token validation. Existing startup's JWKS restrictions remain unchanged. Any new fetch client needs its own bounded transport acceptance. |
| `redirect_uri`, `return_routes` | Exact `public_origin + /auth/callback`; registered byte-for-byte. Only `workspace → /console/` initially. Return-route changes are reviewed configuration, never arbitrary URL parsing. |
| `client_auth_method`, `client_credential_ref` | Reviewed confidential-client authentication and secret-manager reference. No production method/provider/key selected by this document. Credential availability is a startup/deployment prerequisite; never browser assets, build workers or logs. |
| `scope`, `response_mode`, `response_iss_required` | Initially exactly `openid mixer.workspace.read`, query mode, and true. Provider must issue the configured API-audience access token; a provider-specific audience parameter requires a reviewed adapter, not arbitrary passthrough. No email/profile/groups/offline_access request. |
| `session_vault_ref`, `cookie_policy`, `timeouts` | Separate durable server session store with encrypted confidential token custody and controlled key access; immutable policy validated before HTTP starts. Initial session lifetime cannot exceed admitted access-token expiry; transaction lifetime 300 seconds, session idle bound 900 seconds. No environment reload per request. |

Create independent 32-random-byte state, nonce, verifier and browser-session IDs
using the platform CSPRNG; verifier is base64url and challenge is
`BASE64URL(SHA256(ASCII(verifier)))`. Keep the verifier server-side. Store a state
digest, browser-session digest/epoch, expected issuer/profile/version/client,
nonce digest, verifier, exact redirect, allowed return-route enum and expiry.
Protect secret fields in the separate short-lived vault. One atomic transaction
claim consumes the state and checks the initiating browser epoch. A second
callback or another browser cannot claim it. Logout, replacement login, expiry,
issuer disable and configuration change invalidate it. Never hold authorization
database locks during provider network requests. Exchange only the claimed code
using that transaction's verifier/redirect and configured client authentication.
An ambiguous network result requires a new login; do not automatically replay a
possibly consumed code.

Validate the ID token using separate OIDC rules: signature/allowed algorithm,
exact issuer, client audience/authorized-party semantics, expiry/issued-at and
the transaction nonce; apply required authentication freshness. Verify the API
access token separately through `ConfiguredVerifier`. Do not send an ID token as
API bearer. The provider adapter must establish the documented exact relationship
between OIDC `(issuer, subject, client)` and the verified API token's subject/client;
if those subjects differ, an explicit qualified stable binding is mandatory.
Email/name/domain matching cannot link them. [OIDC Core §§3.1.3.7, 5.7, 8](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation),
[JWT access-token profile §4](https://www.rfc-editor.org/rfc/rfc9068.html#section-4).
The required authorization-response `iss` is compared to the saved issuer before
using any code, including error responses. [RFC 9207 §2.4](https://www.rfc-editor.org/rfc/rfc9207.html#section-2.4).

## Cookie custody, CSRF and session change

Proposed cookie: `__Host-mixer-session=<opaque random id>; Path=/; Secure;
HttpOnly; SameSite=Lax`, with no Domain and a bounded lifetime. Rotate the ID on
successful authentication; revoke the pre-auth ID so session fixation fails.
Store only a digest as the lookup key. Callback query mode permits the browser's
top-level return; form_post is outside this first adapter. Secure/HttpOnly alone
do not make a cookie an authorization proof. RFC 6265 describes those attributes;
SameSite and `__Host-` semantics are in the HTTPWG cookie specification, currently
**work in progress**, not a final RFC. [RFC 6265 §4.1.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-4.1.2),
[HTTPWG cookie draft §§4.1.2.7, 4.1.3.2](https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html).

Use a server-bound synchronizer token returned by `/auth/session`; POST requests
must present it in `X-Mixer-CSRF` and an exact `Origin` equal to public_origin.
Reject absent/null/foreign Origin and duplicate headers. A same-site sibling
origin is still foreign. No state-changing GET except the one-time OAuth callback;
that callback instead requires state, browser binding, PKCE, nonce and issuer.
SameSite is an extra layer, not the CSRF check. Cookie routes reject an incoming
Authorization header rather than selecting between competing identities.

Session metadata and CSRF exist only in memory; no bearer/refresh/ID token in
localStorage, sessionStorage, IndexedDB, URLs, telemetry, HTML, worker messages,
service-worker cache or client diagnostics. The opaque HttpOnly cookie is the
browser's only persistent credential. Raw provider tokens live only in the
separate confidential session vault, never `mixer_authz_credentials`, audit rows,
Oban args, source/build outputs or browser JSON. CSP and script/HTML escaping
still require deployment review: an injected same-origin script could perform
session-authorized requests even without reading the cookie.

Each changed session generation, expiry, login, logout or failed current-session
check invalidates all App/controller requests, selections, pages and cursors
before installing a replacement client. Token/session rotation also changes the
generation, even for the same person. Reject late results by captured generation
as well as cancellation. Poll/revalidate on foreground and before accepting a
fresh client; cross-tab notification carries only an invalidation signal, never
credentials or permission. Other tabs must re-read server state. Backend checks
remain decisive between client revalidations. An unavailable check clears private
views and displays retry; it must not show an empty workspace or retain an allow.

## Lifecycle prerequisite, expiry and logout

Login success requires an existing exact profile/issuer/subject/client binding to
an active internal human principal, and an admitted provider `jti` registered in
`mixer_authz_credentials` under a server-owned session-family. The browser cannot
supply the principal, family, credential reference, membership, role or grant.
Unknown identity is an explicit onboarding/invitation requirement, not first-user
owner creation. No membership is inferred from a valid token or an email domain.
The lifecycle writer generates a new non-recycled family ID for each new browser
login; a token's optional `sid` or other arbitrary claim cannot select the family.

**Blocking implementation dependency:** no reviewed ordinary runtime writer yet
exists for these identity/family/credential lifecycle operations. Add a narrowly
privileged controlled writer with exact inputs derived from independently
validated provider evidence; serialize profile → principal → family → credential
and any affected tenant heads, re-read fresh state and commit audit atomically.
Do not grant the read/API login blanket authorization-table DML, disable RLS, use
the migration owner at runtime, or call a test fixture to provision customers.
The browser vault row and family registration need an explicit durable pending →
active protocol so partial commits cannot expose a usable authenticated cookie.
No cookie is returned before all required current state is active. Abandoned
pending rows expire; cleanup preserves audit/revocation meaning. Invitation
acceptance, identity linking, organization bootstrap, owner transfer/deletion,
member writers and SSO/SCIM deprovisioning remain separate audited workflows.
Replacing an authenticated browser session must revoke its previous local family
as part of the activation protocol; callback success cannot leave the replaced
family silently reusable. A failed replacement never grants a new family.

Initial sessions expire at the earliest access-token expiry, family/principal/
profile expiry or 900-second idle bound. Treat `now >= expires_at` as expired;
never extend API token lifetime from a cookie or ID token. Current verifier's
30-second future iat/nbf allowance remains as implemented; no expiry grace is
introduced. Expiry presents sign-in again; a new code flow may use an existing
provider session but must still create fresh state/nonce/PKCE and re-admit current
Mixer identity. No hidden iframe/silent-login loop. Database/verifier outage is
unavailable, not confirmation that the account logged out.

Local logout's success means durable browser-session/family revocation, including
every admitted token reference in that family, under the same lock protocol used
by ordinary requests. Expire the cookie after confirmed revocation; on `503`, the
client retains it to retry logout but clears its ready capability and private
view. The server may still admit that credential until revocation is confirmed;
an unconfirmed logout cannot be reported as succeeded. It is not a claim of global
provider logout. A callback
already doing network work and any future refresh must compare the saved browser
epoch/family revision at final commit; logout wins and returned tokens are
discarded if the epoch changed. An already-authorized operation may finish before
revocation returns; do not promise retroactive cancellation. Provider revocation
and RP-initiated logout are later adapter capabilities: follow their registered
endpoints/redirects and report local versus provider completion separately.
[OAuth revocation §2](https://www.rfc-editor.org/rfc/rfc7009.html#section-2),
[OIDC RP-Initiated Logout §2](https://openid.net/specs/openid-connect-rpinitiated-1_0.html#RPLogout).

Later refresh requires explicit provider qualification and encrypted server-side
refresh custody. Serialize one refresh per family using a bounded lease; perform
provider I/O outside authz locks. Admit the new token through the same verifier,
require the same binding/client/resource and no expanded scope, register its new
`jti` under the same live family, and atomically replace the vault generation only
if epoch/revision still matches. Rotation/reuse behavior must match the provider;
ambiguous or failed refresh cannot resurrect a logged-out family. Revoke/deny the
family on reuse/invalid_grant, retain durable revocation for pending work, and
force interactive login on expired consent or required interaction. Refresh is
not implied by OIDC login and cannot be assumed to exist. [OAuth Security BCP §4.14](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14).

## Locally executable follow-up and evidence

The standard-library model in `verification/console-identity-flow-contract/`
executes the RFC PKCE vector and proposed one-time transaction/browser-epoch
rules, including concurrent claim, expiry and logout/replacement races. It is a
design specimen, not product cryptographic admission,
Phoenix/PostgreSQL integration or a simulated successful customer login. Run:

```sh
python3 verification/console-identity-flow-contract/run.py
```

Next product work must separately implement and test: (1) disabled/configured
startup and the pure transaction owner; (2) controlled lifecycle writers with real
PostgreSQL lock/revocation/adversarial tests; (3) actual Phoenix `/auth` endpoints
with an independently authored loopback synthetic OIDC server and signed fixtures;
(4) the fixed ordinary-API dispatcher and additive cookie `WorkspaceClient`;
(5) host App/session integration, then browser/security/deployment qualification
when computer use resumes. The fixture cannot become a production issuer or
replace qualified provider credentials. Pin any selected authentication/transport
dependency and license in `THIRD_PARTY.yml` before product implementation.

Required negative cases: callback replay/cross-browser/missing or duplicate state,
issuer mix-up, wrong redirect/client/nonce/audience/type/algorithm/signature,
expired code/token/transaction, token response errors or excess bounds, unknown
binding/jti, inactive/changed profile/principal/family/credential, membership
removal, no-membership empty page, logout versus callback/refresh in both orders,
Origin/CSRF/header/cookie ambiguity, open redirects, arbitrary relay destination,
edge cache isolation, no raw query/token logging, restart/multiple-replica claim
races and response failure after durable commit. Actual deployed cookie/CORS/
redirect/SSO behavior, provider incident/logout propagation, customer acceptance,
FieldLog immutable published-package consumption and G22/G24 stay pending.
Computer use, capture, native simulator/emulator and phones remain paused; this
slice starts none. No production publication, credentials, migration, signing,
store, customer message or frozen-lane execution is authorized or performed.
