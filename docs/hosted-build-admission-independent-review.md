# Independent hosted build admission review

Independent review accepts the bounded internal admission development slice.
Root's corrected collection passes 227 host tests, including 17 admission tests
and all 11 independent controls. Two existing Linux-only identity checks are
skipped on this Mac. This accepts no public build route, worker authority,
production coordinator, provider execution, Neon, signing, billing or GA gate.

The contract uses one durable capacity row per organization/platform, shared
across projects, applications and builds. This supplies a fleet-wide cap for
that pair, not an additional organization-total or platform-total hierarchy.
Transactions lock capacity, exact-scope build, reservation and lease in that
order, then sample PostgreSQL `clock_timestamp()`. Retained owner/epoch lease
history must prevent stale tokens from recurring after expiry or release.

Independent controls use real PostgreSQL rows, lock contention, concurrent
transactions and SQL expiry fixtures in `mixer_admission_review_test`, reached
through `MIXER_TEST_DATABASE_PORT`. Root owns collection and the disposable
database lifecycle. No test-double result will qualify durable admission.

The controls cover cross-project/app quota races; expiry and ownership transfer
without a second reservation; stale, expired and mismatched tokens; post-lock
database time; guarded journal/job rollback; and exact definitive completion
before release. Running cancellation and deadline expiry alone retain occupancy.
Queued cancellation may release only the exact replayed never-started current
attempt; claiming capacity authorizes no dispatch, and start must persist before
dispatch. Historical duplicate events must not release a newer attempt. A held
reservation rejects guarded retry; the trusted Storage retry path is available
only after definitive release and requires a new claim for its next attempt.

Review corrected two SQL CHECK expressions that accepted malformed NULL pairs,
and required retained release event IDs to match replayed attempt history before
readmission. A subsequent evidence review found timezone-dependent expiry
fixtures. The corrected tests use explicit UTC assignments and the collector
records a UTC server. Attempt 1 remains preserved as pre-correction evidence;
attempt 2 is authoritative. Its independent lock test proves the competing
transaction began at `1792888594006`, expiry occurred at `1792888594206`, and
the capacity lock remained held until `1792888594359` (database epoch ms).
Renewal rejects the expired lease after waiting for that lock. A second real
lock wait verifies that a new lease's TTL starts after acquisition.

The read-only receipt verifier matches all 86 current inputs, every archived
source file, command exit and output hash against the root-owned collection.
The accepted source-tree SHA-256 is
`f370148dbd058fece3d5b4792efca9056fc7e91523be34204b8856cdd9d17b3c`.
See `verification/hosted-build-admission-independent-review/receipt.json` and
`verification/hosted-build-admission/attempt-2/receipt.json`. Run
`python3 verification/hosted-build-admission-independent-review/verify_receipt.py`
to repeat the byte checks without starting a database. Elixir 1.20.4 / OTP 29
and PostgreSQL 17.11 supplied the local run. PostgreSQL stopped and its owned
scratch directory was removed. The packaged release excludes test workers.

No outstanding source finding blocks this internal slice. The synthetic job
consumer proves atomic intent persistence, not external execution. Loopback
PostgreSQL without TLS supplies no Neon, Cloudflare, zero-traffic wake, provider
isolation or operational recovery evidence. Aggregate organization/provider
quotas, queue estimates, authenticated workers, actual dispatch and external
effects remain pending. Trusted raw Storage composition remains an internal
caller contract. Runtime Ecto migration-module redefinition warnings are
retained in the test log; warnings-as-errors compilation passes. Physical
phones remain disconnected and deferred.
