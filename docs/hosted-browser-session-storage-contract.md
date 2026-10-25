# Proposed durable browser session and lifecycle contract

Status: root selected the four design directions below on 2026-10-25. Product
implementation, migration and deployment remain unselected by this contract. It
does not activate login, select a provider, grant a runtime role, run a migration,
or pass a customer, deployment, browser or GA gate. It refines the durable-storage
prerequisite in [the console identity contract](console-identity-flow-contract.md)
without replacing the binding product plan. Only the ordinary identity,
authorization and audit contracts were examined. Frozen hosted lanes were not
read, imported, compiled or executed.

## Root-selected design direction

1. Root reserves the next additive migration `20261025000007`; this lane does
   not edit it. There are eight current migration files, ending at
   `20261025000006`; their count is not their suffix. Existing eight-migration
   fixture expectations must change in the implementation slice, not here.
2. Use a separate bounded lifecycle Repo/pool with a distinct restricted database
   login. The ordinary bearer/API login retains its existing SELECT-only authz
   topology. The lifecycle login receives only specifically named function
   EXECUTE grants, never authz/vault table DML or membership in a writer/owner role.
3. Beginning replacement login increments the browser epoch and supersedes older
   attempts, while retaining its current authenticated family until successful
   activation. Activation atomically revokes that family. Logout revokes it
   immediately and invalidates the epoch. Failure cannot create a new family.
4. Keep browser rows, attempts, encrypted vault and authz rows in the **same Neon
   PostgreSQL database**, isolated by grants/RLS rather than by a second database.
   The final activation is one transaction. A distributed pending-to-active
   compensation protocol is unnecessary and would weaken this initial slice.

No product file or migration is owned by this contract lane. Root agreed these
defaults for the implementation-ready contract, rather than authorizing this
lane to begin product implementation. Backend routes are still absent; root's
fixed same-origin console transport is a separate component.

## Authority and capability boundary

The browser supplies only an opaque cookie, synchronizer CSRF, closed return-route
enum and a callback already accepted by `BrowserAuth.Protocol.parse_callback/3`.
It never supplies profile, issuer, client, principal, family, credential reference,
scope, revision, membership or audit actor. The Protocol result is parsing evidence,
not authentication or durable claim authority. Its successful provider-error
outcome must also consume the matching attempt once.

The production transaction owner accepts a raw provider access token only from
the bounded, separately reviewed code exchange. It calls the current default
`Identity.ConfiguredVerifier.authenticate(token, fresh_now)` before activation.
It must not accept a caller-supplied `VerifiedIdentity`, use an ID token as API
bearer, or call pure `AccessTokenVerifier.verify/3` with a retained trust snapshot.
The verifier returns exact profile/version/issuer/subject/client, human class,
`jti` as credential reference, `iat`, `exp` and admitted scopes. Those values are
the only external-identity inputs to lifecycle SQL.

A separate qualified OIDC verifier must have validated ID-token signature,
algorithm, issuer, client/audience/authorized-party, time and the claimed nonce.
The initial adapter additionally requires exact equality of OIDC issuer, subject
and client to the API identity. A provider with differing subject namespaces
requires a separately qualified explicit stable binding; this adapter denies it.
Email, name, domain, groups and unverified claims never link identities.

Inside the transaction, resolve the existing active binding under the exact human
profile/version/issuer/client/subject to the existing active human principal.
Verify current profile state and binding revision, current principal fence and
all retained linkage after locks. Unknown binding is onboarding-required. No
first-user owner, membership, organization, project, grant, trust profile or
external-identity link is created. Existing tenant heads are unaffected because
this writer changes no tenancy or membership state.

The SQL functions are a controlled capability for trusted application code, not
a cryptographic database proof of provider verification. Neither an Elixir struct
nor a caller-set GUC protects against hostile code with the lifecycle application's
credentials. The separate pool, narrow fixed operations, current verifier owner
and reviewed caller graph are part of this boundary; the design must not claim
to withstand a compromised lifecycle process or database owner.

## Bounded durable records

Names are proposed public-schema relations so the existing migration/owner model
can qualify them. Use ENABLE and FORCE RLS on every relation, revoke all PUBLIC
privileges, and expose no runtime table/column privileges. All digests are 32-byte
`bytea`; their wire representation is exactly Protocol's canonical 43-character
base64url SHA-256 output. Convert once with validated canonical decoding. All
times/revisions use the existing integer Unix-seconds / `1..2^53-1` bounds.

