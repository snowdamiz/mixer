# Durable build decisions and atomic job insertion

`MixerHosted.Builds.Storage` persists each platform build as a bounded replayable
journal in PostgreSQL. It reconstructs the lifecycle from validated creation
inputs and ordered events; it never trusts a stored `Build` struct or status
snapshot. Every read/transition uses organization, project, application, build
and platform. Unique constraints separately protect build and request identity.

This is an internal storage API. It is not project authorization, membership-aware
RLS, an authenticated build endpoint, worker authentication, quota admission or a
production dispatcher. The existing router remains liveness-only. No frozen
catalog-inspector/authority-driver code or grant is changed. Customer build
routes and the production console data source remain unavailable.

The integration points are:

- `create_multi(multi, name, spec, policy, request_key, now_ms, job_factory)` adds
  the record and an exactly bound Oban job to the caller's transaction.
- `read(scope)` reconstructs a build under its full scope.
- `transition_multi(multi, name, scope, expected_revision, event_id, event,
  now_ms, job_factory)` locks the record and applies revision CAS.
- `cancel_multi` supplies the lifecycle cancel event through the same boundary.

An applied operation returns `%{record: record, build: build, outcome: :applied,
intent: intent}` at `name`. The Oban row is returned at `{name, :job}`. The intent
contains only the durable record ID, exact scope, revision, attempt, fence and
event kind. These fields are reconciliation data, not an authorization token.
The trusted factory chooses a registered worker and bounded job retry/schedule
options. It must not perform I/O or external effects. Storage accepts only fresh
changesets for the `builds` queue, reconstructs them from an allowlist, and checks
the inserted job again. Uniqueness/replacement, insertion callbacks, redirected
schema metadata and historical job state are rejected; they could otherwise
suppress or alter a required intent.

An exact duplicate request/event returns the latest replayed build with
`:duplicate` and a nil job, without calling the factory or incrementing revision.
The first creation/observation time remains authoritative. A conflicting duplicate
fails. New events require the current revision even though the row is locked;
the SQL update reasserts the same full scope and revision. Running cancellation
retains the active worker reference and uncertainty until definitive termination
evidence is reconciled. Insertion or subsequent transaction failure rolls back
both the journal and job.

Creation request keys are scoped to organization/project/application/platform.
This is internal deduplication, not principal-bound customer idempotency. The
future authorized command layer must resolve immutable source inputs, allocate
stable build identity, enforce policy and quota, choose trusted coordinator time,
and authorize within the same transaction. The internal Coordinator now consumes
these intents using durable admission leases. A qualified external adapter and
authenticated worker-result reconciliation remain required before public routes
are enabled. Neither Oban's job ownership nor lifecycle fencing alone satisfies
those requirements. See [the coordinator contract](hosted-build-coordinator.md).

The migration adds `mixer_builds` and its bounds/unique constraints; it changes no
existing tenant policy. Host integration uses a new disposable loopback database
and a test-only Oban consumer. The consumer proves committed intent delivery to
a synthetic probe table, never customer-code execution. The collector can include
an explicit repository-local independent `.exs` file using `--additional-test`;
it binds that file into the source receipt and creates a separate review database.
All fixture databases belong to the collector's ephemeral PostgreSQL cluster and
are removed with it. Neon, production role/RLS separation, provider isolation,
external effects, signing, billing and GA qualification remain pending.
