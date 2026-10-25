# Fixed preauthentication callback claim contract

Status: proposed source contract for independent review, 2026-10-25. No product
code, SQL, catalog, Application child, provider, HTTP route or browser readiness
changes are made by this packet. It continues the accepted private
[begin-login component](hosted-browser-begin-login-review.md) and the broader
[runtime contract](hosted-browser-lifecycle-runtime-contract.md). Sections 13,
17, 18 and 25 of the binding product plan remain required.

This lane owns this new document and
`verification/hosted-browser-callback-claim/` only. Root must assign any product
ownership after independent contract review. The recorded source closure binds
the accepted begin/preauth implementation; root delivery metadata may advance
independently. Computer use, capture, native runtimes and phones stay paused.
No frozen catalog-inspector/authority-driver or rejected Worker V2 source is read,
imported or executed.

## Selection and proposed ownership

Split implementation into two complete acceptance units. First implement the
fixed typed storage prerequisite **without a public callback entry or usable
Claim**. It can prove source binding, atomic consumption, exact comparison and
rollback against PostgreSQL before introducing a second process lifetime.
Then implement the bounded manual ClaimSupervisor, ClaimOwner and RuntimeOwner
join together. An opaque Claim must not be published by a partial owner join.
Neither unit performs provider exchange, OIDC verification, current access-token
verification, preparation/activation or authenticated result publication.

| Unit | Proposed files owned after root approval | Boundary |
| --- | --- | --- |
| A, typed storage | new `hosted/lib/mixer_hosted/browser_auth/callback_draft.ex`; existing `hosted/lib/mixer_hosted/browser_auth/store.ex`; new selected `hosted/test/mixer_hosted/browser_auth/callback_store_test.exs`; this document/evidence | Fixed discover/claim/provider-reject only. Existing owner leases and both current catalogs are mandatory. No callback orchestration or Claim publication. |
| B, private owner | new `hosted/lib/mixer_hosted/browser_auth/claim.ex`, `claim_owner.ex`, `claim_supervisor.ex`; existing `runtime_owner.ex`; new selected `callback_claim_test.exs`; this document/evidence | Fixed raw callback orchestration, bounded supervised secret custody, permit retention, caller-only explicit failure and cleanup. Store failure helper is added only with its closed owner authorization. |
| Root | PLAN/STATUS/work graph/gates, delivery and CI | Acceptance and coherent path-allowlisted delivery. |

Unit A needs no changes to Protocol, Vault, StoredSnapshot, LifecycleRepo,
RuntimeConfig, identity verifier, SQL helper, function/relation catalog or
migration. Existing claim/reject results are already decoded by StoredSnapshot.
The existing `fail_claim` boolean can support Unit B's explicit failure; no
snapshot result or terminal-load visibility is invented. Any discovered need
for SQL/catalog/migration change returns to root before editing those files.
No new dependency is proposed; only already pinned OTP/Elixir/Ecto/Postgrex and
existing product modules are used.

## Fixed parsing and current source boundary

The eventual **private** Unit B entry is:

```elixir
RuntimeOwner.claim_callback(raw_cookie, raw_headers, raw_query, raw_body, metadata)
```

There are no default arguments. `metadata` remains exactly `%{request_id: hex32}`
from trusted server code. `raw_cookie` is a canonical Protocol token. Require
`Protocol.parse_session_cookie(raw_headers) == {:ok, raw_cookie}` before any
database operation. Preserve the complete raw duplicate header pairs; no map or
pre-collapsed cookie projection is accepted. The existing Protocol enforces its
64-pair/16,384-byte bounds and duplicate/Authorization rejection. A callback does
not run begin's same-origin Origin/CSRF check: the expected provider GET is a
cross-site navigation; its browser cookie plus one-time state bind the attempt.
This is not an HTTP method/origin/ingress qualification.

