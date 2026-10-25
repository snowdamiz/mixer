# Internal worker controller selection, version 1

Status: contract selected by root on October 24, 2026; implementation and every
provider enablement gate remain pending. Root approved this contract-only lane
before these files were written. This document implements no controller and
changes no hosted route, dispatch installation, provider account, or credential.
The binding requirements are product-plan sections 13 and 14 and the existing
[coordinator](hosted-build-coordinator.md), [transport](hosted-worker-transport-contract.md)
and [request-header amendment](hosted-worker-transport-amendment-v2.md) contracts.
The client candidate is independently reviewed; selecting a compatible controller
does not accept that candidate or erase its original failed header requirement.

## Authority, placement and first implementation ownership

Phoenix authenticates people and organizations, enforces tenant/project policy,
authorizes immutable source and build inputs, admits capacity and owns business
state. The controller accepts only authenticated, already-authorized internal
`query`, `ensure_started` and `stop` assignments. Identifiers, hashes, fences,
nonces and possession of an app ID confer no tenant authority. The controller
cannot create a build, authorize a source fetch, release capacity in Neon,
publish an OTA update, sign an artifact, submit a store binary or charge a tenant.

Select a separate future `hosted-worker-controller/` directory. None of these
future files exists as a result of this packet:

| Selected file | Interface and ownership |
| --- | --- |
| `src/index.ts` | Internal fixed-route Worker; authenticate, bound body, decode, route one operation to one DO, emit a bounded response. No public tenant API. |
| `src/wire.ts` | Exact wire-v1 decoder/encoder, duplicate-aware JSON parser, canonical decimal and old/new hash bytes. |
| `src/principal.ts` | Closed environment/controller/pool/platform machine principal; constant-time fixed-length token-digest comparison using standard Web Crypto. |
| `src/operation.ts` | `MixerWorkerOperation extends DurableObject`; storage transaction entry points, authenticated runner claims/results and alarm reconciliation. |
| `src/ledger.ts`, `src/schema.sql` | Synchronous SQLite transitions and versioned non-destructive schema. All authoritative effects originate in this ledger. |
| `src/provider.ts` | Finite trusted provider interface described below; no arbitrary URL, module, shell or customer-selected adapter. |
| `src/cloudflare-container.ts` | Later direct `ctx.container` inert-supervisor adapter; initially unavailable. |
| `src/macos-supervisor.ts` | Later explicitly external Apple-host supervisor adapter; initially unavailable. |
| `src/clock.ts` | Qualified-clock interface; default unavailable, finite synthetic clock only in tests. |
| `test/acceptance-driver.ts`, `test/*.test.ts` | Test-only actual runtime/storage adapter for the acceptance runner; no test override exported in the deployment entry point. |
| `package.json`, lockfile, `tsconfig.json`, `wrangler.jsonc` | Root-selected pinned development dependencies, compatibility date, SQLite DO export/migration, explicit GA `default` scheduling and bounded instance count; no deployment in the first slice. |

No production configuration defaults to an enabled provider. The first source
slice implements the codec, principal, transactional ledger, recovery/alarm logic
and a verification-only fake provider. Its executable local DO/SQLite tests can
accept development progress while real providers remain disabled. Root assigns
future source ownership only after this public contract is frozen. Root also
owns dependency selection/inventory and runtime integration. No dependency was
installed or probed by this contract packet. Proposed later tooling is pinned
TypeScript plus Wrangler/workerd test tooling; the direct API requires no
`@cloudflare/containers` wrapper. Exact versions and licenses must be selected,
locked and entered in `THIRD_PARTY.yml` before those tools are installed.

## Documented platform capabilities and the limits of those facts

The following are official Cloudflare documentation observations retrieved on
October 24. The linked pages, retrieval hashes and page update dates are sealed
in this packet's source manifest. The design that follows is Mixer engineering
selection, rather than a Cloudflare guarantee of application safety.

