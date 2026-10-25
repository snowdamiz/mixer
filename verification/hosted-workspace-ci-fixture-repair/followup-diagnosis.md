# Exact-push f2aba240 Phoenix timeout diagnosis

The automatic Phoenix run
[40204405232](https://github.com/snowdamiz/mixer/actions/runs/40204405232)
failed for source `f2aba240ebdecae1c810f50528f0ed4ed6245be1`.
Its printed result is `527/528 passed, 2 skipped`. The five repaired migration
fixtures no longer invalidate their tests, and the membership-expiry lock test
passes. The sole failure is the large-customer workspace pagination case: its
first page returns `authorization_unavailable` when DBConnection exhausts the
5000ms transaction/checkout budget. The stack is inside `Storage.candidates!/4`.
That stack identifies the location at expiration, not which query consumed the
budget. The CI evidence contains no per-query timing for that call. Earlier
runtime topology/admission/policy work or transient scheduling may have consumed
most of the budget; exact attribution remains unknown.

Only `tests.log` and `receipt.json` were initially read from the in-memory CI
artifact ZIP. Root then explicitly authorized the additional
`postgres-version.log` member. No source archive or other archive member was read
or extracted, and the ZIP was not saved to disk. The collection receipts preserve
that allowlist and the archive/output hashes. CI used PostgreSQL 16.15 on Ubuntu
and successfully stopped PostgreSQL and removed its scratch directory.

The local diagnostics use selected ordinary workspace modules, the actual
restricted runtime login and GUC context, the unchanged five-second transaction
and statement bounds and 500ms lock bound, and the original 121 visible projects.
All 122 membership rows remain present, including the foreign principal's row.
The first project query returns 101 candidate rows for a page of 100; the existing
test still checks the remaining 21 projects and uniqueness across all 121.

| Diagnostic | Observation | Limit |
| --- | --- | --- |
| PG17 Homebrew, no JIT | Actual candidate 8.364ms; EXPLAIN ANALYZE execution 3.769ms before explicit ANALYZE and 1.244ms afterward. All 24 methods pass. | Cannot establish Linux/JIT behavior. |
| PG16.15 Debian Linux/arm64, JIT available/on, untouched stats | Actual candidate 16.132ms; estimated cost 1792.12, no JIT plan node. All 24 methods pass. | CI runs Ubuntu/amd64 and its broader suite. |
| Same PG16.15 with diagnostic-only forced generic plans, untouched stats | Actual candidate 13.189ms; generic estimated cost 1792.13, no JIT plan node. No prior cached candidate statement is visible. All 24 methods pass. | A controlled generic plan does not reproduce exact CI scheduling or preceding fixture state. |

The accepted generic diagnostic reports default JIT cost thresholds
100000/500000/500000 and autovacuum analyze threshold 50, scale factor 0.1 and
one-minute worker interval. Autovacuum statistics are asynchronous; these settings
do not guarantee fresh statistics before a newly created customer's first read.
The current evidence does not establish that statistics caused the CI failure or
that ANALYZE would make the production five-second bound safe. A fixture-only
ANALYZE workaround, fewer projects or a larger timeout is therefore not selected.

Two diagnostic implementation faults are preserved rather than hidden. The first
PG17 probe detached because it applied boolean `not` to a missing stage value;
it produced no plan, so its ordinary test pass is not diagnostic acceptance.
The first PG16 probe captured valid first-query data, then detached on the second
page because its stage was an atom. Separate assessment files explain those
limits. The corrected generic probe completes without handler errors. All local
attempts stop their owned PostgreSQL process; both Docker attempts remove their
owned container, and every attempt removes owned scratch. Other containers and
processes remain untouched.

No production or ordinary fixture source was changed for this followup. The
focused PostgreSQL 16 source/migration checks provide bounded host evidence for a
coherent development slice; they do not resolve the failed automatic Phoenix run
or replace a future exact-push Linux result. The next existing automatic CI result
should retain the distinction between total transaction-budget exhaustion and
individual query latency. Provider, browser, native/runtime, physical-device and
GA qualification remain separate pending evidence. The previously committed
repair receipt and its attempts remain unchanged.
