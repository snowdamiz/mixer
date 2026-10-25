# Durable browser lifecycle storage

This implements the PostgreSQL portion of the selected
[browser session storage contract](hosted-browser-session-storage-contract.md).
It does not enable login or any HTTP route. Provider exchange, a qualified OIDC
validator, the current default access verifier owner, production pool admission,
Neon provisioning, encryption-key custody, browser ingress, customer and GA
qualification remain separate work. Browser/capture/native/phone execution is
paused. These are host PostgreSQL development receipts.

## Installation and operator boundary

Migration `20261025000007` installs four FORCE-RLS relations, three closed input
composite types, eighteen fixed SECURITY DEFINER functions, and integrity triggers.
Every function has `search_path=pg_catalog`, a five-second statement/idle timeout,
and 500-ms lock timeout. `bytea_output=hex` is fixed in every helper, including
when the caller selected escape output. SQL qualifies application and catalog relations. PUBLIC
function execution and PUBLIC relation/type privileges are revoked. The migration
adds **no roles, logins, passwords, credentials, lifecycle grants or RLS write
policies**. An ordinary schema owner can apply it; its inert functions cannot
read/write rows through FORCE RLS. It does not start an application or worker.

`StorageSchema.provisioning_statements(writer_role, lifecycle_login)` returns a
fixed operator SQL plan, bracketed by `BEGIN` and `COMMIT`. It executes nothing.
Identifiers are restricted lowercase ASCII names, distinct, at most 63 bytes,
and exclude `public` and `pg_` names. An operator must run the whole plan on one
connection, stop on the first error and roll back on failure. Do not send each
statement through a connection pool independently. This is an initial-provisioning
plan: it rejects existing privileges/ownership/membership instead of silently
rewriting another role. Replay/upgrade admission requires separate review.

The externally preprovisioned writer must be dedicated NOLOGIN, NOSUPERUSER,
NOBYPASSRLS, NOINHERIT, NOCREATEROLE, NOCREATEDB and NOREPLICATION; the separate
lifecycle LOGIN has the same restrictions except LOGIN. Neither may have incoming
or outgoing memberships, schema CREATE, existing table/column privileges, or
relation/schema ownership. The ordinary API login is a third role. The operator
must be able to transfer exact function ownership. This was tested with a
**synthetic local superuser administrator**, not a Neon administrator. The current
preflight disallows even operator membership in the writer; whether a particular
hosted operator can transfer ownership without that membership remains an explicit
deployment prerequisite. No role or credential provisioning was run on Neon.

The operator plan transfers only the eighteen fixed functions to the non-table-
owner writer and immediately revokes its temporary schema CREATE. Only then does
it add role-targeted RLS and minimal privileges. The writer receives SELECT on
profiles/principals/bindings and `UPDATE(state_revision)` / `UPDATE(revision)`
solely for profile/principal locks; their UPDATE `WITH CHECK(false)` prevents
actual mutation. It can INSERT families/credentials and UPDATE only
`active,revision`, preserving immutable IDs/linkage and all tombstones. Browser
and attempt UPDATE grants name only mutable columns. Audit is SELECT/INSERT only.
No writer DELETE/TRUNCATE or membership/tenant grants exist.

The lifecycle login receives schema/type USAGE and EXECUTE on the nine named
public operations; it receives no direct table privileges, owner membership,
internal-helper execution, schema CREATE or ordinary authz-writer privilege.
Existing ordinary role grants and its scoped/directory policies are unchanged.
`catalog_manifest/0` supplies exact expected function source, signatures,
SECURITY DEFINER/configuration and the table/column/policy manifest for independent
runtime admission. Merely finding the tables/functions is insufficient admission.
Deployment must separately check exact effective role reachability, relation
owners/FORCE RLS, grants, policies, signatures/body/search path/ACL, overloads,
views and schema CREATE before startup and each protected transaction.

Rollback removes only this migration's exact objects, named authz policies, and
its dedicated helper owner's exact added authz privileges. It drops no role and
uses no CASCADE. The focused fixture verifies provisioning, rollback, reapply and
reprovisioning while preserving ordinary directory reads. Root owns the complete
nine-migration integration controls.

## Records and fixed operations

`mixer_browser_sessions` stores raw16 browser IDs, raw32 cookie/CSRF/configuration
digests, canonical43 generation, bounded positive53 epochs/revisions/audit
sequence, configuration profile/version, exclusive Unix-second deadlines, and
exact optional existing authz linkage. Preauth carries no authz linkage. Active
requires its existing family and credential; a deferred check confirms the
credential's principal/family/revision. Terminal rows cannot reactivate. Cookie,
CSRF and generation rotate on activation. No raw cookie, CSRF or token is stored.

