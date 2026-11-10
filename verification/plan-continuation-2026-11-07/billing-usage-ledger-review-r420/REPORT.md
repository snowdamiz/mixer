# R420 independent review of R398 usage ledger

**PASS WITH SCOPE LIMITS. No proven product defect found in this four-file,
unselected development component.** The independent final run passed all 17
unchanged candidate tests and nine additional reviewer tests against a fresh
loopback PostgreSQL 17.11 cluster. This is neither commercial billing acceptance
nor GA qualification. Root owns later delivery, migration-list integration and
source selection; this review makes none of those changes.

## Artifact and contract reviewed

Reviewed R398's REPORT.md, INTERFACE.md, result.json, application-map.json,
usage-ledger.patch and four exact afterimages. Patch SHA256:
`b5945302df0c2aa3368dc2a072d91cb71dd87f4e9627890c3b764d49659e3fd7`.
Standard `patch --batch -p1` applied the add-only patch in this review's empty
owned directory. Each applied file, R398 source file, R398 afterimage and tested
review copy matched the map's byte count and SHA256 before/after testing.
`candidate-before.json`, `candidate-after.json` and `patch-application.json`
retain the exact observations.

The contract is an internal trusted-server ledger. Build units are trusted worker
**elapsed milliseconds**, not CPU time or rounded minutes. Active-update units
are app-installation-month counts: initial 1, replacement 0/1, complete UTC
calendar month. They are not unique physical-device counts. Storage units are
exact integer byte-seconds over the explicit half-open UTC interval. There are
no prices, rounding, entitlements, consumers, provider reporting or HTTP changes.

This API validates representation and ledger consistency; it does not prove
metering, authenticate a producer or authorize a tenant. A syntactically valid
observation from an arbitrary request remains untrusted. The module documentation
and interface state this boundary. Scope/source/key production adapters and
app-installation identity policy remain separate pending integration work.

## Executed attacks and results

Final commands, both with `--warnings-as-errors --trace` and `ERL_FLAGS=+S 2:2`:

```
mix test --warnings-as-errors --trace --seed 0 test/mixer_hosted/billing/usage_ledger_test.exs
mix test --warnings-as-errors --trace --seed 420 test/mixer_hosted/billing/usage_ledger_review_test.exs
```

`logs/ledger-tests-fresh2.log`: **17 passed, exit 0**.
`logs/independent-attacks-fresh2.log`: **9 passed, exit 0**.
The reviewer controls are executable in the owned source copy and identified in
`review-test-identity.json`. These exercise the actual Repo and database:

- Empty/control/invalid UTF-8, multibyte-overlength and nonstring identities
  refuse; 128-byte identities and distinct delimiter/Unicode tuples remain
  separate. Unknown string-key fields refuse. Identity reuse conflicts across
  metric and period; adjacent half-open intervals retain separate totals.
- Leap-February and year-rollover installation months succeed; one-second
  changes to the month end fail at both API and direct SQL boundaries. A
  void/reopen chain totals one; retry of the older void remains a duplicate.
- Eighteen mixed duplicate/conflicting observations with six concurrent clients
  yield one append, five duplicates and twelve identity conflicts. Eighteen
  competing/duplicate correction requests yield one append, five duplicates and
  twelve superseded-parent refusals, leaving exactly one current replacement.
- Direct SQL refuses cross-tenant, cross-metric/platform, changed-period and
  changed-source parents. Unique indexes reject a second successor and source
  identity reuse across periods. Self-reference, absent parent and a three-row
  same-statement cycle refuse. Zero-row UPDATE/DELETE and TRUNCATE CASCADE also
  refuse through the append-only database triggers.
- A caller's uncommitted original/correction totals four inside its transaction
  while another connection sees zero and no history. Outer rollback removes both
  and releases the identity for a later append. The unchanged candidate suite
  additionally proves readers retain the old head until replacement commit,
  missing/out-of-order parent retry, and Repo close/reopen durability.