| Relation | Required columns and invariant |
| --- | --- |
| `mixer_browser_sessions` | Server-generated random 16-byte internal `id` PK; unique 32-byte `cookie_digest`; `status` exactly `preauth`, `active`, `revoked` or `expired`; positive `epoch` and `revision`; current random canonical43 public `generation`, stored verbatim because it grants no authority; `csrf_digest`; `created_at`, `last_seen_at`, `absolute_expires_at`, `idle_expires_at`; nullable exact `(profile_id,profile_version,principal_id,family_id,credential_ref,credential_revision)`; immutable initial configuration digest plus current configuration digest; `audit_sequence`. Preauth has no authz links. Active has all links and matching FK to existing family/credential. Revoked/expired cannot reactivate. Rows are not transferred to another browser or principal. |
| `mixer_browser_session_vault` | One row per browser PK/FK; exact `epoch`, session `revision`, positive incrementing `vault_generation`, `ciphertext_version=1`, key identifier, 12-byte AES-GCM IV, 16-byte tag and bounded ciphertext. Preauth plaintext is closed `[1,csrf]`; active plaintext is closed `[2,csrf,access_token]`. CSRF is canonical43; access token is at most 4,089 bytes. Maximum ciphertext 8 KiB. No refresh/ID token. SQL/Elixir validate exact envelope kind and linkage, not an arbitrary JSON map. |
| `mixer_browser_oidc_attempts` | 32-byte `state_digest` PK, browser FK, saved browser epoch/revision, fixed configuration digest, exact profile/version/issuer/client/redirect and return enum `workspace`; `nonce_digest`, encrypted PKCE verifier with independent IV/tag/key/AAD, `created_at`, exclusive `expires_at <= created_at+300`; state exactly `pending`, `claimed`, `provider_rejected`, `completed`, `failed` or `superseded`; optional one-use `claim_digest`, `claimed_at`, exclusive `claim_expires_at <= expires_at`; completion reason from a closed enum. At most one pending/claimed attempt for a browser epoch. No code, raw state, raw nonce, authorization URL or provider response is stored. |
| `mixer_browser_session_events` | Append-only PK `(browser_id,sequence)`; fixed `audit_schema=1`, closed operation/outcome enums, server request ID, fresh recorded time, old/new browser revision/epoch/status, fixed configuration digest, optional attempt-state digest, profile/version, exact internal principal/family, domain-separated hashes of external issuer/subject/client/jti, observed profile/binding/principal/family/credential revisions, and token `iat/exp` only for activation. Event values are derived by SQL from locked old/new rows and validated verified fields, never an arbitrary event JSON supplied by HTTP. No CSRF, cookie, token, PKCE, code, raw subject/issuer/client, provider text or tenant membership. |

Configuration digest is SHA-256 of the exact immutable validated browser-auth
configuration representation, including its expected identity profile/version and
endpoints but excluding secret values. Secret-manager/key version references may
be included; client credentials and encryption keys may not. A different digest
invalidates attempts; it cannot silently redirect an existing claim.

Authz family IDs are generated independently by the server CSPRNG, for example
`browser_` plus 43 canonical base64url characters. Never use provider `sid`, the
cookie, state, subject or principal as family ID. INSERT only; any collision fails
closed and requires a new attempt. Authz credential PK
`(profile_id,profile_version,jti)` also uses INSERT only. Any existing row,
including an inactive or expired tombstone, denies activation. Never reuse,
upsert, transfer or resurrect a family or credential. Retain authz tombstones and
their immutable linkage; no runtime DELETE/TRUNCATE privilege exists.

The new stream is lifecycle audit, independently versioned from
`Audit.CustomerArtifactEvent` v2 and historical `UploadEvent` v1. It is not an
artifact audit event, does not invent a tenant, and makes no historical wire/hash
compatibility claim. A fixed operation must append exactly one matching event and
increment `audit_sequence` by one in the same transaction as its state change.
Deferred constraints reject a mutation without that event or an event without
its transition. Rejections before a valid browser/attempt claim are sanitized
operational observations, not invented successful lifecycle events. Durable audit
failure rolls back activation or logout. Owner-level coherent rewriting remains
outside runtime immutability; independent retention/checkpoints remain pending.

## Encryption and custody

