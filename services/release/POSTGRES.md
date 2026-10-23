# Local PostgreSQL release substrate

This adapter implements the existing versioned release HTTP API with PostgreSQL
transactions. Developer mode and literal loopback HTTP binding remain mandatory.
It does not enable hosted production, an identity provider, organization
onboarding, external jobs, CDN delivery, billing or mobile OTA qualification.

## Configuration and separate credentials

Use the normal scoped-token/root/host configuration from `../README.md`, replacing
the local storage settings with:

```json
{
  "storage_backend": "postgres",
  "postgres": {
    "connection_string_env": "MIXER_POSTGRES_RUNTIME_DSN",
    "max_connections": 4,
    "query_timeout_milliseconds": 5000
  }
}
```

This fragment is not a complete service configuration. The named environment
variable contains an operator-configured PostgreSQL connection string. Only an
absolute Unix socket directory or a literal loopback IP is accepted, including
all driver fallback hosts. There are no default credentials. Connection strings
and SQL driver errors are excluded from HTTP and service errors. Each configured
token hash must be unique and remains bound to one organization/project and role.
The static local token configuration is bootstrap authority; real account,
membership, revocation and credential lifecycle APIs remain open work.

Use PostgreSQL 14+ with `fsync=on`, `full_page_writes=on` and durable synchronous
commits. PostgreSQL 17.11 is exercised by the isolated test runner. Runtime pool
size is 1..16 (default 4), operation timeout is 100..15000 ms (default 5000),
connection establishment is bounded to two seconds, and incoming driver messages
are bounded to 20 MiB. Startup requires the embedded schema checksum, all eight
FORCE RLS tables and a safe runtime role. No migration runs during normal startup.

Apply the embedded migration using separate owner credentials supplied in a
separate environment variable:

```sh
MIXER_SERVICE_CONFIG=/absolute/private/developer.json \
  /absolute/path/mixer-service migrate-postgres \
  --connection-env MIXER_POSTGRES_MIGRATION_DSN
```

The reviewed original migration is `migrations/001_release.sql`. A transactional
migration lock and exact checksum make retries safe; unknown schema versions or
modified checksums fail closed. Startup and migration retry require the explicit
version1 marker as well as its checksum; the checksum alone cannot authorize an
unknown version. Initial group-role creation requires migration
owner CREATEROLE authority, or an operator can precreate the reviewed
`mixer_release_runtime` NOLOGIN group. The service never creates a login or grants
membership to a runtime credential. An operator provisions a distinct runtime
login with inherited membership in that group and without superuser, BYPASSRLS,
CREATEROLE, CREATEDB, or usable ownership of any release schema/table/function.
Runtime startup rejects direct, inherited, `SET ROLE` and administratively
obtainable owner authority. On PostgreSQL16+, membership with `INHERIT FALSE`,
`SET FALSE` and no usable `ADMIN OPTION` path is preserved. Before16, membership
permits `SET ROLE` and is checked accordingly. Startup requires inherited usage
of the runtime group. Schema ownership can drop contained immutable records even
if another role owns the tables; guard-function ownership can remove a trigger
and defeat monotonic updates. The administrator-role closure includes authority
inherited or assumed through other roles, rather than checking direct grants only.

Database ownership alone is not treated as ownership of those installed objects:
the PostgreSQL17.11 probe retained FORCE RLS and denied their alteration. This
does not qualify database administration as a production security boundary;
database credentials and administration remain trusted.

Switching from the local JSON backend does not copy its state into PostgreSQL.
Select a fresh reviewed database explicitly. No destructive migration, remote
credential change or production database operation is performed by this slice.

## Storage and authorization contract

The HTTP middleware derives the storage access envelope from the validated
bearer token and organization/project route. A request's manifest or assignment
cannot select its storage tenant. The store independently checks scope, actor,
required reader/editor/publisher role, artifact identity and assignment identity.
Public delivery has separate read methods and a `delivery` database context that
can select only published artifacts and current channel assignments.

Every PostgreSQL operation begins a transaction, installs tenant/role settings
with transaction-local `set_config`, and uses parameterized tenant predicates.
The settings reset at transaction end before a pooled connection is reused.
FORCE RLS scopes reads and writes; write policies require editor/publisher and
channel publication requires publisher. The runtime has no DELETE/TRUNCATE/DDL
rights. The application server remains trusted to derive those settings from
authenticated context. Possession of its database credential is not tenant user
authentication; RLS is defense against missing predicates and incorrect bindings,
not a sandbox for a compromised service process or DBA.

