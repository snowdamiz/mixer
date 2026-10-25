# Hosted bearer identity transport

`MixerHostedWeb.Plugs.BearerIdentity` is an ordinary Plug prerequisite for a
future protected Phoenix HTTP pipeline. Its default dependency is the existing
`MixerHosted.Identity.ConfiguredVerifier`, with actual Unix seconds. There is no
route, endpoint, application configuration, identity provider, database resolver,
authority driver or outbound Worker integration in this slice.

The full product scope remains `mixer-product-plan.md`. This component does not
complete customer authorization, tenant membership/RLS, provider login/SSO,
browser sessions or the console's live workflows. No frozen authority/catalog
or rejected outbound transport source, fixture or execution is used.

## Credential contract

The plug accepts exactly one `Authorization` field value of at most 4096 bytes.
It matches the Bearer scheme without case sensitivity, followed by one or more
ASCII spaces and a nonempty token of at most 4089 bytes. It applies the RFC 6750
token alphabet and trailing-padding grammar, then passes the exact token bytes
to `authenticate/2`. It never trims, decodes or rewrites the token. Tabs, control
bytes, commas, multiple credentials, misplaced padding and unsupported schemes
are `400 invalid_request`. Identical duplicate fields also reject.

[RFC 6750 §§2–3](https://www.rfc-editor.org/rfc/rfc6750.html#section-2) supplies the
Bearer grammar, prohibition on combining token transmission methods, and
invalid-request/invalid-token challenge semantics.
[RFC 9110 §11.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-11.1) defines
case-insensitive authentication scheme matching. This implementation's strict
400 response for unsupported schemes follows Mixer's existing identity
contract; it does not claim every OAuth resource server must make that choice.
These specifications were checked against their primary publications during
implementation. Plug APIs were checked against pinned local Plug 1.20.3 source.

## Alternative-input policy

These are explicit constraints for this JSON-oriented protected API pipeline,
not universal OAuth requirements:

- Before invoking the verifier, scan at most 8192 raw query bytes and 128 fields
  separated by `&`. Decode only field names, once, using percent escapes and
  form-style `+` spaces; decoded names are at most 256 bytes. Reject malformed
  name escapes, control/DEL bytes, invalid UTF-8 names and bound overflow with
  `400 invalid_request`. Query values are never decoded or inspected. A decoded
  `access_token` name or `access_token[` prefix rejects, including encoded names,
  bracket forms and names without `=`. Matching is case-sensitive. An empty
  terminal query segment is ignored. Ordinary query names and values remain
  available to subsequent request processing; no parameter map is constructed
  or fetched by authentication.
- Reject every `application/x-www-form-urlencoded` request with
  `400 invalid_request`, whether a credential is present or not. Excluding a
  body credential would otherwise require consuming/parsing the body. Inspect
  at most one Content-Type value, bounded to 1024 bytes, through pinned Plug's
  media-type parser plus a complete bounded parameter-grammar scan; duplicate,
  comma-combined, malformed parameter or oversized values reject. Quoted commas,
  escaped quoted characters and empty parameter slots remain valid. The media type comparison
  is case-insensitive. Authentication never reads a body. JSON, binary and other
  non-form bodies, including their already-fetched parameters, remain untouched
  and never supply a credential.
- Cookies remain ordinary ignored data. They are neither fetched nor interpreted
  as authentication, and never become an Authorization header. A cookie alone
  cannot authenticate; an explicit valid Bearer header is still required.

The plug uses only the raw query string for this check, so an upstream parsed map
cannot erase duplicate or encoded token names. It does not inspect nested JSON
fields as an alternative OAuth mechanism. Separate route parsers must enforce
their own request/body limits and reject unsupported application inputs.

## Typed verification and response contract

Every call first removes a pre-existing `:verified_identity` assign. Only
`{:ok, %MixerHosted.Identity.VerifiedIdentity{}}` from the invoked verifier is
assigned anew. The plug grants no principal, actor, organization, membership,
action or scope permission. Verified token scopes remain identity evidence for
later authoritative checks. Token role/tenant claims and HTTP assertion headers
cannot create those checks or bypass the verifier.

Expiry, current trust and admission remain the existing configured verifier's
responsibility. The middleware introduces no raw-token/claim fallback, owner
startup, provider refresh call, retry loop or 429 reinterpretation. The existing
owner's typed unavailable/admission behavior remains 503.

| Condition | HTTP / JSON code | WWW-Authenticate | Retry-After |
| --- | --- | --- | --- |
| No Authorization field | 401 / `unauthenticated` | `Bearer` | absent |
| Malformed/ambiguous or alternative credential input | 400 / `invalid_request` | `Bearer error="invalid_request"` | absent |
| Syntactically valid token rejected by verifier | 401 / `unauthenticated` | `Bearer error="invalid_token"` | absent |
| Verifier unavailable, unsupported return, ordinary exception/throw or invalid clock result | 503 / `identity_unavailable` | absent | `1` |

Errors halt the connection and return only the existing JSON envelope fields
`error.code`, `error.message`, and `request_id`. Messages are constant, generic
and bounded; tokens, claims, provider bodies and exception details are omitted.
The 503 message supplies bounded retry advice. Existing challenge/retry headers
are removed in full, including duplicate occurrences, before writing this
response's applicable values. Error Content-Type is likewise normalized. All calls set
one `Cache-Control: no-store` value, replacing all duplicate directives, including
accepted identity requests for downstream
private handling.

A safe 20–200 byte upstream `x-request-id` response value is retained. The safe
alphabet is ASCII letters/digits and `-._~+/=`; absent, duplicate or unsafe values
are replaced with `Plug.RequestId.generate/0`. The response header and JSON ID
match. This works with the endpoint's existing `Plug.RequestId`; this component
does not modify its configuration or read a credential from request-ID data.

`init/1` accepts only unique `:verifier` and `:clock` options. The module must
export `authenticate/2`; the clock must be an exported MFA returning integer
Unix seconds in the existing identity time range. Invalid dependency options
fail initialization. These are trusted application/test options, never HTTP
selectors. Ordinary raised exceptions and thrown values fail closed generically;
process exits and fatal VM failures propagate and are not hidden by an
all-class catch. A typed struct from arbitrary malicious BEAM code is outside
the application's trust model; this plug is not a BEAM sandbox.

## Verification and remaining integration

Run the bounded receipt producer from the repository root:

```text
python3 verification/hosted-bearer-identity-transport/verify.py
```

It records exact argv, cwd, Elixir/Mix/OTP versions, source revision, hashed live
compiler inputs and pinned dependency API sources, source stability, raw output
and cleanup. It uses an isolated build directory and runs only the new actual
Plug.Conn middleware tests plus the existing pure AccessTokenVerifier suite,
with no application startup or database. Fresh synthetic RSA keys exist only in
test process memory. The real RS256/TrustSnapshot join uses a trusted test
adapter and never fetches JWKS. A separate case calls the actual default
ConfiguredVerifier with no owner and confirms unavailable behavior.

The corrected host run passes all 47 tests with zero skips: 31 middleware groups
and 16 existing pure-verifier regression groups. Elixir and Mix are 1.20.4 on
Erlang/OTP 29 (ERTS 17.1); compile/test source hashes remain unchanged throughout
the run and owned build scratch is removed. The raw log preserves upstream
dependency deprecation warnings; this is not a warning-free dependency build.

Independent review found two repair families in the initial 42-test candidate:
malformed parameter tails could be silently discarded by Plug, and single-header
helpers left duplicate response metadata behind. Root added a complete parameter
scan and unique response-header replacement. Five new regression groups include
all 256 quoted-value bytes, valid quoted commas/escapes, malformed tails and
duplicate metadata across successful identity and all denial classes. Parameter
syntax follows [RFC 9110 §§5.6.2, 5.6.4 and 5.6.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.6).
Original source/report/logs and all fourteen initial bindings remain under
`original-handoff/`; independent failures remain in the separate review packet.
Corrected independent review is pending.

The first flat temporary build path failed during pinned JOSE compilation
because its relative include link resolved at the wrong depth. Its raw output
and failed receipt are retained in `prior-attempts/1/`; its scratch was removed.
The runner now places its isolated directory at the normal `_build/<name>`
depth without editing a dependency. The current result and scratch cleanup are
recorded in `verification/hosted-bearer-identity-transport/receipt.json`.

Live HTTP route integration, membership/RLS composition, provider selection and
qualification, login, browser/session/CSRF handling and console integration
remain pending. These host tests do not establish deployment, customer,
operational, native or GA acceptance. No phone, simulator or emulator is used.
