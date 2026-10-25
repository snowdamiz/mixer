# Hosted bearer identity independent review

## Final finite review acceptance

Current outcome: **accepted for the unrouted bearer-identity development
prerequisite**. No actionable findings remain within this bounded review. The
final candidate's only middleware change from corrected attempt 1 requires both
media type and subtype to be nonempty. All five previously accepted empty-subtype
values now reject before calling the verifier. Original malformed-parameter and
duplicate-response-header failures remain closed.

The final producer seal SHA-256 is
`36ab588aa70ae3199ea549024840b18fc3dc64fe5215d5785c49113042c3c36c`;
all 74 bindings match. The reviewed middleware SHA-256 is
`957f96d3403a265f454757a993dd9b5e7890a1bf4c52136f52a502716be75b54`.
A fresh owned copy runs the exact seven original independent groups and exact
three additional groups: **10 passed, zero failures, zero skips**. The source and
dependency digest is
`623c1c29aa243c3a8cc34a53073f2d79b3132f0bef456bb19910779c4acb9a4b`;
66 source/control files and 915 dependency files remain unchanged throughout.
The producer's sealed 47-pass, zero-skip baseline is inspected in this final
confirmation; it is not presented as another independent baseline rerun.

The accepted final command is:

```text
python3 verification/hosted-bearer-identity-review/final-confirmation-1/verify.py
```

[`final-confirmation-1/receipt.json`](../verification/hosted-bearer-identity-review/final-confirmation-1/receipt.json)
contains exact commands, versions, source/dependency hashes, output bindings,
source stability and successful owned-copy/build cleanup. The original seven
groups remain byte-for-byte unchanged, including their historical bitstring pin
deprecation warning. No new speculative controls were added to this final run.
The full final producer packet is preserved in `final-confirmation-1/producer-handoff/`.

Historical failure evidence remains immutable. The complete 61-member prior
review handoff, including its exact report, is self-contained under
`final-confirmation-1/prior-review-handoff/`. The complete initial 12-member
review handoff is already self-contained in corrected attempt 1's
`original-review/` snapshot. Their historical report bindings resolve against
those snapshot roots. The final root review seal binds the current report and
all retained review artifacts.

This acceptance concerns header parsing, generic error mapping, typed identity
assignment and the tested pure verifier join. The Plug grants no application
authority and remains unrouted. Active configured-owner/admission/provider
lifecycle, wire/adapter integration, login, membership/RLS, database, console,
deployment, operational, native and GA qualification remain pending. No
producer edit, Git/index edit, network/provider request, database connection or
native activity was performed by the review.

## Historical corrected candidate review, attempt 1

Outcome at that handoff: **changes required** for one additional malformed-media-base
case. The candidate sealed by producer manifest SHA-256
`7e79a878f7e15ddf8893af8581ea9f6a22273fbb17b93313b609d8fce1b4a4f7`
passes all 47 baseline tests and all seven original independent groups, with
zero skips. The original malformed-parameter, duplicate-ID exception and stale
challenge/retry failures are closed by executable assertions. Three additional
bounded groups pass quoted-pair byte/escape handling and success/error duplicate
normalization, but fail the following base-media check:

**P2 — reject an empty media subtype returned by the pinned parser.**
`application/`, `application/ `, `application/; charset=utf-8`,
`application/; profile="one,two"` and `application/; ;` all reach the verifier
and return an accepted connection. A well-formed parameter suffix cannot make
an empty subtype valid. Require a nonempty type/subtype in the parser-result
admission. Exact observations are preserved in
[`corrected-attempt-1/command-5.log`](../verification/hosted-bearer-identity-review/corrected-attempt-1/command-5.log).

The fresh attempt verifies all 34 producer seal members, copies the ordinary
sources and dependencies into an owned isolated build, and records unchanged
input digest `6873f76fe48ef78e15f690963a3e64945354caec2dd3b75bb3f52b05512a530c`.
Both live producer and review scratch remain untouched except that owned review
scratch was removed. The full source/command/output/cleanup receipt is
[`corrected-attempt-1/receipt.json`](../verification/hosted-bearer-identity-review/corrected-attempt-1/receipt.json).

The original report and every initial seal member remain byte-for-byte available
in the self-contained
[`original-review/`](../verification/hosted-bearer-identity-review/corrected-attempt-1/original-review/)
snapshot. The original root receipt/logs/controls/candidate snapshots have not
changed. Its historical seal's report binding resolves against this snapshot;
this report now adds the current outcome. The corrected producer's complete
34-member packet is separately retained under `corrected-attempt-1/producer-handoff/`.
Original limitations and pending integration gates below continue to apply.

## Original candidate review

Outcome: **changes required** for the original sealed candidate. This is a finite
host-only review of the ordinary `BearerIdentity` prerequisite. It neither routes
the middleware nor accepts customer authorization, deployment or a GA gate.

The reviewed source is based at `6b8aba350224ed19f678669bdbea6b359d8de68b`.
All 14 entries of the producer's
[`handoff-sha256.json`](../verification/hosted-bearer-identity-transport/handoff-sha256.json)
matched before execution. The middleware SHA-256 is
`0688d9fd3b380f3e8aff2ac73c0232f2291c3514851dd46ef752dba517eee9f4`.
The review's source/dependency inventory digest is
`8346c10136bad3990d346d02cd12c232f7605dd4ef93745e4b65d748631e60e9`;
all 65 inventoried source/control files and 915 dependency files remained stable.
The exact original middleware, producer test and transport document are retained
under the review's `candidate/` directory so a later repair cannot erase the
reviewed bytes.

