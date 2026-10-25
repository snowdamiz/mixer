# Browser lifecycle runtime owner and admission contract

Contract version 1, proposed for root integration on 2026-10-25. This is an
implementation contract, not runtime implementation or acceptance. It extends
[the selected storage contract](hosted-browser-session-storage-contract.md) and
[the reviewed component checkpoint](hosted-browser-session-integration.md).
Sections 13, 17, 18 and 25 of the binding product plan remain required. The
reviewed baseline is `7e434330cad8e3566a4a21a6d7ff996da3bc4967`.

No new HTTP route, browser readiness response, provider, credential, grant or
migration is activated by this document. Unknown exact identity binding remains
`onboarding_required`; no tenant, membership, principal, trust profile or first
owner is created. Browser/capture/native runtime/phones remain paused. This lane
owns only this document and its verification directory. Frozen catalog-inspector,
authority-driver and rejected outbound Worker V2 lanes were not consulted.

## Public internal interfaces and ownership

These are trusted application interfaces, never request-selected modules,
repositories, clocks, keys, SQL names, provider callbacks or destinations. Opaque
references/structs express ownership inside trusted BEAM code; they do not defend
against arbitrary hostile code running with its credentials.

| Module | Exact interface and responsibility |
| --- | --- |
| `MixerHosted.BrowserAuth.LifecycleRepo` | Separate `Ecto.Repo`, `otp_app: :mixer_hosted`, Postgrex adapter; used only by lifecycle storage. It is never the ordinary `MixerHosted.Repo`, Oban Repo, migration Repo or a request argument. |
| `MixerHosted.BrowserAuth.Custody` | `new(reference, %{reference: reference, key_id: id, key_bytes: bytes}) -> {:ok, custody} \| {:error, :session_unavailable}`. Exact keys only; validates configured reference equality and calls existing `Vault.key/2` for external bytes32/key ID. Inspect exposes no fields. No resolver, environment read, KMS call, key generation or credential update occurs here. |
| `MixerHosted.BrowserAuth.RuntimeConfig` | `new(browser_env, hosted_config, lifecycle_repo_config, custody) -> {:ok, config} \| {:error, :session_unavailable}`. Receives the trusted validated `MixerHosted.RuntimeConfig` used for live startup, calls `Config.load(browser_env, hosted_config.role, hosted_config.identity_startup)`, then `ConfigurationDigest.digest/1`. Uses hosted_config.repo for the exact ordinary connection and validates separate connection/custody binding below; never hardcodes :api or accepts unrelated startup/Repo lists. Struct shape alone proves no provenance. Disabled browser mode returns a disabled runtime config and forbids lifecycle/custody settings. Inspect exposes only mode and connection bound. |
| `MixerHosted.BrowserAuth.RuntimeSupervisor` | `start_link(runtime_config)` supervises the dedicated Repo and owner only for configured API mode. No processor child or fallback pool. Owner starts after the ordinary configured identity owner and dedicated pool; startup admission is mandatory. |
| `MixerHosted.BrowserAuth.RuntimeOwner` | `start_link(runtime_config)` and `status/0 -> %{phase: :disabled \| :unavailable \| :storage_ready, generation: non_neg_integer}`. Owns custody/configuration, bounded operation admission and monitors its Repo and the registered default identity owner. `storage_ready` is internal storage admission only, never browser authentication readiness. Replacement/death clears readiness and invalidates owned claims; re-admission is required. |
| `MixerHosted.BrowserAuth.Catalog` | `admit!/0 -> :ok`; private to an owned LifecycleRepo transaction, with failure causing rollback. Reads only ordinary PostgreSQL catalogs through fixed statements. It compares the compiled expected manifest and explicit trusted role names, never values learned from an untrusted caller. No cached startup result substitutes for each transaction's check. |
| `MixerHosted.BrowserAuth.Store` | Fixed functions `bootstrap/2`, `load/1`, `begin_login/2`, `claim/2`, `provider_reject/2`, `prepare_activation/2`, `activate/2`, `fail_claim/2`, `logout/2`, `expire/2`. First argument is the exact typed server-generated draft/digest input described by its SQL signature; second is server request metadata where applicable. They own all transactions; no exported generic SQL executor, operation callback or caller-selected Repo. `load/1` contains cookie/configuration digests derived by the owner. |
| `MixerHosted.BrowserAuth.Sessions` | Fixed application facade below. It obtains the current registered owner; production callers cannot inject a verifier, provider, dispatcher, Repo or clock. SQL drafts and secrets never appear in a public response. |
| `MixerHosted.BrowserAuth.ClaimOwner` | One short-lived supervised process per successful code claim, with a private one-use record and monitored original caller PID. Only Sessions drives its fixed completion/failure messages. No durable resume, generic message callback or public secret lookup. |

