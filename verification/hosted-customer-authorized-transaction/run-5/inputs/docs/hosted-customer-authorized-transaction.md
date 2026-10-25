# Customer transaction-owned authorization prerequisite

`MixerHosted.Authorization.with_authorized_transaction/4,5` owns a new local
PostgreSQL transaction from verified human identity through a bounded local SQL
callback and final current authorization check. It supports only the accepted
`artifact.upload`, `artifact.read` environment scopes and `audit.read` project
scope. The binding product scope remains `mixer-product-plan.md` §§13, 17 and 18.
No customer route or production process activates this seam.

The four-argument seam uses `MixerHosted.Repo`; the optional fifth argument is a
trusted server/test Repo module, never an HTTP-controlled selection. The callback
receives a `Transaction.Context` and returns exactly `{:ok, value}` or
`{:error, reason}`. The closed error reasons are `invalid_request`,
`unauthenticated`, `not_found`, `permission_denied`, `authorization_unavailable`,
`conflict` and `storage_unavailable`. A malformed envelope, exception, throw,
exit, SQL error or timeout rolls back and returns a bounded failure. Callback
payloads and internal exception text do not become public diagnostics.

The existing pure Policy, Decision, Repository and PostgresRepository contracts
are unchanged. A pure Decision remains audit-oriented evaluation data and is
never accepted as transaction authority. This facade invokes Session.prepare!
and Evidence.load! directly inside its own transaction, without starting a
nested PostgresRepository transaction. Identity, action and target validation
runs before any database work. An existing transaction or active request-local
context rejects; facade recursion cannot join an unknown transaction.

## Live binding and effects

The facade uses `Repo.transaction(queue: false, timeout: 5000)`, the existing
READ COMMITTED transaction and five-second statement/idle bounds, the 500 ms lock
bound and the existing exact profile → principal → family → credential →
organization-head → project-head lock order. The runtime remains SELECT-only on
all authorization tables with execution of the six existing fixed lock helpers;
this change adds no authz DML grant or security-definer function.

One bounded owner-process dictionary entry retains the complete immutable
Context and locked policy evidence for this invocation. No global mutable
authority, reusable authorization ticket, allow cache or request registry exists.
Every checkpoint compares the entire Context, owner PID, Repo and dynamic Repo,
exact action and Scope, live transaction state, PostgreSQL backend PID and
transaction ID, current/session user and all identity/target/linkage/action
settings. A distinct random 256-bit transaction-local marker binds that SQL
transaction. Fabricated/changed fields, foreign tasks/connections/repositories,
a changed identity setting and reuse after commit/rollback reject. Failures are
latched before rollback, so catching a rollback or exception in the callback
cannot make finalization succeed. The binding is deleted on every completion.

`Context.checkpoint!(context, repo, action, exact_scope)` returns a fresh checked
Snapshot. `Context.effect!(context, repo, action, exact_scope, fn snapshot -> ...
end)` performs that check immediately before calling synchronous local SQL code.
A future domain store must checkpoint again after waiting for its own later
mutation head and use effect! immediately before a write or a cached-result
return. No domain mutation head or artifact metadata resolver is implemented in
this slice. In particular, private artifact read still needs a separate bounded,
project-visible metadata-only resolver before this exact-environment seam.

Callbacks must use the same transaction for synchronous local SQL only. They
must not open/close transactions, issue transaction-control SQL, switch Repo,
spawn database work or perform filesystem/network/provider/external effects.
An effect callback may return an ordinary SQL result, Snapshot or other value.
An explicit `{:error, reason}` return instead latches rollback: a recognized
bounded reason is retained and an unknown reason becomes
`authorization_unavailable`. An escaped effect exception, throw or exit also
latches rollback before sanitizing the failure; catching it in the outer callback
and returning success cannot commit prior SQL.

External effects cannot be rolled back. Structs, process dictionaries and this
trusted BEAM API discipline are not a sandbox against malicious application
code, hostile SQL or compromised database credentials. Deployment still needs
its separate least-privilege and accountable security review.

## Time and immutable evidence