`mixer_browser_session_vault` binds browser/epoch/revision and monotonic vault
generation to version 1, kind `preauth` or `active`, ASCII key ID
`[A-Za-z0-9._-]{1,128}`, IV12, tag16 and ciphertext1..8192. Logout/expiry preserve
an `erased` metadata row with all cipher fields NULL. SQL checks structural
linkage; the separate Vault module supplies authenticated encryption and exact
AAD/plaintext validation. The PostgreSQL fixture deliberately uses synthetic
ciphertext and does not claim AEAD interoperability evidence.

`mixer_browser_oidc_attempts` retains fixed configuration/profile/version/issuer/
client/redirect/return route, state/nonce digests, saved begin cookie digest,
generation, browser epoch/revision, exclusive expiry at most 300 seconds from
creation, and encrypted verifier. A unique partial index permits at most one
pending/claimed row for a browser epoch. Claim, provider rejection, failure,
completion and supersession erase verifier ciphertext. State/claim/nonce/code/
provider plaintext is never inserted; claim digests remain one-use tombstones.
The claim deadline is at most the attempt deadline and fresh time plus 60 seconds.

`mixer_browser_session_events` is an independent version-1 lifecycle stream.
Operation/outcome and old/new status/revision/epoch combinations are closed,
request IDs are server-generated lowercase hex32, and SQL derives all event data.
Only activation/replacement includes bounded token times, observed profile/
binding/principal/family/credential revisions and domain-separated SHA-256 hashes
of issuer/subject/client/jti. External identity, token, cookie, CSRF and PKCE
plaintext are absent. UPDATE/DELETE is denied by grants and an immutable trigger.
Deferred constraints tie browser state, vault mutation, attempt transition and
audit sequence together; a missing/orphan/invalid audit transition rolls back.
Coherent database-owner rewriting remains outside this runtime guarantee.

`StorageSchema.public_signatures/0` is the exact typed SQL interface. Its nine
operations are bootstrap, load, begin, claim, provider_reject, fail_claim,
activate, logout and expire. Inputs are primitives plus three closed composites:

- `mixer_browser_cipher(key_id,iv,tag,ciphertext)`;
- `mixer_browser_attempt(state_digest,nonce_digest,profile_id,profile_version,issuer,client_id,redirect_uri,expires_at,cipher)`;
- `mixer_browser_verified(profile_id,profile_version,issuer,subject,client_id,credential_ref,issued_at,expires_at,scopes,profile_revision,binding_revision,principal_revision)`.

All byte strings are bound PostgreSQL `bytea`, not decoded provider/browser SQL.
The verified composite is a trusted internal result of the future current-verifier
owner; it is not browser authority or proof against a compromised lifecycle
process. There is no JSON operation input, SQL/GUC capability, arbitrary function
selector, provider callback, implicit identity creation or membership bootstrap.
Unknown exact active human bindings fail onboarding-required. Activation requires
human profile/binding/principal, exact issuer/client, current revisions,
`mixer.workspace.read`, principal valid-after fence and unexpired token.

Activation INSERTs a fresh CSPRNG `browser_` + canonical43 family and a new
profile/version/jti credential, both revision 1. Any collision, including inactive
tombstones, fails the entire operation. `not_before=min(token iat,fresh now)`
correctly admits an already-issued token while respecting the principal fence.
No UPSERT, transfer, resurrection or refresh exists. Beginning replacement retains
the old authenticated family; successful activation revokes that family and its
single registered credential atomically with cookie/vault rotation and audit.
A second unexpected family credential makes revocation unavailable until a
separately qualified refresh protocol exists. No partial login helper is exposed.

`load` is encrypted discovery only and grants no authentication. Missing,
terminal, expired or config-mismatched rows return SQL NULL without mutation.
A live snapshot includes the current pending attempt, or NULL; claimed and
consumed attempts do not appear on later load. Claim/provider_reject/activate
return their exact attempt metadata after their committed transition. Claim and
provider_reject leave browser epoch/revision unchanged and increment only audit
sequence, avoiding a needless vault/AAD reseal. Begin/activation/logout/expiry
increment epoch/revision and reseal or erase the vault atomically. Expire handles
one supplied browser ID/revision; it performs no unbounded scan and does not
schedule itself or delete retention tombstones.

