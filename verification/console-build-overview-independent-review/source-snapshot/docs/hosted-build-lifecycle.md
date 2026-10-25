# Hosted build lifecycle

Status: root-coordinated internal contract implemented; independent/root review pending.

This slice implements deterministic per-platform build-attempt decisions required
by product-plan sections 13.2, 14, and 17. It does not dispatch work, authenticate
worker observations, persist state, grant tenant permission, publish artifacts,
sign releases, submit to stores, or incur/reconcile a charge. Existing identity
code remains authoritative for identity verification; this module accepts no
credential and creates no replacement identity model.

## Internal API and values

One independently authored module, `MixerHosted.Builds.Lifecycle`, under
`hosted/lib/mixer_hosted/builds/lifecycle.ex`, with nested data structs:

- `Spec`: exact tenant/build scope (`organization_id`, `project_id`,
  `application_id`, `build_id`), source (`kind: revision | upload`, immutable
  `sha256`, and bounded human-readable `reference`), `toolchain_lock_sha256`,
  `build_definition_sha256`, and one `platform: ios | android`. Authorization,
  actual source resolution, dependency checks, toolchain availability, worker
  placement, and digest/content verification remain caller responsibilities.
- `Policy`: explicitly supplied `max_attempts` in 1..5, `timeout_ms` in
  1..86_400_000, and bounded `retry_backoff_ms` in 0..3_600_000. This is a small
  fixed-delay policy; it does not infer capacity, queue position, or wait time.
- `Build`: immutable spec/policy; current attempt number and monotonically
  increasing fence; state; active worker reference when one may still execute;
  desired terminal state during reconciliation; bounded attempt history;
  timestamps supplied by the caller; accepted-event fingerprints; and immutable
  successful output references, initially absent.
- `WorkerRef`: explicit `organization_id`, `project_id`, `application_id`,
  `build_id`, `platform`, `attempt`, and `fence`. Numerically equal references
  from another scope cannot match. It is reconciliation data, not an
  authentication token, authority, distributed lock, or durable CAS proof.
- `ArtifactRef`: closed kind, lowercase SHA-256 digest, and positive byte count;
  it has no mutable download URL. Success supplies distinct references for an
  unsigned native binary, guest artifact, resource inventory, debug symbols,
  compatibility report, SBOM, and provenance. The pure module validates shape
  and one reference per required kind. Different kinds may reference identical
  content digests only with identical byte counts. It does not verify existence,
  content, provenance truth, or release eligibility.
- `Failure`: a closed classification/code pair. Compiler, test, policy, and
  unknown failures do not retry. A failure retains an immutable diagnostic SHA-256
  reference; a timeout observed from a successful completion may have none.
  Only allowlisted infrastructure failures are retry eligible: worker
  unavailable/lost, dependency transport, artifact
  transport, and worker timeout. Classification is trusted input; this slice
  does not classify compiler text or run customer code.

`new(spec, policy, request_key, now_ms)` validates closed bounded input and
creates attempt 1/fence 1 in `queued`. The request key is retained for the future
durable API adapter; the pure constructor cannot provide cross-request
idempotency or uniqueness without caller-owned storage.

`transition(build, event_id, event, now_ms)` returns
`{:ok, updated_build, :applied | :duplicate}` or `{:error, reason}`. All accepted
events retain their exact bounded payload and first accepted coordinator
observation time. Repeated event IDs compare payload only, excluding the new
delivery's `now_ms`, so exact redelivery at a later time returns the unchanged
latest state while retaining the first observation time. Reusing an ID with
different data is a conflict. New events require monotonically nondecreasing
integer time in 0..9_223_372_036_854_775_807; deadline/backoff arithmetic checks
overflow before addition. A retry-after overflow preserves the observed terminal
failure and blocks retry explicitly. The accepted-event ledger has a hard
32-entry ceiling; a full ledger rejects new events without mutation while
existing exact duplicates remain readable. At most 20 successful transitions are
possible across five attempts: four start/expire/stop/retry cycles, then a final
start/expire/cancel/stop cycle. No function reads a clock, process, file, network,
or database.

`customer_status(build)` projects the exact platform state, attempt count,
retryability/retry-after value when known, failure code, pending worker
completion, and immutable successful references. It supplies no estimated queue
position/wait, aggregate green result, signing status, distribution status,
release permission, or billing conclusion.

`worker_ref(build)` returns exact scoped data for queued or possibly active work.
It confers no right to dispatch and returns no active reference after completion.

## Events and transitions

The states are `queued`, `running`, `cancelling`, `reconciling`, `succeeded`,
`failed`, `cancelled`, and `timed_out`. `succeeded`, `failed`, `cancelled`, and
`timed_out` are terminal for an attempt; only an eligible failed/timed-out attempt
may explicitly retry. A build is a single platform, so another platform cannot
mask its failure.

