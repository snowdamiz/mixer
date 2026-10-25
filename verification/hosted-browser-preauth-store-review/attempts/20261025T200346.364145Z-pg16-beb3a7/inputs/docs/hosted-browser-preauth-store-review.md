# Browser preauthentication Store independent review

Prepared on 2026-10-25; runtime review remains incomplete. The original frozen
candidate was compiled and exercised on an owned PostgreSQL 16 fixture. Three
caller-ownership controls failed: rejected finish, failed and legacy release-cast
messages could remove another caller's operation slot. The exact source, results
and successful resource cleanup are retained in
[the initial attempt](../verification/hosted-browser-preauth-store-review/attempts/20261025T195345.779043Z-pg16-1263b6/receipt.json).
An automated cybersecurity check then stopped the review agent. Root verified
the recorded failure and cleanup and is continuing local component review while
the producer corrects ownership and closes the allowed attempt policy. No
component acceptance is claimed. The preparation below describes planned
controls; unexecuted controls remain pending.

The selected fixed API has no intrinsic design blocker. Acceptance requires the
authority, timing and publication checks below; their presence in the selected
contract does not prove that the implementation performs them. Existing accepted
components were read only to define independent controls. The current repository
HEAD and hashes in the preparation receipt are context, not a candidate seal.

The binding product plan remains broader than this slice. AGENTS and PLAN keep
computer use, capture, native simulator/emulator tests and physical phones paused.
No route, provider, Application child, production credential, customer message,
publication, FieldLog or GA acceptance is part of this review.

## Exact selected scope

The candidate consists of new `LifecycleRepo`, `RuntimeOwner`, `PreauthDraft` and
`Store` modules plus the producer's preauth composition document. Existing
custody, configuration, Vault, decoder, SQL and catalog prerequisites stay fixed.
The public component API is manually started registered
`RuntimeOwner.start_link(runtime_config)`, `status/0`,
`bootstrap(%{request_id: hex32})` and `load(raw_cookie)`. Bootstrap/load orchestration
runs in the original calling process. Successful private preauth output contains
only the selected raw cookie, canonical CSRF, expiry and typed StoredSnapshot;
it grants no authenticated or workspace capability.

`Store.bootstrap(typed_draft, metadata)` and `Store.load(typed_input)` are fixed
operations. Store startup admission is callable only from the actual registered
owner. It must verify retained owner state and the actual original caller. A
struct, supplied PID, process dictionary marker, cached catalog result or direct
Store invocation cannot grant authority. Process dictionary checks may deny an
existing ordinary authorization context; they cannot authorize lifecycle work.
There is no caller-selected Repo, query/executor, provider, clock or callback.

Startup is a manually composed component fixture. It must bind the actual fixed
LifecycleRepo, ordinary Repo and default KeyOwner PIDs. The selected LifecycleRepo
binding uses a protected ETS table created in its actual Ecto supervisor's
`init(:supervisor, config)`, with an exact accepted-start-options fingerprint and
the table owner equal to the currently registered fixed Repo PID. Missing, stale
or foreign-owned tables deny. Include all accepted credentials and connection,
pool, timeout and TLS policy in that fingerprint without exposing material.
Disallow URL, hooks, pool overrides and alternative registration. Ecto 3.14.2's
supervisor source places that init callback in the actual Repo supervisor, so
the proposed table lifetime is suitable in principle; runtime proof is pending.
Ordinary Repo `config/0` is configuration observation, not attestation of its
running start options. This does not prove production Application startup provenance,
that the KeyOwner contains the supplied identity-startup manifest, or same-PID
trust generation continuity. No active authentication is attempted in this slice.

The initial five-second monotonic deadline begins before lease, draft and Vault
work. The same absolute `DBConnection` deadline must cover checkout, BEGIN, both
catalog checks, effect, decode, COMMIT and returned-result processing. Remaining
positive timeout values cannot extend that deadline. The fixed separate pool has
two connections, one pool and no queue; the owner independently admits at most
32 operations, including draft/Vault work outside SQL. Every transaction rejects
an existing lifecycle/ordinary transaction or authorization context, uses READ
COMMITTED and exact Catalog-admitted LOCAL settings, and requires both V2
`:function_surface_verified` and `:relation_surface_verified` on its own fixed
connection. The local installed DBConnection 2.10.2 source confirms that the
transaction options, including absolute `:deadline`, reach commit and rollback.
This is dependency-source evidence only; runtime enforcement remains pending.

One concrete redaction prerequisite was found before candidate review. In local
Ecto SQL 3.14.0, the query callback emits telemetry metadata with query parameters
and result before evaluating `log: false`; that option alone cannot redact
sealed-envelope query parameters from telemetry. Sensitive fixed Store queries
need an explicit selected control such as `telemetry_event: nil`. Ecto's Repo
supervisor also emits full startup options, including a database password, to
its `[:ecto, :repo, :init]` telemetry event. That trusted in-process event is not
a log or receipt by itself, but the slice cannot claim that every internal
telemetry metadata value is credential-free. Tests and evidence capture must
never persist it unredacted. Root and producer were notified before freeze.