Use platform `:crypto` AES-256-GCM authenticated encryption with an externally
supplied 32-byte key and fresh independent 96-bit random IV per encryption.
Standard AEAD is required; do not implement a cipher. Key material is supplied
only to the API lifecycle owner from reviewed secure runtime custody. The
database stores only a bounded key identifier, IV, tag and ciphertext. No source,
fixture default, Vite asset, build worker, log, Oban argument or database setting
contains the key. Missing key/version, bad tag, unknown envelope, mismatched AAD,
oversized ciphertext or malformed plaintext is unavailable and clears readiness.

AAD is a closed deterministic length-prefixed byte encoding with a separate
`mixer.browser.vault.v1\0` or `mixer.browser.attempt.v1\0` domain. Vault AAD binds
browser ID, cookie digest, epoch, session revision, vault generation, ciphertext
version, explicit expected configuration profile/version, configuration digest,
envelope kind and exact optional authz linkage. Attempt AAD binds ciphertext
version, state digest, browser ID/epoch, config digest, exact
profile/version/client/redirect and attempt expiry. The implementation must
specify and independently compare those
bytes; string concatenation without lengths is forbidden. Copying a ciphertext
between rows/generations/attempts must fail authentication.

Preauth CSRF must also be recoverable from encrypted custody: a digest alone
cannot return the same synchronizer token on a later `/auth/session` read.
Decrypt only after a successful bounded lookup and verify the plaintext CSRF
digest. The application validates token length/type before use. Keys/decryption
stay outside SQL; SQL never returns plaintext secrets. Raw provider tokens remain
only in bounded memory until encrypted/used and are never exposed in errors.
Memory zeroization is not promised by BEAM. Initial code has one configured key
version and no runtime rotation workflow; production key rotation/recovery is a
separate qualification gate, not permission to create/change credentials here.

## Exact internal API

Proposed namespace: `MixerHosted.BrowserAuth.Sessions`. HTTP callers cannot choose
Repo, verifier, clock, key, profile, endpoint, family or SQL function. Trusted
fixture variants remain distinct and are never routed in production.

```elixir
bootstrap(cookie_or_nil, request_metadata)
  # {:ok, %{cookie: :unchanged | {:set, raw_cookie, deadline},
  #          session: %{state: :unauthenticated, csrf_token: csrf} |
  #                   %{state: :authenticated, generation: generation,
  #                     expires_at: deadline, csrf_token: csrf}}}

begin_login(raw_cookie, raw_csrf, :workspace, request_metadata)
  # {:ok, %{authorization_url: bounded_url}}; existing cookie stays unchanged

claim_callback(raw_cookie, protocol_callback, request_metadata)
  # {:ok, %Claim{...}} for a code outcome, only after durable claim commit
  # {:error, :provider_rejected} after durable consumption of that outcome

complete_login(claim, bounded_exchange_result, verified_oidc_result, request_metadata)
  # owner calls current default access verifier; caller cannot supply its identity
  # {:ok, %{cookie: {:set, fresh_raw_cookie, deadline}, redirect: :workspace}}

fail_claim(claim, closed_failure_reason, request_metadata)
  # :ok only after a durable failed/tombstoned claim; never retry code exchange

logout(raw_cookie, raw_csrf, request_metadata)
  # {:ok, %{cookie: :clear}} only after confirmed durable revocation

with_workspace_access(raw_cookie, request_metadata, fixed_dispatcher)
  # callback receives access token only in trusted server code; returns bounded
  # ordinary /v3 workspace response after ordinary default verifier/Repo admission
```

`Claim` is an owner-process-bound opaque reference plus random one-use claim secret,
browser/state digests, saved epoch/config digest, nonce digest, exact verifier,
redirect and exclusive deadline. It grants only one completion/failure for the
already claimed attempt. It is not permission, a `VerifiedIdentity`, an authz
transaction Context or a durable bearer ticket. A restarted worker cannot resume
exchange from an exposed claim. Claim lookup and final SQL require its digest,
current exact durable state and deadline; a copied map/foreign process/reused
reference is rejected by the owner. Database fencing still applies across replicas.

The token exchange/qualified ID-token verifier remains a prerequisite; these APIs
must not provide an injectable HTTP/provider callback to request code. Request
metadata is exactly a server-generated 32-lowercase-hex request ID and optional
trusted canonical ingress IP. It conveys no authority. Public errors are closed:
`invalid_request`, `unauthenticated`, `provider_rejected`, `onboarding_required`,
`identity_unavailable`, `authorization_unavailable`, `session_unavailable`.
Never include provider error strings, SQL errors, cookies or external identity.

