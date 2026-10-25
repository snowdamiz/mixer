# Internal build coordinator independent review

Accepted as an internal development slice. The final combined root run passes
261 tests, with two existing Linux-only identity tests skipped on this Mac.
Independent verification rehashes all 92 current and archived source inputs and
all 21 command logs. The exact decision is recorded in
[`receipt.json`](../verification/hosted-build-coordinator-independent-review/receipt.json),
bound to root's
[`attempt-5-final`](../verification/hosted-build-coordinator/attempt-5-final/receipt.json).

The review covers product-plan sections 13.2, 13.5 and 14 against the existing
lifecycle, transactional journal/job storage and retained admission contracts.
The independent lane changed only this document and
`verification/hosted-build-coordinator-independent-review/`. Root collected all
database, Oban and packaged-release runtime evidence. The independent reviewer
reviewed source, wrote separate controls and verified the immutable evidence;
it started no database, service, provider or native runtime. The frozen catalog
inspector and authority driver remain outside this review.

The accepted source revision is `e8ab06649f122862f3ef4e3c68124af2da1af744` with
the complete tested source closure bound by SHA-256
`c21aff5bfbfcbe113e39c7ac99747336f69b91f5b40bb7363ff2df54700c2026`.
The runtime receipt retains exact commands and outputs for Elixir 1.20.4 on
Erlang/OTP 29, PostgreSQL 17.11 and a UTC loopback database. The independent
verifier uses Python 3.14.8. Run
`python3 verification/hosted-build-coordinator-independent-review/verify_receipt.py`
to recheck source/archive/log bindings without starting a service.

Nineteen producer tests and fourteen independently written hostile controls are
included in the total. They verify closed current-intent binding, historical-job
replay, committed start and successor-job visibility before external callbacks,
crash-after-effect reconciliation, local transport retirement after coordinator
death, original worker identity across lease takeover, stale actions, permanent
stop tombstones, malformed observations, cancellation/timeout uncertainty,
compiler failures, concurrent retry/backoff, and yield rollback/stale ownership.
The independent adapter registry is defined only in the review test and imports
no producer fixture. It models immutable operation bindings, expired-request
rejection, lexicographic epoch/revision ordering and terminal tombstones.

One separate asynchronous processor test uses Oban with testing disabled and a
real supervised builds queue with one slot. It calls neither
`Coordinator.perform` nor `Oban.drain_queue`. The persisted creation job moves
from available/attempt 0 to completed/attempt 1. The successor is executing at
callback time, then scheduled/attempt 0 with `meta.snoozed = 1`, matching the
pinned Oban version's snooze semantics. Both jobs name the production
`MixerHosted.Builds.Coordinator`; the journal and successor are committed before
the adapter sees them. Occupancy remains held and the lease is yielded. Job
errors are empty. The test retains queue, job and notifier diagnostics, stops
its owned Oban supervisor and clears its dedicated database rows. Root then
stops PostgreSQL and removes its disposable scratch directory. The packaged
release contains Coordinator/Dispatch and excludes the modeled adapter modules.

Two initial source findings are closed by source and runtime evidence. Committed
start and expiry successors now atomically yield the preceding lease; finished
callback paths also yield while retaining worker occupancy. An actual abrupt
coordinator death retains the live lease until expiry. A definitively released
terminal attempt now reaches guarded retry, which checks exact released evidence,
current revision and backoff under the established capacity/build/reservation/
lease lock order. Competing terminal consumers create one subsequent attempt/job.

Earlier attempts remain preserved with accurate provenance. Attempt 1 failed two
fixture assertions: a visibility query used the Elixir-prefixed worker spelling,
and a tombstone probe reused an expired lease guard. Attempt 2 passed all direct
worker controls but did not observe an asynchronous callback. Targeted attempt 3
showed the notifier lacked database application configuration; its review
diagnostic also incorrectly treated keyword options as a map, bypassing the
explicit test cleanup path while ExUnit/root cleanup remained separately
evidenced. The corrected fixture sets and restores identical pool/notifier
configuration, waits for a bounded PostgreSQL notification round trip and makes
cleanup unconditional. Targeted attempt 4 passes; the final combined attempt 5
is authoritative. No production source changed for these fixture corrections.

This accepts local PostgreSQL and asynchronous Oban execution with modeled
external operations. The provider remains explicitly unconfigured by default.
No real provider persistence, authentication, hostile-code isolation, external
exactly-once execution, billing, public authorization/RLS, queue estimates,
artifact publication, signing, Neon/Cloudflare deployment, failover/restore,
native/physical-phone or GA gate is accepted. Physical phones remain disconnected
and deferred under the standing user instruction.