Seal runs before bootstrap's transaction; open runs after load's transaction.
Before release, compare complete retained source/cipher/AAD/config/cookie/CSRF
and snapshot bindings, and recheck caller, owner generation, registered owners,
configuration, wall time, durable expiry and monotonic deadline. Only the fixed
admitted load helper's SQL NULL may yield `{:ok, nil}`. A non-NULL active,
malformed, expired or conflicting-attempt snapshot returns a redacted error,
never absence. The producer document must state its exact preauth attempt policy;
the review will not invent pending/claimed-attempt resumption.

## Independent fixture and pressure controls

The prepared [fixture builder](../verification/hosted-browser-preauth-store-review/synthetic_runtime_fixture.exs)
creates only synthetic in-memory component settings. Its loopback host,
randomly assigned non-5432 port and plaintext local PostgreSQL connection are an
explicit exception to the production constructor's verified TLS/direct-host/5432
requirements. It deliberately does not call `RuntimeConfig.new/4`, and cannot
qualify that constructor, Neon, TLS or external custody. It creates no process,
database, network request or credential outside the disposable fixture. It uses
the actual existing default KeyOwner implementation with a synthetic valid
manifest; no fake verifier or identity result is supplied.

After root announces a freeze, the independent fixture will use exactly one
owned disposable PostgreSQL 16 instance, distinct restricted ordinary/lifecycle
LOGIN roles and non-LOGIN writer/relation-owner roles, plus the reviewed original
SQL and additive V2 preparation surface. Native macOS tools found during
preparation are PostgreSQL 17.11, so they cannot be mislabeled PG16. The PG16
container image identity, server version/locale, configuration and cleanup must
be recorded before any result is accepted. No broad hosted harness or frozen
catalog-inspector, authority-driver or rejected Worker V2 source is used.

End-to-end pressure uses the actual RuntimeOwner API and fixed two-connection
Repo. An operator connection holds both lifecycle connections in real bounded
transactions; a third request must fail without waiting, and an independent
ordinary Repo query must remain usable. This is distinct from the 32-slot test.

Owner-only tests may use the fixed trusted internal message
`{:reserve, original_monotonic_deadline_ms, original_wall_seconds}` from 32 real
caller processes, then hold those callers before SQL. The returned typed Lease
has exactly `owner`, `reference`, `caller`, `generation`, `deadline`, `started_at`
and `runtime`; the owner retains complete equality. The 33rd reservation denies,
caller death releases a slot, and copied/foreign/stale references deny. The fixed
checkpoint/finish/failed messages and release cast are tested as owner-component
controls, never counted as public end-to-end or 32-concurrent-SQL evidence.
Test-only `:sys.get_state` may observe slot cleanup; product code cannot use
introspection as KeyOwner authority.

Commit/error adversity must preserve the candidate source. A high-priority trace
of the actual relation-admission return, followed by the owner's real checkpoint
yield, may suspend an observed caller before effect. The test must first confirm
that no browser write occurred, then install a disposable operator-owned deferred
constraint trigger and resume. This operator DDL is outside the admitted-schema
threat boundary and tests rollback/error handling only. Real backend termination
or a bounded local transport proxy may test response loss and unknown outcome.
A source-rewritten Store, changed SQL helper, or injected result is separately
labeled mutant/instrumentation evidence and cannot satisfy unchanged-candidate
runtime controls. If exact COMMIT timing cannot be established, that control
stays pending; no pre-COMMIT failure is renamed a commit failure.

## Frozen review and receipts

The machine-readable [pending matrix](../verification/hosted-browser-preauth-store-review/adversity-plan.json)
defines 44 bounded controls. Initial O03 ownership observations failed as recorded
above; the remaining preparation controls have not been accepted. On each freeze, take a new allowlisted
source/dependency snapshot and verify its seal before compilation, before and
after each runtime partition, and after cleanup. Use a fresh VM and explicitly
selected modules/dependency BEAMs. Root-owned revision/metadata changes during
the run are context; selected source changes invalidate the affected partition.

Each attempt records exact command, tool/server versions, root revision, source
tree hashes, output, method IDs/counts and evidence scope. PostgreSQL rows/audits
are inspected only through the independent operator fixture for assertions; the
production lifecycle login retains no direct table capability. Successful
publication needs confirmed COMMIT and final continuity; timeout, uncertain
commit, caller/owner loss and result loss never retry or recover a cookie.
Error/result/log/telemetry receipts must contain no synthetic raw cookie, CSRF,
key bytes, credential, ciphertext, SQL exception details or private identity.
Actual `:sys.get_status` and abnormal GenServer termination diagnostics must
exercise redaction of state, pending message, reason and debug log; a direct
call to `format_status` alone is insufficient. Telemetry tests distinguish the
standard trusted Repo-init event from sensitive Store query-event suppression.

Every successful or failed attempt terminates only its owned BEAM processes,
tracers, proxy, connections and PG instance, with bounded process/port cleanup
verification. Other projects' active processes and data are preserved. Current
preparation started none of those resources. Production startup, provider/OIDC,
current verifier joins, browser HTTP/console, operational custody/Neon,
customer/FieldLog, native/device and GA evidence remain pending.