For the fixed workspace dispatcher, load a versioned encrypted active snapshot,
decrypt outside database locks, then run the **ordinary protected pipeline** with
the exact access token. It must invoke current default verification and ordinary
authorization, not dispatch using saved identity/linkage. No arbitrary path,
method, headers or remote destination is accepted. Family locks serialize this
ordinary request with logout/replacement: an admitted request may finish before
revocation returns; after revocation success a new request denies. The returned
token/snapshot never reaches browser JSON. Root owns this fixed dispatcher and
console capability composition.

## Transaction and lock protocol

Use one lifecycle connection/transaction per operation, READ COMMITTED, `queue:
false`, five-second total/statement/idle bounds and 500-ms lock timeout, with no
automatic transaction retry. Do not join an unknown existing transaction. No
provider request, current-verifier/JWKS request, KMS network call or user callback
runs while database locks are held. Prepare encryption/decryption outside locks;
recheck exact source revision/epoch under locks before publishing its result.

Global lock order for a transaction touching authz is:

1. Affected profiles `(id,version)` sorted by exact UTF-8 identity, then existing
   principals sorted by ID. Read exact binding only after profile lock; it is
   immutable linkage and binding writers must conflict on that profile fence.
2. Every affected existing family sorted by ID, then every affected credential
   sorted by `(profile_id,profile_version,reference)`. Use conflicting UPDATE
   locks for revocation/activation and SHARE for read-only current-session checks.
   Newly inserted family/credential PKs are unique insertion claims, not a reason
   to skip existing locks. Never lock a credential first to discover its family.
3. Browser row, then attempt rows sorted by state digest, then vault row. Browser
   revision/epoch is re-read after the final wait. Rows with absent authz linkage
   use only this final order.

Existing ordinary requests retain profile → principal → family → credential →
tenant-head SHARE locks. A browser-only bootstrap/begin/claim transaction never
later requests authz locks. Activation/logout use an initial **unlocked bounded
projection** only to discover expected authz IDs; after taking canonical locks
and the browser lock they compare every discovered link/revision. If it changed,
roll back and require a new operation; never follow a replacement linkage while
holding an incomplete lock set. Different old/new profile/principal values are
both locked canonically. No tenant heads are taken for unchanged membership.

Every decision uses fresh trusted time after the last wait and immediately before
effects/private result. Require `now < attempt expiry`, `now < claim expiry`,
`now < token exp` and all current browser/family/credential windows; at equality
deny. No expiry grace or cookie-derived token extension. Existing future `iat/nbf`
allowance remains the current verifier policy. Guard every positive revision and
sequence increment against `2^53-1` overflow. SQL error, timeout, exception,
malformed callback, failed final invariant or audit failure rolls back everything.
An ambiguous commit returns unavailable and never issues a new authenticated
cookie. A bounded commit may finish just after the last time check; this contract
does not claim atomicity with the passage of wall-clock time.

## Operation algorithms

**Bootstrap.** With no valid cookie, generate independent cookie, generation and
CSRF from the CSPRNG; encrypt the preauth envelope outside locks; one browser-only
transaction inserts a 300-second preauth row/vault and event. Reuse an existing
live preauth envelope without sliding its absolute deadline. Active inspection
loads/decrypts a bounded versioned snapshot, calls the current default verifier
outside locks, then uses canonical identity/browser locks and fresh stored state
to validate exact credential/family/binding/config/vault linkage. Readiness never
implies membership. Idle extension, if performed, is bounded by the token-backed
absolute deadline and updates envelope/AAD/revision atomically. Expiry returns
sign-in state; database/verifier failure returns unavailable, not successful logout.

**Begin.** Exact Origin/CSRF checks precede side effects. Generate independent
state, nonce and verifier with Protocol; retain only state/nonce digests and
encrypted verifier. Under browser lock require a live preauth or active row,
matching CSRF/config/revision; increment epoch, mark all earlier pending/claimed
attempts superseded and insert one pending attempt with that new epoch, fixed
redirect and bounded expiry. Reencrypt browser vault with the new AAD/epoch in the
same transaction. The existing active family remains usable until replacement
activation. Return a URL built only from configured endpoints/closed parameters
after commit. Failed URL construction/encryption must occur before that commit.