Start the single original five-second operation deadline and wall sample at
entry, before parsing, reserve once, retain that exact lease/configuration and
call `Protocol.parse_callback(lease.runtime.browser_config, raw_query, raw_body)`
in this invocation. The raw body must be exactly `""`; raw query is 1..8,192 bytes.
Protocol requires canonical raw state, exact configured issuer after one decode,
and exactly code or sanitized provider error; it rejects duplicate/unknown keys,
encoded key aliases, mixed outcomes and invalid bounds. Code is opaque decoded
printable ASCII, 1..4,096 bytes, and must never be decoded again. A code such as
an encoded literal percent retains that literal byte. The parser already limits
the issuer to 2,048 bytes and discards provider error name/description/URI.

The result map is parsing data, never an authority or provenance ticket. Unit B
does not accept a caller-authored parsed callback. It immediately checks exact
three-key shape, canonical state, exact current Config issuer and the closed
outcome under its retained lease. A freshly parsed callback is not necessarily a
fresh callback: only durable pending state, browser/epoch/revision/configuration
binding, current expiry and atomic consumption establish that. Invalid parsing
causes no discovery or mutation. No raw query, code, cookie, state, error text,
URL, PKCE, nonce, CSRF, key, secret or ciphertext is emitted to logs/receipts.

The future HTTP adapter must independently enforce GET `/auth/callback`, exact
raw path, trusted Host/ingress origin, body/content-type policy, sensitive-query
log suppression and response/cache policy. No callback route is enabled here.

## Typed Store interfaces for Unit A

All new structs are exact-key, Inspect-redacted trusted application types. They
provide ownership clarity inside trusted BEAM code, not a sandbox against hostile
code with application credentials. No Repo, clock, module, SQL name, provider,
verifier, executor, endpoint or callback argument is added.

```elixir
%CallbackDraft.Discovery{lease: lease, cookie_digest: bytes32, state_digest: bytes32}
%CallbackDraft.Claim{lease: lease, source: committed_snapshot,
  verifier: canonical43, claim_secret: independent_raw32, claim_expires_at: integer}
%CallbackDraft.Reject{lease: lease, source: committed_snapshot}

Store.discover_callback(%CallbackDraft.Discovery{})
Store.claim(%CallbackDraft.Claim{}, metadata)
Store.provider_reject(%CallbackDraft.Reject{}, metadata)
```

Discovery returns only `{:ok, %StoredSnapshot{}}` from a confirmed committed read,
or the existing redacted Store.Failure. There is no nil-success callback outcome.
Claim/reject return only their confirmed committed exact StoredSnapshot or that
same failure shape. Store never returns PKCE, code or claim secret. Fixed errors
retain phase `admission|effect|decode|commit` and outcome
`not_started|rolled_back|committed|unknown`; no error authorizes automatic retry.

Failure receipts describe that Store call, not a combined facade operation:
invalid/foreign/altered draft or expired lease before checkout is
`admission/not_started`; a rejected operation inside an entered transaction is
its reached phase with `rolled_back`; a pre-COMMIT decode/full comparison failure
is `decode/rolled_back`. PostgreSQL ERROR class 23/40 or ERROR 57014/P0001
rejecting COMMIT is `commit/rolled_back`; FATAL/PANIC, driver/connection loss or
other ambiguous COMMIT acknowledgment is `commit/unknown`. An acknowledged
COMMIT followed by failed continuity/time checks is `commit/committed`, with the
snapshot withheld. Catalog drift inside admission is `admission/rolled_back`,
not `not_started`. The same existing owner `{:failed, lease, error}` path must
receive any authorized failure before its original deadline, so unknown results
and catalog admission failures invalidate readiness and advance generation.
There is no new arbitrary failure callback. Each of the three new fixed Store
operations owns its error reporting: before returning an authorized Failure it
synchronously sends the existing closed `{:failed, lease, error}` call to the
retained registered RuntimeOwner, as the actual lease caller and within the
original remaining deadline. Require the owner acknowledgment for a claim of
completed readiness invalidation/release. Foreign/malformed leases cannot affect
another slot; failed reports do not turn errors into success. If no acknowledgment
can be obtained by the original deadline, return the same unavailable Failure,
with no readiness assertion or new operation: existing expiry invalidation and
caller monitoring govern. This is a sampled owner acknowledgment, not atomic
cross-process revocation. Unit A has no production callback caller; its selected
test caller explicitly verifies acknowledged unknown/admission invalidation and
deadline cleanup. Unit B will own the full production orchestration. A successful
discovery keeps the original lease alive for the second transaction; Unit A's
test caller finishes/releases a successful terminal snapshot under the existing
exact caller protocol, without constructing a Claim.