Proposed facade signatures preserve the selected storage behavior while removing
injectable provider results and dispatcher callbacks:

```elixir
Sessions.bootstrap(raw_cookie_or_nil, metadata)
Sessions.begin_login(raw_cookie, raw_headers, :workspace, metadata)
Sessions.claim_callback(raw_cookie, protocol_callback, metadata)
Sessions.complete_login(claim, metadata)
Sessions.fail_claim(claim, reason, metadata)
Sessions.logout(raw_cookie, raw_headers, metadata)
Sessions.workspace(raw_cookie, workspace_request, metadata)
```

`protocol_callback` must be freshly produced by `Protocol.parse_callback/3` in
the same trusted request flow; Sessions rechecks its closed shape and exact issuer
against current validated Config. A plain map is parsing data, never durable
claim evidence. `raw_headers` are duplicate-preserving headers accepted by
Protocol; owner recovers expected CSRF and uses `Protocol.verify_csrf/3` before
begin/logout. Metadata is exactly `%{request_id: hex32}`: generated server-side,
not copied from an untrusted correlation header. No trusted IP field is added to
this SQL schema, whose events currently have no IP column.

Facade success shapes are the selected storage contract's cookie/session,
authorization URL, opaque claim, fixed redirect and clear-cookie shapes. Workspace
requests are only `{:organizations, page}` or `{:projects, organization_id, page}`
with the existing ordinary input bounds. There is no arbitrary path/method/header
or network target. `fail_claim` accepts only `:exchange_failed`, `:oidc_failed`,
`:identity_failed`, `:session_failed`. It returns `:ok` only for confirmed durable
failure; lack of a failure receipt cannot revive a consumed claim.

All facade errors are exactly `{:error, code}`, where `code` is one of:
`invalid_request`, `unauthenticated`, `provider_rejected`, `onboarding_required`,
`identity_unavailable`, `authorization_unavailable`, `session_unavailable`.
Store failures are private redacted `%Store.Failure{code: code, phase: phase,
outcome: outcome}`: phase is `admission|effect|decode|commit`; outcome is
`not_started|rolled_back|committed|unknown`. No SQL exception, stack, token,
provider text, identity, key/reference, raw query or ciphertext is retained in
this value. Only the facade code crosses the HTTP boundary. `P0001` alone never
means onboarding; only the exact fixed error from the admitted helper may map to
`onboarding_required`. Other SQLSTATEs, unexpected results and malformed outputs
map to `session_unavailable`. Known provider rejection can be `committed`.
No error authorizes automatic retry.

## First constructor slice: exact inputs and outputs

Freeze the first pure implementation as `Custody.new/2` and
`RuntimeConfig.new/4` only, with selected pure tests/evidence. No Application,
RuntimeSupervisor, Repo, Catalog, Store, route or provider wiring belongs to that
first slice. The independent catalog expectation matrix can proceed separately
against this shared contract.

- `browser_env` is a map with only string keys `MIXER_BROWSER_AUTH_MODE` and
  `MIXER_BROWSER_AUTH_CONFIG`. Disabled mode accepts the existing default/explicit
  disabled form and no CONFIG entry. Configured mode requires exactly both keys
  and uses existing Config.load with the actual hosted role/identity_startup.
- `hosted_config` is the trusted `%MixerHosted.RuntimeConfig{}` returned by the
  ordinary startup loader. It carries the actual `role`, `identity_startup`,
  `repo` and `database_connection_bound` (plus its existing Oban/Endpoint fields).
  A processor cannot be recast as API by a positional argument. The constructor
  is pure: it does not consult Application, env, running owners or callbacks and
  cannot attest that a struct is the live configuration. Later startup must pass
  the same loaded value to both child graphs and prove that composition in tests.