| Event | Allowed state | Result |
| --- | --- | --- |
| `start` with exact current reference | queued | running; retain active reference and explicit deadline. The future adapter must persist this before external dispatch. |
| matching worker success before deadline | running | succeeded; clear active reference; retain immutable successful references once. |
| matching worker failure before deadline | running | failed; clear active reference; retain classification and bounded diagnostic reference/code. |
| `cancel` with a bounded reason | queued | cancelled, because no worker reference has been activated. |
| `cancel` | running or reconciling | cancelling; advance fence and retain the old active reference solely for terminal reconciliation. It does not prove worker termination. |
| explicit deadline expiry | running, now at/after deadline | reconciling with intended timed_out; advance fence; retain active reference; replacement remains forbidden. |
| matching terminal/definite-stop observation | cancelling | cancelled; clear active reference; discard success references. |
| matching terminal/definite-stop observation | reconciling | timed_out; clear active reference; discard success references. |
| matching terminal result observed at/after deadline | running | timed_out directly; report itself establishes worker completion; discard success references. |
| matching definite-stop observation before deadline | running | failed with worker_lost; clear active reference. |
| explicit `retry` | eligible failed/timed_out, no active worker, before attempt cap, at/after retry-after | queued with attempt +1 and fence +1; original spec/policy and previous history remain unchanged. |

Every terminal transition advances the fence to revoke normal result authority.
A cancellation/expiry already advances it; its completion observation checks
the retained active reference, rather than treating that revoked reference as a
new success authority. A stale reference, unissued future reference, unexpected
transition, conflicting event duplicate, or attempted output replacement fails
closed without changing state. Exact previously accepted events may return
duplicate even after a later retry, always without changing the current state.

If a terminal result arrives after the deadline, the coordinator observation
time governs this initial policy; a worker-provided completion time cannot
extend the deadline. A known compiler/test/policy/unknown failure retains its
nonretryable classification even in `timed_out`, so delayed reporting cannot
turn an expensive compiler error into an infrastructure retry. This trades
possible late-report rejection for a single explicit deterministic deadline rule.
Retry is still impossible until that
terminal report or a separate definite-stop observation proves the earlier
execution ended. Cancellation has priority once requested, including over a
previous timeout awaiting reconciliation.

## Invariants and integration requirements

1. Source, toolchain lock, build definition, platform, and tenant/build scope do
   not change across retries. Successful references cannot be replaced.
2. At most one active worker reference exists. Cancellation and lease expiry
   never themselves claim an external process stopped, authorize replacement,
   or authorize a second external effect.
3. Attempts increase only on explicit eligible retry; fences only increase.
   No stale/duplicate observation can overwrite newer output or state.
4. Unknown failures and compiler errors fail without automatic retry. Every
   retry consumes a finite attempt and observes explicit backoff.
5. Every input, diagnostic reference, artifact list, event ID, and history is
   bounded. Unknown fields and unsupported enum values fail closed.
6. Caller-owned durable storage must serialize transitions using compare-and-set
   under the exact scope and persist transitions/jobs atomically. Authentication,
   tenant authorization, durable event/request uniqueness, leases, global
   admission, actual worker termination, artifact content checks, upload
   reconciliation, charges, signing, and publication require separate adapters
   and evidence. Constructing a struct is not proof of any of them.

## Implementation and verification

The coordinated implementation owns only:

- `hosted/lib/mixer_hosted/builds/lifecycle.ex`.
- `hosted/test/mixer_hosted/builds/lifecycle_test.exs` using asynchronous pure
  ExUnit tests; the standalone command does not load `hosted/test/test_helper.exs`.
- This document and `verification/hosted-build-lifecycle/` evidence.

Tests cover the complete transition matrix, closed-shape bounds, immutable spec
and artifacts, exact/conflicting duplicate events, old/future/wrong-scope references,
cancellation before/after dispatch, success during cancellation, expiry with
unconfirmed worker, definitive completion after expiry, no replacement without
terminal observation, infrastructure-only bounded retries/backoff, and truthful
per-platform projections. A bounded generated sequence test explores events
across the small attempt cap and asserts state/fence/output invariants.

The local read-only discovery found `/opt/homebrew/bin/elixir` 1.20.4 compiled
with Erlang/OTP 29 and exact OTP 29.1.1; `hosted/mix.exs` pins Elixir 1.20.4 and
`hosted/.tool-versions` specifies Elixir 1.20.4-otp-29 / Erlang 29.1.1.
The verified standalone pure command is:

```sh
ERL_FLAGS='+S 2:2' elixir \
  -r hosted/lib/mixer_hosted/builds/lifecycle.ex \
  -e 'ExUnit.start(); Code.require_file("hosted/test/mixer_hosted/builds/lifecycle_test.exs")'
```

Retain command, tool versions, source revision plus owned-file digest, raw
output, result count, and exact host-only scope in the receipt. Use the existing
local toolchain; install no dependency and run no Mix application/provider/DB
or native-device harness. The entire hosted/W12/G22/GA operational gates remain
pending: these tests cannot prove durable reconciliation, isolation, dispatch,
capacity, secure worker observations, artifact publication, signing, customer
delivery, or billing.

The producer receipt records 21 passing ExUnit tests, including the 56-case
state/event matrix, five-attempt/20-transition path, and 64 deterministic
40-candidate event schedules. Run `python3
verification/hosted-build-lifecycle/run_pure_tests.py` from the repository root to
retain a new bounded command/version/source/output receipt. Failed initial
attempts remain in the evidence directory. Independent/root acceptance is a
separate review; the producer test result does not imply that acceptance.
