# Durable customer authorization lookup prerequisite

`MixerHosted.Authorization.PostgresRepository` supplies real current PostgreSQL
evidence to the existing pure authorization callback. It supports the existing
human artifact read/upload and project audit read decisions with their exact
verified token scopes and six-role ceilings. The binding scope remains
`mixer-product-plan.md` §§13, 17 and 18. This is a lookup prerequisite, not a
complete protected customer operation, connected console, or GA acceptance.

Root froze the contract before implementation. This slice owns only the new
adapter, its `authorization/postgres/` modules, migration `20261025000003`, focused
test, this document and its verification directory. Existing policy, repository
facade, shared Repo/config/router/dependencies and test harness were unchanged.
The ordinary facade still defaults to `Repository.Unavailable`; no production
route or process activates this adapter.

## Records and authority

All new relations are independently named `public.mixer_authz_*`. They do not
reinterpret the existing build tables or historical Go migration.

| Relation suffix | Meaning |
| --- | --- |
| `profiles` | Versioned issuer, registered client, class and active state; verifier trust/JWKS configuration remains separately owned |
| `principals` | Internal human/service identity, active state, valid-after fence and revision |
| `bindings` | Exact profile/version/subject to principal and class; profile carries the exact issuer/client/class tuple |
| `families` | Existing registered credential-family state, validity window and revision |
| `credentials` | Existing registered verified JWT `jti`, namespaced by profile/version, linked to one matching principal/family, with its own state/window/revision |
| `organizations`, `projects`, `applications`, `environments` | Stored active ancestry with composite foreign keys through every parent |
| `organization_heads`, `project_heads` | Existing serialization rows and current authorization revisions |
| `memberships` | Non-wildcard lifecycle IDs, principal, six canonical roles, exact project or explicit organization binding, active/window/revision |

Unknown profiles, bindings, principals, token references or families cannot
bootstrap authority. The adapter checks the whole verified issuer/client/class
tuple. The family and token state intersect: either disablement denies, the
later valid-after fence applies, and the earlier non-null expiry applies. No
bearer token is stored. Service identity and unsupported actions remain denied.

Composite constraints prevent foreign project/application/environment lineage,
cross-principal families and class confusion. Organization memberships distinguish
`organization_only` from explicit `all_projects`; project memberships require
`exact_project`. Queries do not infer wildcard authority from a null project.
Provisioning and revocation writers are test-only in this slice; a production
audited writer and lifecycle/non-recycling enforcement remain separate work.

## Connection and locking protocol

`with_evidence/2` implements the existing trusted callback seam using
`MixerHosted.Repo`. The `with_evidence/3` variant selects a Repo only from trusted
server code and supports isolated verification. Neither accepts HTTP-controlled
repository selection. Invalid direct lookups fail closed. The adapter rejects an
existing transaction rather than joining one with unknown isolation, deadlines
or context.

The adapter starts a fresh real Repo transaction with `queue: false`, a five-second
transaction/statement timeout and a shorter 500 ms lock timeout. It explicitly
uses READ COMMITTED. All identity and scope settings use parameterized
transaction-local `set_config` on that transaction's connection. Shared locks
are acquired in this order:

1. Exact trust-profile/version row.
2. Principal resolved from the exact external binding.
3. Existing credential-family row resolved from the registered token reference.
4. Exact registered token row.
5. Requested organization authorization head.
6. Requested project authorization head.

Each state, membership and target query then runs as a separate fresh statement
after the final lock wait. The post-lock binding/principal/family relationships
must match the rows whose locks were acquired. The adapter never follows an
unlocked replacement principal or family. These reads establish current stored
ancestry; the caller's requested scope alone is insufficient. They do not bind
an artifact payload or replace immutable-manifest admission.

The indexed membership lookup filters exact principal/organization and only the
requested project plus explicit `all_projects` rows, orders lifecycle IDs, and
uses `LIMIT 65`. At most 64 matching lifecycle rows enter policy. A 65th row,
including inactive matching history, yields `authorization_unavailable`; the
adapter does not approximate permission from an incomplete result. Unrelated
projects and organization-only populations do not consume that bound. Query,
pool, lock or transaction failures roll back and deny. No positive evidence is
cached and no automatic retries are added.

The test-only writer takes shared locks on earlier classes and a conflicting
update lock on the affected class/head, in the same order, before changing
state and applicable revision. Project membership insert/reactivation/removal
uses the existing project head; organization-wide changes use the organization
head. Binding/linkage changes require the profile fence. An admitted lookup
retains its shared locks through its callback. A concurrent revoke waits for
that lookup to finish; after the revoke commits, a new lookup denies. In the
reverse ordering, authorization waits and then reads the revoked state. This
does not undo an operation admitted before revocation returned.

## RLS and runtime privileges

Every table enables and forces RLS. Scoped identity visibility requires the
exact verified profile/version/issuer/client/class and subject. Principal,
family, credential and membership visibility joins the matching binding;
an arbitrary principal GUC alone cannot expose another identity. Membership
rows remain scoped to that principal and requested organization/project.
Resource rows additionally require a currently active, in-window matching
membership and the exact stored requested ancestry. Authorization heads remain
visible under exact bound identity/tenant context even when no membership
exists, so provisioning can serialize absence through an existing lock row.