- Eight maximum-bigint storage observations sum to exactly
  `73786976294838206456`; replacing one with zero gives exactly
  `64563604257983430649`. The adjacent period stays zero. No floating-point or
  bigint-total conversion is involved.

Source inspection corroborates the observed invariants: the unique identity is
tenant/source/key across scopes; parent locking plus the unique successor index
prevents branches; the composite FK preserves parent scope/source; causal insert
checking plus immutable existing rows prevents cycles; totals use one statement
over current heads and transport PostgreSQL numeric as text to an Elixir integer.
None of these facts establishes upstream observation authenticity.

## Preserved findings, responses and failed attempts

No earlier ledger review finding was supplied. R398's existing implementation
history and limitations remain intact:

- Its R1 ran all original 15 tests but strict execution failed on an unused
  default argument. R398 removed that default; R2 passed 15 strict tests.
- R398's own later inspection identified direct-SQL cycle risk. Its response was
  a causal predecessor insert guard and two controls; final R3 passed 17. R420
  re-executed those exact bytes and additionally refused a three-node cycle.
- R398 reports an initial overly broad filename discovery. That recorded scope
  deviation is preserved; R420 used named files and the supplied exact manifest.
- R398's original three stopped-cluster receipts and its pending trusted
  adapters, migration-list integration, producer policy and commercial gates
  remain historical evidence/limitations, not new R420 qualifications.

R420 fresh1 independently passed the unchanged 17 tests, then passed six of nine
reviewer tests. Three reviewer assertions incorrectly expected `Repo.insert/1`
to return raw Postgrex errors; Ecto raised constraint exceptions instead. These
were review-harness defects, not product defects or successful bypasses. The
reviewer replaced those calls with parameterized direct SQL and reran in a
second fresh cluster. Both failed and final raw logs are retained; candidate
source/test bytes were not changed. No finding or response was discarded.

## Preservation, cleanup and limitations

`preservation.json` and before/after manifests observe zero changes to the 184
named canonical/reference inputs, including prior billing route/app/auth/build
source and R394 delivery references. A separate exact-manifest comparison checks
all **185** canonical selected members against R394's frozen manifest, with zero
mismatches. Selection remains
`14868be39631a86c79f4ba7b6bfb9386c6d80062ef4d0ddebbf55aea833afc96`;
manifest remains
`25eb542fa628e8bb0eeaaca57b879b34abbfc266d9bdd566e08e3d90d090564a`.
All four new ledger paths remain absent from canonical source. The existing
migration allowlist and source collector were not edited. No Git operations,
devices, held namespaces, remote services, credentials or subchildren were used.
Writes were confined to this R420 output directory.

Fresh1 and fresh2 bound only 127.0.0.1, used ports 59819 and 60357 respectively,
disabled UNIX sockets and used separate owned data/log directories. Both exact
directory stops exited 0; subsequent pg_ctl status exited 3 and postmaster PID
files were absent. `cleanup-fresh1.json` and `cleanup-fresh2.json` retain these
observations. Inactive DB data/logs remain. No historical custody hold is released
and no general descendant-absence claim follows from a direct command exit.

`commands.json` records argv, cwd, PID/PGID, timeout, exit, elapsed time and raw
output paths. Tools: Elixir 1.20.4, OTP 29, PostgreSQL 17.11, Python 3.14.8 on
Darwin/arm64. Existing pinned dependencies and build caches were copied into
owned paths; no dependency was fetched. Two BEAM schedulers were chosen for this
bounded run under current contention, not as a standing capacity limit.

Limits: finite synthetic component testing on local PG17, default transaction
isolation, no hostile DBA disabling constraints, no Neon production-role or
operational validation. Successful append inside a caller transaction is
provisional; database/storage failures can raise. Pagination, overlapping-period
producer policy, trusted worker/assignment/storage adapters, immutable package
consumers, provider reconciliation, HTTP authorization, prices/rounding,
entitlements, quotas/caps and commercial/GA gates remain pending. Full-suite
migration integration must update the existing allowlist and rollback
expectations coherently in a later root-owned delivery.
