# Independent browser Vault and configuration-digest review

The frozen pure modules pass this independent local review. No blocking defect
was found in their documented bounded contracts. This is evidence for a product
prerequisite, not acceptance of a complete browser login or any deployment/GA
gate. The review made no producer edits and did not run a producer runner.

Run `python3 verification/browser-vault-digest-review/run.py`. The current
[receipt](../verification/browser-vault-digest-review/receipt.json) records the
exact revision, complete source manifest/tree digest, existing Jason BEAM hashes,
commands, tool/backend versions, output hashes, attempt history and cleanup. Its
`review_report_sha256` binds this report. Producer source/test hashes are pinned
in the reviewer runner, checked before compilation, and checked again after
verification; changing that freeze requires another review.

| Independent evidence | Observed result |
| --- | --- |
| Selected reviewer ExUnit | 16 groups; zero failures, exclusions or skips. |
| Configuration bytes and hash | Seven independently constructed Node JSON/SHA-256 vectors match exact product bytes/hash: baseline, JSON escaping/control bytes, composed/decomposed Unicode, line/paragraph separators, astral Unicode and maximum UTF-8 client bytes. |
| All three custody purposes | Independent Node length-prefix/U64/domain/AAD and typed-envelope bytes successfully open through Vault; every product ciphertext opens through Node and reproduces its exact ciphertext/tag on reseal. |
| Authenticated malformed plaintext | All 40 independently encrypted vectors deny, including wrong purpose/kind, endian/length/truncation/trailing bytes, noncanonical tokens, CSRF digest mismatch, invalid bearer syntax and excessive bearer size. |
| Context and ciphertext substitution | Every context field, missing/extra fields, purpose/row/digest/key/link/revision/generation changes, IV/tag/ciphertext changes, key-ID rebinding and unknown versions deny. |
| Bounds, canonicality and exceptions | Every Config scalar/fixed policy and durable integer/raw/text bound is exercised. All 64 possible final Base64URL characters are checked independently for CSRF, PKCE and generation; exactly 16 canonical trailing-bit values pass each. Malformed public arguments return closed errors without private exception text. |
| IV and redaction | The only public encrypt operation is `seal/3`; no nonce override exists. 128 sampled product IVs are distinct and 12 bytes, with full 16-byte tags. Nested Key/plaintext/Sealed Inspect output remains redacted; Config reveals only mode. |
| Backend sanity | Node AES-256-GCM matches the fixed zero-key/zero-IV known-answer vector. This review used Elixir 1.20.4 / OTP29 crypto5.10 (OpenSSL4.0.3) and Node22.23.3 (OpenSSL3.5.8). |

The Node reviewer never imports product code. Its independent fixed-order field
list, JSON serialization, length-prefix/U64 AAD encoder, typed-envelope encoder,
hash and AES-GCM operations provide the byte oracle. Node-generated malformed
payloads are authenticated under the correct independent context, so their
rejection exercises plaintext validation after successful authentication rather
than merely producing invalid tags. Synthetic keys and fixed review IVs remain
in verification only. Nonce sampling is a regression check; it is not a proof of
CSPRNG quality or a qualified per-key usage policy. The implementations share
the OpenSSL family of primitives, so this is interoperability evidence rather
than cryptographic module certification.

The digest includes exactly all 21 current Config fields. Future struct fields,
missing fields, secret-value fields and unsupported policy values fail closed.
The constructor-shaped baseline is also independently passed through `Config.load`
with a matching trusted human manifest. Config input order cannot affect its
explicit ordered encoding; exact Unicode and field boundaries remain distinct.
The digest does not establish constructor provenance, provider trust or a right
to authorize. It does not resolve keys or credentials, and its source accepts
only secret/key references as configuration fields.

One nonblocking integration limitation is explicit: existing Config/Manifest
bounded UTF-8 metadata allows NUL in matched `profile_id`, `client_id` and
`api_audience`; ConfigurationDigest binds those exact bytes. Vault text rejects
NUL for PostgreSQL compatibility, including the first two attempt fields. The
review reproduces this using the actual Config constructor and confirms Vault
denies incompatible text. The lifecycle/configuration admission owner must narrow
such inputs or clear readiness before SQL/Vault use. No authority is granted by
this scope difference. URL validation, provider qualification and SQL admission
are separate contracts and are not delegated to this digest.

Producer evidence was inspected as separate, scoped evidence: configuration
receipt `verification/hosted-browser-configuration-digest/attempts/20261025T152959450620Z/receipt.json`
reports 20 tests (14 existing Config plus six digest), tree digest
`ee5209329fe1069a6bf49d59986f71fa201cc07b68daf4526780cf31277b958d`.
Vault producer freeze and receipt
`verification/hosted-browser-session-vault/attempts/20261025T153141814050Z/receipt.json`
report 25 tests, three independent CryptoKit AAD/envelope/reseal comparisons and
two known-answer vectors, including nonempty AAD/plaintext. These producer checks
are not included in the independent review counts above.

The first reviewer attempt failed because it incorrectly treated the legal key
ID `private-sentinel` as malformed. The test was corrected to the invalid
`private/sentinel`; no product source changed. That failed attempt is retained at
`verification/browser-vault-digest-review/attempts/20261025T153510824793Z/receipt.json`.
Subsequent passes were expanded to isolate each canonical-token check and add
constructor/SQL text compatibility evidence. The runner records all prior
attempts and removes its owned compiler/BEAM temporary directory after every
pass or failure. No owned compiler output/cache survives outside the receipt
directory; no shared application, database, provider/network operation, browser,
capture, native UI, simulator/emulator or phone process was started. Other
projects' processes and data were preserved. The frozen catalog-inspector,
authority-driver and rejected outbound Worker transportV2 lanes were not read,
imported, compiled or executed.

The following remain pending: external reviewed runtime key custody, rotation,
recovery and per-key usage limits; trusted immutable lifecycle context and current
configuration provenance; durable session owner/SQL transaction joining and
fencing; provider exchange and current OIDC/API verification; shared startup,
HTTP/console/ingress composition and deployment; browser/security/customer
qualification; paused native/physical-device checks and all specified GA
acceptance. A successful decrypt, synthetic record, host unit test or local
checkout does not satisfy these gates.