**Claim.** Parse and issuer-check with Protocol first. Load the bounded encrypted
attempt snapshot and recover its verifier into bounded owner memory outside locks;
this preliminary read grants no claim or provider permission. Under browser → attempt
locks require cookie digest, live browser, matching state, current saved epoch,
configuration digest, exact recovered ciphertext/revision and exclusive expiry.
A single conditional UPDATE
`... WHERE status='pending' AND browser_epoch=$expected ... RETURNING ...`
changes it to claimed with independent random claim digest and deadline, erasing
the durable verifier ciphertext only after its matching plaintext is already in
bounded owner memory. Check row count exactly one. A validated provider-error
callback does not need to decrypt PKCE and instead consumes it
directly to `provider_rejected`, appends an event and performs no provider I/O.
Return plaintext verifier/nonce digest only after durable claim commit. Duplicate,
other-browser, stale-epoch, expired or superseded claims deny. Concurrent replicas
cannot both consume the row. Uncertain claim commit performs no exchange.

**Exchange outside locks.** Use the claimed verifier/exact redirect/configured
client authentication once, under the separate bounded provider adapter. Never
retry a possibly consumed code after timeout, disconnect or ambiguous result.
Any failure leaves the attempt consumed and requires a new login. Do not persist
the code, ID token, provider error or response body. Apply qualified OIDC checks,
current default API verification and exact identity relation outside locks.

**Activate.** Generate fresh cookie, public generation, CSRF and non-recycled
family ID; encrypt the active envelope outside locks using expected new epoch/
revision/linkage. Canonically lock both the incoming exact existing identity and
any currently active replaced identity; lock existing old family/credential and
then browser/claimed attempt/vault. Re-read current profile/binding/principal,
saved epoch/config/claim/deadlines and old linkage. Require human class, exact
issuer/client/profile/subject, `mixer.workspace.read`, current active principal,
`verified iat >= principal.not_before`, and current token expiry. New family and
credential use revision 1, `not_before=min(verified iat,fresh now)` and
`expires_at=verified exp`; using `now` alone would incorrectly deny tokens issued
slightly earlier. This does not bypass the principal's current valid-after fence.

Insert family/credential with no conflict handler. Revoke the previous local
family under its UPDATE lock and every admitted credential in it, incrementing
their revisions once; never move credentials to the new family. Initial browser
families admit exactly one credential and no refresh; enumerate at most two and
fail unavailable on a second unexpected registration until refresh is implemented.
Rotate browser cookie digest/CSRF/generation, increment epoch/revision, set active
linkage, replace encrypted vault and complete the attempt in this same transaction.
Absolute/idle expiry is no later than token `exp` and `fresh now+900`. Append the
closed activation/replacement audit transition atomically. No usable pending
family or authenticated cookie is visible before commit. There is no separate
activation transaction and no durable plaintext token. If response delivery fails
after commit, the old cookie is invalid; the new family expires normally and a
new interactive login is required. Never reconstruct/re-send the new cookie from
an old-cookie tombstone.

**Logout.** Exact Origin/CSRF, bounded unlocked link discovery, then canonical
authz locks → browser → attempts → vault. Re-read exact discovery/epoch/revision;
revoke the local family and all its admitted credentials under conflicting locks,
increment their revisions, mark browser revoked with a higher epoch/revision,
supersede outstanding attempts, erase vault ciphertext and append audit in one
transaction. Repeating a confirmed revoked-cookie logout is harmless after the
same CSRF proof retained as digest, but never revives or returns secret material.
Return 204/clear-cookie only after confirmed commit. Storage unavailable retains
the browser cookie for retry and clears client private views without claiming
success. This is local Mixer revocation, not provider logout. A late exchange
result cannot activate because the browser epoch/status/claim no longer matches.

**Expiry/cleanup.** Current-time admission denies expired sessions/families even
before cleanup. A separately bounded worker uses the same canonical protocol to
mark expired browser rows, supersede attempts, erase ciphertext and append expiry
audit; it cannot remove family/credential tombstones or invent activity. Initial
retention proposal: erase consumed attempt verifier ciphertext immediately at
claim/failure/completion; retain its consumed metadata for at least 24 hours after
expiry, then remove only through a later reviewed retention writer. Claimed
verifier is already in bounded owner memory when erased. Browser/authz audit and
revocation retention, rate limits, cleanup scheduling and operational bounds need
implementation/qualification; no unbounded cleanup scan is acceptable.

## Controlled SQL and role topology

Proposed fixed helpers, each with exact typed arguments/results and no overloads:
`mixer_browser_bootstrap`, `mixer_browser_load`, `mixer_browser_begin`,
`mixer_browser_claim`, `mixer_browser_activate`, `mixer_browser_fail_claim`,
`mixer_browser_logout`, `mixer_browser_expire`. Read/claim results expose ciphertext
and bounded metadata only. Helpers implement the algorithms above; they must not
accept SQL, operation names, arbitrary GUC context, dynamic relation names or
arbitrary audit data. All identifiers/data are parameters. Never construct SQL
from provider/browser text.