The owner hashes canonical raw cookie/state ASCII bytes using the existing
SHA-256 convention. The digest in Discovery must equal the exact returned
pending attempt state; neither raw token enters SQL. The trusted code-claim
owner independently generates `claim_secret = :crypto.strong_rand_bytes(32)`
and `claim_digest = :crypto.hash(:sha256, claim_secret)`. This is separate from
cookie/state/nonce/PKCE/generation/reference randomness; a raw cookie/state,
their digest or local reference is never reused as the claim secret. Store
recomputes this digest from the exact 32 bytes for SQL and result comparison.

Discovery invokes only unchanged `mixer_browser_load(cookie_digest, config_digest)`.
Use the same strict preauth source checks as accepted Store plus exact nonnil
pending attempt, state digest, admitted Config profile/version/issuer/client/
redirect and `workspace` return route. Require the full attempt/source context
and sealed-envelope agreement, no claim/completion fields, and exclusive current
browser idle/absolute and attempt expiry. Active snapshots fail closed. Ordinary
load continues rejecting every projected attempt. Begin's allowance for replacing
an expired pending attempt must not widen callback discovery.

The current SQL projects only pending attempts in the current browser epoch.
Claimed/provider-rejected/completed/failed/superseded durable records are hidden
by load: they produce a live browser with nil attempt, not a resumable claim or
a distinguishable terminal status. Missing/revoked/expired/config-mismatched
browsers produce nil. Both outcomes reject callback discovery. Snapshot's ability
to decode claimed/provider-rejected results does not change load visibility.

## Two transactions, exact mutation and no retry

1. Reserve once under the original five-second deadline. Discovery performs
   current FunctionCatalog V2 and RelationCatalog checks in its own READ COMMITTED
   transaction/checkout, uses fixed LifecycleRepo, queue:false, existing exact
   LOCAL settings and remaining absolute driver deadline, then commits the
   encrypted source. No provider/current verifier/custody resolution runs there.
2. After that confirmed COMMIT, code-claim preparation opens the exact retained
   preauth session envelope and requires canonical CSRF matching its digest/AAD;
   explicitly require `:crypto.hash(:sha256, csrf) === source.browser["csrf_digest"]`.
   it opens the exact pending attempt envelope with existing Vault and requires
   the canonical `%Vault.Verifier{verifier: verifier}`. No new AEAD is introduced.
   Compare all source Config/cookie/state/epoch/revision/generation/profile and
   provider fields, including exact contexts and sealed bytes. This authenticates
   source integrity, not an authenticated user. Preserve PKCE and nonce digest
   before SQL erases the ciphertext. No PKCE is returned to the caller.
3. Fix claim expiry before mutation as
   `min(lease.started_at + 60, attempt.expires_at, browser.idle_expires_at,
   browser.absolute_expires_at)`. Check exclusive expiry and nondecreasing wall
   samples. A fixed deadline that SQL rejects because of clock disagreement
   fails closed. It is never extended or recomputed after a wait.
4. Store independently validates/authenticates the Claim draft **outside** the
   mutating transaction; Vault.open must never run in its transaction body.
   Then it begins a separate transaction under the **same** original lease and
   deadline. Both current catalogs must pass again in that checkout.
5. Invoke fixed load in that transaction first. Strictly decode and compare the
   entire rediscovered StoredSnapshot `=== draft.source`, including every browser
   field/audit sequence, both contexts, all sealed bytes and every attempt field.
   The helper's browser SHARE lock stays held. Nil, a hidden attempt, changed
   audit sequence, replacement or any malformed/different field rolls back.
6. Invoke only unchanged claim with cookie/state/config/source revision,
   independently recomputed claim digest, fixed expiry and request ID. Its
   SHARE-to-UPDATE upgrade may deadlock or lose serialization/lock admission.
   The loser rolls back and gets no Claim/provider exchange/retry. No authz lock
   is acquired by discovery/claim. Concurrent begin/logout/expiry retain their
   existing canonical lock behavior; this slice does not pre-lock then activate.
