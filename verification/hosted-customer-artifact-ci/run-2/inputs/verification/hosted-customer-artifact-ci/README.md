# Customer artifact CI integration

`python3 verification/hosted-customer-artifact-ci/run.py run-N` creates a new,
immutable attempt directory. It snapshots selected ordinary product sources,
test fixtures, seven migrations, the named CI provisioning helpers and the
collector itself. It compiles only those product sources and executes the copied
tests using pinned local general-purpose dependency BEAMs.

Only `provision_customer_transaction_fixture` and
`provision_customer_artifact_fixtures` are extracted from the shared harness's
AST. Its main body is never executed. The functions create separate synthetic
transaction, storage, metadata-resolution and public-facade databases and roles
inside the collector's disposable loopback PostgreSQL instance. No live
application configuration or existing database is changed.

The selected tests exercise current policy, transaction ownership, staged
metadata reads, immutable artifact storage and the actual CustomerArtifacts
entry points. The migration smoke applies all seven ordinary migrations,
confirms an idempotent rerun, rolls back the latest four, and reapplies them.
The build-aggregate test retains its original rollback target despite the two
subsequent authorization migrations and new artifact migration above it.

This focused host check does not execute the full application, a provider,
native runtime or any frozen/rejected hosted lane. Standard Phoenix CI remains
a separate result for its exact pushed revision and PostgreSQL version.
Per-attempt receipts contain source hashes, commands, tool versions, output
hashes, actual result and owned-process/scratch cleanup. A successful focused
check never substitutes for a missing standard CI or deployed workflow result.