Snapshot JSON has exactly `browser`, `vault`, `attempt` keys and uses each
relation's exact named columns. PostgreSQL encodes bytea as `\\x` plus lowercase
hex; bigint values are restricted to JavaScript's exact integer range. No
snapshot contains plaintext. This is internal typed transport, never browser JSON.

## Locking, time and application prerequisites

Lifecycle authz mutations discover old linkage without locks, then lock profiles
sorted by UTF-8 identity/version, principals sorted by identity, existing family,
credential rows sorted by profile/version/reference, browser, sorted attempts,
and vault. Both incoming and old identity fences are locked during replacement.
The browser is re-read and compared with its entire initial projection; changed
linkage rolls back instead of following an unlocked replacement. Browser-only
bootstrap/begin/claim never later acquire authz locks. No provider/verifier/KMS
call or callback runs under a database lock. The application must prepare the
correct cipher/AAD outside locks and publish only after this exact CAS succeeds.

Every temporal decision uses `clock_timestamp()` after the last lock wait.
Activation checks time again after unique INSERTs, which can themselves wait.
Equality denies attempt/claim/token/browser windows. Counters have checked
positive53 bounds. Fixed database timeouts supplement the owner's required
READ COMMITTED, queue:false, five-second total bounded transaction with no retry
and no join to an unknown existing transaction. The caller must set statement/
transaction bounds on its connection as well; function-local settings do not
replace connection/commit bounds. Commit ambiguity must yield unavailable and
never issue a new authenticated cookie. Response loss after successful activation
cannot recover/resend the new cookie from the old digest.

A trusted owner must still prove Protocol callback validation, independent PKCE
recovery **before** claim erases it, exact qualified OIDC relation and nonce,
current default access-verifier provenance outside locks, and owner-process claim
custody. The fixed workspace owner must decrypt only internally and call the
ordinary current-verifier/authorization pipeline. Encrypted `load` alone does
not validate membership or an active token. These joins are explicitly pending;
this storage component cannot enable a permissive fallback.

## Observed host evidence

Run from the repository root:

```sh
python3 hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py
```

The runner starts one disposable loopback PostgreSQL 17 process, compiles only
StorageSchema and the selected ordinary 3/4/6/7 migration modules against existing
dependency beams, and runs focused ExUnit through restricted lifecycle/ordinary
logins. It never runs `hosted/scripts/test-local.py`, whole-app compilation,
frozen hosted lanes, a provider, a browser, native runtime or production action.
Its `finally` block stops the owned database even after partial startup and removes
owned scratch data. `--pg-bin /path/to/postgresql/bin` selects an existing PostgreSQL
installation; the local default is Homebrew PostgreSQL 17. Every run gets a fresh
immutable `attempts/<timestamp>/` directory with manifests before/after execution,
complete selected ordinary migration inputs, locked dependency-beam hashes,
bounded subprocess commands and cleanup. Existing hosted application beams are
excluded. `latest.json` is only a mutable pointer. The retained development snapshot
contains the final overwritten pre-attempt logs; earlier overwritten runs were
not retained or reconstructed.

[The latest completed immutable receipt](../verification/hosted-browser-session-storage/attempts/20261025T154627.762502Z-289be41e/receipt.json) binds
commands, tool versions, HEAD, exact source digests, outputs and cleanup. Cases
cover isolated role/RLS/column grants/SET ROLE; stable preauth discovery; provider
error consumption; stale/cross-browser/config claims; duplicate replica claims;
claim supersession/failure; exact binding/revisions/scope/time fences; active and
inactive jti reuse and family non-recycling; atomic activation/replacement/logout;
late activation after logout; durable audit failure rollback; owner fault
injection against audit/vault/attempt transitions; exact catalog source; expiry
both at a lock timeout and after a successful lock wait; ordinary family SHARE
serialization of logout/replacement; bounded expiry; and rollback/reapply with
ordinary directory visibility preserved. The completed run passed 18 tests, including a real synthetic-token AES-GCM
roundtrip through SQL and the typed decoder, canonical hex despite hostile caller
bytea output, and failed non-superuser ownership transfer rolling back completely.
Provider authentication is not established by that synthetic token. Broader AEAD
qualification, production pool/catalog
admission, current-verifier provenance, provider/OIDC, Neon/TLS/key custody,
commit/response uncertainty, retention scheduling, customer and GA evidence
remain separate gates. No unrun gate is marked passed.