7. Decode and compare before COMMIT. The returned browser must equal the source
   browser with **only audit_sequence + 1**; epoch/revision/generation, identity
   linkage and every time/digest remain identical. Session envelope/context/
   cipher are identical. Attempt equals the source with only status `claimed`,
   exact independently computed raw32 claim digest, SQL claimed_at between the
   entry/current wall samples, exact fixed claim_expires_at, and key_id/iv/tag/
   ciphertext nil. Completion remains nil; ciphertext_version remains 1 and
   attempt_envelope is nil. All other attempt fields remain identical. Compare
   the whole map; pending cipher map fields are canonical PostgreSQL hex, while
   envelope sealed fields are decoded bytes. Never equate those representations.
8. Confirm COMMIT and all original lease/current dependency/configuration/time
   checks. Unit A returns only the private snapshot and releases no facade Claim.
   Unit B must retain its reserved slot as described below before publishing a
   handle. Unknown COMMIT invalidates readiness and drops every prepared secret;
   no second claim/discovery/reconstruction/provider exchange is attempted.

The provider-error outcome takes a separate fixed branch. It still opens and
authenticates the exact preauth session envelope outside the mutating transaction,
requires canonical CSRF and independently hashes it against the browser CSRF
digest; it needs no PKCE open, claim secret or ClaimOwner. Its committed encrypted discovery, exact Config/
cookie/state/current pending binding, same-checkout rediscovery/full source
comparison and original deadline are required. Invoke only unchanged
`mixer_browser_provider_reject`. Compare the entire browser with only audit +1,
identical session envelope and the entire attempt with only status and
completion_reason `provider_rejected`, erased cipher and nil claim fields.
It returns `provider_rejected` only after confirmed COMMIT and final publication
checks; uncertainty returns session_unavailable. Provider text never reappears.
Replay/hidden terminal state cannot produce a second rejection receipt.

## Unit B manual supervision prerequisite

Existing manually started bootstrap/load/begin remain usable without a claim
supervisor. `storage_ready` remains storage admission; it neither means claims
are supported nor enables browser authentication/readiness. A callback code
operation fails before SQL consumption if the claim supervision prerequisite is
absent, replaced or unhealthy. The fixed provider-reject branch can be accepted
independently without code-claim custody.

Proposed fixed manual setup: `RuntimeOwner.enable_claims/0` (no arguments) asks
the current admitted owner to start and retain a registered `ClaimSupervisor`
itself. Only that actual owner PID may invoke its fixed start-child wrapper.
The supervisor is a dedicated OTP DynamicSupervisor with at most 32 children;
only fixed ClaimOwner specs are used, and children are `restart: :temporary`.
The owner's parent link makes supervisor/children terminate on owner shutdown;
supervisor death/replacement invalidates claims and claim admission. It accepts
no injected supervisor, config, callback or child module. Existing RuntimeOwner
dependency monitoring and current identity/Repo PID checks still apply. Shared
Application wiring and automatic re-admission are outside this slice.

Child startup must not block the RuntimeOwner mailbox or use an unbounded
supervisor RPC as an end-to-end deadline. Reserve first; a fixed monitored
startup helper may wait on DynamicSupervisor while the request/owner observe
the original deadline. At most one such helper belongs to each of the 32 slots.
ClaimOwner init is dormant, retains the original deadline, monitors its actual
owner/caller, and performs no SQL/provider work. It must receive an exact
private arming handshake from the retained RuntimeOwner before mutation is
allowed. A late startup, timed-out request or removed slot cannot arm, and its
child/helper terminates. Retain explicit owned PID/monitor/timer identity so
cleanup never scans/stops unrelated processes. Test late-start cleanup, not
merely a successful synchronous start.

## One slot through setup, committed claim and retirement

The RuntimeOwner keeps a **single combined cap of 32 operations/claims**, with no
waiting queue. Its pool stays two connections. A claim is not a new free pool
lease, fleet quota or organization quota. The same reserved slot has these
closed phases: `operation -> staged_claim -> retained_claim -> terminal`.
Explicit failure may retain the slot in `terminal_cleanup` before `terminal`;
that local Claim is already unusable and the slot still counts toward 32.
All transitions match the exact retained original lease, actual GenServer caller,
owner PID/generation and private child/reference/arming token. Foreign/altered/
copied messages cannot remove, transfer, revive or extend somebody else's slot.

