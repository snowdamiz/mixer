# Ordinary browser-session encrypted custody

Status: local product prerequisite for W11/W14, pending root review. This module
implements AES-256-GCM custody for the selected durable browser-session contract.
It does not activate login, resolve production keys, start a process, perform
provider/database I/O, authorize a user or qualify deployment/customer/GA gates.
No frozen hosted lane was read, imported, compiled or executed.

## Public API and trusted boundary

`MixerHosted.BrowserAuth.Vault` accepts metadata supplied by the trusted lifecycle
owner after bounded durable lookup. The caller must use the exact current row,
saved attempt context and expected configuration fingerprint. A map, struct or
successful decryption is not evidence of provider verification or authorization.
The lifecycle owner must recheck fencing under the selected transaction protocol
before publishing prepared encryption or using a decrypted token.

| API | Closed result |
| --- | --- |
| `key(key_id, raw_key)` | `{:ok, %Vault.Key{}}` for exactly 32 supplied key bytes and a key ID of 1 through 128 ASCII letters/digits/`._-`. |
| `seal(key, context, plaintext)` | `{:ok, %Vault.Sealed{version: 1, key_id: ..., iv: ..., tag: ..., ciphertext: ...}}` with a new independent CSPRNG 12-byte IV and a full 16-byte tag. No IV/RNG parameter exists. |
| `open(key, context, sealed)` | `{:ok, %Vault.Preauth{}}`, `{:ok, %Vault.Active{}}` or `{:ok, %Vault.Verifier{}}`, authenticated before parsing. |
| `associated_data(key_id, context)` | `{:ok, binary}` with exact deterministic public metadata encoding below. |

Every failure returns only `{:error, :vault_unavailable}`. Missing/foreign key
versions, malformed/unknown fields, changed metadata, bad tags, invalid envelope
kinds, trailing bytes, crypto backend failures and oversized ciphertext deny.
`Key`, plaintext and `Sealed` Inspect implementations hide secret material;
`Sealed` reveals only its version. This does not protect deliberate field access,
raw maps, VM dumps or a compromised caller. The module promises no BEAM memory
zeroization. Raw keys, CSRF, bearer and PKCE values must never enter logs, job
arguments, database settings, frontend assets or build-worker custody.

The initial module accepts one supplied key version per operation, with no key
lookup, fallback, environment access, startup wiring or production rotation
workflow. A lifecycle adapter must clear readiness when custody fails. Secure
runtime key custody, per-key usage limits, rotation and recovery need operational
qualification. No key, provider credential or production configuration is created
or changed by this slice. Synthetic keys in verification are test values only.

## Exact contexts

Contexts are closed atom-keyed maps: every listed field is mandatory and unknown
fields reject. Digests are raw 32-byte SHA-256 values, not canonical43 wire text.
`browser_id` is raw16. Public `generation` is a canonical unpadded Base64URL token
of exactly32 bytes (43 ASCII characters, including canonical trailing bits).
`epoch`, `revision`, `vault_generation`, `credential_revision` and `expires_at` are
positive integers at most `9007199254740991`. `profile_version` is a positive
PostgreSQL int32 at most `2147483647`.

Session context fields are exactly:

```elixir
%{purpose: :preauth | :active, browser_id: raw16,
  cookie_digest: raw32, csrf_digest: raw32, epoch: positive53,
  revision: positive53, generation: canonical43, vault_generation: positive53,
  config_digest: raw32, profile_id: utf8_128, profile_version: positive_int32,
  principal_id: nil | utf8_128, family_id: nil | utf8_128,
  credential_ref: nil | utf8_256, credential_revision: nil | positive53}
```

Preauth requires all four authz links nil. Active requires all four links with
their exact values. The expected configuration profile/version are supplied even
for preauth. Plaintext CSRF must be canonical43 and its ASCII SHA-256 must equal
`csrf_digest` using OTP constant-time comparison, both on seal and after open.

Attempt context fields are exactly:

```elixir
%{purpose: :attempt, state_digest: raw32, browser_id: raw16,
  cookie_digest: raw32, epoch: positive53, revision: positive53,
  generation: canonical43, config_digest: raw32, profile_id: utf8_128,
  profile_version: positive_int32, issuer: utf8_2048, client_id: utf8_256,
  redirect_uri: utf8_2048, expires_at: positive53}
```

The attempt cookie digest, revision and generation are the saved values at begin,
not values inferred from a newer browser row. The exact issuer/client/redirect
come from the validated immutable configuration. UTF-8 fields are 1 through their
byte bound, valid UTF-8 and NUL-free for PostgreSQL text compatibility. They retain
spaces, slashes and all exact bytes; no trim, URL canonicalization or Unicode
normalization occurs here. Config validation and durable linking stay with their
respective owners.

