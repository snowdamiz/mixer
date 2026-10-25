# Fixed preauthentication begin-login component contract

This selected development slice adds private preauthentication begin-login only.
It does not authenticate a browser, activate Sessions or HTTP routes, exchange a
provider code, or authorize Application readiness. Active-session begin remains
pending until the current default identity verifier is joined. The unchanged
accepted SQL/Vault/catalog sources remain prerequisites, not deployment evidence.

## Closed interfaces and results

`RuntimeOwner.begin_login(raw_cookie, duplicate_preserving_raw_headers,
:workspace, %{request_id: lowercase_hex_32})` establishes its one 5,000 ms
monotonic deadline at function entry, before validation, lease acquisition,
discovery, CSPRNG, custody or either transaction. It reserves the existing
caller-monitored permit (32 total; fixed lifecycle pool 2; no queue). It never
calls `RuntimeOwner.load/1` or reserves a second lease/deadline.

The sole successful result is `{:ok, %PreauthDraft.Authorization{url: url,
expires_at: expires_at}}`. Inspect exposes no fields. This private result contains
no cookie, CSRF, raw verifier, source snapshot or authenticated session. The URL
is at most 8,192 bytes, uses the exact admitted fixed OIDC endpoint/client/redirect,
code/query/openid+workspace/S256 options, and carries fresh state and nonce. It is
released only after confirmed mutating COMMIT and final owner/configuration/
PID/generation/caller/deadline/wall-clock/expiry continuity. Closed Store.Failure
results remain the only failures; no automatic retry or URL reconstruction follows
unknown COMMIT, lost acknowledgement, expiry or continuity failure.

`Store.discover_begin(%PreauthDraft.Load{})` is a separately named fixed operation,
using the existing admitted `mixer_browser_load` helper. Unlike ordinary
`Store.load/1`, it permits the helper's valid projected pending attempt. Ordinary
load continues to reject every non-null attempt/envelope. `Store.begin_login(
%PreauthDraft.Begin{}, metadata)` has no policy selector, Repo, clock, verifier,
callback or executor argument. Begin contains only the retained lease, committed
source snapshot, new session context/cipher, new attempt context/cipher, fresh
state/nonce/verifier, recovered CSRF and the fixed URL. All structs have private
Inspect output. The producer validates the exact draft and retains no durable
raw state, nonce or verifier; SQL stores digests and encrypted verifier only.

## Ordering, replacement and exact comparisons

1. Validate closed metadata, canonical supplied cookie, exact `:workspace`, and
   duplicate-preserving raw headers. The parsed cookie must equal the separately
   supplied cookie. Duplicate, ambiguous or Authorization-bearing headers deny.
2. Under the one retained lease, commit fixed encrypted discovery with both
   catalogs checked. SQL NULL means unavailable here, never an authorization URL.
   Require preauth status, exact cookie/config/initial-config/profile/version and
   matching decoded session context. No family, credential or principal is admitted.
3. Only after that confirmed discovery COMMIT, authenticate/open the preauth
   session envelope, then verify exact Origin and recovered synchronizer CSRF.
   Wrong Origin/CSRF and cookie mismatch cause no durable mutation.
4. Generate independent platform-CSPRNG state, nonce and verifier. Advance
   session epoch/revision/vault_generation by one while preserving cookie,
   generation, CSRF, identity absence, initial configuration and browser deadlines.
   The attempt binds those new counters, cookie/config/profile/provider/redirect
   fields and has exclusive expiry `min(entry_wall + 300, browser idle, absolute)`.
   Fresh wall-clock samples may reject stale work but never rebase or extend
   this retained-entry expiry.
   Build/bound the URL and seal both new envelopes before mutating SQL.
