# Hosted access-token verifier independent review

Status: bounded independent source review and adversarial execution passed on October 24, 2026. No actionable product finding was identified within the scope below. Root retains final slice acceptance.

This review owns only this document and `verification/hosted-token-verifier-review/`. It evaluates the pure token helper and immutable trust constructor against the root-selected RS256 compatibility profile. It does not qualify a configured `Verifier.authenticate/2` adapter, HTTP, active trust replacement, JWKS fetch/cache, provider issuance, revocation, membership, database policy, deployment, native execution or GA acceptance.

The reviewer independently authors attacks and runs them against an exact archived copy of the producer's frozen product modules. Producer tests are not independent review evidence. Synthetic private keys exist only in test-process memory. The review starts no listener and uses no native runtime, screen capture, UI automation or device.

## Bounded adversarial matrix

| Group | Executable checks |
| --- | --- |
| Positive cryptographic controls | Real RSA-2048 and RSA-4096 signatures; both admitted access-token types; original noncanonical JSON bytes remain verifiable; configured identity class and bounded scopes appear in the result. |
| JSON ambiguity | Validly signed escaped-equivalent duplicate header/claim names; nested duplicate names in ignored claims; duplicate JWKS root/key members; nonobjects, malformed UTF-8/JSON, excess depth and element/member bounds. |
| JWK admission | RSA size endpoints; weak/oversized/leading-zero/even modulus; exponent 3, scalar or padded exponent; private and unknown fields; wrong/missing metadata; key-operation confusion; repeated key IDs; all-or-nothing rejection. |
| Token purpose and signature | ID-token and case-confused purpose; unsupported algs/HMAC public-key confusion; unknown headers including key URLs and critical/unencoded payload; wrong key/signature, altered claims, canonical-base64 and segment/token bounds. |
| Claim types and authority | String/float/boolean/negative times; audience arrays with wrong types, repetitions or excessive length; malformed/bounded scopes; exact issuer/client binding; absent or oversized identifiers; signed tenant/role/kind claims supply no authority. |
| Time and current trust | Human 900/service 300 lifetime boundaries; 30-second iat/nbf boundaries; exact expiry; absent/future/stale trust; disabled profile; overlapping rotation then removal; failed candidate construction does not mutate an existing immutable snapshot. |

The independent suite executed **23 passing ExUnit tests**, zero failures in the final [run-2](../verification/hosted-token-verifier-review/run-2/receipt.json). These tests exercise the actual six frozen product modules, standard JOSE RSA signatures and independent test inputs; they do not import or count the producer's tests. The test-only compact framing preserves deliberately ambiguous raw JSON while JOSE's RS256 implementation performs signing. RSA private keys were generated in memory and neither written nor printed.

Reviewed product aggregate SHA-256: `23fda3b2f8c03a11e5ee5300216071eca95b25f05011619d6225e8b1db09d724`, calculated over sorted file-hash/path lines. The producer's seven-file source/test freeze is `7ed3970197eca3840d16655b2b770829a8534d0b42a73af49f0fdebff95b7407`. Every frozen file matched before and after execution. The final run observed checkout revision `ff1bb262aa66c01790df4fbd1371c8ff33caabe8`; the source digest, rather than an intervening unrelated commit, identifies the reviewed implementation. [Source manifest](../verification/hosted-token-verifier-review/run-2/source-manifest.json) and [compact source archive](../verification/hosted-token-verifier-review/run-2/product-source.tar.gz) retain the exact six modules.

The initial [run-1](../verification/hosted-token-verifier-review/run-1/receipt.json) passed 22/23 tests and failed because the reviewer called nonexistent `JOSE.JWK.to_public_pem/1`. The reviewer corrected the harness to `to_public/1` followed by `to_pem/1`, then reran the full bounded matrix. An escaped JWKS-root duplicate input was also made explicitly raw. The initial exact test/runner inputs were reconstructed and verified against their pre-run hashes before retention; the attempt was a harness failure, with no product edit or cryptographic bypass. [Attempts](../verification/hosted-token-verifier-review/attempts.json) records the distinction.

The runner copied the six product modules and the independently authored suite to a uniquely owned canonical `/private/tmp/` directory, copied the existing exact JOSE/Jason dependency sources into that isolated tree, compiled and executed there, then removed the tree. It did not modify shared build directories or start a listener. Both runs completed their owned child processes and removed their scratch directories. Exact argv, environment overrides, runtime versions, dependency/source hashes, logs and cleanup are retained in each receipt. Reproduce from the repository with `python3 verification/hosted-token-verifier-review/run.py --run-name <new-name>` after confirming the producer freeze still matches.

The observed host was macOS 27.0.1 arm64, Elixir/Mix 1.20.4, OTP 29 / ERTS 17.1, JOSE 1.11.12, Jason 1.4.5 and OpenSSL 4.0.3. The test process observed `jose_json_jason`, `crypto_fallback=false`, and `unsecured_signing=false`. Existing OTP 29 JOSE deprecated-catch warnings remain in the compilation and test logs; this is not warning-free dependency qualification.

No further probe expansion was needed after the agreed matrix passed. The review covers immutable candidate construction and caller-supplied fresh/disabled/rotated snapshots. It does not establish active snapshot ownership, freshness derivation from authenticated HTTP, current disable/revision propagation, cache/network bounds, provider interoperability, principal/credential revocation, membership or authorization. The behavior remains unwired. All hosted operational/provider and native/device checks outside this slice remain pending; computer use and native runtimes remained paused throughout. This is no production, independent security-audit or GA claim.

Root retains final acceptance ownership.