The runtime is read-only on authorization tables. PostgreSQL requires UPDATE
privilege and an applicable UPDATE USING policy for `SELECT ... FOR SHARE`,
so six fixed SQL `SECURITY DEFINER` helpers perform only the scoped shared-lock
queries. Each has `search_path=pg_catalog`, fully qualified objects, no dynamic
SQL or DML, and no PUBLIC execution. A scoped UPDATE USING policy permits the
same locked row, with `WITH CHECK (false)` preventing row updates. Operators
must explicitly grant runtime SELECT and helper EXECUTE; the migration creates
no role, runtime grants or production credentials.

The adapter rejects superuser/bypass/role-admin/database-admin/replication
authority, owner-role chains, a switched privileged session, missing FORCE RLS,
unsafe helper-owner topology, missing helper privileges, and table or column
authorization DML grants. Both relation and helper owners must be nonlogin,
non-superuser, non-bypass roles. The fixture demonstrates FORCE RLS still
applies to that owner, including helper calls with missing context, and that the
separate runtime cannot directly lock rows, mutate policy, assume the owner or
create objects in the protected public schema.

This is the existing trusted API threat boundary. The application can set
identity GUCs; these are not cryptographic database identity and do not protect
against hostile application SQL or compromised API credentials. A production
security review must qualify all role chains, function ownership, grants and
schema ownership in the deployed database. Synthetic local evidence does not
qualify that topology on Neon.

## Preserved boundaries

The existing policy receives the caller's captured evaluation instant. The
lookup seam contains no token timestamps or trusted clock. Current rows are
read after waits, while token/credential/principal temporal policy uses that
captured instant. A finite test deliberately evaluates after wall-clock token
expiry with the earlier instant and succeeds; a new request with current time
denies. This documents the current seam, adds no cache/TTL/grace allowance, and
does not claim a fresh check immediately before an effect. Membership RLS also
checks the database statement clock and can deny more conservatively. The
future domain facade must use a trusted clock and recheck before persistence.
The existing 30-second future issued-at allowance remains unchanged.

The callback envelope is returned unchanged from within the real transaction.
Its reference and complete Decision projection remain accidental-adapter-error
containment, not a malicious-BEAM sandbox or transferable capability. A pure
Decision is not accepted by a domain repository. Its existing
`credential_revision` is the exact token-row revision. The projection still
lacks separate family, binding and per-membership revisions required by the
future immutable audit schema; no lossy aggregate revision was invented.

Still required: transaction-bound domain authority, immutable artifact/content
binding, a same-connection domain/RLS check before private storage, trusted-clock
recheck, immutable actor audit, principal-bound idempotency after current
authorization, atomic Oban intent, protected HTTP/console workflows, audited
provisioning/revocation, customer restrictions and release/service/CI policies,
real issuer/SSO, Neon/TLS/hosting and operations qualification, FieldLog published
package consumption and accountable GA review. None is marked accepted here.

## Executed evidence

Run the explicitly selected collector:

```sh
python3 verification/hosted-customer-authorization-postgres/run.py \
  --output verification/hosted-customer-authorization-postgres/run-N \
  --source-revision ROOT_SUPPLIED_REVISION
```

It compiles only the ordinary identity/policy sources and this adapter/migration
with warnings as errors, checks formatting, loads the existing pinned Ecto and
Postgrex dependencies, and runs the focused ExUnit file without Mix application
startup or the shared test harness. It creates a unique owned temporary root,
a loopback-only PostgreSQL cluster on an ephemeral port, synthetic admin and
separate nonlogin owner/runtime roles, and one owned disposable database.
No existing PostgreSQL service/database is selected. Each attempt records exact
selected inputs, copied source bytes, source digest, supplied revision, commands,
tool versions, outputs and cleanup. No Git or frozen lane runs.

Producer `run-8` passes **23/23 methods**, including all 18 six-role/action
combinations, six lock-class orderings in each direction, project provisioning,
family/token windows and fences, exact ancestry, identity/RLS/adversarial role
checks, membership bounds, callback rollback/context reuse and timeout behavior.
The executed source-tree digest is
`beec602cfcc4cb17fc49ae09a636608d8c970240e8e9c5dc276edc95e2fdd45b`;
revision `cb56d4b9d979ffc02554be991466a180e7882cd3` is root-supplied context,
not a queried Git revision. Environment: Darwin arm64, Elixir 1.20.4,
OTP 29 / ERTS 17.1, PostgreSQL 17.11 and Python 3.14.8, `ERL_FLAGS='+S 2:2'`.
The owned cluster stopped and temporary root was removed.

Attempts `run-1`–`run-7` are retained as failed historical evidence. They exposed
format/compile and fixture issues, the PostgreSQL row-lock RLS requirement, and
test-helper mistakes before the passing run. Every attempt cleaned its owned
scratch and any started cluster. No production migration/deployment, provider,
customer communication, native/UI/simulator/emulator or physical-device work
occurred. Independent review remains required before integration acceptance.