5. Validate draft shape, authenticated source/session cipher, new preauth cipher,
   verifier cipher, independently recomputed URL, nonce/state digests and exact
   new contexts under the same exact retained caller-owned lease. Store does not
   trust a caller-authored URL, context, ciphertext or decoded payload. Then a
   second separate transaction rechecks both catalogs and
   invokes only unchanged `mixer_browser_begin` using source revision CAS.
   Decode and compare the entire produced browser map against the source with
   only epoch/revision/audit_sequence incremented; compare new session context,
   cipher and vault generation exactly. Compare every attempt field, status,
   nullable claim/completion field, created time (between entry/current sample),
   expiry, digests, context and cipher before COMMIT. Any mismatch rolls back. Claim or provider rejection after discovery can
   increment audit_sequence without revision: revision CAS may succeed, but the
   complete browser comparison rejects and rolls back that race without a URL
   or retry.
6. Confirm COMMIT, check final continuity and exclusive expiry, then release only
   the private bounded authorization result and the original permit.

The existing closed `{:finish, lease, expires}` message is the authoritative
permit release. Its private success reply changes from `:ok` to
`{:ok, checked_wall}`; bootstrap/load and begin all consume the same private,
Inspect-redacted publication packet. `checked_wall` is the exact nondecreasing
owner sample used for finish expiry admission. After finish, the caller samples
status on that retained owner PID using the original remaining deadline, requires
the same ready generation/current dependency binding, and then checks local
monotonic deadline, wall `>= checked_wall`, exclusive expiry and registered-owner
identity immediately before returning the private result. Failure here remains
`commit/committed`, with no retry. Fallback release applies only to non-success
cleanup and cannot delay a successful response after its final sample. This is a
sampled publication boundary; it cannot make delivery atomic with the subsequent
check-to-return scheduling interval, network response or caller consumption.

Projected pending attempts must be exact current-browser pending records with
the admitted provider metadata, valid authenticated verifier envelope and expiry
bounded by browser deadlines. The old verifier is authenticated only for source
integrity and is never returned, reused or included in the new URL. A projected
pending attempt may already be expired; its authenticated, structurally valid
record can be superseded while the browser remains live. Its decrypted old
verifier must satisfy Vault's exact canonical 43-character/32-byte token decoder;
the attempt's state/cookie/config digests and all context fields must equal the
source browser and projected attempt. The schema has no separate verifier-digest
column; authentication binds the encrypted canonical verifier to that exact AAD,
and no independent stored verifier-digest claim is made. This is replacement,
not pending resumption. SQL source-revision CAS permits only one winner when two
begins discover the same revision; the loser returns no URL and does not retry.

The fixed load helper does not project claimed, superseded, completed or
provider-rejected attempts. This component cannot observe those hidden records
and does not claim otherwise: when a live preauth browser is returned with nil
attempt, begin may proceed; unchanged SQL supersedes hidden pending/claimed rows
under its existing locks. Active browsers, malformed/non-null unsupported
snapshots, absent/revoked/expired browsers and config mismatches return unavailable.
No active family/user is altered by an admitted preauth operation.

## Verification boundary

The bounded runner will compile only the selected preauth source closure with
warnings as errors and use the actual default KeyOwner plus one owned random-port
PostgreSQL fixture with synthetic restricted roles. It records commands, versions,
revision/source/dependency/tree/output hashes and all attempt/cleanup outcomes.
The fixture's manual localhost/ssl:false RuntimeConfig does not qualify production
constructor/TLS/direct-host/custody/startup binding. No injected verifier/provider,
broad hosted harness, frozen catalog-inspector/authority-driver/rejected Worker V2,
native runtime, UI, capture, device or unrelated-process discovery is used.

Selected controls cover exact URL/state/nonce/PKCE/cipher agreement, cookie-header
binding, raw duplicate/Origin/CSRF failures without mutation, pre-mutation URL/cipher
failure, replacement/CAS, expiry/deadline/COMMIT uncertainty, source/AEAD comparison,
actual-caller continuity and private redaction. The full 40-case owner, 18-case
lifecycle and 48-case relation runtime matrices remain pending, as do active begin,
current-verifier/provider/HTTP joins, Application startup, Neon/TLS/operational
custody, complete native/phone/FieldLog/customer and accountable GA acceptance.

Root approved the contract after an independent fresh-context review. Product
implementation and producer/runtime review evidence are in progress; no acceptance
is inferred before the immutable handoff and independent verification.
