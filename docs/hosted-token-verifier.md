# Pure hosted access-token verifier

Status: implemented bounded host component with passing recorded host checks;
independent review is in progress. These checks cover only this component.
It does not activate a provider, expose
an authenticated route, implement authorization, or verify a GA gate. Product
scope remains `mixer-product-plan.md` §§6.4, 13, 17 and 18.1 and the accepted
[identity contract](hosted-identity-contract.md).

## API and authority boundary

```elixir
profile = %{
  profile_id: "reviewed-profile-v1",
  profile_version: 1,
  issuer: "https://issuer.invalid/oauth",
  audience: "mixer-api",
  client_id: "registered-client",
  identity_class: :human, # or :service; configured, never selected by a claim
  enabled: true
}

{:ok, snapshot} = MixerHosted.Identity.TrustSnapshot.new(
  profile, raw_jwks_json, fetched_at, fresh_until
)

MixerHosted.Identity.AccessTokenVerifier.verify(compact_token, now, snapshot)
# {:ok, VerifiedIdentity.t()}
# {:error, :unauthenticated | :identity_unavailable}
```

`TrustSnapshot.new/4` returns `{:error, :invalid_trust_configuration}` for an
invalid profile, time interval or any invalid key in the entire raw JWKS. The
exact profile fields above are required; unknown fields reject. Profile IDs are
1–128 UTF-8 bytes, versions are integers 1–2^31-1, the exact HTTPS issuer is
1–2048 UTF-8 bytes without userinfo/query/fragment, and audience/client IDs are
1–256 UTF-8 bytes. Times are integer Unix seconds in 0–2^53-1. `fresh_until` is
exclusive and later than `fetched_at` by at most 300 seconds. This ceiling does
not replace the transport owner's obligation to respect shorter HTTP freshness.

`compact_token` excludes the HTTP `Bearer ` prefix. This helper accepts at most
4089 bytes. A later HTTP adapter must enforce a single authorization value and
the 4096-byte bound including that prefix. No HTTP parsing or route is supplied
here. The `MixerHosted.Identity.Verifier.authenticate/2` behavior is preserved;
there is deliberately no configured adapter until its trust owner exists.

The result has exactly `profile_id`, `profile_version`, `issuer`, `subject`,
`client_id`, `credential_ref`, `issued_at`, `expires_at`, `identity_class` and
`scopes`. A `credential_ref` is the validated `jti` within its exact
profile/issuer/client namespace. It is not a globally authoritative credential
key. Signed organization, project, role, group and kind claims supply no
authority. No raw token or unrestricted claims are retained. These opaque
types document ownership within the trusted BEAM application; hostile code
already running inside that application is outside this API boundary.

## Fixed first compatibility profile

The dependency choice is direct JOSE **1.11.12** and Jason **1.4.5**, pinned by
root. [Dependency qualification](hosted-verifier-dependency.md) explains the
standard cryptographic dependency and its boundaries. This component uses
`JOSE.JWS.verify_strict(key, ["RS256"], original_compact_token)`, checks the
returned payload against the exact preflighted bytes, and never reserializes
the signed input before verification. Root config selects `:jose_json_jason`,
disables unsecured signing and disables crypto fallback; executable tests
assert that running configuration. No custom verification primitive or
token-derived algorithm allowlist is used.

The compatibility restrictions are:

- Exactly three nonempty canonical unpadded base64url JWS segments; no JWE,
  detached/unencoded payload or JSON JWS serialization. Decoded header, claims
  and signature bounds are 2048, 3072 and 512 bytes.
- Exactly protected `alg`, `typ` and `kid` fields. `alg` is `RS256`, `typ` is
  `at+jwt` or `application/at+jwt`, and `kid` is 1–128 UTF-8 bytes. Extensions,
  critical headers, embedded keys and key URLs reject. No field initiates a
  network request.
- Jason ordered objects with copied string keys/values, duplicate decoded
  names rejected recursively before conversion to maps. This includes
  escaped-equivalent names in unknown nested claims. Raw byte bounds apply
  before parsing; depth is at most 16 with root depth zero, and each object or
  array contains at most 64 members/elements. Nonobject roots reject.