- `lifecycle_repo_config` is **exactly** `%{username: login, password: password,
  writer_role: writer, relation_owner: owner}` in configured mode. No extra keys,
  URL, host/database override, pool option, resolver or callback. Login/writer/
  owner names use the restricted role-name grammar; login differs from the
  ordinary hosted Repo username. Password is externally supplied, nonempty binary
  within the ordinary loader's 4,096-byte bound. The constructor provisions
  nothing. It derives host/database/port/TLS exclusively from trusted hosted Repo
  options, retains the loader-owned verified TLS policy, and constructs fixed
  lifecycle pool/timeout settings below. An invalid trusted connection shape or
  weakened TLS/direct-host policy fails closed rather than silently repairing it.
- `custody` is exactly the successful `%Custody{reference: reference,
  key: %Vault.Key{...}}` produced by `Custody.new/2`; reference must equal Config's
  session_vault_ref and key is revalidated by Vault.key/2. Custody.new's reference
  uses Config's bounded canonical `vault://` grammar and its material map has
  exactly `reference`, `key_id`, `key_bytes`, with matching reference. No raw key
  or a key resolver appears in browser_env or lifecycle_repo_config. Forging a
  struct remains outside the trusted application threat boundary, not custody
  provenance.

The result struct has exactly `mode`, `browser_config`, `configuration_digest`,
`lifecycle_repo`, `expected_roles`, `custody`. In configured mode expected_roles
is exactly `%{lifecycle_login: login, writer: writer, relation_owner: owner,
ordinary_runtime_login: ordinary_username}`; lifecycle_repo is the derived fixed
Ecto keyword configuration. Its added connection count is 2, and callers derive
the future total from hosted_config.database_connection_bound + 2. In disabled
mode both lifecycle_repo_config and custody must be nil, and all five result
fields other than mode are nil. Both Inspect implementations reveal no keys,
passwords, reference values, configured endpoints or identity. There are no
function-valued caller hooks; only the already loader-owned TLS hostname-check
policy is retained. Constructor errors are the single closed session_unavailable
error and contain no input echo.

## Connection and current catalog admission

The startup owner passes the same validated hosted configuration produced by
`MixerHosted.RuntimeConfig.load!/1` to the ordinary application children and this
constructor. It must require exact role/identity_startup/Repo equality with those
actually supervised, rather than trusting a request-created struct. Configured
browser mode requires its actual role `:api`; Config.load rejects configured
processor mode. No production constructor/start call accepts caller injection.

Configured lifecycle connection settings must use the ordinary connection's
exact direct host, port 5432, database and verified-TLS root/hostname policy, with
a distinct externally provisioned lifecycle login/password. No URL with extra
options, pooler endpoint, disabled verification or ordinary-login fallback is
accepted. The initial lifecycle pool is exactly 2 connections, `pool_count: 1`,
with 5,000-ms connect/query limits and sensitive connection errors disabled.
Every checkout/query/transaction uses `queue: false`; no application wait queue
or automatic SQL retry. Aggregate per-node bound becomes the existing ordinary
pool plus its existing Oban notifier connection plus these 2 connections. Replica
count and operational Neon capacity remain qualification work.

Trusted lifecycle settings additionally name the expected lifecycle login,
writer role, relation owner and ordinary runtime login. Names are distinct,
restricted role identifiers admitted by the existing provisioning contract. They
are expectations, not authority discovered by the application. Constructors only
accept supplied credentials/material; they create/change no credential or grant.
`Custody.new/2` checks material shape/reference, not the security of its source.
A reviewed external source and secret injection into only the API owner remain
production prerequisites. Raw key/credential material never enters Config,
configuration digest, Vite, Oban, build workers, database GUCs, errors or receipts.
The initial owner has one key ID/version, no fallback key and no rotation API.
BEAM memory zeroization is not promised.

Startup admission and each Store transaction perform the same positive checks,
in the transaction/connection that will invoke the operation:

1. `current_user = session_user = expected_lifecycle_login`. Lifecycle role is
   LOGIN, NOINHERIT, NOSUPERUSER, NOBYPASSRLS, NOCREATEROLE, NOCREATEDB,
   NOREPLICATION. Writer has the same flags except NOLOGIN. No incoming or outgoing
   `pg_auth_members` edge may involve either, including memberships with SET ROLE
   capability. Recursively examine reachable roles for ordinary runtime and every
   named owner; deny runtime reachability of writer/owners, privileged/predefined
   `pg_` roles, or ownership routes. Deny lifecycle/writer relation/schema
   ownership, all schema CREATE including PUBLIC/inherited paths, ordinary login
   equality, and any writable-view/foreign-table path.
