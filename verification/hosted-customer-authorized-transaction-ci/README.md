# Transaction fixture and migration CI integration

`run-2/receipt.json` records the corrected live facade against the exact new
`provision_customer_transaction_fixture` helper in `hosted/scripts/test-local.py`.
The collector extracts only that named function with Python AST; the shared
harness main and unrelated product lanes are never executed locally.

The new fixture is wired into normal CI test discovery with separate synthetic
admin, nonlogin owner, restricted runtime and database. The transaction test
loads its two migration modules itself when ordinary Mix discovery has not
already loaded them; the selected compiler deliberately excludes migration
modules to exercise that path. The informational test tag does not exclude it.

Observed results on PostgreSQL 17.11:

- Selected-source compilation with warnings as errors and formatting pass.
- All six ordinary migrations apply and an immediate repeat applies none.
- The latest three migrations roll back in order 004, 003, 002 and reapply as
  002, 003, 004. A final repeat applies none.
- All 18 corrected transaction ExUnit methods pass.
- The disposable PostgreSQL cluster stops and its scratch directory is removed.

Five existing build/foundation suites now expect six migrations. The aggregate
suite rolls back the latest three so its original held-worker assertion still
tests removal and restoration of migration 002. Its behavioral assertions are
unchanged. These five whole suites are not rerun by this focused collector;
their complete execution on the new source remains for normal hosted CI.

`run-1` preserves the earlier 17-method pass before independent review reproduced
the rescued effect callback defect. It is historical, not acceptance of the
corrected source. `run-2` includes the actual-write rollback correction.

Every run preserves selected source copies/hashes, command arguments, stdout and
stderr, dependency BEAM hashes, tool versions, scope and cleanup. No product
HTTP routes, artifact storage, provider deployment, native/phone or GA gate is
qualified here. Previous pushed checkpoint d385adf3 passed standard Phoenix and
Engine CI; that does not substitute for CI on this new source.
