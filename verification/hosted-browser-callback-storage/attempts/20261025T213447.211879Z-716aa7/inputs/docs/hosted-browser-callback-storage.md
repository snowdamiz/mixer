# Typed callback storage prerequisite

This Unit A candidate adds private `CallbackDraft.Discovery`, `Claim`, `Reject`
and fixed `Store.discover_callback/1`, `claim/2`, `provider_reject/2` operations.
Producer evidence covers this storage component; independent review and root
acceptance remain pending. No callback facade, Claim owner, provider, HTTP route,
authenticated browser or readiness response is enabled.

Discovery commits an encrypted, live non-null PREAUTH pending source before any
Vault opening. It requires exact cookie/state/configuration/provider/context and
cipher agreement and exclusive browser/attempt expiry. Active browsers, absent
browsers/attempts, wrong state, expired pending and hidden durable terminal records
fail closed. Ordinary preauth load and begin replacement keep their prior scope.

Claim authenticates canonical recovered CSRF against the saved digest and opens
the exact verifier outside its mutation transaction. The trusted caller creates
independent raw32 claim randomness; Store independently computes its SHA-256 for
SQL and the full output comparison. Claim expiry is fixed at the minimum of
original lease wall entry plus 60 and the saved attempt/browser deadlines.
Rejection authenticates the session without opening the verifier. Both recheck
current function/relation catalogs on their mutation checkout and fixed-load the
whole committed source under the browser SHARE lock before unchanged SQL.
Browser audit alone increments; every other browser/session field remains
identical. The whole attempt equals its source with only the reviewed terminal
fields changed and its cipher erased. Every output field is compared before
COMMIT; claim additionally brackets SQL claimed_at and checks exact expiry.
There is no retry, exchange, resume or public claim authority.

Each new Store operation owns one synchronous closed `{:failed, lease, error}`
report to the retained RuntimeOwner as its actual original caller, within the
original deadline. This releases that exact slot on acknowledgment and clears
readiness for unknown outcomes or entered admission failures. Future Unit B must
not assume the lease survives an error or give reporting another timeout.
Foreign/altered leases cannot release another slot. No acknowledgment implies no
readiness assertion; original expiry/monitor cleanup remains the bound. Successful
discovery retains the original slot for mutation. Success returns only a private
StoredSnapshot and grants no Claim authority or automatic replay.

Caller-local wall samples are retained by exact lease across successful discovery
and mutation. Records are bounded to 32 and pruned only at their original
monotonic deadlines; a foreign/altered lease cannot change another live record.
Every callback-side wall check uses this nondecreasing record, including the
shared pending-source structural check. Terminal Store success/error removes its
exact local record and the private active-call guard is restored. A caller that
finishes discovery without a terminal Store operation leaves a bounded local
record until its original deadline or caller death. The actual RuntimeOwner
independently samples its current dependencies, exact caller/lease/generation and
wall continuity. After known COMMIT, callback source/time checks are followed by
another owner checkpoint, final retained wall/expiry checks, exact registered
owner PID and original remaining deadline. These are sampled fences; the
check-to-return/scheduling interval is not atomic delivery. Local wall custody
ends at terminal Store return. Future Unit B's separately reviewed publication
and ClaimOwner handoff must carry/fence its last sampled wall; Unit A does not
supply that end-to-end handoff or a new wall-query API. Actual OS wall-clock
rollback was not injected or changed by the producer.

Run `python3 -B verification/hosted-browser-callback-storage/run.py` for the full
selected PostgreSQL 17 producer, including both unchanged 30-method preauth and
30-method begin regression suites. `--callback-only` explicitly omits those
regressions; optional `--case text` runs exactly one matching callback method.
Diagnostic probes are recorded separately and cannot select the final handoff.
The full callback suite has 35 named compound methods, including 87 source-leaf
denials and 58 raw result-leaf corruptions for each of claim/rejection. Counts
overlap and do not complete the original 39-case A/B matrix automatically.

The controls exercise live exact success, missing/wrong/active/expired/hidden
state, every source/context/sealed field, typed shape/metadata/foreign lease,
canonical verifier authentication, session-only rejection, no Vault opening in
owned transactions, audit-only and session-cipher races, unchanged ordinary
load/begin, independent catalog drift, redaction/SQL telemetry, exclusive expiry,
original absolute deadline, deferred known rollback, unknown COMMIT loss and
known committed withholding after owner loss for discovery/claim/rejection.
The concurrency receipt proves two owned mutation checkouts held their current
source decodes (and browser SHARE locks) before upgrades; one consumes and one
rolls back without retry. The valid active fixture uses unchanged claim/activate
SQL plus synthetic authorization rows and an authenticated active Vault; it
qualifies active callback rejection, not identity verification or active login.

Synthetic operator DDL introduces per-field output corruption only after both
catalogs pass; fixed load remains unchanged until the terminal result. Such
controls test comparison/rollback, not protection from a coherent malicious
operator. Synthetic restricted roles, random loopback port, plaintext local
PostgreSQL and a manually assembled RuntimeConfig are component fixtures, not
Neon/TLS, Application startup or custody provenance qualification. The accepted
default KeyOwner starts without provider work. No product source is rewritten by
the fixture; no verifier/Repo/clock/provider is injected into the product API.

All producer failures remain archived. The initial expired-pending fixtures
first used an impossible creation ordering, then failed to reseal the verifier
under the changed expiry AAD. A deferred wait returned definite COMMIT rollback
at its original deadline, so its receipt records the actual known/unknown
outcome instead of assuming uncertainty. A real candidate defect allowed a
snapshot after a queued checkpoint reply and confirmed owner death. Its
`returned_snapshot:true` receipt is preserved; the corrected common callback
fence resamples the owner after local checks and verifies its retained registered
PID before return. A formatter first-pass failure and diagnostic probes remain
separate evidence. No skipped or failed probe is reported as a pass.

The producer archives exact selected source, migrations, dependency source and
BEAM files; before/after hashes, source revision/tree, commands, tool versions,
stdout/stderr, failed attempts and exact owned resource cleanup are retained.
Helper failures retain only closed assertion/exception classes; no raw query,
private value or PostgreSQL error metadata is printed. PostgreSQL logs suppress
error statements/parameters. `seal.py` selects only a full unchanged-source run
with successful cleanup and both prerequisite regressions. No broad hosted
harness, frozen catalog-inspector/authority-driver/rejected Worker V2, native
runtime, UI, capture or unrelated process discovery is used.

Unit B manual supervision/claim custody, provider/OIDC/current-verifier/HTTP and
Application joins, full owner/lifecycle/relation matrices, Neon/TLS/operational
custody, immutable external FieldLog/customer evidence and accountable GA
acceptance remain pending. Phones remain disconnected and native/UI/capture
execution remains paused. This component promotes no GA gate.