Session revision/epoch changes at bootstrap, begin, activation, logout and expiry
require new matching encryption or erasure. Claim, provider-rejection and failed
claim audit-only changes preserve session revision/epoch/generation and the vault
context. SQL and owner integration must enforce these transitions; this pure
module does not establish transaction provenance or persistence.

## Plaintext and authentication data bytes

`LP(x)` is unsigned big-endian32 byte length followed by exactly the bytes of `x`.
`U64(x)` is exactly8 unsigned big-endian bytes. Every AAD field, including integers
and single-byte tags, uses LP. There is no Erlang term serialization or JSON.

Closed plaintext encodings are exactly:

| Typed input/output | Bytes |
| --- | --- |
| `%Vault.Preauth{csrf: csrf}` | `0x01 || LP(csrf)` (48 bytes). |
| `%Vault.Active{csrf: csrf, access_token: bearer}` | `0x02 || LP(csrf) || LP(bearer)` (53 through4141 bytes). |
| `%Vault.Verifier{verifier: verifier}` | `0x03 || LP(verifier)` (48 bytes). |

CSRF and PKCE verifier must be canonical43. Bearer is 1 through4089 ASCII bytes
with a nonempty `[A-Za-z0-9._~+/-]+` body followed by zero or more `=` padding bytes;
embedded padding, whitespace and controls reject. This is custody syntax only.
The ordinary current configured verifier must independently authenticate the
opened access token each time; even an accepted opaque value grants no authority.
No refresh token, ID token, additional field or trailing byte is accepted.
Ciphertext is bounded before decryption to 1 through8192 bytes. The closed current
envelopes are smaller, and authenticated padding or larger plaintext still denies.

AAD starts with the exact literal domain (including its terminal NUL), followed
by LP fields in precisely this order:

```text
Session domain: mixer.browser.vault.v1\0
LP(0x01 ciphertext version), LP(key_id), LP(kind:0x01 preauth/0x02 active),
LP(browser_id), LP(cookie_digest), LP(csrf_digest), LP(U64(epoch)),
LP(U64(revision)), LP(generation), LP(U64(vault_generation)), LP(config_digest),
LP(profile_id), LP(U64(profile_version)),
  preauth: LP(0x00 absent linkage)
  active:  LP(0x01 present linkage), LP(principal_id), LP(family_id),
           LP(credential_ref), LP(U64(credential_revision))

Attempt domain: mixer.browser.attempt.v1\0
LP(0x01 ciphertext version), LP(key_id), LP(0x03 verifier kind),
LP(state_digest), LP(browser_id), LP(cookie_digest), LP(U64(epoch)),
LP(U64(revision)), LP(generation), LP(config_digest), LP(profile_id),
LP(U64(profile_version)), LP(issuer), LP(client_id), LP(redirect_uri),
LP(U64(expires_at))
```

The saved key ID is both checked against the supplied key and authenticated in
AAD. Version1 is the only accepted ciphertext version. Domain separation, kind
and exact linkage prevent using a session ciphertext as a verifier or changing
preauth into active custody. Every substituted row/digest/epoch/revision/
generation/config/key/profile/link/client/redirect/expiry must deny. This does not
prevent a privileged database owner from rewriting coherent rows and does not
replace current row lookup or owner/database lifecycle fencing.

## Host evidence and remaining gates

Run `python3 verification/hosted-browser-session-vault/run.py`. It explicitly
compiles only `vault.ex` with warnings as errors, runs the selected ExUnit file on
bounded BEAM schedulers, and uses a separate host Swift CryptoKit CLI to derive
all three AAD/envelope encodings independently, open Elixir ciphertext and
reproduce the exact ciphertext/tag. Fixed IVs exist only in verification code.
Both standard platform implementations check a zero-key/zero-IV known-answer
vector and exact published nonempty plaintext/AAD data from
[NIST GCM-AES256 Example #4, PDF pages25–26](https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/AES_GCM.pdf).
The source URL and exact values are preserved in `nist-gcm-vector.json`. These
checks are interoperability evidence, not cryptographic module certification. Product AES-GCM/CSPRNG/hash operations use
[OTP crypto](https://www.erlang.org/doc/apps/crypto/crypto.html), following the
standard [NIST GCM mode](https://csrc.nist.gov/pubs/sp/800/38/d/final).

The runner records exact selected source/context hashes, revision, commands,
versions, stdout/stderr and cleanup in timestamped attempts plus `receipt.json`.
It deletes its owned BEAM/binary/compiler-cache temporary directory, starts no
shared application or database/provider/network/UI process, and preserves other
projects. No whole-app compilation, broad hosted runner or frozen lane is used.
The Swift executable is a macOS host cryptography test, not native app/device UI
qualification. Browser/computer use/capture/simulator/emulator/phones remain
paused. No customer or production publication, migration or credential change
occurs. Durable owner/storage joining, controlled writer, production key custody,
provider exchange, OIDC verification, HTTP/console/ingress composition, deployment,
customer and GA qualification remain pending.