* The [direct Container API](https://developers.cloudflare.com/containers/api/durable-object-container/)
  exposes `ctx.container.start()`, `running`, `getTcpPort()`, `destroy()` and
  `monitor()`. Starting validates options before readiness; `running` is not
  readiness. Monitoring must be reattached after DO restart and prevents eviction
  for at most 15 minutes. These APIs do not implement Mixer's job claim or fence.
* [Scheduling policies](https://developers.cloudflare.com/containers/configuration/scheduling-policy/)
  distinguish GA `default` service scheduling from public-beta `durable_object`.
  Select explicit `default`: image, size and `max_instances` are application
  configuration. Policy is immutable. No beta snapshots, dynamic image choice or
  beta scheduling is required. The [GA announcement](https://developers.cloudflare.com/changelog/post/2026-04-13-containers-sandbox-ga/)
  establishes service availability, not Mixer qualification.
* [SQLite DO storage](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/)
  is transactional and strongly consistent per DO. `transactionSync` is
  synchronous and rolls back on throw; `sync()` waits for pending writes. SQL
  numeric values cross a JavaScript precision boundary, so persist all protocol
  int64 values as canonical decimal TEXT and compare with `BigInt`. Do not
  round-trip an epoch, revision, time, size or fence through SQL INTEGER results.
* [Alarms](https://developers.cloudflare.com/durable-objects/api/alarms/)
  provide one scheduled alarm per DO and at-least-once delivery. Failure retries
  start at two seconds and are limited to six. Cancellation is best effort for
  retries, and constructors can disturb an already scheduled alarm. These facts
  do not guarantee a queue latency bound or unlimited retry liveness.
* [Container lifecycle](https://developers.cloudflare.com/containers/concepts/architecture/)
  distinguishes startup, readiness and shutdown. Platform shutdown can allow up
  to 15 minutes after SIGTERM before SIGKILL; disk is ephemeral. A stopped
  process can subsequently be restarted through the same DO. Neither stable DO
  identity, SIGTERM nor disposable disk proves one job execution.
* [Instance limits](https://developers.cloudflare.com/containers/platform/limits/)
  currently describe `standard-1` as 0.5 vCPU/4 GiB/8 GB and `standard-4` as
  4 vCPU/12 GiB/20 GB. These are bounds to qualify against an actual image and
  workload, not evidence that Android toolchains fit or hostile code is isolated.

One DO is addressed by a stable hash of the versioned fixed-order JSON tuple
`[environment_id,pool_id,controller_id,operation_id]`. The namespace identity is
durable deployment configuration; no restore/deploy may silently replace it.
One Android operation DO may own its own direct container binding. An iOS
operation uses the same ledger and an external macOS provider identity; Linux
compute never satisfies the Apple-host requirement. Distinct image/role identities
keep Phoenix processors, trusted supervisors and customer sandboxes separate.

## Frozen application wire and managed-ingress boundary

Keep endpoint `/internal/mixer-build-worker/v1`, version 1 JSON, fresh lower-case
hex128 request nonce, exact complete echo and both existing SHA-256 algorithms.
The amendment selects **eight client-originated headers**, including explicit
`User-Agent: mixer-worker/1`. That inventory is measured at the TLS peer in the
client fixture. A Cloudflare Worker receives managed ingress metadata; its
normalized `Headers` representation cannot prove the client's raw duplicate
absence or reconstruct original field bytes. Do not reject an otherwise valid
request merely because Cloudflare added `CF-*`/forwarding metadata. Do not accept
ambiguous, comma-joined, transformed or repeated application authentication.
Actual ingress duplicate handling and required provider transformations remain
an enablement gate. Never authorize a principal using forwarded headers.

Authenticate before body parsing/routing or DO creation. Match the fixed
method/path and configured environment/controller/pool/platform principal. Read
a stream with a 16,384-byte body cap before assembling/decoding it; constrain
controller-owned requests/subrequests, rather than claiming to limit allocations
already performed by Cloudflare ingress. Reject unexpected content encoding,
media type, missing/ambiguous authorization and malformed fields. A bad machine
credential returns a fixed non-200 error with no binding echo or ledger mutation.
Authenticated but invalid wire returns a fixed non-200 error. For a valid
authenticated request, return only a closed wire-v1 200 response, including
closed `stale`, `unavailable` or `uncertain` observations. No raw error detail,
request/token, source reference or provider exception enters a sink.

The decoder rejects duplicate or escaped-equivalent member names at every depth,
invalid UTF-8, unknown/missing keys, JSON floats/exponents, excessive depth/tokens/
string-token size, and every noncanonical decimal. Version and attempt are the
only numeric JSON fields. Protocol int64 fields stay decimal strings on wire and
in storage; calculations use BigInt, max `9223372036854775807`. Revision is 0–32;
attempt is 1–5; positive fields cannot be zero. Preserve expiry microseconds.
Scope, source kind, artifact kinds and failure class/code pairs retain the
existing finite Lifecycle contract. Never normalize Unicode strings, IDs or
opaque `source.reference` before hashing or authorization.

Recompute `operation_id` using the original Dispatch array, including **an exact
integer JSON token for fence**. Recompute `immutable_sha256` using the transport's
fixed-order binding array, with fence and deadline **strings**. A TypeScript
serializer must emit old fence digits without calling Number. Equal digests do
not replace exact ref/spec/deadline equality on an existing ledger row. The
fixture packet contains exact UTF-8 bytes and hashes for ASCII, Unicode, quoting,
backslash, tab/newline escape, `9007199254740993` and maximum int64 boundaries.
They are independently computed expectations; Jason interoperability remains an
explicit future acceptance step rather than a claimed pass here.

Echo exactly this request's version, three machine IDs, nonce, command, operation
ID, immutable hash, ref and entire guard, including the original expiry spelling.
Never echo a persisted previous nonce/guard as an idempotency shortcut. Nonce is
response binding, not operation identity or authorization; repeated nonces do
not bypass any check and do not create additional work. Replies never include
`spec` or `deadline_ms`. Return bounded terminal results only after complete
runner/object/provenance validation. Absence/running/uncertainty never releases
admission capacity; Phoenix remains responsible for its own terminal transition.

**HTTP compatibility remains unverified.** The frozen client requires an actual
HTTP/1.1 200, canonical Content-Length, at most 32,768 body bytes, bounded headers,
no transfer encoding/compression/trailer/extra response and clean peer EOF inside
its original 5,000 ms total deadline. [Workers Response](https://developers.cloudflare.com/workers/runtime-apis/response/)
documents fixed-length bytes/string/FixedLengthStream bodies for Content-Length;
manual length is ignored and other streams use chunking. Select a bounded UTF-8
byte body. [Workers Node HTTP](https://developers.cloudflare.com/workers/runtime-apis/nodejs/http/)
states that connection management belongs to the platform and Connection headers
are unused; switching to that wrapper does not supply an EOF guarantee. We infer
that a fixed response body alone cannot establish clean closure. No deployed
Cloudflare ingress has been tested here. Keep real enablement closed until the
unmodified client passes the complete actual edge header/framing/EOF fixture.
Failure requires root to select a qualified ingress or explicitly amend and
independently re-review the client contract; it must not silently weaken EOF.

## Ledger, serialization and clock contract

There is one immutable `operation` row and bounded current `effect`/`claim` rows
per DO. Store closed enums with CHECK constraints; SQL is static parameterized
text, never interpolated customer data. Keep compact terminal identity forever.
No TTL, `deleteAll`, namespace reset, counter wraparound, tombstone recycling or
restore to an earlier watermark is allowed. Archived detail may move to private
immutable storage only after its digest/reference and permanent local identity
remain sufficient for every replay decision.

| Persisted group | Required fields |
| --- | --- |
| Immutable identity | Schema version; environment/controller/pool; operation ID; record UUID; exact original ref/spec/deadline; binding bytes/hash; source/toolchain/definition hashes. |
| Authority watermark | Epoch/revision decimal TEXT; owner ID; maximum accepted expiry TEXT; clock qualification ID and last accepted clock interval. |
| Desired and observed | `none/run/stop`; `unlaunched/launch_pending/inert/claim_consumed/running/stop_pending/completed/stopped/uncertain`; monotonic state version; exact terminal result/evidence hash. |
| Provider | Provider kind; immutable resource identity; expected pinned image/toolchain/definition; observed instance/boot IDs; no replacement identity after ambiguity. |
| Effect | Unique bounded effect ID; kind; state version; issued pair/owner/expiry; intent `prepared/dispatched/uncertain/settled`; timing/deadline; response evidence hash. |
| Claim | Stable operation claim ID; provider instance/boot; immutable job hash; `unissued/consumed/revoked`; consumed time; result acceptance state. Never reset consumed to unissued. |
| Reconciliation | Next due time; failure counter capped to a finite value; retry class; bounded diagnostic hash. No raw logs in ledger. |

Acquire the per-operation transaction before sampling time. Every request uses
an injected *qualified* time interval `[lower_us, upper_us]` with an externally
measured finite maximum error and freshness limit. Cloudflare wall time alone is
not documented here as a bounded-error clock. Production default is unqualified,
which fails closed with unavailable and performs no new authorized effect. A
deployment receipt must select the actual trusted clock source, error budget,
refresh mechanism, rollback detection and outage behavior before enabling work.

In tests choose an explicit interval; do not present it as deployed clock proof.
At request acceptance and immediately before granting any new launch/claim,
require `upper_us < expires_at_us` and `upper_us < deadline_ms * 1000`. Equality
is expired. For definite deadline cleanup use `lower_us >= deadline_us`; during
clock ambiguity do no new launch/claim, retain occupancy and reconcile owned
resources. A committed explicit stop remains valid forever and may be enforced
without renewing the original lease, even if a later request is stale or clocks
are unavailable. That enforcement derives from the persisted stop, never from
new authority in an expired request. Resume cannot reopen a stopped identity.

Detect excessive backward time movement against the persisted last interval;
quarantine new effects until a new qualified-clock receipt resolves it. Do not
clamp a wall clock to a stale timestamp and call that safe. Post-lock clock sample,
final authority recheck and result acceptance check must all be executable tests.

For a previously bound operation compare `(epoch, revision)` lexicographically
with BigInt, never concatenated text/SQL lexicographic ordering. Smaller pairs
return stale with no ledger write, provider query, claim or effect. Within one
epoch, a different owner is stale even if revision increases. Equal pairs for the
same owner may move expiry forward only. They may not shrink expiry, mutate
binding or clear desired stop; query itself does not authorize a launch. A larger
epoch can select a new owner and a lower revision. An older command's later
callback must not overwrite newer desired state, grant a claim or erase evidence.

Transactions contain no provider, DNS, network, R2, Web Crypto await or customer
code. Compute validated digest material before entering; inside the synchronous
transaction compare the complete immutable data, sample clock, decide and write
intent. Use `storage.sync()` after that transaction before any external side
effect. Reacquire and recheck current intent/pair/owner/expiry before effect
dispatch; mark dispatch before the call. A crash after dispatch marking is
ambiguous, never permission to issue launch again. Storage locking alone does
not lock an external provider across awaits; claim/tombstone checks close the
late-launch path. A single finite in-memory effect task per DO avoids accidental
parallel calls, while durable state handles process death and reentrancy.

## Required transition table

All rows assume a valid principal, exact immutable binding, qualified fresh clock
and nonstale live guard unless they explicitly describe recovery or rejection.
The table is a selected application state machine, not platform behavior.

| Current state / input | Atomic commit before external work | External work and response |
| --- | --- | --- |
| Missing + query | Bind full identity and watermark; desired none; no launch intent. | Return absent. Persisted absence never proves no delayed older launch exists. |
| Missing + stop | Bind identity/watermark, desired stop, permanent tombstone, revoked claim, stop intent for stable provider identity. | Reconcile identity and all launch tickets; return uncertain until definitive stopped evidence. |
| Missing/known unlaunched + ensure | Bind/validate, advance watermark, desired run; choose stable provider resource ID once; persist launch intent and next due work. | Start inert supervisor once. Startup return is not readiness, running or build success. |
| Any nonterminal + older pair/wrong owner/expired guard | No change. | Return stale; zero provider calls. |
| Any + conflicting immutable fields/hash | No change. | Reject request; zero provider calls. |
| Launch pending + duplicate ensure/query | At most same-owner forward expiry renewal; retain original identity and uncertain intent. | Inspect/reconcile original identity; never create replacement or resend a possible launch. |
| Inert supervisor + valid one-shot claim | Recheck desired run, live guard/deadline, exact resource/instance/boot and binding; consume claim durably before grant. | Grant once outside customer scripts. A lost grant may lose work; it never permits a second grant. |
| Consumed/running + duplicate claim/restart | Retain consumed claim, binding and resource identity. | No new script grant. Reconcile original work or stop/fail conservatively. |
| Any active + newer stop | Desired stop/tombstone, revoke every unissued claim, persist stop intent and current watermark. | Stop original identity; late start/claim cannot run scripts. Reply uncertain while any accepted launch/effect/descendant is unresolved. |
| Committed stop + delayed launch completion | Keep stop, claim revoked and launch evidence; add/reconcile stop work. | Destroy matching original resource; no launch/claim retry. |
| Any active + definitely elapsed immutable deadline | Persist desired stop and stop intent; keep original attempt/identity. | Enforce stop and reconcile; no capacity release by age. |
| Running + authenticated valid terminal report | Verify all immutable objects/results first; persist exact terminal evidence, revoke future claim and begin teardown. | Return completed only after definitive owned-work termination and no unresolved delayed launch. Until then uncertain. |
| Stop pending + definitive provider drain proof | Persist stopped with diagnostic/evidence hash; retain identity, binding, claim and maximum watermark forever. | Return stopped. Stop API acknowledgement, absent inspection or SIGTERM alone is insufficient. |
| Completed/stopped + valid later request | Optional valid forward watermark/expiry change; terminal identity/result and desired stop cannot change. | Echo current request and return retained terminal observation. Ensure never restarts it. |
| Crash/storage failure/provider timeout | Preserve committed intent or roll back entire transaction. | Uncertain; no inferred terminal state or blind replacement. |

Stop wins over a completion that was not durably accepted before the stop
transaction. A completion accepted first remains immutable; a later stop may
enforce teardown but cannot replace its result. Reports may be retained as
bounded evidence after ownership transfer, but do not become accepted results
until current authorization, immutable binding and owned-work termination are
validated. Terminal identity never expires, even if every coordinator lease does.

## Provider and trusted runner boundary

The selected internal interface is deliberately finite:

```typescript
interface Provider {
  inspect(identity: ResourceIdentity): Promise<ProviderObservation>;
  launchInert(intent: PersistedLaunchIntent): Promise<ProviderObservation>;
  stop(intent: PersistedStopIntent): Promise<ProviderObservation>;
}
```

`ResourceIdentity` contains provider kind, environment/controller/pool/operation,
stable resource key and pinned trusted-supervisor image identity. Every effect
includes ledger effect ID and immutable hash. Observations contain exact resource
and instance/boot identity, finite state, bounded diagnostic/evidence hash and
explicit whether delayed launches and all descendants are eliminated. The
adapter cannot declare definitive stop solely because an API says absent. The
ledger verifies observations against persisted identity and current desired
state. Provider interfaces do not accept source URLs, raw shell, arbitrary
environment variables, cloud account tokens or signing keys from request bodies.

Cloudflare direct `start()` can restart a container after exit. Consequently,
the stable DO identity is only addressing: durable claim consumption outside the
untrusted process enforces the no-second-script-grant invariant. A restarted
image boots inert, authenticates as the expected supervisor, presents a fresh
instance/boot ID and cannot recover permission from container disk. Never call
`exec()` with customer code from the controller. The trusted supervisor launches
the separately qualified job sandbox only after its one-shot grant, and consumes
that grant in a trusted durable execution domain before spawning scripts.
Supervisor crash recovery must never replay spawn from an acknowledged intent;
an uncertain spawn forces reconciliation/termination. Exactly-once successful
execution is not claimed; avoiding duplicate execution may sacrifice liveness.

The separate runner channel authenticates an operation-scoped supervisor identity
and supports only `claim` and terminal report. It is not a fourth client command.
Grant binds immutable operation/ref/attempt/fence/spec/deadline, claim ID, exact
provider identity, instance/boot and grant expiry. A grant issued before a later
stop cannot be recalled by a database write alone: terminal stop additionally
requires confirmed sandbox/descendant disposal and no outstanding launch/spawn
ticket. Result retries return a retained acknowledgement for the identical
report digest; different reports conflict. Lost acknowledgements do not rerun
scripts. Unauthenticated, wrong-instance, wrong-attempt or object-mismatched
reports cannot create terminal evidence.

The pool token stays in Workers secret injection; store only bounded token
digests for principal matching. No pool/cloud/account credential enters the
container or customer environment. Provider provisioning authority stays in a
trusted adapter. Supervisors receive operation-scoped short-lived source and
private-object grants resolved by Phoenix, never public arbitrary fetch URLs;
customer scripts cannot access the supervisor/result credential. An authenticated
hash declaration does not prove an immutable R2 object's existence, size,
provenance, successful build, app identity, signing or OTA eligibility. Validate
all seven artifact kinds, hashes/sizes and immutable-object existence plus the
appropriate producer attestation before accepting success. OTA signing keys are
absent from this controller, client and every untrusted build environment.

## Resource, expiry, alarms and recovery selection

Choose a finite development profile: 16 KiB request/32 KiB response, one operation
row, one current launch/stop intent, one claim, one terminal evidence object,
at most 32 bounded audit summaries and one provider call in flight per DO. Archive
old audit detail by immutable digest; never discard safety state. Exceeding any
limit fails closed with uncertainty and retained occupancy. A deploy must cap
the total active operations/DO allocation and private logs separately; a per-DO
cap is not a fleet memory/FD/storage limit. Keep permanent tombstone storage in
capacity/billing accounting; exhaustion cannot justify erasure.

Request work must fit the client's total 5-second lifetime: select at most 2-second
provider calls, a 4-second controller handler budget and no inline readiness wait.
On timeout persist ambiguity and schedule reconciliation; return uncertainty if
there is still time, otherwise let the client's unchanged deadline reject it.
This selects bounds, not measured latency. A timeout cannot prove a remote
operation was cancelled. Background reconciliation has finite call counts,
bounded exponential delay capped at 60 seconds and persistent retry state; it
does not renew a coordinator lease or grant a claim on its own.

Persist `next_due_us` in the same state transition as intent; arm the one DO alarm
and await durable writes before an effect. Alarm delivery replays the ledger,
processes at most one provider action, rechecks clock/desired state and rearms
the earliest pending task/deadline before return. Repeated delivery is harmless.
Constructor initialization cannot overwrite an earlier alarm. Reattach monitor
after each restart when a container is running; monitor is a hint, while ledger
and provider inspection remain authoritative. No long-lived monitoring promise
or `waitUntil` is the only wake mechanism.

After a crash between intent and alarm/effect, request/recovery replay uses that
same intent and identity. After launch dispatch but before acknowledgement it
inspects the same identity; absence does not authorize a replacement or a second
launch. Missing provider proof may retain uncertainty indefinitely. Alarm retry
exhaustion, failed rearm and namespace-unavailable cases require a separately
qualified independent scheduled audit with a durable registry of pending
operations. That audit may wake/reconcile known identities, never authorize new
builds. First implementation tests the registry interface and fault behavior;
zero-customer-traffic wake latency and actual scheduled audit are still deployed
qualification gates. This operation controller does not by itself solve waking
the separate Phoenix/Oban processor roles.

DO point-in-time restore, deployment rollback, namespace recreation and provider
recreation can erase a fence or consumed claim. The selected first slice has no
automatic restore/replacement. Quarantine affected identities; root must prove
an independently retained nonrollbackable watermark/tombstone/claim record and
reconcile external effects before re-enabling. A Neon restore cannot restore DO
authority backwards, and a DO restore cannot make Neon capacity safe to release.
No backup/PITR feature is accepted as safe application recovery without this
cross-system receipt. Never run two authoritative dispatcher namespaces.

## Executable acceptance and truthful completion boundary

`verification/hosted-worker-controller-contract/acceptance.mjs` is a dependency-free
future-candidate acceptance runner, with explicit test-driver interface in its
header. It contains no controller implementation. With no candidate it exits 77
and records a pending result. Its candidate mode must exercise actual candidate
codec/ledger code using SQLite-backed DO runtime storage, fresh durable state per
case, fault injection, independently observable provider call history and runtime
restart. A claimed metadata field is not platform evidence; root verifies the
source/runtime/commands in the candidate receipt. An in-memory model cannot pass
the actual DO/storage gate. Test APIs and synthetic clock/provider/credential
configuration are verification-only and absent from the deployment bundle.

The first implementation must pass all of these source-bound tests:

| Group | Executable evidence required |
| --- | --- |
| Exact codec | Shared fixed bytes/hashes and int64 precision; reject malformed/duplicate/escaped-equivalent keys, type/enum/range/shape errors; exact response nonce/echo for every command. Replay against the separately accepted Elixir client. |
| Authentication | No ledger allocation/mutation/provider call for wrong/missing/ambiguous token, wrong environment/controller/pool/platform, source/ref scope mismatch or immutable conflict. Distinct synthetic credentials and secret-sink scans. |
| Ordering and time | Post-lock sample; every smaller lexicographic pair rejected before provider query; same-epoch owner conflict; exact equal-pair renewal; higher epoch/lower revision; boundary expiry and microseconds; unqualified/stale/backward clock; final claim/effect recheck. |
| Effects and stop | Concurrent duplicate ensure; query-absent binding; stop before ensure; crash before/after durable intent, dispatch, provider effect, claim, result and response; launch timeout/absent never relaunch; delayed start after newer stop; one-shot grant lost/retry/restart; definitive stop requires descendants and no launch ticket. |
| Durable lifecycle | Actual SQLite rollback/durable restart, terminal permanence after lease/deadline, bound identity on all callbacks, stale result cannot rewrite stop, immutable result retry conflict, malformed/unknown provider evidence retains uncertainty. |
| Wake/resources | Duplicate alarms; no incoming HTTP; rearm failure, constructor wake, retry exhaustion/audit recovery; bounded calls/bytes/rows/audit/logs; cleanup all owned tasks/timers/sockets/test DO state without other project processes. |

The packet's separate `verify_packet.py` validates its independently computed
fixture bytes/hashes, source manifests and required acceptance scenario inventory.
Passing that check proves packet consistency only. It is neither a controller
test nor a Cloudflare runtime/provider receipt. Exact commands, Python/Node
versions, scoped source-tree digest, retrieval hashes and outcomes are recorded
in `receipt.json`; no Git, package install, DB, hosted application, provider API,
native runtime, customer source or signing credential is accessed by this lane.

After source acceptance, keep these independent gates pending: actual Cloudflare
ingress header/framing/EOF and deployed TLS; measured bounded clock; default-policy
image/size/egress/isolation and toolchain fit; stable launch/stop/descendant proof;
Apple-host supervisor; source/private-R2 grants and runner attestation; whole-domain
memory/CPU/task/FD/log ceilings; zero-traffic Oban wake; Neon/R2/DO restore and
namespace permanence; credentials/key custody; operational audit/latency/SLOs;
public authorization, signing, store and customer qualification. This contract
closes no GA gate and provides no deployment authorization.