## Required repairs

1. **P2 — validate Content-Type parameter syntax before accepting a media type.**
   In the candidate's `content_type_policy/1`, lines 174–176 treat a successful
   `Plug.Conn.Utils.content_type/1` result as proof that the entire value is
   valid. Pinned Plug deliberately discards invalid parameter pairs. The value
   `application/json; charset=utf-8, application/x-www-form-urlencoded` therefore
   becomes `{:ok, "application", "json", %{}}`; the middleware invokes the
   verifier and accepts the connection. This contradicts the documented rejection
   of invalid and comma-combined Content-Type values. Reject malformed parameter
   syntax and unquoted combination delimiters while preserving valid quoted
   parameters such as `profile="one,two"`. No body-token fallback or authentication
   bypass was established by this case.
2. **P2 — remove all duplicate response headers before installing canonical
   values.** Pinned Plug's `put_resp_header/3` and `delete_resp_header/2` change
   only the first matching list entry. In the candidate's `request_id/1`, line
   193 replaces only the first of two upstream response IDs; the denial path's
   `[id]` match at line 222 then raises `MatchError`, producing no generic JSON
   authentication envelope. The documented duplicate-ID recovery must leave
   exactly one safe ID on accepted and rejected connections. The same behavior
   at lines 219–221 leaves the third stale `www-authenticate` value and the second
   stale `retry-after` value instead of clearing existing values. Remove every
   matching occurrence before writing this response's canonical headers. These
   repros use upstream Plug response state; they do not assert that a remote
   client can directly create response-header duplicates in the current endpoint.

The precise assertions are in
[`independent_controls_test.exs`](../verification/hosted-bearer-identity-review/independent_controls_test.exs).
The original failure output is preserved in
[`command-4.log`](../verification/hosted-bearer-identity-review/command-4.log):

- Malformed Content-Type expected status 400; the connection remained accepted.
- Duplicate request IDs raised at the middleware's singleton-ID match.
- Three stale challenges produced `["Bearer", "stale-three"]` instead of
  `["Bearer"]`. This assertion stops before the following Retry-After assertion;
  the remaining retry value is additionally supported by the inspected pinned
  `List.keydelete/3` implementation, rather than claimed as a separately completed
  dynamic assertion.

## Reviewed behavior and executable evidence

The producer's 42 middleware/pure-verifier tests pass independently in a fresh
copied tree, with no skips. They cover the real synthetic RS256/TrustSnapshot
join, altered signature, expiry, audience and stale-trust response mapping; the
actual default ConfiguredVerifier without an owner returns unavailable. This
does not exercise an active configured owner's admission or current-trust
lifecycle. The source inspection confirms that the default dependency uses the
existing ConfiguredVerifier, rather than introducing a token/claim fallback.

Seven added independent groups produce four passes and three failures, with no
skips. Passing controls check the whole 256-byte token alphabet, every singly
percent-encoded position in the reserved query names and bracket forms, valid
quoted Content-Type commas, and consecutive success/failure stale-identity
removal. The failing groups are the contract repairs above. Body authentication
remains absent: the documented policy rejects all URL-encoded form requests,
does not read request bodies, and ignores cookies. This is the specified
`application/x-www-form-urlencoded` restriction; it is not a claim that every
possible multipart form media type is rejected.

Command:

```text
python3 verification/hosted-bearer-identity-review/verify.py
```

The runner copies only accepted ordinary `hosted/lib`, `hosted/test/support`,
focused tests, config, manifests and installed general-purpose dependencies into
an owned copy. The unique build path stays at `_build/<name>` within that copy.
It runs `mix test --no-start` only for the original 42-test pair and the seven
review groups. The original runner returns nonzero to preserve the failed
acceptance boundary. It refuses to overwrite an existing receipt. No frozen
catalog/authority or rejected outbound Worker V2 source or evidence is read,
imported, compiled or executed; no broad verification command is invoked.

[`receipt.json`](../verification/hosted-bearer-identity-review/receipt.json)
records exact argv/cwd, exit codes, output hashes, source/dependency hashes,
revision, timestamps and cleanup.
[`review.json`](../verification/hosted-bearer-identity-review/review.json)
records the entry command, Python/platform version and finite outcome. Elixir
and Mix are 1.20.4 on Erlang/OTP 29 / ERTS 17.1. Original dependency warnings and
an independent-control bitstring pin deprecation warning remain in raw output;
this is not a warning-free build claim.

The owned copied source, dependency and build scratch was removed after both
runs; source hashes remained unchanged. No application/owner startup, provider
request, network listener/request, database connection, native instance, Git
index change or live producer edit was performed by the review. The existing
test helper starts supporting OTP applications without starting MixerHosted.

A corrected sealed candidate requires a bounded rerun of the necessary controls
and an updated review outcome. Live routes, adapter/wire parsing, login, provider
qualification, current-owner lifecycle, membership/RLS, console, deployment,
operational and GA acceptance remain outside this review.