Before mutating SQL, create and acknowledge the dormant child and exact private
record while retaining the operation slot and original caller monitor. SQL
claim still executes in the original caller under its unchanged lease; no
transfer grants a different process authority over that in-flight transaction.
After confirmed claim COMMIT, a new closed `retain_claim` owner call atomically
replaces that slot's operation phase with the exact already-staged child and
committed snapshot. It does **not** call ordinary finish/release and then reserve
again. The combined count never falls during transfer or exceeds 32. The owner
and child both retain original caller monitoring and exact identity; child death,
caller death, explicit terminal failure or generation invalidation releases once.
Private timer tokens are separate from the copied handle/lease references.

Opaque `%MixerHosted.BrowserAuth.Claim{owner_pid: claim_owner_pid, reference: ref}`
has exactly those fields and redacted Inspect. It contains no raw cookie/state,
code, PKCE, nonce, claim secret, identity, config, SQL snapshot or endpoint.
ClaimOwner retains the original caller PID, immutable RuntimeOwner PID/generation/
Config digest/custody and registered default KeyOwner/ordinary Repo/LifecycleRepo
PIDs, raw32 claim secret/digest, canonical PKCE, nonce digest, bounded opaque code,
exact committed claimed snapshot and both exclusive lifetime bounds. These
records/messages/status/log/reason output are redacted. No secret lookup exists.

The five-second operation deadline still covers parsing, both transactions,
child setup/retention and private Claim publication. Separate claim custody is
bounded by the already fixed durable expiry and a monotonic deadline computed
from the **initial** operation sample plus at most 60,000 ms; neither begins anew
after SQL, process startup, transfer or a later call. Each fresh wall sample must
be >= the retained previous sample and < browser idle/absolute, attempt and claim
expiry. Equality, backward wall time or expired monotonic time denies and
retires. Timers do not extend authority. No clock is injected.

Publication uses a private retained-claim receipt containing checked_wall and
the exact child/reference. Original caller then samples the retained RuntimeOwner
under the original remaining operation deadline, requires unchanged ready
generation/dependency/supervisor binding, exact live child/reference and local
wall >= checked_wall, exclusive expiry and original monotonic deadline; sample
registered RuntimeOwner identity immediately before returning the handle. Known
COMMIT followed by loss withholds the handle (`commit/committed`). Failure to
retain/publish retires staged custody and leaves SQL consumed; it cannot make a
resumable claim. Cleanup after a successful final sample must not add another
blocking RPC before return. This is sampled private publication, not atomic
external delivery or an assurance about the scheduling interval after that sample.

## One use, failure and cleanup

There is no completion/provider entry in the selected claim component. A later
separately reviewed completion must atomically change the local state from
`retained` to `exchange_started` **before** any provider call and require actual
original GenServer caller identity, exact handle and current owner/config/default
identity PID continuity. It must never accept fake/injected verifier/provider,
fabricated VerifiedIdentity, saved TrustSnapshot or caller-selected clock.
Default KeyOwner PID continuity alone does not attest same-PID trust/JWKS
generation. Later activation still requires current default authenticate/2 and
its finish checks; no stronger current-generation API is assumed here.

Unit B may add only `RuntimeOwner.fail_claim(claim, :session_failed, metadata)`
for caller-initiated abandonment before exchange. Other reason atoms in SQL are
reserved for actual later provider/OIDC/identity failures. Original caller only;
mark local state terminal atomically before initiating that one SQL attempt.
The exact child obtains a closed cleanup lease from its retained slot, bounded
by min(now + 5,000 ms, original claim monotonic deadline) and original durable
expiry, with actual child caller/owner/generation matching. It cannot reserve a
33rd slot or use an expired initial operation lease. Store.fail_claim accepts
only the new exact Failure draft containing that lease, committed claim snapshot,
raw32 claim secret and fixed reason; no generic operation/executor is exported.

Freeze these proposed Unit B types before dependent implementation:

