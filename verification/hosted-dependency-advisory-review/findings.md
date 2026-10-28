# Hosted dependency advisory review

Observed at `2026-10-28T02:46Z`, source revision
`a4f1d13fe83415377e84b3fc33869e667da30fae`. This is a read-only dependency
investigation. That revision's test-fixture correction does not remediate these
advisories. No dependency, lockfile, product source, workflow, deployment or gate
was changed. No Mix command, installation, compiler, hosted listener, native
runtime, UI automation, capture or process inventory was run.

## Result

The actual saved Phoenix job log reports **19 advisory matches affecting two
exact pins**: Bandit `1.13.1` (nine HIGH, two MEDIUM) and JOSE `1.11.12` (one HIGH,
seven MEDIUM). `hosted/mix.exs`, `hosted/mix.lock`, and `THIRD_PARTY.yml` agree on
both versions. All 19 maintainer advisory pages and their public repository API
records were checked; the pins fall inside every stated affected range. No
collected advisory was withdrawn. This is affected-version evidence, not an
exploit demonstration or a statement about a running production service.

The minimum published fix candidates covering every logged match are
**Bandit `1.14.0` and JOSE `1.11.13`**. Both Hex release API records returned 200
with `retirement: null`; the candidate records had empty `security_advisories`
arrays when retrieved. This review covers the saved report's 19 matches, not an
exhaustive new audit of every dependency or a guarantee against future reports.
See [Bandit release](https://github.com/mtrudel/bandit/releases/tag/1.14.0),
[Bandit Hex record](https://hex.pm/api/packages/bandit/releases/1.14.0),
[JOSE release](https://github.com/potatosalad/erlang-jose/releases/tag/1.11.13),
and [JOSE Hex record](https://hex.pm/api/packages/jose/releases/1.11.13).

## Exact primary ranges

Each linked GHSA is the package maintainer's advisory, not a secondary security
article. CVE aliases, severity, range, publication/update timestamps and source
response hashes are retained in [advisories.json](advisories.json). The table
uses the CI/GitHub HIGH/MEDIUM labels; GitHub's page wording calls MEDIUM
"Moderate".

| Pin | Advisory / CVE | Severity | Affected versions | Patched | Affected operation |
| --- | --- | --- | --- | --- | --- |
| Bandit 1.13.1 | [GHSA-c3g7-2pg5-qvwh](https://github.com/mtrudel/bandit/security/advisories/GHSA-c3g7-2pg5-qvwh) / CVE-2026-108525 | HIGH | >= 0.3.1, < 1.14.0 | 1.14.0 | HTTP/2 inbound DATA flow control |
| Bandit 1.13.1 | [GHSA-7gfj-7gvq-3xqj](https://github.com/mtrudel/bandit/security/advisories/GHSA-7gfj-7gvq-3xqj) / CVE-2026-109584 | HIGH | >= 0.3.3, < 1.14.0 | 1.14.0 | HTTP/2 decoded cookie allocation |
| Bandit 1.13.1 | [GHSA-j363-h72p-296m](https://github.com/mtrudel/bandit/security/advisories/GHSA-j363-h72p-296m) / CVE-2026-108529 | HIGH | >= 0.3.6, < 1.14.0 | 1.14.0 | HTTP/2 blocked-stream SETTINGS work |
| Bandit 1.13.1 | [GHSA-2v5v-8f9v-xh85](https://github.com/mtrudel/bandit/security/advisories/GHSA-2v5v-8f9v-xh85) / CVE-2026-110314 | MEDIUM | >= 0.5.1, < 1.14.0 | 1.14.0 | WebSocket handling after server close |
| Bandit 1.13.1 | [GHSA-47x4-3fxf-82fr](https://github.com/mtrudel/bandit/security/advisories/GHSA-47x4-3fxf-82fr) / CVE-2026-110499 | HIGH | >= 0.3.6, < 1.14.0 | 1.14.0 | HTTP/2 response HPACK encoder table |
| Bandit 1.13.1 | [GHSA-jwh3-j29h-qfmw](https://github.com/mtrudel/bandit/security/advisories/GHSA-jwh3-j29h-qfmw) / CVE-2026-111101 | HIGH | >= 0.1.0, < 1.14.0 | 1.14.0 | HTTP/1 tiny-chunk memory amplification |
| Bandit 1.13.1 | [GHSA-2238-pgfc-w82m](https://github.com/mtrudel/bandit/security/advisories/GHSA-2238-pgfc-w82m) / CVE-2026-111103 | HIGH | >= 1.9.0, < 1.14.0 | 1.14.0 | HTTP/2 StreamError state rollback |
| Bandit 1.13.1 | [GHSA-29cr-8477-rg6r](https://github.com/mtrudel/bandit/security/advisories/GHSA-29cr-8477-rg6r) / CVE-2026-113436 | HIGH | >= 1.0.0-pre.7, < 1.14.0 | 1.14.0 | HTTP/1 and HTTP/2 integer header parsing |
| Bandit 1.13.1 | [GHSA-cpx7-qf6w-jc63](https://github.com/mtrudel/bandit/security/advisories/GHSA-cpx7-qf6w-jc63) / CVE-2026-114213 | HIGH | >= 1.11.0, < 1.14.0 | 1.14.0 | WebSocket fragment memory amplification |
| Bandit 1.13.1 | [GHSA-w5wc-g2hc-g7m2](https://github.com/mtrudel/bandit/security/advisories/GHSA-w5wc-g2hc-g7m2) / CVE-2026-114216 | MEDIUM | >= 1.12.4, < 1.14.0 | 1.14.0 | HTTP/1 chunk-extension parser mismatch |
| Bandit 1.13.1 | [GHSA-p2qv-vx88-385x](https://github.com/mtrudel/bandit/security/advisories/GHSA-p2qv-vx88-385x) / CVE-2026-115269 | HIGH | >= 1.4.0, < 1.14.0 | 1.14.0 | HTTP/2 request body timeout reset |
| JOSE 1.11.12 | [GHSA-6gxw-6f7r-cjr6](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-6gxw-6f7r-cjr6) / CVE-2026-65625 | MEDIUM | >= 1.2.0, < 1.11.13 | 1.11.13 | JWE AES-GCM tag handling |
| JOSE 1.11.12 | [GHSA-vwvr-f994-6j9j](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-vwvr-f994-6j9j) / CVE-2026-65626 | MEDIUM | >= 1.3.0, < 1.11.13 | 1.11.13 | RSA1_5 JWE decryption |
| JOSE 1.11.12 | [GHSA-wfpv-qxp8-x5gm](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-wfpv-qxp8-x5gm) / CVE-2026-65627 | MEDIUM | >= 1.0.0, < 1.11.13 | 1.11.13 | JWE decompression |
| JOSE 1.11.12 | [GHSA-fpj2-9h59-32pp](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-fpj2-9h59-32pp) / CVE-2026-65628 | MEDIUM | >= 1.5.0, < 1.11.13 | 1.11.13 | ECDH shared-secret type mismatch |
| JOSE 1.11.12 | [GHSA-h4gx-8jq2-mfhc](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-h4gx-8jq2-mfhc) / CVE-2026-65629 | HIGH | >= 1.10.0, < 1.11.13 | 1.11.13 | Password-encrypted private-key export |
| JOSE 1.11.12 | [GHSA-xvr2-gggj-h2pp](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-xvr2-gggj-h2pp) / CVE-2026-65630 | MEDIUM | >= 1.10.0, < 1.11.13 | 1.11.13 | Pure-Erlang X25519 private operations |
| JOSE 1.11.12 | [GHSA-3m45-vrpj-xmrq](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-3m45-vrpj-xmrq) / CVE-2026-65631 | MEDIUM | >= 1.7.7, < 1.11.13 | 1.11.13 | RSA private-JWK prime recovery |
| JOSE 1.11.12 | [GHSA-44hw-rpw9-mwg4](https://github.com/potatosalad/erlang-jose/security/advisories/GHSA-44hw-rpw9-mwg4) / CVE-2026-65632 | MEDIUM | >= 1.0.0, < 1.11.13 | 1.11.13 | ECDSA signature-length validation |

## Relevance to the configured hosted code

**Bandit API listener: protocol exposure is present in source configuration.**
`hosted/config/config.exs:7` selects `Bandit.PhoenixAdapter`.
`RuntimeConfig.endpoint!/2` (`runtime_config.ex:96–112`) disables the server for
processors but enables HTTP for API processes, defaulting to loopback and
allowing `0.0.0.0`. It supplies no HTTP/2 override. Bandit 1.13.1
[defaults HTTP/2 to enabled](https://raw.githubusercontent.com/mtrudel/bandit/1.13.1/lib/bandit.ex)
and its [initial handler](https://raw.githubusercontent.com/mtrudel/bandit/1.13.1/lib/bandit/initial_handler.ex)
accepts the prior-knowledge HTTP/2 preface on a cleartext connection. The
[Phoenix adapter](https://raw.githubusercontent.com/mtrudel/bandit/1.13.1/lib/bandit/phoenix_adapter.ex)
passes endpoint HTTP options to Bandit. Using HTTP rather than HTTPS therefore
does not remove these HTTP/2 code paths.

Several HTTP/2 issues operate before application authentication (header
allocation, integer parsing, connection state). Bearer authorization is not a
blanket mitigation. The inbound-DATA and blocked-send advisories additionally
need their described stream/backpressure conditions; this review did not
demonstrate those conditions against Mixer. The HTTP/1 tiny-chunk advisory also
describes draining unread bodies on keep-alive, so the lack of an application
body read is not sufficient to dismiss it. Request-smuggling exploitability
depends on a front-end proxy parsing chunk extensions differently; no deployed
proxy/origin behavior was inspected. No deployment, public ingress, running
listener, memory exhaustion or exploit reachability is established here.

**WebSocket: affected version, no configured application path found.**
The reviewed endpoint contains only RequestId, Head and Router plugs; the router
declares JSON HTTP routes and no socket or WebSock upgrade. The two WebSocket
advisories require an upgraded WebSocket/handler, which was not found in
`hosted/lib`. A generic Bandit dependency and its default WebSocket support do
not alone prove an application upgrade route exists.

**Private webhook candidate: narrower settings, not a general mitigation.**
`billing/webhook_transport.ex:618–666` declares a loopback/ephemeral-port
candidate with one concurrent HTTP/2 stream, one request per connection and a
16 KiB decoded header list limit. The finite decoded limit matches the cookie
advisory's documented workaround on 1.12.2+. This candidate is not an
Application child or a router route. Its limits must not be generalized to the
API listener; the StreamError advisory specifically concerns bypasses of stream
and request limits. No candidate transport was started for this investigation.

**JOSE: all eight version matches; vulnerable operations not found in reviewed
application call sites.** `identity/access_token_verifier.ex:35–48,74–77`
accepts a bounded three-part compact JWS, fixes `alg` to RS256, checks the RSA
signature size, and calls `JOSE.JWS.verify_strict(key, ["RS256"], token)`.
`identity/trust_snapshot.ex:23,129–137` permits only public RSA signing-key
fields (`kty alg use key_ops kid n e`) before `JOSE.JWK.from_map/1`; a private
`d` is rejected before JOSE, removing the documented private-prime-recovery
input from this import path. No application JWE decrypt/decompress, ECDH,
X25519, ECDSA verification or encrypted private-key export call was found.
`config.exs:5` explicitly disables JOSE crypto fallback and unsecured signing.
This source review does not claim whole-system unreachability, and keeping
affected code pinned is unnecessary when a small supported upgrade exists.

## Minimal next dependency-change slice

1. Coordinate the shared hosted lane, then change only the exact Bandit pin to
   `== 1.14.0` and JOSE pin to `== 1.11.13` in `hosted/mix.exs`; refresh their
   legitimate lock records using the pinned Elixir/OTP environment. Update both
   `THIRD_PARTY.yml` entries and bind the new dependency inventory to a new
   receipt. Keep `.github/workflows/hosted.yml` and
   `hosted/lib/mixer_hosted/browser_auth/store.ex` unchanged. Review the lock diff
   and explain any extra package change before selecting it.
2. The current graph is compatible by published constraints: Bandit 1.14.0's
   [mix.exs](https://raw.githubusercontent.com/mtrudel/bandit/1.14.0/mix.exs)
   keeps Elixir `~> 1.13`, HPAX `~> 1.1`, Plug `~> 1.18`, Telemetry
   `~> 0.4 or ~> 1.0`, Thousand Island `~> 1.6`, WebSock `~> 0.5`.
   Every currently locked production transitive version satisfies these;
   Phoenix 1.8.16 permits Bandit `~> 1.0`. JOSE 1.11.13's
   [mix.exs](https://raw.githubusercontent.com/potatosalad/erlang-jose/1.11.13/mix.exs)
   also requires Elixir `~> 1.13` with no Hex production dependencies. The
   project's Elixir `1.20.4` / OTP `29.1.1` pins need no planned change. This is
   constraint compatibility; compilation/behavior must still be verified.
3. Run the existing hosted locked-dependency, formatting, zero-warning compile,
   browser protocol/storage/migration/callback and disposable-PostgreSQL host
   lanes on the upgraded graph, preserving their exact commands and environment
   in receipts. Exercise the actual Bandit workspace/artifact HTTP integration
   tests and RS256 identity/JWKS tests. The dependency report must stop matching
   all 19 reviewed IDs. The current test-only revision's CI is separate evidence
   and cannot validate an unmade dependency upgrade.
4. Add bounded host protocol regressions for pre-Plug malformed HTTP/1 numeric
   headers/chunk extensions and HTTP/2 decoded-header, stream-error and
   non-progress read-deadline behavior at the upgraded listener. Bind expectations
   to the package's refusal semantics and clean up owned sockets/processes. Test
   body byte caps when one HTTP/2 read returns more than the requested `:length`:
   the [1.14.0 changelog](https://raw.githubusercontent.com/mtrudel/bandit/1.14.0/CHANGELOG.md)
   explicitly changes DATA batching, default concurrent/header limits and body
   read deadlines. Existing request readers compare returned bytes with remaining
   budgets, but those source checks are not runtime proof. Cover public-only JWK
   admission and RS256 rejection of other algorithms after the JOSE upgrade.
   Do not add WebSocket/JWE product features to exercise unused code.
5. Root can deliver the validated dependency slice and inspect its actual remote
   CI. Keep deployment ingress/proxy qualification and all existing native,
   physical-device, browser/provider and GA gates pending. Runtime/UI pause
   remains in force; this review does not authorize new native or capture work.

## Evidence and limitations

[receipt.json](receipt.json) binds source revision/tree, 22 selected file hashes,
their aggregate digest, collector command, Python/TLS/Git versions and scope.
[ci-advisory-excerpt.log](ci-advisory-excerpt.log) preserves the relevant actual
job output; its complete source hash is bound in the receipt.
[upgrade-candidates.json](upgrade-candidates.json) records public Hex metadata
and response hashes.
[validation.json](validation.json) passes metadata consistency, 19 exact
affected-version matches, candidate publication, and all five protected-file
hash comparisons. It is not a product behavior or exploitation test.

The first unauthenticated *global* GitHub advisory API request returned 404;
the public *repository* security-advisory API succeeded for all 19. Two web-tool
Hex API opens were unavailable; ordinary HTTPS GET of the exact official Hex
release API URLs succeeded and is recorded. A display-only Python one-liner
failed to parse because of shell quoting; the corrected heredoc displayed the
already collected metadata. Neither diagnostic failure changed product files.
