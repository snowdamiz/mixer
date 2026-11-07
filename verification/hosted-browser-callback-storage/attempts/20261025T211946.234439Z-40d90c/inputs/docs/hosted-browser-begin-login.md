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

Root approved the contract after an independent fresh-context review. The first
complete producer run passes 30 begin component methods and separately reruns all
30 unchanged accepted preauth bootstrap/load methods under the new shared finish
receipt. These counts overlap and are not the full owner/lifecycle matrices.
The selected compile treats product warnings as errors. The actual local tools
are Elixir 1.20.4, OTP 29 and PostgreSQL 17.11; independent PostgreSQL 16 review and
root acceptance remain pending at producer handoff.

Run `python3 verification/hosted-browser-begin-login/run.py`. Its immutable
attempts archive the exact selected source closure, migrations, contract inputs,+pinned BEAM dependencies, revision, argv, tool versions, stdout/stderr and owned
resource cleanup. `handoff.json`/`handoff.sha256` select the final unchanged-product
replay and preserve every earlier receipt. The runner uses one owned PostgreSQL
cluster per attempt, random loopback port, C locale and synthetic restricted roles.
Cleanup checks the scratch/data device+inode and exact postmaster identity before
stopping/removing only owned resources. All recorded attempts remove their owned
PostgreSQL instance and scratch; all selected BEAM processes are absent after the
successful scripts, and no provider fetch worker starts.

The first product failure was the whole-attempt map comparison: StoredSnapshot
retains ciphertext members there as canonical PostgreSQL hex while its envelope
contains decoded bytes. The corrected comparison requires exact canonical hex
and independently compares the full binary sealed envelope. Subsequent retained
fixture failures include an intentionally corrupting UPDATE rejected by SQL's
attempt transition trigger, and pool readiness after deferred COMMIT rejection:
PostgreSQL idle connections alone did not establish DBConnection checkout
readiness. The final fixture constructs corruption through the unchanged trusted
SQL helper and waits for both actual pool permits before settings checks. These
changes do not retry product operations or alter product admission.

An asynchronous finish-return trace alone did not prove an identity fault preceded
the final status sample; two retained timing attempts returned a URL without a
proved pre-sample fence and are not accepted controls. The corrected final
identity-loss control uses one online scheduler, suspends the owned request and
RuntimeOwner in its tracer, and requires exactly one queued final `:status` call
from that request before applying the fault. It records only the suspension/
queue/count booleans, never a reply, tag or secret. Both processes resume on every
exit path. The final producer run proves this fence and then observes
`commit/committed` with no URL after default identity-owner loss. Separate methods
cross deadline and exclusive expiry after successful finish and confirm the same
known-committed withholding. The check-to-return interval described above remains
an explicit limit, not an atomic-delivery claim.

Selected methods also verify fresh URL/state/nonce/S256/verifier agreement, no
durable raw token/CSRF/verifier, pending replacement and old-cipher erasure,
expired-pending replacement, hidden claimed/provider-rejected behavior, ordinary
load rejection, raw duplicate/cookie/Origin/CSRF/route/metadata admission,
source/context/cipher mismatch rejection, both audit-only claim/rejection races,
same-revision concurrent one-winner CAS, foreign caller denial, Inspect/status
redaction, one deadline across both transactions and work, deferred COMMIT
rejection/loss/wait, committed-result withholding and cleanup.

Independent valid active-browser runtime rejection, all-field mutation and complete
failure-schedule matrices remain broader pending evidence. Active begin itself is
not implemented. No Application, Config, Vault, LifecycleRepo, identity verifier,
SQL helper, catalog, migration, provider, route or credential provisioning is
changed by this three-product-file slice. This handoff is producer evidence only;
independent review and root delivery decide local component acceptance.