2. The accepted four browser relations and five touched authz relations exist as
   exact ordinary relations with ENABLE/FORCE RLS and the explicit distinct
   non-login/non-superuser/non-bypass relation owner. Check expected columns/types,
   FKs, checks, indexes and enabled integrity/audit triggers and their exact
   function OIDs/definitions against reviewed installation manifests. Existence
   and FORCE RLS alone are insufficient. Compare schemas without reading data.
3. Match **all eighteen** baseline `StorageSchema.signatures/0` functions, their
   typed inputs/results, PL/pgSQL language, exact `pg_proc.prosrc` bytes from
   `catalog_manifest/0`, SECURITY DEFINER, non-login restricted writer owner,
   exact function configuration and effective ACL. Require no overloaded or extra
   `mixer_browser_*` executable helper. Function configuration is exactly
   `search_path=pg_catalog`, `statement_timeout=5s`, `lock_timeout=500ms`,
   `idle_in_transaction_session_timeout=5s`, `bytea_output=hex`; no extra setting
   or dropped timeout is accepted. Check composite field order/types and revoked
   PUBLIC type usage. Use qualified fixed functions with explicit argument casts.
4. Expand effective ACLs including default/PUBLIC and inherited rights. Lifecycle
   gets only schema/type USAGE and the nine public function EXECUTEs below; no
   direct browser/authz table or column SELECT/DML/REFERENCES/TRIGGER/TRUNCATE,
   internal-helper EXECUTE, temporary writer membership or writable view. Ordinary
   runtime receives none of these nine EXECUTEs. Reject other application-schema
   SECURITY DEFINER functions callable by lifecycle unless explicitly reviewed
   and listed (initial allowlist: these nine only). Catalog discovery functions
   themselves must resolve to pg_catalog. No dynamic SQL from request data.
5. Writer effective grants are exactly: SELECT/INSERT on all four browser tables;
   UPDATE only the three mutable-column lists in `catalog_manifest/0`, none on
   session_events; SELECT on authz profiles/principals/bindings/families/credentials;
   UPDATE(state_revision) on profiles, UPDATE(revision) on principals solely for
   locks; INSERT and UPDATE(active,revision) on families/credentials. No table-
   level UPDATE, DELETE/TRUNCATE, PK/linkage update, tenant/member grants or
   privilege with grant option. No unreviewed function execution expands this.
6. Match the complete role-targeted policy sets, commands, permissiveness, USING
   and WITH CHECK expressions, not just their names. Browser read/insert/update
   are `true` for writer only; session_events has no update policy. Authz writer
   read policies are `true`; profiles/principals lock policies have USING true /
   WITH CHECK false; families/credentials insert/update policies are true. Existing
   ordinary scoped/directory policies remain exactly reviewed: their accepted
   `scoped_read`, `scoped_lock` and `directory_read` policies omit TO and therefore
   target PUBLIC, with their existing restrictive predicates. Preserve those exact
   baseline PUBLIC targets/predicates; lifecycle still has no direct table grants.
   Reject additional/widened PUBLIC or ordinary-runtime policies and any added
   ordinary-runtime target on the new writer policies. Reject unexpected permissive OR
   policies, altered trigger enablement, missing constraints or widened grants.

The baseline compiled manifest is necessary but does not currently implement
this inspector or supply every relation/ACL/ordinary-policy comparison. The new
Catalog module must author its fixed expected matrices independently from the
ordinary reviewed migrations, StorageSchema and ordinary Session topology. Never
reuse the frozen inspector/driver lane. Source-derived expectations are fixed at
build time; live catalog state cannot generate its own expected answer. Store
operation admission cannot be replaced by a caller-set GUC or cached boolean.
These non-login relation-owner expectations are production contract requirements,
not claims about an existing deployment or all historical local fixtures. New
disposable fixtures must explicitly provision this topology; any historical owner
LOGIN shortcut cannot pass this admission. No general runtime schema repair/
provisioning is permitted. Owner-level coherent
DDL/rewriting is outside this security boundary; serialized operator schema
changes remain required, and per-transaction checks detect observed drift rather
than promising protection against a malicious database owner.