Use a dedicated non-login, non-superuser, non-BYPASSRLS, non-owner writer role.
It owns these fixed SECURITY DEFINER functions with `search_path=pg_catalog` and
fully qualified objects, but owns no relation/schema. Grant it only the exact
authz/browser columns and operations needed by the fixed helpers. Explicit
role-targeted RLS permits that role's bounded lifecycle read/write operations;
it does not disable FORCE RLS or make the ordinary caller a table writer. The
relation owner remains separate non-login/non-bypass authority. Revoke PUBLIC
function execution; lifecycle login gets EXECUTE only on selected helpers and
no direct table privileges. Do not grant it membership in either writer/owner,
CREATE in a protected schema, unsafe existing helper execution, predefined `pg_`
roles, CREATEROLE/CREATEDB/replication authority, or SET ROLE paths. Existing authz
scoped read/lock policies and ordinary runtime topology remain intact.

Row-lock grants are explicit: PostgreSQL `SELECT ... FOR SHARE/UPDATE` needs
appropriate UPDATE privilege beyond SELECT. Grant the fixed-function owner only
`UPDATE(state_revision)` on profiles and `UPDATE(revision)` on principals for
their locks, with role-targeted SELECT/UPDATE USING policies and `WITH CHECK
(false)` so it cannot actually change either relation. Binding SELECT is enough
because its profile fence serializes binding changes. The application login
receives none of these column privileges. Family/credential locking uses the
same narrow mutable-column privileges needed for their actual lifecycle changes.

The internal writer role may SELECT/INSERT family and credential records and
UPDATE only active/revision/window fields as specified, never UPDATE their PK or
linkage and never DELETE. It may SELECT/UPDATE browser state, insert attempts,
update only their closed state/fencing/ciphertext fields, replace/erase vault
ciphertext and INSERT typed audit events. No grants cover principals/bindings/
profiles/memberships/tenants except bounded SELECT and row-lock requirements.
Audit event UPDATE/DELETE/TRUNCATE remains unavailable even to this writer.
Independently re-run the current ordinary authz role/RLS invariants after adding
role-targeted policies: permissive policy OR-composition must not widen ordinary
read visibility, permit its DML/column-DML, grant it writer EXECUTE, or let it
reach the writer/owner role. Both existing helper ownership and new fixed writer
ownership must remain non-login/non-bypass and unreachable by ordinary logins.

Before startup admission and each protected lifecycle transaction, validate exact
login/session-user equality, all reachable roles, relation owners/FORCE RLS,
role-targeted policies, table/column grants, expected function signature/body/
ownership/search_path/ACL, no PUBLIC execution, no writable views or unreviewed
writer overloads, and no schema CREATE. An ordinary read-only adapter must not
gain these EXECUTE grants implicitly. Migration creates no production login,
password, key or provider credential; deployment/operator grants are separate
reviewed operations. A disposable fixture can create synthetic roles explicitly.

## Required implementation evidence

The matrix in `verification/hosted-browser-session-storage-contract/` is pending
product evidence, not an executable design model. The implementation must run
focused ExUnit plus real disposable PostgreSQL tests through the restricted
lifecycle login and ordinary runtime, with exact source/tool/output/cleanup binds.

Required cases include the existing ordinary authz RLS/role invariants after new
policies and column-lock grants; exact existing binding and no bootstrap; current default
verifier provenance; unknown/reused/inactive jti; family non-recycling; runtime
role/RLS/DML/SET ROLE denial; AEAD row/generation/key/AAD substitution; independent
CSRF recovery; restart/multi-replica one-use claim; provider-error consumption;
duplicate/cross-browser/stale config/epoch/claim expiry; concurrent begin/claim;
logout versus callback in both orders; network result arriving after logout;
replacement versus old ordinary request in both lock orders; all-or-none audit/
vault/family/credential activation; commit/response uncertainty; exact expiry after
lock waits; revoked-browser denial; all-family token revocation; bounded cleanup;
and nine-migration apply/rollback/reapply if the proposed migration is selected.
The actual provider adapter, OIDC validator, Phoenix route join, Neon deployment
roles/key custody, ingress/cookie/cache/logging, customer acceptance and GA review
remain pending. Browser/capture/native runtime/phones remain paused; no such
process or production change is started by this contract.
