# Hosted access-token verifier dependency recommendation

Status: dependency qualification complete for a **standalone synthetic host test**; recommendation awaits root integration review. Product identity implementation remains unstarted at the user's pause. This document does not freeze a provider, deploy authentication, grant membership, or verify a GA gate.

Recommend adding **JOSE 1.11.12** directly and retaining the foundation's **Jason 1.4.5**. Pin both exact versions in the root-owned hosted manifest/lock and inventory only when implementation resumes. No product dependency or inventory was changed by this lane.

~~~elixir
{:jose, "== 1.11.12"}
{:jason, "== 1.4.5"} # already selected by hosted/
~~~

The executed environment was Elixir/Mix 1.20.4, Erlang/OTP 29.1.1 / ERTS 17.1, OTP crypto 5.10, public_key 1.21.7 and OpenSSL 4.0.3. Tests use standard JOSE/OTP cryptography with JOSE fallback and unsecured signing disabled. Linux container qualification remains pending. See [receipt](../verification/hosted-verifier-dependency/run-1/receipt.json), [test log](../verification/hosted-verifier-dependency/run-1/tests.log) and [closeout](../verification/hosted-verifier-dependency/closeout.json).

## Selection and maintenance evidence

Live official Hex API metadata was retrieved on October 24, 2026. Search snapshots showing Joken 2.6.2 were stale; the live API reports 2.7.0.

