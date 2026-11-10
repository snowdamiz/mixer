# R398 isolated usage ledger candidate

Ready for root's independent slice review. `usage-ledger.patch` adds exactly four
files: a private ledger module, Ecto row schema, new migration, and executable
PostgreSQL tests. The patch is 29,452 bytes, SHA256
`b5945302df0c2aa3368dc2a072d91cb71dd87f4e9627890c3b764d49659e3fd7`.
`application-map.json`, `afterimages/`, and `application-check.json` bind exact
delivery bytes. Standard `patch` applied it in a fresh owned directory and all
four results matched their afterimages. Canonical production source is unchanged.

## Contract and implementation

Root coordinated the interface before implementation and clarified build usage
as **build_elapsed_milliseconds**, the trusted worker's elapsed build duration.
There is no CPU-compute substitution, minute rounding, pricing or charge policy.
`INTERFACE.md` records the small usage sketch and design comparison.

`UsageLedger.scope/1` validates explicit tenant, metric, platform and half-open
UTC Unix-second period. `append(repo, observation)` accepts that scope plus stable
trusted source/key, exact nonnegative bigint units and optional predecessor UUID.
This is an internal trusted-server boundary, not measurement attestation or
authorization. A caller must derive facts from authoritative server observations;
arbitrary request fields do not become proven measurements by entering this API.

The other raw metrics are **active_update_installations**, app-scoped
installation-months with a complete UTC calendar-month period, and
**storage_byte_seconds**, exact integer byte-seconds over the explicit period.
An installation-month producer must use one stable source key, initial units 1,
with correction units 0/1. Polls, retries and individual assignments are not new
base observations. Installation-months are not unique physical devices. The
published monthly-active-device commercial definition and trusted producer
adapters remain pending. Storage prorating, retention and pricing are not chosen.

Identity is unique on tenant/source/key across metric, platform and period.
Exact retries return the existing row; changed observations refuse. Transaction
advisory locks serialize competing first inserts, with a unique index retaining
the DB invariant. Corrections use a new identity and an existing same-scope/source
predecessor. Row locks and a unique successor index allow exactly one successor.
Missing or wrong-scope predecessors refuse without reserving the new identity;
retry after arrival can succeed. Stale parents refuse. A retry of an already
applied correction remains idempotent, even after later corrections.

Absolute replacements preserve all history. `total/2` selects current heads in
one PostgreSQL statement. SUM(bigint) stays PostgreSQL numeric, travels as text,
and is parsed to an arbitrary-precision Elixir integer; it never wraps or passes
through float. `entries/2` returns history for the explicit scope in stable
source/key order. Both APIs require an explicit validated scope.

The composite parent foreign key prevents cross-tenant/scope/source linkage;
insert guards require the predecessor already to exist and refuse causal cycles.
UPDATE, DELETE and TRUNCATE refuse through DB triggers. These safeguards are not
a defense against a privileged DBA disabling constraints. A successful append
inside an enclosing transaction is provisional and rolls back with it.
Storage errors raise to the internal caller; no public error/HTTP contract is
invented. `entries/2` is an internal history query, without production pagination.

## Executed evidence

`logs/ledger-tests-r3.log`: **17 passed**, exit 0, seed 0, trace and
`--warnings-as-errors`, using fresh owned loopback PostgreSQL 17.11. Tests execute:

- Twelve-way identical insert deduplication; competing observation conflicts;
  twelve competing correction successors with exactly one winner.
- Tenant/source and exact metric/platform/period isolation, foreign-parent and
  direct SQL cross-tenant refusal, exact retries and changed-content conflicts.
- Missing/out-of-order predecessor refusal followed by successful exact retry,
  correction chains, stale-parent refusal, immutable retained original units,
  and app-scoped installation-month void/reopen.
- Enclosing transaction rollback and retry, concurrent reader visibility before
  and after correction commit, and Repo close/reopen durability.
- Exact integer validation, unknown-field refusal, scoped empty totals, three
  maximum-bigint values summing exactly beyond bigint, DB mutation refusal, and
  same-statement causal-cycle refusal.

This is a development component receipt. The out-of-order case inserts a synthetic
known-ID predecessor directly into this isolated DB; it does not claim an upstream
producer protocol exists. Twelve tasks ran with at most eight concurrent clients.
Compilation and tests used `ERL_FLAGS=+S 3:3`, adapted to current host contention.
Tools: Elixir 1.20.4, OTP 29, PostgreSQL 17.11, Python 3.14.8 on Darwin/arm64.
Existing pinned dependencies and compiled caches were copied into owned paths
from R394. No dependency fetch or new dependency was used. `commands.json` records
argv, cwd, PID/PGID, bound, exit, duration and raw output; `tested-source.json`
identifies copied source bytes. `run.py` can execute another fresh owned test DB
with an unused label, e.g. `python3 .../billing-usage-ledger-r398/run.py review1`.

The first strict command executed all original 15 tests successfully, then exited
1 because the test helper declared an unused default argument. That warning and
raw result remain in `logs/ledger-tests-r1.log`. Removing the unused default led
to 15 strict passes in R2. Source review then identified the direct-SQL cycle risk;
the explicit predecessor guard and two new controls produced the final 17 passes.
R1/R2 are not substituted for the final source receipt.

All three owned clusters bound only 127.0.0.1 with UNIX sockets disabled. Exact
directory stops exited 0, statuses exited 3/no server, and postmaster PID files
are absent; `cleanup-r1.json`, `cleanup-r2.json`, and `cleanup-r3.json` preserve
those observations. Inactive DB data and raw logs remain. No new UNKNOWN custody
or historical hold release is claimed; direct command exits do not prove absence
of arbitrary descendants. No device, signing, provider, credential, customer data,
remote mutation or subchild was used.

## Preservation and remaining integration

`preservation.json` verifies all 184 original named inputs/references unchanged.
`frozen185-check.json` separately compares every canonical member to the immutable
185-member selected manifest: zero mismatches; manifest and selection retain their
expected hashes. R394 references are unchanged and no R394 artifact was written.
The candidate files exist only under this output directory. No canonical test
helper, webhook, identity, auth, build, module configuration or consumer was edited.

After independent review, root owns any coherent integration and reviewed source
selection successor. The existing closed migration allowlist in
`test/test_helper.exs` intentionally remains unchanged here; later integration
must update that existing owner and relevant migration rollback expectations
together. Applying this primitive-only patch without that work is not full-suite
integration. No successor selection was generated or authorized by this slice.

Still pending: real trusted worker/assignment/storage adapters, provider
reconciliation, customer-to-tenant binding, Stripe usage reporting and test-mode
corrections, commercial rules, quotas/caps, consumer/public UX integration,
production migration/roles/Neon operation, ordinary CI and W14/G23 acceptance.
The full binding commercial scope is not complete.

Scope deviation: initial filename discovery used `rg --files hosted services |
head -100` and enumerated unrelated nested `services/verification` filenames.
No contents there were read, and subsequent source exploration was restricted to
named hosted paths and explicit billing references. This discovery was broader
than the task's no-broad-verification-scan instruction; no held namespace was
accessed or operated on.