## Exact existing SQL surface

These nine unchanged baseline signatures are machine-compared with the reviewed
source by the contract checker. Results are internal; JSONB always passes
`StoredSnapshot.decode/1`, never direct browser serialization.

```text
public.mixer_browser_bootstrap(bytea,bytea,text,bytea,bytea,text,integer,bigint,public.mixer_browser_cipher,text) -> jsonb
public.mixer_browser_load(bytea,bytea) -> jsonb-or-NULL
public.mixer_browser_begin(bytea,bytea,bytea,bigint,public.mixer_browser_attempt,public.mixer_browser_cipher,text) -> jsonb
public.mixer_browser_claim(bytea,bytea,bytea,bigint,bytea,bigint,text) -> jsonb
public.mixer_browser_provider_reject(bytea,bytea,bytea,bigint,text) -> jsonb
public.mixer_browser_fail_claim(bytea,bytea,bytea,bytea,text,text) -> boolean
public.mixer_browser_activate(bytea,bytea,bytea,bytea,bigint,public.mixer_browser_verified,bytea,bytea,text,text,bigint,public.mixer_browser_cipher,text) -> jsonb
public.mixer_browser_logout(bytea,bytea,bytea,bigint,text) -> boolean
public.mixer_browser_expire(bytea,bigint,text) -> boolean
```

`load` NULL is absence/terminal/expired/config mismatch, not authenticated state.
`false` from expire is no transition, not successful expiry mutation. All other
operations require exactly one expected non-NULL result and exact post-state.
The internal helpers (`snapshot`, `cipher_valid`, `audit`, four integrity/audit
trigger functions, `lock_existing`, `revoke_existing`) are catalog-admitted but
never directly executable by either application login. Their full signatures,
source hashes and settings are in `baseline-catalog.json` in the evidence folder.

## Required additive activation-preparation seam

This is a **proposal for the next separately reviewed prerequisite**, not a
change to the accepted nine-helper schema. `ConfiguredVerifier.authenticate/2`
returns no database revisions or principal ID. Those values cannot be invented
from `VerifiedIdentity`, profile version, the browser or StoredSnapshot, and the
lifecycle login must not gain direct authz SELECT to obtain them.

Add one closed composite and one fixed helper in an additive migration, whose
number is coordinated by root before implementation:

```text
public.mixer_browser_access_evidence AS (
  profile_id text, profile_version integer, issuer text, subject text,
  client_id text, credential_ref text, issued_at bigint, expires_at bigint,
  scopes text[]
)
public.mixer_browser_prepare_activation(
  p_cookie bytea,p_state bytea,p_config bytea,p_claim bytea,p_revision bigint,
  i public.mixer_browser_access_evidence
) -> jsonb
```

Only the trusted ClaimOwner constructs `i` immediately after current default
access verification and exact qualified OIDC issuer/subject/client equality.
It independently requires identity_class `:human` and required workspace scope;
SQL additionally validates all text/integer/array bounds, no NUL or NULL scope
member, exact current Config profile/version/issuer/client and temporal fields.
This type contains token identity evidence only, no caller-supplied DB revision.

The helper performs one fixed bounded SELECT with exact cookie/state/claim keys,
joining browser, vault, claimed attempt, incoming profile, exact subject binding
and principal in **one MVCC statement snapshot**. It takes no row locks or effect,
so it cannot invert the activation lock order. It checks current cookie/config,
expected revision/epoch/generation, all saved attempt linkage, status claimed,
claim digest, profile/version/issuer/client/redirect, active human profile/binding/
principal, and valid-after fence against verified token iat. Use fresh database
`clock_timestamp()` at entry and again after the projection; equality denies
browser idle/absolute, attempt, claim and token deadlines. A missing/mismatched/
expired foreign claim returns session unavailable before revealing binding state.
Only a valid same-browser current claim can yield onboarding_required for an
unknown exact binding. Disabled/mismatched profile or inactive binding/principal
denies; it never links by email/domain or creates anything. The SQL read returns
at most one browser/attempt/vault/profile/binding/principal tuple; absent or extra
rows fail closed. Lookup must use existing unique keys, never an unbounded scan.

Return exactly:

