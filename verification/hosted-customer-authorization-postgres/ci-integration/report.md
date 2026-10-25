# Focused standard-harness integration

The ordinary PostgreSQL test harness now provisions the synthetic authorization
database and roles and supplies `MIXER_AUTHZ_TEST_PORT`. The focused test can load
its migration during ordinary test discovery. Existing foundation/build suites
retain all-migration coverage with the fifth migration included. This packet
does not execute or accept the broader shared test harness, frozen lanes or CI.

Root froze the minimal integration delta after the finite security correction
passed independent review. The original baseline's 208 sealed file entries and
the correction's 30 sealed file entries remain byte-identical. Their source
binding maps describe their historical capture; this additive packet binds the
current sources. The original `run.py` collector is restored byte for byte;
the expanded collector is a new `ci-integration/run.py` file. A transitional
audit caught the driver preservation mistake before delivery, and the earlier
attempts and their source snapshots remain retained.

The exact changes are captured in `selected-delta.patch`, before/after hashes
in `delta-manifest.json`, and untouched before copies in `inputs-before/`:

- `hosted/scripts/test-local.py` adds one unique top-level
  `provision_customer_authorization_fixture` helper and one call after its owned
  local cluster starts. It creates a synthetic fixture superuser for test-only
  administrator writes, a separate nonlogin/non-superuser/non-bypass owner, a
  separate nonprivileged runtime, the owned authorization database and the
  required connect/schema restrictions. It grants no production credential or
  role authority.
- The focused test conditionally requires the exact migration file when it has
  not been compiled. The precompiled standalone path remains supported.
- Foundation and storage expected migration lists append `00003`; admission,
  aggregate and coordinator counts become five. Every `all: true` remains.
  Aggregate rollback now reverts `[00003, 00002]` and reapplies `[00002, 00003]`.
  Its held-worker assertions remain unchanged.
- The new migration's `down` removes only its own two policies on its twelve
  tables before relation drops. Real rollback initially exposed dependencies
  from resource policies to membership tables. No `DROP CASCADE` or authority
  policy/up change was added.

The new collector extracts and compiles only the exact unique named provisioning
FunctionDef through Python AST. It never imports or executes the ordinary
script's main body. The selected helper source SHA-256 is
`648bd53e0b94641cd5764486b28e7c99e2687447cccf59ecdba1005ec323ed3b`.
The new collector SHA-256 is
`c7ddea6d61a52ef1072c7c66e56c800d273a2add4bd7667981339e42a232c87e`.
Its explicit nested `ROOT` resolution and resulting `HOSTED` path are recorded
in `environment.json` and confirmed by the executed input/command paths.

The focused command is:

```sh
python3 verification/hosted-customer-authorization-postgres/ci-integration/run.py \
  --output verification/hosted-customer-authorization-postgres/ci-integration/run-N \
  --source-revision ROOT_SUPPLIED_REVISION --ci-integration
```

`run-3` passes the exact shared helper provisioning, selected source compilation
with warnings as errors, formatting and **25/25 authorization methods**. Its
compiler argv omits migration compilation; the focused test loads `00003`
itself. A separate selected ordinary migration process applies all five
migrations to a second empty disposable database, confirms an empty idempotent
rerun, reverts the latest two in descending order, verifies their tables are
gone, reapplies both in ascending order and confirms another empty rerun.
Only completed ordinary migration modules are unloaded between migration waves
inside that isolated process, avoiding expected duplicate-module warnings.

The final selected input-tree digest is
`2d9f921e665f993592a74dc38c4fbe1836b8b1d7ddbf4dabc38e6fc95df53916`.
The restored original standalone collector also passes **25/25** methods in
`standalone-run-2`. All owned clusters stopped and scratch roots were removed,
including earlier failed attempts. `run-1` records the rollback dependency
failure; `run-2` and `standalone-run-1` preserve the transitional collector path
before restoration/relocation. No historical result was rewritten.

Environment remains Darwin arm64, Elixir 1.20.4, OTP 29 / ERTS 17.1,
PostgreSQL 17.11 and Python 3.14.8 with `ERL_FLAGS='+S 2:2'`. Revision
`cb56d4b9d979ffc02554be991466a180e7882cd3` is root-supplied context; no Git ran.
PostgreSQL 16 was unavailable at both recorded conventional local binary paths;
PG16 and full standard CI remain explicitly pending. The five ordinary suites'
changed assertions were inspected and formatted but those suites were not
executed, including their held-worker runtime assertions. The migration smoke
establishes the actual migration order and rollback dependencies, not complete
build/foundation regression coverage.

The authorization result is still a current read-only evidence lookup feeding
the existing pure callback. Transaction-bound domain authority, current-clock
before-effect checks, immutable domain/audit/idempotency/Oban composition,
protected customer routes/console, deployed roles/Neon/TLS/provider and
operational/GA qualification remain pending. The baseline and runtime-role
correction reports retain the remaining scope limitations.