The schema contains:

| Table | Durable responsibility |
| --- | --- |
| `tenant_heads` | Project-scoped mutation lock, audit high-water and state commitment |
| `artifacts` | Immutable signed-manifest transport and bounded payload bytes |
| `artifact_state` | Separate monotonic protocol-validation/publication flags |
| `assignments` | Immutable signed assignment history, including full uint64 sequence |
| `channel_heads` | Current assignment FK and strict increasing sequence |
| `idempotency` | Tenant/key request hash, exact response bytes and status |
| `audit_events` | Immutable tenant-ordered event bytes and hash-chain links |
| `outbox` | Immutable pending local work committed with its event |

Each mutation locks its tenant head before reading idempotency or domain state.
The request hash binds method, route and exact request bytes. A matching retry
returns the original status and response bytes. A changed operation or body with
the same tenant/key returns 409. Another tenant can use that key independently.
Failed operations roll back every row and reserve no key. Competing assignments
therefore observe the committed high-water; exactly one can commit the same next
sequence. Rollback needs a newer signed sequence and a previously published
immutable artifact. Immutable-content conflicts cannot replace artifact bytes.

One commit includes domain changes, assignment history/head, idempotency response,
audit and outbox. A connection failure or uncertain commit returns sanitized 503;
retrying the same key distinguishes a committed result from an aborted one.
There is no blind automatic transaction retry and no external effect performed
inside a transaction. The pending outbox has no worker, lease, fencing token,
delivery acknowledgement or external dispatch claim yet.

Queries fetch a single artifact (at most 16 MiB), a single channel, a bounded
64-row capacity count or at most 100 audit/outbox records. No mutation loads all
payloads for a tenant. The development cap is 64 artifacts per PostgreSQL tenant.
Retention, quotas, object storage and customer deletion/export policies need
separate implementation and operational review.

## Audit byte contract

PostgreSQL audit IDs start at one within each tenant. The existing `after` cursor
is opaque to clients and is interpreted within that tenant. Filesystem audit IDs
retain their original local-store ordering. No response field shape changes.

Audit hash input is Go `encoding/json` serialization of the fixed `Event` struct
with `hash` set to the empty string. Struct field order is fixed; nested domain
map keys are sorted by the JSON encoder. Exact serialized bytes are stored as
BYTEA rather than reserialized JSONB. The previous audit hash and event identity
are verified at the tenant head before mutation and across paginated audit reads.

The PostgreSQL `previous`/`current` fields commit to the ordered transaction
transcript: the initial state is SHA256 of `mixer.release.tenant-state.v1`, then a
change hashes the prior commitment and ordered `{kind,key,before,after}` target
hashes. An operation with no domain change retains the state commitment. This
avoids full-tenant payload scans. Target hashes use deterministic JSON struct/map
encoding; hash inputs do not depend on map insertion or SQL row order. Local JSON
storage retains tenant-domain snapshot hashes. Neither chain is an externally
anchored, DBA-resistant audit log.

## Reproduce real database tests

From `services/`:

```sh
GOTOOLCHAIN=go1.26.4 go test -race ./...
GOTOOLCHAIN=go1.26.4 python3 verification/postgres.py \
  --output /absolute/new/evidence-directory
```

The runner requires installed `initdb`, `pg_ctl`, `psql` and Go. It creates a new
0700 directory, Unix-socket-only PostgreSQL cluster, rejects TCP connections, uses
local trust solely inside that private test cluster, and deletes the cluster on
completion. It never opens the installed Homebrew cluster or creates credentials
in another database. The tagged real tests refuse a database without the runner's
private marker and matching `data_directory`.

Real database tests cover two service instances, twenty concurrent idempotent
uploads, competing assignment publication, cross-tenant/RBAC/RLS adversaries,
immutable rows, pagination, full uint64 sequence, maximum/oversize payloads,
query cancellation, owner/unsafe-role/schema refusal, corrupt ledger head,
before/after publication commit faults, and an actual immediate PostgreSQL crash/restart
inside an uncommitted publication. Unit tests and controlled faults are recorded
separately from real database crash evidence. Multi-zone failover, backup restore,
operational RPO/RTO, hosted authentication and launch review remain open.