There is no production `now`/clock argument. Server wall time is read before
admission, freshly after the final authorization lock wait, before entering the
callback, immediately before every effect/checkpoint, and as the last operation
before returning successful callback data to Ecto's commit. Policy is evaluated
at those current times. Expired identity/credential/family/membership windows
cannot use the earlier caller-captured time of the pure lookup seam. Wall-clock
regression below admission or the last successful checkpoint fails closed.
An independent monotonic deadline bounds the complete owned transaction to
five seconds, including synchronous callback execution, in addition to Repo's
connection timeout. The existing Policy 30-second future-issued-at allowance
is preserved. An OS clock adjustment itself was not performed during testing.

The closed bounded Snapshot contains:

| Record | Retained fields |
| --- | --- |
| Request | Server-generated random 128-bit hex request/correlation ID, exact action/target and checked server time; caller request IDs grant no authority |
| Profile | Full id/version, issuer, client, identity class, active state and separate state revision |
| Binding | Immutable composite profile/version/SHA-256(exact subject) key, class, principal, active state and binding revision |
| Principal | Full id/class/active/valid-after state and revision |
| Credential | Exact profile/version/reference, principal and family ID, independent active/window/revision |
| Family | Exact family id/profile/version/principal, independent active/window/revision |
| Selected memberships | Full lifecycle id, principal, role, scope, project-binding mode, active/window/revision |
| Heads | Organization/project ids and independent authorization revisions |
| Verified token identity | Exact verified namespace/class/reference and subject digest, token issued_at/expires_at and scopes; these are token times, never auth_time |

The loader verifies raw locked row linkage, the current pure policy projection,
the complete closed nested Snapshot and exact live Context binding separately.
Snapshot validation does not weaken Policy or Decision shape. Raw subjects and
bearer token bytes are absent from the Snapshot. Later checkpoints return newly
selected full membership rows if a timed grant expires and another valid grant
still permits the action. The initial snapshot inside the exact Context remains
immutable. The request ID and binding nonce are distinct random values.

Migration `20261025000004` adds only profile `state_revision` and binding
`revision`, each positive bigint bounded to 9007199254740991 with DEFAULT 1.
This is an initial baseline for the newly introduced schema, not reconstructed
old history. Migration 003 is unchanged. Controlled audited writers, monotonic
revision advancement and lifecycle/non-recycling enforcement remain pending.

## Verification and limits

The owned collector runs without the shared harness, application startup, Git,
network/provider actions, frozen catalog/authority/WorkerV2 code or native/UI
work:

```sh
python3 verification/hosted-customer-authorized-transaction/run.py \
  --output verification/hosted-customer-authorized-transaction/run-N \
  --source-revision ROOT_SUPPLIED_REVISION
```

It loads existing pinned dependency BEAMs and compiles only the named ordinary
Repo/identity/policy/Session/Evidence sources and this facade/migrations, with
warnings as errors. It checks formatting of the new owned sources and runs only
the new focused test. It owns a unique temporary loopback-only PostgreSQL cluster,
new database, synthetic superuser fixture, nonlogin authorization owner and
separate read-only runtime. The SQL write probe is a disposable test-only table,
not a domain artifact product implementation. Every attempt records exact
selected source copies, hashes, root-supplied revision, dependency BEAM hashes,
commands, versions, output, failures and owned cluster/scratch cleanup.

Real PostgreSQL cases cover all 18 six-role/action intersections; full separate
revision snapshots and bounds; fabricated/modified context and closed nested
snapshot values; wrong owner/task/Repo/dynamic Repo/action/target/GUC; capture
and reuse after commit/rollback; every callback envelope/failure class with an
actual SQL write rolled back; expiry during an observably blocked row-lock wait;
expiry before effect and before final commit; surviving timed grants; lock and
full-transaction timeouts; exact state/windows; direct and indirect privileged
role rejection; and connection-reuse cleanup. A controlled last-checkpoint state
probe exercises the clock-regression rejection branch without changing the host
clock; it is not an OS clock-correction receipt.

Protected artifact metadata/content, immutable manifest admission, same-connection
domain RLS, immutable actor audit encoding/storage, principal-bound idempotency,
Oban composition, protected HTTP/console, audited identity/membership writers,
provider-issued identities, deployed Neon/Cloudflare/TLS/topology, operations,
FieldLog immutable published-package consumption and accountable GA acceptance
remain pending. No production migration/publication, customer message, signing,
credential change, native/simulator/emulator/physical-device action occurred.