- Raw JWKS at most 256 KiB and exactly one `keys` member, containing 1–16 keys
  with unique `kid`. Keys permit only `kty`, `alg`, `use`, optional `key_ops`,
  `kid`, `n`, `e`. Require RSA/RS256/signature metadata, optional
  `key_ops=["verify"]`, canonical unsigned odd modulus of 2048–4096 bits and
  exponent 65537. Unknown fields, private material, leading zero encodings,
  weak keys and alternative key representations reject. A token selects one
  exact key; unrelated keys are never tried.
- Required `iss`, `sub`, `aud`, `client_id`, `iat`, `exp`, `jti`; exact configured
  issuer and client. Subject/token IDs are 1–256 UTF-8 bytes. Audience is the
  exact configured string or a unique 1–8-element array of 1–256-byte UTF-8
  strings containing it.
- Nonnegative bounded integer time claims, `iat < exp`, lifetime at most **900
  seconds for humans / 300 seconds for services**, at most 30 seconds future
  allowance for `iat` and optional `nbf`, `nbf < exp`, and no acceptance at or
  after `exp`. These accepted class ceilings supersede the dependency
  proposal's 600-second value.
- Absent scope retains no action scopes. Present scope is a 1–1024-byte OAuth
  scope string, at most 32 distinct space-separated nonempty words, using the
  OAuth ASCII scope-token character set. Malformed or repeated scope words
  reject. Retain only the exact `mixer.artifact.read`,
  `mixer.artifact.upload`, `mixer.audit.read` names in that stable order.
  Unknown well-formed scopes contribute nothing.

## Snapshot replacement and errors

Construction is pure: success returns a complete immutable candidate, and
failure returns no candidate. Tests supply overlapping old/new snapshots and
a successful replacement without the old key: the old token then rejects
immediately. An invalid candidate cannot partially install keys or extend a
previous snapshot's freshness. These tests prove only function inputs/outputs;
they do not prove activation, distributed invalidation or a cache lifecycle.

With usable fresh trust, malformed credentials, every validation/signature
failure and unknown `kid` normalize to `{:error, :unauthenticated}` without
details or token logging. An explicitly disabled valid profile is an
authoritative deny and also returns `:unauthenticated`. Missing, stale or
future-fetched trust, or an unusable clock, return `:identity_unavailable`.
Expiry and freshness are exclusive boundaries.

The future configured adapter must select current enabled profile/revision
state for each protected request and own an atomic active pointer. Passing an
old snapshot after a newer disable/removal cannot be detected by a pure
function. No application-environment token authority, always-available provider,
network discovery, fetcher, mutable cache, refresh process, negative cache or
HTTP transport is implemented here.

Still required are authenticated HTTPS origin/path and issuer binding; TLS,
DNS/private-address/rebinding/redirect defenses; 256 KiB/2-second/four-fetch
bounds; HTTP freshness; single-flight and 30-second refresh limits; bounded
128-entry unknown-key state; atomic replacement/removal/disable propagation;
and distinction between a fresh authoritative absence and an unavailable
required refresh. Stale acceptance cannot be extended by a refresh failure.
The eight-profile inventory ceiling belongs to that future configuration owner.

## Evidence and remaining qualification

The [source manifest](../verification/hosted-token-verifier/source-manifest.json)
freezes the six product modules and executable test source. The
[receipt](../verification/hosted-token-verifier/receipt.json) records exact argv,
environment, runtime versions, input/output hashes and scope. Tests generate
all private RSA/EC/EdDSA/HMAC keys in memory; no signing-key fixture is stored.

The scoped host matrix executes real 2048/4096-bit RSA signatures, tampering,
wrong keys, none/HMAC confusion, native unsupported algorithms, alternate token
purposes/headers, signed duplicate and escaped JSON, structure/format bounds,
required claims, audience/scope/time limits, configured human/service classes,
unavailable/disabled trust, malformed/private/weak/duplicate JWKs and pure
rotation/removal. JOSE's known OTP deprecated-catch warnings remain dependency
warnings, not a warning-free compatibility claim. An initial `/tmp` build-path
failure and its canonical `/private/tmp` correction are retained in
[attempts](../verification/hosted-token-verifier/attempts.json).

No PostgreSQL, HTTP route/listener, selected provider issuance, hosted Linux,
Cloudflare/Neon deployment, principal/revocation/membership policy, tenant RLS,
browser/CLI login, service federation, production signing, external FieldLog
package, customer or operational qualification is supplied by these tests.
Computer use, screenshots, native simulator/emulator runtime and physical
device checks remain paused and were not attempted. Root owns full hosted
integration, shared dependencies/configuration, trackers and delivery.