```elixir
%CallbackDraft.CleanupLease{owner: runtime_owner_pid, reference: original_slot_ref,
  caller: exact_claim_owner_pid, original_caller: original_request_pid,
  generation: retained_runtime_generation, deadline: bounded_cleanup_deadline,
  started_at: cleanup_wall_sample, claim_reference: exact_claim_ref,
  runtime: retained_runtime_config}
%CallbackDraft.Failure{lease: cleanup_lease, source: committed_claim_snapshot,
  claim_secret: independent_raw32, reason: :session_failed}
Store.fail_claim(%CallbackDraft.Failure{}, metadata)
```

Both are exact-key/Inspect-redacted. The cleanup lease is distinct from an
ordinary PreauthDraft.Lease and cannot authorize bootstrap/load/begin/claim.
RuntimeOwner retains the exact cleanup lease and checks actual child caller plus
same original request, slot, claim and owner generation. Its expiry token is
separate private state. Only the already caller-authorized terminal transition
can mint it, once; a timer/crash cannot. Cleanup success/failure/expiry releases
the counted slot once, even though local use was consumed before SQL started.

Use only the unchanged exact cookie/state/config/claim-digest helper. Its boolean
`true` plus confirmed COMMIT proves a failed transition; it returns no snapshot,
so do not claim an independently compared post-state or revision/audit receipt.
Unknown outcome invalidates readiness; second use and automatic retry deny.

Timer expiry, caller death, owner crash/restart/configuration generation change,
supervisor/child loss and inability to publish retire local custody and release
exactly its own slot without provider exchange. They do **not** automatically
call fail_claim: expiry equality can already make SQL failure illegal, and no
unfenced retry/cleanup lease is inferred from a timer. The SQL `claimed` tombstone
may remain claimed until existing expiry/replacement machinery; consumed does
not mean status changed to failed. A later begin may supersede it via its
existing SQL rules. Another replica/load cannot reconstruct the erased verifier
or raw claim secret. BEAM memory zeroization is not promised.

## Required executable acceptance and current limits

The packet checker is documentation/source-binding evidence only. It records
commands, Python/Git versions, exact revision, selected source/context hashes,
output hashes and that it starts no DB/BEAM/native/capture/provider process.
It does not establish runtime security. All runtime cases below are pending:

- A: exact raw cookie/state/config/pending binding and active/expired/hidden
  claim/terminal denial; both committed discovery and mutating catalog checks;
  valid Vault/source agreement; all-field/context/cipher mismatch rollback;
  exact claimed/rejected post-state and audit-only race controls; two SHARE
  upgrade contenders with at most one winner; begin/reject/claim drift; wrong
  browser/state; original deadline and exclusive expiry; deferred COMMIT
  rejection/loss/wait; zero provider exchange and no retry on every failure.
- B: actual caller-only, copied/altered/foreign/second-use denial; combined cap32
  through setup/retention/terminal and two-pool no-queue pressure; absent/replaced
  supervisor; late startup/arming/COMMIT/retention/publication loss; caller and
  child death; owner/default identity/Repo PID/configuration generation loss;
  exact timer spoof resistance; wall rollback/expiry equality; private
  publication withholding; explicit failure's one bounded SQL attempt, unknown
  outcome and double-use; owned supervisor/helper/child/fixture cleanup.

Each runtime runner must compile only its exact selected projectless source
closure with warnings as errors and pinned existing BEAM dependencies. Use one
owned random-loopback PostgreSQL fixture with immutable inputs, restricted roles,
actual default KeyOwner and fixed pool; no fake current verifier/provider. Bind
tool versions, source/dependency/output hashes and exact postmaster/data inode
identity; preserve every failed attempt and cleanup receipt. No broad hosted
harness, unrelated process discovery, provider/credential/customer/production
exchange or native runtime is permitted. Root coordinates PG17 producer and
independent PG16 review after the interface freeze.

Original complete 40-case owner, 18-case lifecycle, 48-case relation, full
authorization/HTTP/native/FieldLog/provider/Neon/operator/GA qualification remains
pending. This storage/claim contract does not narrow those gates or qualify an
authenticated browser session. No GA gate is promoted by this document.
