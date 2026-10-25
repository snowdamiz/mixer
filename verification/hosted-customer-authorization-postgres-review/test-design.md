# Independent review design

Status: contract design only; no candidate source has frozen and no database
review has executed. Root supplied source revision context
`cb56d4b9d979ffc02554be991466a180e7882cd3`.

Review owns this directory and
`docs/hosted-customer-authorization-postgres-review.md` only. The producer owns
the new adapter, its PostgreSQL support, the coordinated new migration, focused
tests and producer evidence. No shared root tracker, router, configuration,
dependency, product plan, ordinary policy, or producer file may be edited here.

The pure policy correction is accepted only as finite host evidence. Its result
does not establish current database state, locks, revocation, RLS or a reusable
domain authority context. The candidate must keep that boundary explicit.

## Required review observations

1. The exact verified profile/version/issuer/subject/client/class tuple resolves
   an immutable binding, then its non-recycled principal, an existing registered
   token reference and its explicit credential family. Token claims and caller
   target selectors cannot create rows, memberships or a family. Disabled,
   unknown, mismatched and unsupported state fails closed.
2. Each evidence call owns a fresh READ COMMITTED transaction on its actual
   injected Repo. Nested calls reject. Ecto checkout has `queue: false`; the
   transaction and statements have 5-second limits and locks have 500 ms. No
   positive decision cache, detached connection, session SET, asynchronous
   callback or second pool may stand in for same-connection evidence.
3. Shared row locks occur in canonical profile, principal, family, credential,
   organization head, project head order. Real conflicting update-lock writers
   follow that same order. Forward races prove a revoke waits for an admitted
   reader; reverse races prove a reader waits then rejects revoked state. Fresh
   SELECTs after all waits must see membership removal/insertion and head changes.
4. Principal, profile, family and credential enablement, valid-after fences and
   validity windows apply. Family/credential projections intersect without
   inventing an audit revision encoding. Immutable identity and family linkage
   cannot silently change while admission waits on later lock classes.
   The existing facade captures caller-supplied `now` before database admission;
   its lookup contains identity key/action/target only. Current database records
   after locks do not prove a new trusted wall-clock expiry check. An explicit
   expiry-during-wait control must preserve this distinction: policy still uses
   the captured instant, a new evaluation at expiry rejects, and no new TTL/grace
   is created. Future effect persistence still requires trusted-clock recheck.
5. Real target existence and active ancestry match every requested ancestor.
   Project-only audit and environment artifact scopes remain distinct. The six
   pure human role ceilings and exact OAuth scopes remain in force. Organization
   access requires explicit all-project binding and never crosses organizations.
6. Indexed exact-target membership reads are bounded. Exactly 64 qualifying
   lifecycle rows may evaluate; observing a 65th returns unavailable. Inactive or
   role-ineligible exact-target rows cannot hide an overflow by filtering first.
7. All authz tables use FORCE RLS, runtime SELECT only, exact identity and target
   scope policies, and no global principal/member enumeration. Missing, malformed,
   wrong identity or tenant context exposes no private rows. Direct UPDATE,
   INSERT, DELETE, TRUNCATE, owner role changes, unsafe role chains and bypass
   attributes cannot create runtime authority.
8. The fixed SQL SECURITY DEFINER helpers only acquire scoped shared locks.
   Function and table ownership belongs to a nonlogin, nonsuperuser,
   non-bypass role, functions fix pg_catalog search_path, use fully qualified
   relations, contain no dynamic SQL or DML, and deny PUBLIC execution. Runtime
   lacks UPDATE privilege; SELECT FOR SHARE is supplied only by the helpers.
9. Runtime safety checking rejects migration/table/helper owner authority and
   direct or indirect unsafe role membership. Catalog inspection must use
   real PostgreSQL state. Function grants, policy expressions, owners and role
   topology are part of the review, not inferred from source alone.
10. Callback exceptions, throws, SQL errors, lock timeout and total transaction
    timeout return bounded unavailable results, roll back, release every lock,
    clear transaction-local context on pooled connection reuse and never leak a
    success envelope. Callback executes once on the transaction connection.

## Evidence rules

After source freeze, retain exact selected input bytes and hashes, executable
independent probes, commands, tool versions, source revision/tree digest,
stdout/stderr, status and cleanup. Rerun producer tests independently where the
selected standalone harness permits. Use a unique owned loopback PostgreSQL
fixture; stop it and remove its scratch root even after test failure. Do not
import or execute shared Mix startup or any frozen/rejected hosted lane.

Root subsequently extended review to the minimal ordinary standard-harness
fixture provisioning and selected migration-loading integration. Review only
that additive frozen delta and an explicitly selected safe invocation; do not
run broad shared test discovery or a frozen lane. The completed security run
and historical failure reproduction remain separate immutable evidence.

Acceptance can cover only this local PostgreSQL evidence adapter. Full immutable
audit construction (including binding, family and membership revisions), the
separate domain authorization context, domain/idempotency/audit/Oban atomicity,
protected routes, customer console, provider/Neon/deployment, service/CI,
release/approval, operational and accountable GA review remain pending.

## Primary references consulted

- PostgreSQL READ COMMITTED: new statements take new committed snapshots and a
  waiting locking SELECT can lock an updated row. Fresh subsequent reads remain
  necessary for other tables and membership insert/remove races:
  https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL row locks and their transaction lifetime:
  https://www.postgresql.org/docs/current/explicit-locking.html
- PostgreSQL 17 RLS, owner/bypass behavior and FORCE RLS:
  https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- PostgreSQL 17 SELECT permissions and locking:
  https://www.postgresql.org/docs/17/sql-select.html
- PostgreSQL security-definer search_path and PUBLIC execute defaults:
  https://www.postgresql.org/docs/current/sql-createfunction.html
- Ecto transaction API and DBConnection pool/timeout boundaries (live docs are
  not a substitute for the exact pinned dependency source used by the fixture):
  https://ecto.hexdocs.pm/Ecto.Repo.html
  https://db-connection.hexdocs.pm/DBConnection.html