| Candidate | Observed stable version / license | Dependency shape and decision |
| --- | --- | --- |
| [JOSE](https://hex.pm/packages/jose/1.11.12) | 1.11.12, released 2025-11-20; MIT | Zero Hex dependencies. Direct JWK conversion and algorithm-allowlisted JWS verification fit the fixed adapter. **Selected.** |
| [Joken](https://hex.pm/packages/joken/2.7.0) | 2.7.0, released 2026-08-28; Apache-2.0 | Requires JOSE ~> 1.11.12. Claim helpers do not remove this adapter's bounded parsing, issuer policy or JWKS ownership. The extra abstraction is unnecessary for the first profile. |
| [Guardian](https://hex.pm/packages/guardian/2.5.0) | 2.5.0, released 2026-08-17; MIT | Requires JOSE ~> 1.11.9; optional Plug integration. A general authentication framework adds session/token integration choices outside the narrow seam. |
| [Jason](https://hex.pm/packages/jason/1.4.5) | 1.4.5 stable; Apache-2.0 | Already in hosted/. Optional Decimal is unnecessary with native numeric decoding. Ordered-object mode preserves duplicate JSON member names for explicit rejection. |

The [JOSE upstream](https://github.com/potatosalad/erlang-jose) was not archived or disabled and reported a push on 2026-10-21. That is project activity, not a maintenance SLA or security audit. JOSE compiled and executed on OTP 29, with **deprecated-catch warnings** retained in [deps-compile.log](../verification/hosted-verifier-dependency/run-1/deps-compile.log). Do not suppress or misreport them as warning-free compatibility. Future OTP compatibility and upgrades need renewed qualification.

Official release metadata reports no applicable advisories or retirement for these exact releases, and [mix hex.audit](../verification/hosted-verifier-dependency/run-1/hex-audit.log) exited zero for the selected pair. JOSE's [package advisory](https://hex.pm/packages/jose/advisories), CVE-2023-50966 / GHSA-9mg4-v392-8j68, affects versions **below 1.11.7** and concerns an excessive JWE PBES2 iteration count. The selected version is outside that range; this adapter also rejects JWE. This is a dated advisory check, not proof of absence of vulnerabilities.

Official snapshots, URLs, retrieval times and SHA-256 hashes are in [sources.json](../verification/hosted-verifier-dependency/sources.json). Exact lock entries are in [qualified.mix.lock](../verification/hosted-verifier-dependency/qualified.mix.lock). JOSE's Hex outer checksum is 31e92b653e9210b696765cdd885437457de1add2a9011d92f8cf63e4641bab7b; Jason's is b0c823996102bcd0239b3c2444eb00409b72f6a140c1950bc8b457d836b30684. Package notices and dependency file hashes are retained. No dependency implementation source is vendored into Mixer.

## First profile proposed for root freeze

Use one configured **RFC 9068 access-token / RS256** profile. [RFC 9068 §§2 and 4](https://www.rfc-editor.org/rfc/rfc9068.html) defines access-token typing and validation of issuer, audience, signature and expiry, and requires RS256 support. [JWT BCP §3](https://www.rfc-editor.org/rfc/rfc8725.html) requires configured algorithm policy and separates token purposes.

These are Mixer compatibility restrictions and initial test values; a standards-compliant provider may need a separately reviewed adapter:

- Accept compact signed JWS only, with exactly three nonempty canonical unpadded base64url segments. Bound the full HTTP authorization value at 4096 bytes and the compact token at 4089 bytes after the seven-byte Bearer prefix. Reject JWE, JSON JWS serialization, detached/unencoded payload, compression and unsecured tokens.
- Admit only protected header fields alg, typ and kid. Require alg=RS256, typ=at+jwt or application/at+jwt, and nonempty UTF-8 kid of at most 128 bytes. Reject all critical extensions and other headers, including b64, jku, x5u, jwk and x5c. No token data may select a network URL.
- Fix issuer, API audience, registered client and identity class in a reviewed profile snapshot. Select one unique key by profile plus exact kid; never try unrelated keys or infer a broader algorithm from the token. Validate the whole snapshot before activation: at most 16 keys and no repeated kid.
- First JWK shape: public RSA signing keys with explicit alg=RS256, use=sig, optional key_ops=["verify"], canonical unsigned n/e, modulus 2048–4096 bits and exponent 65537. Reject unknown/private key fields. Some providers omit this explicit metadata; qualify a different policy before accepting them. [RFC 7518 §3.3](https://www.rfc-editor.org/rfc/rfc7518.html#section-3.3) supplies the 2048-bit minimum.
- Require iss, sub, aud, client_id, iat, exp and jti; exact issuer/client and intended API audience. Permit a string audience or a unique array of at most eight bounded strings containing that audience. Bound subject/token ID to 256 UTF-8 bytes. Integer nonnegative times only, iat < exp; proposed lifetime at most 600 seconds, future iat/nbf allowance at most 30 seconds, and no acceptance at or after exp. **Root/provider review of these lifetime/skew values remains pending.**
- Missing scope supplies no action. Validate bounded OAuth scope syntax and retain only the exact three scope names in the identity contract. Signed roles, groups, kind, organization and project claims supply no authority.
- Reject malformed JSON, nonobject header/claims, and duplicate decoded member names at every depth, including escaped-equivalent names. Proposed additional bounds: decoded header 2048 bytes, claims 3072 bytes, depth 16, object members/array elements 64.

ES256, EdDSA/Ed25519, RS512 and PS256 were verified as native library capabilities in the scratch tests and then rejected by the fixed profile. They are **unsupported adapter inputs**, not fallback choices. HMAC, all other algorithms, alternate token purposes and different provider binding semantics remain unsupported until reviewed profiles and executable matrices exist.

## Integration seam and responsibility

Preserve the existing contract:

~~~elixir
@callback authenticate(bearer :: binary(), now :: integer()) ::
  {:ok, MixerHosted.Identity.VerifiedIdentity.t()} |
  {:error, :unauthenticated | :identity_unavailable}
~~~

Only the adapter constructs the immutable result after full validation. Follow the existing specimen: profile_id, profile_version, exact issuer, subject, registered client_id, validated credential_ref, issued_at, expires_at, configured identity_class, bounded scopes. A validated jti is a credential reference **within its exact issuer/client/profile namespace**; a database lookup cannot treat it alone as globally authoritative. The result contains no organization, project, role, raw token, unrestricted claims or membership grant. Opaque Elixir types document API ownership inside the trusted BEAM; they are not a sandbox against malicious in-process code.

For raw header, claims and JWKS objects, use [Jason ordered-object decoding](https://hexdocs.pm/jason/1.4.5/Jason.html#decode/2) with string keys and copied strings. Recursively reject repeated **decoded** names before converting pairs to maps. Tests observed that ordinary Jason map decoding retains the first repeated value and erases ambiguity; it cannot establish duplicate rejection.

After preflight and unique configured key selection, call [JOSE.JWS.verify_strict/3](https://hexdocs.pm/jose/JOSE.JWS.html#verify_strict/3):

~~~elixir
{true, exact_payload_bytes, _jws} =
  JOSE.JWS.verify_strict(JOSE.JWK.from_map(validated_public_jwk), ["RS256"], original_compact_token)
~~~

Check the returned payload against the preflighted raw payload and validate claims from that duplicate-checked parse. Do not reserialize before verification or use peek results, verify/2, header-derived allowlists, custom primitives or algorithm plugins as authority. Configure JOSE's JSON backend explicitly and disable unsecured signing/crypto fallback at application boot. The qualification sets Jason in its test process. A separate runtime-inspection process observed the default OTP JSON backend; that log does not describe the configured test process.

**JOSE provides** standard JWK/JWS decoding, algorithm allowlisting and cryptographic signature verification. Tests execute real positive signatures, signature/payload tampering, wrong RSA key, an RSA-public-PEM-as-HMAC attack, adapter rejection of weak RSA, and native EC/EdDSA capabilities.

**Mixer owns** bounded parsing and duplicate policy; header/purpose/claim/time rules; identity linkage; atomic JWKS validation; exception normalization; owned versioned trust configuration; network/cache state; and principal, revocation and membership checks. In executed cases, raw strict verification accepted signatures over an expired/wrong-issuer payload, duplicate claim JSON, duplicate protected alg names, unknown crit and key URL headers. Those are library boundaries, not access-token acceptance.

Keep the identity contract's network bounds: preconfigured authenticated HTTPS origin/path, chain/hostname checks, no redirects or token URLs, DNS/private-address/rebinding defense, 256 KiB response, two-second total deadline, four concurrent fetches/process. Keep cache freshness at most HTTP freshness or 300 seconds, single-flight refresh at most once/30 seconds/profile, a bounded 128-entry/30-second unknown-key cache, atomic replacement and key removal/profile-disable semantics. This lane ran **no transport/cache integration tests**. Fresh authoritative key absence means unauthenticated; unavailable required refresh means identity unavailable. Refresh failures cannot extend stale acceptance.

## Executed result and pause boundary

[run-1](../verification/hosted-verifier-dependency/run-1/receipt.json) records **21 passing ExUnit tests**, zero failures in the sealed run, exact argv/tool/runtime versions, logs, input hashes and dependency source hashes. Cases include both supported RSA size endpoints, genuinely signed policy rejections, confusion and substitution, missing/wrong/time claims, unsupported headers, malformed/duplicate/escaped JSON, bounded format/structure, key selection, atomic malformed-snapshot rejection, overlapping synthetic keys and removed-key rejection. This controlled in-memory harness is not hosted product code.

Two initial failures are preserved in [attempts.json](../verification/hosted-verifier-dependency/attempts.json): Mix required a test helper; then an observation assertion incorrectly expected Jason's last duplicate value rather than the first. Both were corrected before the sealed run. No cryptographic check was mocked or skipped to obtain a pass.

Hosted HTTP, PostgreSQL, provider login, JWKS transport/cache concurrency, production Linux, real issuance, revocation/authorization, native/device, external dogfood, security-review acceptance and GA remain pending. No provider/cloud resources, production keys, publication, customer messages, product/lock/inventory/tracker edits, commits or pushes occurred. Test keys lived only in memory; no listener was started. The owned scratch dependency/build tree was removed after preserving its lock, notices and hashes. Identity integration remains pending until the user resumes.
