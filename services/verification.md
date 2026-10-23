# Update/release local reference evidence

Date: 2026-10-22. Lane: W10/W11 update/release local reference.
Requested/selected delegate: `gpt-6.1-sol`, `xhigh`, fresh context, bounded to
`services/**` and `contracts/release-v1.json`.

Tool: `go version go1.26.4 darwin/arm64`.
Source identity: the commit containing this file; reproducible lane tree digest
is the sorted SHA256 list of all files under `services/` plus
`contracts/release-v1.json` (excluding this receipt). The root integration
verification index records the exact commit/tree digest after commit.

Run from `services/`:

```sh
go test -race ./...
go vet ./...
go test ./protocol -run '^$' -fuzz FuzzStrictJSONNeverPanics -fuzztime=3s
go test ./... -cover
go build -o /tmp/mixer-service-reference ./cmd/mixer-service
```

Observed results:

- Race tests passed in protocol, release and updater packages. No race reports.
- `go vet ./...` passed with no diagnostics.
- The bounded strict-JSON fuzz run passed: 387,614 executions in 4.142 seconds,
  45 newly interesting inputs on that run. A prior exploratory five-second run
  also supplied local fuzz cache; the quoted run is the fully captured receipt.
  This is bounded fuzz evidence, not exhaustive parser/security qualification.
- Statement coverage from the final captured run: protocol 83.9%,
  release 85.4%, updater 78.8%. Helper,
  durable and command packages are exercised transitively but Go's per-package
  default coverage output reports 0.0% for packages without direct tests.
- The runnable service binary built successfully outside the checkout.

Executed behavior includes:

- Hand-authored canonical CBOR integer, string, boolean, collection and ordering
  vectors; exact signed-domain byte checks; unsupported data model rejection.
- A static cross-language manifest/assignment vector contains exact canonical
  CBOR hex, public keys, signatures, payload, digest and cohort bucket. Signing
  keys were generated ephemerally once and discarded; no private fixture keys
  are retained. Go verifies the fixture independently on every test run.
- App/tenant/environment/platform/runtime/protocol/ABI/UI/capability/state/budget
  substitutions, payload digest/size tampering, separate assets/compression,
  unknown keys, wrong key roles, revocation and root validity windows fail.
- Assignment replay and stale rollback fail. New-sequence rollback succeeds.
  Signed rollout changes fail; deterministic cohort expansion preserves members.
  JSON duplicates, unknown fields, trailing values, negative/fractional/overflow
  integers fail; maximum uint64 survives transport without precision loss.
- Resumable interrupted downloads, source overruns/tamper, cancellation retaining
  high-water, free-space reserve, private process locks and contract changes on
  reopening. Startup attempts are durable; health windows reject missing
  milestones, early completion and backwards clocks. Confirmed startup traps
  quarantine; unrelated/unknown interruptions do not count as guest failures.
- Disk eviction/corruption retains healthy/native fallback. Retention is bounded
  to two healthy generations and the current candidate. Existing healthy
  selection remains possible offline and after root revocation/expiry changes.
  Cached manifest/assignment signatures and artifact identity are reverified;
  metadata tampering cannot turn cached bytes into an authorized selection.
- Injected ENOSPC before write, file fsync, rename, after rename and directory
  fsync for metadata; before payload write, payload fsync and payload rename.
  Reopening sees an intact previous or next state, never a half-selected update.
  These are controlled in-process I/O faults, not real power-loss/device tests.
- Versioned HTTP upload/validate/publish/promote/rollback, unauthenticated public
  assignment/download, tenant isolation, reader/editor/publisher permissions,
  signed-scope substitution, immutable upload, malformed input/rate limits.
- Twenty concurrent identical mutations produce one durable audit/outbox result.
  Two distinct concurrent next-sequence promotions produce one success and one
  replay conflict. Changed route/body with the same idempotency key conflicts.
- Each commit fault can restart/retry without duplicate audit/outbox entries.
  Audit-chain corruption fails opening. Restart retains rollback sequence;
  newly revoked artifact authority cannot authorize publication.
- Actual loopback HTTP health request and graceful context shutdown pass.
  Public listener/hostname, duplicate roots/hosts, missing authority and
  production mode are rejected.

Limitations of the initial local JSON receipt: No PostgreSQL, multi-host transaction isolation, object storage/CDN,
external outbox delivery, build workers, billing, hosted operations, compiler
eligibility integration, executable VM update loading, mobile storage adapters,
device signing, store distribution, data-migration proof or independent FieldLog
package consumption was verified here. No physical iOS/Android, dogfood or GA
gate is passed by these local Go tests. Independent adversarial review and
device fault matrices remain required.


## W11 PostgreSQL substrate follow-up

The subsequent original PostgreSQL adapter is documented in
[`release/POSTGRES.md`](release/POSTGRES.md). Its schema and HTTP field shapes are
separate concerns: the signed v1 manifest/assignment protocol was not changed.
The detailed follow-up receipt is
[`verification/postgres-2026-10-22.json`](verification/postgres-2026-10-22.json).

Final checks use pinned Go 1.26.4, pgx 5.11.0 and real isolated PostgreSQL 17.11.
`go test -race -count=1 -json ./...` recorded 60 passed test/subtest events, zero
failures and zero skips (24 top-level tests/fuzz targets). `go vet ./...`,
`go mod verify` and the runnable service build passed. The existing complete local
HTTP/CLI release workflow also passed for both platform scopes.

The dedicated real PostgreSQL runner executes seven database test functions
plus three commit-interruption subtests, as well as the unit configuration test
selected by its name filter. It covers two independent service instances,
concurrent idempotency/sequence conflicts, tenant/RBAC/FORCE RLS, immutable rows,
uint64 limits, a 16 MiB payload, query deadlines, unsafe-role/schema refusal,
ledger corruption, exact retry after uncertain publication, actual immediate
PostgreSQL crash/restart, and dual-platform delivery through an actual loopback
HTTP listener. The database cluster uses only a private Unix socket, disables TCP
listening and is deleted after the run. Database crash recovery is real local
PostgreSQL evidence; injected before/after-commit response faults are controlled
faults. Neither is a hosted multi-zone, backup restore or mobile/device receipt.

Local config tokens remain bootstrap authority. Identity/account/membership
lifecycle, SCRAM/TLS deployment, workers/outbox dispatch with leases/fencing,
object storage/CDN, retention/quotas and operational/independent security review
remain open. Production startup is still refused. No W11 hosted launch, D0 or GA
gate is passed by this substrate.
