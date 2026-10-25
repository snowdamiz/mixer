# Independent activation-preparation SQL review

The corrected additive prerequisite passes this bounded independent development
review. The selected source is
`hosted/lib/mixer_hosted/browser_auth/activation_preparation_schema.ex`, SHA-256
`d58bc6009d6118ba9469f087af99e893df6a99038cdccec11ba5048d48bf4ae8`.
No unresolved blocker remains in the reviewed component. This does not approve a
migration, combined version-2 catalog admission, runtime readiness, ClaimOwner,
provider exchange, an authenticated browser workflow or a GA gate.

The independently authored raw-SQL suite passes **38 methods, zero failures,
skips or exclusions** on PostgreSQL 16.15. Selected compilation with
`--warnings-as-errors` and the actual Mix formatter also pass on isolated
projectless copies. The terminal immutable packet is
[`20261025T183408.316090Z-6aef9df0`](../verification/hosted-browser-activation-preparation-sql-review/attempts/20261025T183408.316090Z-6aef9df0/receipt.json).
The producer's PostgreSQL 17 methods are separate, overlapping evidence; this
review does not add their counts to its own.

## Finding and correction

The original candidate, SHA-256
`0a890fe19711ae715a9cc57225c931857f1173dd2f63fed9fbeac41c98982531`,
failed an independent privilege control. After inert installation, explicit
PUBLIC EXECUTE on the new SECURITY DEFINER function and PUBLIC USAGE on its type
were accepted by the upgrade preflight. Ownership transfer would preserve those
grants, exposing the new helper beyond the lifecycle login. The old result is
retained in
[`20261025T182807.198176Z-75c68643`](../verification/hosted-browser-activation-preparation-sql-review/attempts/20261025T182807.198176Z-75c68643/receipt.json):
33 of 34 methods passed; the preflight returned success where the independent
oracle required SQLSTATE `42501`.

Root corrected the product source within its ownership lane. Initial admission
now compares the new function and type's complete raw ACL tuples with the inert
owner-only expectation, including grantor, grantee, privilege and grant option.
Finalization requires the exact final function owner/ACL and type owner/ACL and
no surviving writer CREATE. The correction rejects rather than repairing
unexpected grants. No baseline function, relation, policy or grant was changed.

The corrected runtime controls cover explicit PUBLIC and third-party grants,
owner grant options, custom function/type default privileges, and grants or type
ownership changes injected after preflight but before finalization. Each dirty
state fails. Explicit rollback restores inert ownership and privileges, removes
temporary CREATE and preserves the complete recorded baseline. The operator
must still execute the returned transaction in order and roll back every error;
this module supplies SQL statements, not an operator transaction owner.

## Exercised behavior

The review read the accepted `ActivationPreparation`, `StoredSnapshot`,
`StorageSchema`, `AccessTokenVerifier` and `Identity.Encoding` sources, the
[preparation specification](hosted-browser-activation-preparation-sql.md) and the
[runtime contract](hosted-browser-lifecycle-runtime-contract.md). The test oracle
was authored independently. Only the ordinary accepted storage fixture's
installation/provisioning and lifecycle setup helpers were reused.

The runtime suite verifies:

- Exact six-key projection and complete claimed StoredSnapshot compatibility,
  including the erased attempt cipher. The singleton additive manifest matches
  installed source, settings, signature, argument names and ordered type fields;
  its decoder digest and actual build-tracked external resource match.
- Direct raw SQL denial for a NULL composite, every NULL access field, malformed
  digest sizes, invalid revisions, oversized and multibyte text, invalid UTF8/NUL
  input, numeric-date bounds, human lifetime, future skew and strict expiry.
  Zero is a valid numeric-date shape in Encoding; a zero-issued human token is
  necessarily expired at this real clock under the 900-second lifetime limit.
- Scope cardinality, dimensionality and lower bound; NULL, empty and duplicate
  members; required workspace scope; actual ASCII scope-word grammar; and the
  exact aggregate 1,024-byte boundary including separators. Valid unknown scope
  words and 64 unique words are accepted without inventing a four-value SQL
  allowlist.
- Exact cookie/state/configuration/claim/revision and profile/issuer/client
  linkage. Missing exact subject binding discloses onboarding only after a valid
  current claim and active matching human profile. Case or email-like aliases do
  not link. Current profile/binding/principal activity, class, issuer/client,
  revision and valid-after fences remain authoritative. NULL stored security
  fields cannot exploit SQL three-valued logic.
- Missing unique-key rows and a deliberately duplicated exact binding fail
  closed. Synthetic constraint changes are restored before proceeding.
- A concurrent writer atomically changes browser generation, attempt generation,
  vault key ID and all three authorization revisions. Eighty preparations during
  sixty commits contain one consistent generation and remain decoder compatible.
  The read takes no row locks, changes no table content and permits concurrent
  canonical row locks. An uncommitted principal revocation does not block the
  read; activation denies after it commits.
