# Workspace CI fixture repair

The exact-push Phoenix run for `9a2bf16b59f98f2e0094ea6820c337ec1ed82c8c`
exposed stale seven-migration expectations in five database fixtures after the
workspace discovery migration added an eighth migration. Their setup now includes
that migration. The aggregate-admission rollback test also rolls back five
migrations to reach its original aggregate boundary and reapplies all five.

The workspace membership-expiry test previously aligned its wall clock before
database updates, writer startup and reader authorization preparation. Those
steps consumed its eligibility window on Linux before the reader reached a lock.
The repaired test completes setup and captures the actual membership witness
before aligning the immediately following project-head query. Test-only Ecto
telemetry identifies that boundary. PostgreSQL activity must show the exact
project-head query blocked before expiry; the writer is released after actual
wall-clock expiry. The test additionally requires a successful lock result and an
empty selected-row reread after the lock. That RLS reread is the first rejection
boundary after membership expiry. A lock timeout cannot satisfy those
assertions. Production sources and the 500ms lock timeout are unchanged.

The collector in `verification/hosted-workspace-ci-fixture-repair/run.py` selects
only ordinary workspace modules, pinned dependency BEAMs and the eight migrations.
It never imports the shared broad harness or frozen lanes. It formats all six
changed test files, executes eight-migration apply/rollback/reapply controls in an
owned disposable database, and executes the 24 workspace storage methods in a
separate owned disposable database. Exact command, tool, source and output hashes,
lock chronology and cleanup are preserved in each attempt directory.

Attempt 1 stopped before PostgreSQL startup because the expanded migration
collector omitted the ordinary artifact-schema module used by migration 000005.
That failed compile and its cleanup receipt are preserved. Adding the explicit
schema module produced a clean attempt 2: all 24 workspace methods and all eight
migration controls passed, with zero skipped or excluded methods. A final attempt
3 binds the widened test-only witness-message allowance and complete JSON output
hashes. The production query timeouts remain unchanged.

Local evidence is host PostgreSQL evidence. Execution of the broader foundation,
build-storage, admission, aggregate-admission and coordinator fixture suites is
reserved for the automatic Linux Phoenix workflow after root delivery. That CI
result, provider operation, customer browser sessions, physical devices, native
runtimes and all GA qualification remain separate pending evidence.