```text
{
  "version": 1,
  "snapshot": {"browser": ..., "vault": ..., "attempt": ...},
  "principal_id": bounded_text128,
  "profile_revision": positive53,
  "binding_revision": positive53,
  "principal_revision": positive53
}
```

Snapshot uses the existing exact StoredSnapshot format with status `claimed` and
its erased attempt cipher. A new closed `ActivationPreparation.decode/1` validates
all six top-level keys/types, delegates snapshot decoding and binds all fields
to the owner-retained claim/access identity/current config. The decoder proves
shape only. Metadata grants no permission or future validity. Decode does not
synthesize an authenticated session, membership or provider verification.

The preparation snapshot supplies existing browser/vault revision/generation and
new principal for the next active AAD. ClaimOwner adds its fresh server family,
cookie, generation and CSRF plus verified jti and credential revision 1. It
constructs existing `mixer_browser_verified` by combining the latest current
verified token fields with **these provisional DB revisions**, then calls the
unchanged activate. Existing activate must revalidate incoming exact profile/
binding/principal revisions and old linkage, claim/cookie/config/revision/time
under its canonical locks; any intervening drift rolls back. Nothing from the
preparation helper is a durable authority ticket. If token evidence changes,
discard preparation rather than mixing rows/evidence.

Combined lifecycle catalog manifest version 2 must explicitly add this type,
helper source/signature/result/configuration/ACL and decoder source binding.
There will be 19 admitted functions and 10 public EXECUTEs; internal functions
remain inaccessible. Its writer can use existing narrow SELECT privileges; no
new table write policy or direct login read is required. PUBLIC execution/type
usage remains revoked. An explicitly reviewed operator upgrade plan must add
only this helper/type grant; the accepted initial provisioning plan must not be
silently replayed on an already provisioned role. Migration down removes this
helper/type only. Version-1 admission must reject the added surface until the
reviewed version-2 owner is selected. Test mixed-version deployment fail closed.

## Transaction ownership, AEAD and exact publication

Every Store operation owns one READ COMMITTED transaction on LifecycleRepo; it
rejects any existing lifecycle or ordinary authorization transaction/context.
The operation's initial monotonic deadline covers checkout, admission, SQL,
decoding, final checkpoints and commit: at most 5,000 ms, `queue: false`, no
retry. Driver queries use the remaining positive budget, never a reset five
seconds per query. Before operations set and verify LOCAL statement/idle limits
at most 5,000 ms, lock timeout at most 500 ms, `jit=off`, and hex bytea output;
keep the reviewed helper-local settings unchanged. Local values restore on both
commit and rollback. Function-local timers alone cannot bound total/commit time;
driver deadline/cancellation and final result checks are also required. Record
this as per-transaction scope, not a five-second end-to-end provider guarantee.

Fresh trusted wall time is checked after waits and immediately before private
result release, with monotonic rollback/deadline guards. SQL uses its existing
post-unique-wait temporal checks. No caller clock. Expiry equality denies. Any
exception, unexpected result, deferred audit/integrity failure, timeout or
foreign/nested context rolls back. SQLSTATE deadlock/serialization/lock errors
and pool exhaustion do not retry. Preserve ordinary authorization's current
five-second/500-ms and `jit=off` policy; do not route it through LifecycleRepo.

No provider, OIDC/JWKS, default access verifier, custody network resolution or user
callback executes during a lifecycle transaction. Encrypted discovery is loaded
and its transaction closed before `Vault.open/3`; encrypt prepared drafts with
`Vault.seal/3` before the mutating transaction. Never implement new AAD or cipher:
use the existing Vault versioned contexts, digest binding and envelope bounds.
Compare Config digest/profile/version, cookie digest, browser and attempt
identity, exact contexts and cipher fields with the retained expected snapshot.
CSRF digest must match the decrypted canonical43 CSRF; active token remains
bounded to 4,089 bytes and never reaches the browser.

Publication/CAS rules are operation-specific:

- Bootstrap draft fixes browser ID, cookie/CSRF/config digests, generation,
  epoch/revision/vault_generation=1 and preauth deadline before seal. Returned
  snapshot must exactly match it apart from SQL-owned fresh timestamps/audit.
- Begin seals the session for expected epoch+1, revision+1, vault_generation+1;
  the attempt AAD uses those exact saved values and fixed Config metadata.
  Existing begin compares source revision; its allowed writers never alter vault
  context/cipher without that revision advancing. Compare resulting snapshot,
  exact sealed bytes/attempt metadata, and new counters before commit. A failed
  compare rolls back supersession and all writes.
