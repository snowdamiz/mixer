# Browser authentication protocol primitives

Status: implemented local component prerequisite for W11/W14, pending root review.
This is independently authored product Elixir code in
`MixerHosted.BrowserAuth.Config` and `MixerHosted.BrowserAuth.Protocol`, extending
the [proposed identity flow](console-identity-flow-contract.md). No login endpoint,
provider selection, provider request, application startup change, identity writer,
session vault, or authenticated customer login is implemented by this slice.
The existing bearer transport and identity startup schema are unchanged.

## Public boundary

| Function | Result and responsibility |
| --- | --- |
| `Config.load(env, role, identity_startup_config)` | `{:ok, %Config{}}` or `{:error, fixed_atom}`. Pure; never reads or reloads the process environment, resolves secrets, or starts a child. |
| `Protocol.random_token()` | Canonical unpadded 43-character Base64URL of 32 platform-CSPRNG bytes. Call independently for state, nonce, PKCE verifier, browser ID and CSRF. No injected RNG. |
| `Protocol.token?(value)` | Exact 32-byte canonical encoding check, including unused trailing bits. |
| `Protocol.digest(token)` | Canonical 43-character SHA-256 digest of the token's ASCII bytes, or `{:error, :invalid_token}`. Durable transaction/session owners store the digest lookup key, not the raw cookie or state. |
| `Protocol.pkce_challenge(verifier)` | `{:ok, challenge}` or `{:error, :invalid_token}`. Implements S256 only. |
| `Protocol.authorization_url(config, %{state: ..., nonce: ..., verifier: ...})` | `{:ok, url}` or `{:error, :invalid_request}`. Fixed code/query/openid/workspace-read/S256 request. No caller-supplied issuer, audience, scope, redirect, prompt or return destination. |
| `Protocol.session_cookie(token, max_age)` | `{:ok, set_cookie_value}` or fixed error. Owner must first cap `max_age` to the admitted deadline; 1 through 900 seconds accepted, pre-auth owner must cap at 300. |
| `Protocol.clear_cookie()` | Fixed cookie deletion string; may be sent only after confirmed durable logout/revocation. |
| `Protocol.parse_session_cookie(raw_headers)` | `{:ok, token_or_nil}` or `{:error, :invalid_request}`. Preserve raw duplicate header pairs; do not pass a map or pre-collapsed cookie projection. |
| `Protocol.verify_csrf(config, raw_headers, expected_token)` | `:ok` or `{:error, :invalid_csrf}`. Requires one canonical session cookie, exact configured Origin and one canonical `X-Mixer-CSRF`, compared with OTP `:crypto.hash_equals/2`. The expected token must be loaded from that current server session. |
| `Protocol.parse_callback(config, raw_query, raw_body \\ "")` | `{:ok, %{state: state, issuer: issuer, outcome: {:code, code} \| {:error, :provider_rejected}}}` or `{:error, :invalid_callback}`. Successful parsing does not authenticate, claim, or authorize anything. |

Only a constructor-validated trusted `%Config{}` may enter these functions.
The future HTTP layer must enforce the exact method, route, trusted Host/ingress
origin, body and content-type rules before using the helpers; the query parser
does not determine whether an HTTP request used GET. Bodies are rejected by the
callback primitive. The login body enum, session/logout JSON, response JSON,
response headers, cache isolation and HTTP error mapping remain HTTP-layer work.

## Closed configuration

`MIXER_BROWSER_AUTH_MODE` is absent/`disabled` or exactly `configured`.
Disabled with any `MIXER_BROWSER_AUTH_CONFIG` key, including nil/empty, rejects.
Configured is API-only and requires the existing configured
`Identity.StartupConfig`: revalidate its manifest, require its binding to match,
and require the profile to be enabled and human. The profile ID/version, issuer,
OAuth client ID and API audience must match exactly. No identity is provisioned.
The root still owns runtime wiring: these environment names are an input contract,
not currently active environment settings.

Configured JSON is at most 16,384 bytes and contains exactly these 17 fields:

| Field | Validation |
| --- | --- |
| `version` | Integer 1. |
| `public_origin` | Canonical `https://` lower-case DNS host, default port, no explicit port, userinfo, path, query or fragment. At least two host labels; no IP address, trailing dot, Unicode or percent encoding. |
| `profile_id`, `profile_version`, `issuer`, `client_id`, `api_audience` | Exact active bound human trust values, integer profile version. Issuer is canonical HTTPS with optional literal safe path. |
| `authorization_endpoint`, `token_endpoint`, `id_token_jwks_endpoint` | Explicit canonical HTTPS DNS-host URL with path, default port, no query, fragment or credentials. Non-root path segments contain only ASCII alphanumeric or `-._~`; no empty/dot segments, percent encoding, duplicate slash or trailing slash. This narrow first-adapter policy needs provider compatibility qualification. |
| `redirect_uri` | Exact `public_origin + /auth/callback`. |
| `client_auth_method` | Exactly `client_secret_basic`, the only declared generic confidential method in this component. Token exchange is unimplemented; no production provider or client has been selected. Other methods require separately reviewed code and qualification. |
| `client_credential_ref` | `secret://` plus bounded safe reference segments, at most 256 bytes total. No raw secret field. |
| `session_vault_ref` | `vault://` plus bounded safe reference segments, at most 256 bytes total. No vault key field. |
| `scope` | Exactly `openid mixer.workspace.read`; no `offline_access`, identity-profile or other scopes. |
| `response_mode`, `response_iss_required` | Exactly `query` and JSON true. |

