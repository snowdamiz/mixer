# Phoenix service foundation

The new `hosted/` application implements the selected Phoenix/Plug/Bandit,
Ecto/Postgrex and Oban foundation. The existing Go service remains the reference
for future protocol and migration parity. No authoritative route was switched.

The API exposes process liveness only and cannot dispatch or stage jobs. The
processor has no HTTP endpoint and uses six separately bounded queues with
database leadership. Normal release startup requires explicit role/database
configuration. Database settings require direct DNS endpoints, certificate and
hostname verification, bounded pools and timeouts; inspected settings redact
secrets. This is not an identity or readiness implementation.

Root's final local receipt is
[`candidate-5/receipt.json`](../verification/phoenix-foundation/candidate-5/receipt.json):
eight tests pass on Elixir 1.20.4, OTP 29.1.1 and PostgreSQL 17.11. They exercise
actual Bandit HTTP, JSON liveness/404 behavior, API/processor separation, repeat
migration safety, transaction commit and rollback after both domain-fixture and
job inserts, and a real delayed Oban job completing without HTTP requests. The
production release builds and rejects missing runtime configuration with the
expected error. Each collector stops its own database and removes its scratch.

Two initial findings are retained in candidate-1: disabling all Oban plugins also
disabled processor leadership, preventing delayed execution; and an initial
rollback test used an Ecto.Multi preflight error, which rejected before inserts.
The processor now retains database leadership, and rollback is tested through a
runtime transaction failure after both inserts. Candidates 2 and 3 pass. Candidate
4 passed its executable checks but failed source stability because the expected
release boot rejection generated a crash dump. Candidate 5 disables that dump and
keeps generated artifacts out of source accounting. No product source changed
between candidates 2 and 5; only collection, inventory and documentation changed.

The independent review is recorded separately in
[`phoenix-foundation-review.md`](phoenix-foundation-review.md). Root acceptance
binds the final source, logs, dependency inventory and review receipt at
[`root-acceptance.json`](../verification/phoenix-foundation/root-acceptance.json).

The added GitHub workflow pins the BEAM toolchain and runs the same collector
against the Ubuntu runner's PostgreSQL 16 fixture. Its actual version and output
must be recorded by CI; a local macOS pass is not Linux evidence.

All hosted release gates remain open. The PostgreSQL fixture uses local trust and
no TLS; current evidence checks TLS configuration, not network handshakes or Neon.
The domain table/worker are synthetic test code, not a product outbox or exactly
once external execution. Cloudflare deployment/wake/recovery, orphan rescue,
global quotas, fencing, restricted runtime roles/RLS, identity, signing, billing,
R2 isolation, Go wire parity and production migration remain pending. Sixteen
downloaded license/notice files are retained for 19 pinned Hex dependencies;
four packages omit a top-level notice, so upstream notice collection and release
license review remain pending. No native runtime or computer-use test ran.