- Claim decrypts the exact pending attempt before claim erases it. In the claim
  transaction call load first, compare the complete retained browser/attempt/
  vault snapshot under load's browser SHARE lock, then call claim and validate
  its exact claimed metadata/digest/deadline and erased cipher before commit.
  This browser-only SHARE-to-UPDATE upgrade can lose to another claim/deadlock;
  rollback and require a new operation, never retry. It obtains no authz locks.
  Provider rejection needs no PKCE open and consumes exactly once via its fixed
  helper; compare its committed metadata without releasing provider text.
- Activation preparation is a separate completed read transaction; seal active
  envelope outside locks. Invoke activate directly without an earlier browser
  SHARE lock in that mutating transaction. SQL locks incoming/old profiles,
  principals, existing family/credentials, browser, attempt and vault in its
  reviewed order; p_revision, full SQL discovery comparison, current claim and
  observed identity revisions fence publication. Compare returned active context
  and exact sealed bytes to the prepared draft before commit. Audit sequence may
  include separately committed claim events and is validated, never invented.
- Logout/expire invoke their canonical SQL directly; never pre-lock browser and
  then request authz locks. A successful bool has no decrypted result. Expire
  targets one server-selected ID/revision, with no scan/retention scheduler.

The exact comparisons above rely on admitted fixed writers, immutable linkage
and no direct table access. They do not attest ciphertext to SQL or prevent a
compromised API process from forging its own draft.

Only an explicit confirmed `{:ok, expected_result}` after transaction commit,
source/config/caller continuity and final time/deadline check may publish a new
cookie, authorization URL, usable Claim or authenticated private result. An
unknown commit outcome returns unavailable, clears readiness for re-admission,
and drops prepared secrets. Never resend/reconstruct a fresh cookie using the
old digest. An uncertain claim performs zero provider exchange. An uncertain
activation may leave a family committed but no cookie delivered; allow normal
expiry/new interactive login, never repair by resurrecting linkage. An uncertain
logout never claims success or clears its retry cookie. A later user-initiated
logout is a new operation, not automatic SQL replay. Definite response loss after
commit has the same no-cookie-recovery rule. Fault-inject each boundary.

## Process claims and verifier provenance

Reserve a bounded owner slot before durable claim: initially 32 concurrent
operations/claims per API node, no waiting queue, distinct from the pool bound.
This is per-node admission only, not an organization/fleet quota. Each opaque
`%Claim{owner_pid: pid, reference: ref}` contains no claim secret, PKCE, code,
nonce, raw cookie or identity. The private ClaimOwner record retains the original
caller PID, random reference and independent random raw32 claim secret/digest,
exact durable claim snapshot, Config digest/runtime generation, nonce digest,
PKCE, bounded code and exclusive durable deadline (at most attempt expiry and
claim time+60 seconds). Local lifetime is additionally monotonic-bounded.

The monitored original request process alone can complete/fail it. Check actual
GenServer caller PID, not a supplied PID field; reject copied maps/foreign process,
unknown reference, second use, caller death, owner restart/config generation
change or deadline equality. Atomically change local state to `exchange_started`
before any provider call; it cannot reenter or exchange twice. On restart/loss,
SQL's claimed tombstone stays consumed; another replica cannot reconstruct the
secret or resume from a later load, which excludes claimed attempts. Terminate
on bounded completion/failure/expiry and release the permit in all paths. Best-
effort fail_claim is a single bounded new transaction and does not relax SQL
expiry; failure leaves consumed state. No retry of exchange or callback code.