The already accepted `Identity.BoundedJSON` rejects duplicate/escaped-equivalent
object keys and unknown fields fail the whole configuration. Its byte-before-decode,
depth/container checks are reused; this is not streaming JSON preallocation
enforcement. Configuration errors are fixed atoms. Inspect exposes only the mode.
No reference resolution occurs; syntax validation does not prove a secret store,
encrypted vault, credential or provider exists.

The return path is fixed `/workspace`; failure path is fixed `/login`. Neither is
an input JSON field. The console already has `/workspace`; the future HTTP/console
implementation still needs to add `/login`. Transaction lifetime is fixed at 300
seconds and session idle cap at 900. Those constants do not enforce durable expiry.

## Parsing and confidentiality

Header parsing walks at most 64 raw pairs and 16,384 aggregate name/value bytes;
names are 1 through 128 ASCII letters/digits/hyphens and values at most 8,192
printable ASCII bytes. Names compare case-insensitively. Every repeated name,
any Authorization header (even empty), control character, malformed tuple, map,
improper list or excess bound rejects. This intentionally strict first-adapter
policy also rejects repeated unrelated headers; ingress compatibility remains to
be qualified without collapsing sensitive duplicates before this check.

At most one Cookie header, 8,192 bytes and 32 semicolon-separated pairs are parsed.
Pairs permit only surrounding ASCII spaces; names are ASCII alphanumeric,
hyphen or underscore. Percent-encoded names, duplicate names, quotes, malformed
delimiters, controls and noncanonical session values reject. Other accepted cookie
values follow cookie-octet ranges; the session cookie requires the canonical token.
Unrelated accepted cookies are ignored after checking duplicates. Cookie names are
case-sensitive. `__Host-mixer-session` is emitted with `Path=/; Secure; HttpOnly;
SameSite=Lax` and `Max-Age`, never Domain. Cookie production does not grant authority.

Callbacks accept at most 8,192 raw bytes, six recognized key slots, a 4,096-byte
decoded code, 2,048-byte issuer, 43-byte canonical state, 128-byte error name,
1,024-byte error description and 2,048-byte error URI. Each pair is visited once;
each value has at most one bounded percent/form decode. Encoded values are bounded
to three times their decoded field limit and the whole-query limit still wins.
Parameter names are exact ASCII literals: percent-encoded key aliases, duplicates,
unknown names, empty pairs and alternate separators reject. State is canonical in
the raw query too, so percent/plus aliases cannot select the same transaction.
Malformed percent sequences, non-ASCII, controls and raw fragment/semicolon/HTML
delimiters reject. Encoded printable bytes inside an opaque code remain literal
decoded bytes, including an encoded percent sign; callers must never decode them
again. Query-order changes do not change accepted semantics.

Issuer is required and compared exactly to the configured issuer after one decode,
on both success and error. There must be exactly state, issuer and one code, or
state, issuer and one error with bounded optional description/URI. A code combined
with error metadata rejects. Provider errors return only the fixed
`:provider_rejected` outcome; error name, description and URI are discarded.
The validated state and issuer are retained specifically so the future durable
owner can match the browser/epoch and consume rejected callbacks too.

The owner must atomically claim state and the bound browser epoch, reject expiry,
replay, supersession and cross-browser access, and keep the verifier in its
short-lived encrypted custody. It must perform provider I/O outside authorization
locks. A parsed success has no claim or authorization power. Do not log callback
query, code, raw state, generated URL, nonce, verifier, CSRF, cookie or provider
response. Only fixed categories may enter public errors.

## Cryptography and evidence

No dependencies were added: Elixir/Erlang OTP and Jason are already recorded and
pinned in `THIRD_PARTY.yml`/the hosted lockfile. CSPRNG, SHA-256 and constant-time
comparison use platform `:crypto`. The S256 implementation and official test vector
are checked against [RFC 7636 §4 and Appendix B](https://www.rfc-editor.org/rfc/rfc7636.html).
Issuer-before-code/error admission follows
[RFC 9207 §2.4](https://www.rfc-editor.org/rfc/rfc9207.html#section-2.4).
The strict duplicate policy deliberately narrows the general response syntax in
[RFC 6749 §4.1.2](https://www.rfc-editor.org/rfc/rfc6749.html#section-4.1.2).
OTP supplies [the cryptographic operations](https://www.erlang.org/doc/apps/crypto/crypto.html).
This is protocol parsing and token generation, not an independently invented
cryptographic primitive or JWT verifier.

Run only this slice and its four explicit existing identity helpers:

```sh
python3 verification/hosted-browser-auth-protocol/run.py
```

The runner loads only pinned existing Jason dependency BEAMs, compiles the six
explicit source modules with warnings as errors into an owned temporary directory,
runs the two selected ExUnit files, records source/dependency digests, revision,
command/version/output and cleanup, then removes the owned build. It does not
compile or start the shared hosted application, use its broad test script, or
read/import/execute the frozen lanes. The first selected run passes 39 methods,
zero failures/skips; final receipts preserve actual subsequent results.

Provider transport and credentials, ID-token signature/algorithm/nonce/audience
validation, OIDC/API subject relationship, ordinary access-token admission,
durable claim/epochs/replay/logout, encrypted token vault and controlled lifecycle
writer, HTTP/console/ingress composition, provider/deployment qualification,
physical phones and all GA gates remain pending. Computer use, capture, browser,
native simulator/emulator and phones stayed paused; this slice starts none.
No production publication, customer message, migration or credential change occurs.