- Valid preparations immediately before each real DB deadline, followed by
  denial at absolute, idle, attempt, claim and token deadline equality before
  unknown-binding disclosure. Actual database clock reads immediately before and
  after each denial equal its tested deadline. A genuine relation-lock wait crossing token expiry
  is denied by the post-projection DB clock check.
- Provisional revisions cannot authorize unchanged activate after intervening
  profile, binding or principal revision drift. Fresh ordinary activation works,
  and its consumed preparation subsequently denies.
- PUBLIC, ordinary-login, direct table-read and writer-role isolation; strict
  role-name and topology preflight; temporary CREATE rollback; and down/reapply
  preserving baseline function OIDs, source, settings, ownership and ACLs, types,
  relation ownership/ACL/RLS and policies. Actual version-1 Catalog admission
  accepts the baseline and down state, and rejects the additive surface.

Source inspection additionally confirms the single `SELECT INTO STRICT` uses
existing unique-key joins and constructs the snapshot inline. It does not call
the baseline multi-query snapshot helper. Its only cipher predicate is the
accepted relation-free primitive. This inspection complements executable
concurrency and privilege tests; it is not independent runtime qualification by
itself.

## Reproduction and bindings

Run from the repository:

```sh
python3 verification/hosted-browser-activation-preparation-sql-review/run.py
```

The runner starts one uniquely named disposable PostgreSQL 16 container from
`postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97`,
uses only loopback, creates isolated synthetic roles/database, and uses the exact
ordinary 3/4/6/7 migrations. The allowlist compiles only StorageSchema,
CatalogManifest, Catalog, the new schema, Vault, StoredSnapshot, the accepted
decoder and Encoding. AccessTokenVerifier is copied as a reviewed source but is
not invoked as a provider/verifier. The seven explicitly selected existing
dependency ebin directories exclude the hosted application's ebin. No broad
hosted Mix harness, app startup or discovery is executed.

Tools were PostgreSQL 16.15 (Debian 16.15-1.pgdg13+2), Elixir/Mix 1.20.4 with
Erlang/OTP 29, Python 3.14.8 and Docker Engine 29.8.2. Every command, timeout,
exit status, stdout/stderr digest and copied input is retained in the packet.
The observed HEAD was `0a6f110d8857b3732ce40b56aad33b006a187138`; the candidate
and review are bound by file digests because the shared checkout had active work.

| Bound item | SHA-256 |
| --- | --- |
| Complete selected source manifest | `278a667709143479bf509f9e8f91fed246bb45536b11d0d59c6f27f9c233768b` |
| Dependency beam manifest | `c544378354d431a88740973b97517211c514bcad9a51616cb6188cf6ee502645` |
| Accepted decoder | `e208e159719dd29ff75186667404cb6018391a2ecc3b8a3534db131d1bc281f5` |
| Independent review suite | `6ece6bb4edd403d63dd55d5654f7e5cdb6ddb2a3e44209b892f5acf5cd95c3cd` |
| Independent runner | `844631f6fa4a0eef31d4c986d09b24aeaf44666fdd730bac98b68257ed2b7670` |
| Terminal test stdout | `149127f666d8e03331b40e2a15d170c2521d526fa092f7553b2e3a2c5de5456c` |
| Terminal receipt | `be03cf57f3232c877561ae5248ab8bb6ff44e4ce77b31c0b4d1dce74395cf79d` |

Sources and selected dependency beams remained unchanged during the terminal run.
All review-owned containers were stopped and verified absent after every attempt,
including setup failures. Selected compiler products were hashed then removed;
earlier products have a separate
[cleanup record](../verification/hosted-browser-activation-preparation-sql-review/earlier-compile-cleanup.json).
Immutable source snapshots and command outputs remain. The two early setup
failures (migration pool size, then an unready `queue: false` connection) are
retained as harness failures, not product passes. No unrelated process or native
instance was discovered, started, stopped or altered.

## Remaining acceptance boundaries

The helper cannot compare the saved redirect with the current redirect because
its fixed arguments and current profile row supply no such current value. The
future owner must compare the complete retained attempt with current validated
Config, including redirect, and compare the retained claim/current access
identity/configuration before sealing. Decoder success proves shape only.
Preparation is a provisional snapshot; unchanged activate's canonical locks and
CAS remain the authority. Concurrent changes after preparation are expected and
must deny later activation.

This is an additive manifest only. Full relation/index/constraint/trigger/policy/
grant admission and combined version-2 owner admission remain pending. Operator
schema changes still require serialization. Store transaction ownership and
original operation budget, runtime pool/readiness, current verifier/custody/OIDC
provenance, production migration integration, Neon/operator deployment, HTTP/
console sessions, customer/FieldLog and GA qualification remain pending. No
frozen catalog-inspector/authority-driver or rejected Worker V2 source was read,
imported or executed. Computer use, capture, simulator/emulator runtime and
physical-device checks remain paused and were not attempted.