Only production ClaimOwner calls
`Identity.ConfiguredVerifier.authenticate(access_token, System.system_time(:second))`.
No injected verifier, `authenticate/4`, retained TrustSnapshot, pure
AccessTokenVerifier call, fabricated VerifiedIdentity or ID token is an allowed
activation source. Use current registered default KeyOwner/admission; preserve
ConfiguredVerifier's existing current-trust finish checks. Its internal one-time
current-trust retry is not a transaction or provider-code retry. Require a fresh
successful call for every activation; no identity retained across operations.
Bind exact profile/version/issuer/client/subject/jti/iat/exp/scopes to the
preparation/activation. Require human class and workspace scope, then let SQL
revalidate current DB fences. Require exact Config profile/version/issuer/client matching and registered
default-owner PID continuity; loss/PID replacement denies. RuntimeOwner's own
configuration generation is separately fenced in its private state. Existing
KeyOwner can replace its manifest/trust generation within the same PID; a process
monitor does not observe that change, and no current-generation read/notification
API is assumed here. The bounded guarantee is a fresh successful default
authenticate/2 with its existing finish checks plus exact Config and registered
PID matching. This does not claim an atomic fence between later same-PID trust
changes or JWKS rotation and PostgreSQL commit.

For active bootstrap/workspace, encrypted load and AEAD validation alone never
return authenticated state. The separate fixed protected pipeline must call the
current default verifier and ordinary current authorization/identity-state checks
against the exact decrypted token. Saved principal/family/revision is comparison
metadata, never authorization. An admitted ordinary family SHARE request may
finish before logout/replacement returns; new requests after confirmed revocation
deny. This requires the ordinary Repo/family lock pipeline, not a lifecycle
precheck followed by unprotected dispatch.

## Provider, OIDC and HTTP prerequisites

A later fixed provider adapter owns one configured client_secret_basic exchange
with the claimed exact PKCE/redirect/client, bounded egress/DNS/peer/TLS, response
bytes/time/type and sanitized errors. No provider is selected or qualified here;
canonical Config URLs alone do not qualify transport. A separate OIDC verifier
must validate signature/algorithm, issuer, audience/client/authorized party,
times and nonce digest, then require issuer/subject/client equality to the API
identity. Differing subject namespaces deny pending separately qualified binding.
No ID/refresh token persists. Any timeout, disconnect or ambiguous exchange
consumes the code attempt and requires new login. No provider I/O occurs in SQL.

The workspace dispatcher is a fixed ordinary application join, not a SQL bridge
function or injectable callback. Root owns the two selected workspace reads,
current bearer verifier, ordinary authorization, bounded page transport, JSON
projection and same-origin session fencing. No arbitrary destination or token
serialization. HTTP must separately prove duplicate-preserving cookie/Origin/
CSRF/callback handling, exact raw paths/methods, cache/no-store/private handling,
log redaction, cookie deadline, fixed redirects and response loss behavior.
Until those prerequisites and end-to-end owner checks are accepted, all login/
callback/session/workspace browser readiness remains unavailable. `/health/live`
continues to mean process liveness only. `storage_ready` cannot enable a route.

## Next vertical slice and evidence boundary

Implement the first bounded slice in dependency order: freeze the exact catalog
expectation matrix and pure custody/runtime construction first; then implement
dedicated LifecycleRepo and independent current Catalog admission; then fixed
Store bootstrap/load and the real preauth Vault/StoredSnapshot roundtrip. In this
first slice any loaded active snapshot is private discovery data only and must be
explicitly rejected for facade authentication/workspace use until the current
default verifier plus ordinary identity-state/protected pipeline is implemented.
Parallel
lanes may begin only after their shared expectation/configuration interfaces are
coordinated. Use only synthetic
local fixture credentials/keys and restricted lifecycle/ordinary roles in one
owned disposable PostgreSQL instance. Keep application routes disabled and active
session inspection unavailable. Tests must prove pool exhaustion/no queue,
transaction ownership, current drift detection, rollback/commit uncertainty,
redaction and AEAD/source comparison; this is a meaningful executable storage
slice without an invented provider.

Then add/review the claimed-attempt-bound preparation type/helper/manifest v2 and
its single-snapshot tests, followed by begin/claim/activate/logout process-owner
composition. Synthetic trusted provider fixtures are distinctly test-only, not
production fallback or provider qualification. The immutable machine-readable
adversity matrix in this directory lists all required host cases; they are
**pending runtime implementation**, not passed by the document checker.

The recorded checker executes only ordinary standalone StorageSchema in memory,
compares signatures/manifests against this text and exercises negative controls.
It is structural documentation evidence, not catalog admission, runtime security,
PostgreSQL integration, cryptographic or endpoint acceptance. No production or
native/capture process was started. Provider/Neon/operator/key-rotation/retention,
customer browser/FieldLog and GA gates remain pending, with no new approval step
added to already authorized implementation or coherent root delivery.
