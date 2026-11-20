# Restore a local hosted test database

Use a fresh PostgreSQL 17 cluster for the restore. Keep it disconnected from the
source cluster and leave the API and build processor stopped until the restore
checks finish. Have the custom-format database dump, the matching worker
SQLite backup and artifact files, and the fixture's roles. Use the same Mixer
source that created the dump.

## Restore the database

Set the variables below to the owned restore cluster, its owner role, the
custom-format dump, and the database name stored in the dump. The cluster
should accept only local connections. Create the fixture roles in that cluster
before running `pg_restore`.

```sh
: "${restore_port:?Set the port of the owned local PostgreSQL cluster}"
: "${restore_owner:?Set the owner role in the target cluster}"
: "${restore_dump:?Set the path to the database dump}"
: "${restore_db:?Set the database name recorded in the dump}"

pg_restore --exit-on-error --create --host 127.0.0.1 --port "$restore_port" \
  --username "$restore_owner" --dbname postgres "$restore_dump"
```

Use `pg_control_system()` on the restored database to confirm that its system
identifier differs from the source cluster's identifier.

## Restore the two pinned CHECK expressions

PostgreSQL can flatten the nested conjunction in the expiry constraints on
`mixer_authz_families` and `mixer_authz_credentials` during a dump and restore.
Mixer checks the exact catalog expression on startup.

After confirming the target cluster identity, run this from the Mixer checkout
root. The script uses one transaction and accepts only the known flattened
form or the already pinned form. An unexpected expression, missing or
unvalidated constraint, or validation failure stops the transaction.

```sh
psql -X --host 127.0.0.1 --port "$restore_port" --username "$restore_owner" \
  --dbname "$restore_db" --file scripts/restore-local-authz-expiry.sql
```

## Check the restored service

Configure the local API to use the restored cluster and the matching retained
artifact store. Start it under the restricted runtime role and check that
catalog admission reaches `storage_ready`. Sign in again, open the settled
build, and download its unsigned build, debug symbols, and resource inventory.
Check artifact sizes and SHA-256 digests against the original build record and
verify the restored worker journal shows the original operation and start count.

If startup fails after the script succeeds, preserve the restore and inspect the
exact admission error. Verify the remaining catalog, roles, and selected Mixer
source before proceeding.

## Reproduce the CHECK repair

Use the PostgreSQL 17 client and server tools from the same installation.
From the checkout root, run the maintained diagnostic with their bin directory.

```sh
python3 -B tests/integration/hosted-expiry-restore/replay.py --postgres-bin /opt/homebrew/opt/postgresql@17/bin
```

The test reads table declarations from the checked-in migration and expected
expressions from the PostgreSQL 17 catalog manifest. It creates two disposable
loopback clusters, dumps and restores four seeded rows, checks the exact
repaired expressions, and verifies that the repair preserves rows, rejects
invalid expiry values and rolls back when it encounters an unexpected
constraint. This command exercises the PostgreSQL repair. Use the service
checks above to qualify the restored API and artifacts.

## Replay one settled iOS Starter backup

Use a Mixer checkout containing the Starter restore replay and the three
pinned commits below. The replay reads the Starter launcher from
`57f3ed4f17b80f15fc6d646b14c6dbfa05bd7eea` and verifies its exact bytes. A
normal clone contains the commits. For a shallow clone, fetch them from
`https://github.com/snowdamiz/mixer.git`.

```sh
git cat-file -e '57f3ed4f17b80f15fc6d646b14c6dbfa05bd7eea^{commit}'
git cat-file -e '201ead70ff68bfe18de24c0642f518701459e0a4^{commit}'
git cat-file -e 'fad0d0b3e65fd3be3b49675601693e5d91999fbe^{commit}'
```

Use Python 3.14, Elixir 1.20.4, and PostgreSQL 17. Run the zero-build control
first. It restores the ordinary hosted fixture into a new cluster and signs
in through the loopback identity provider under the restored authorization
catalog.

```sh
python3.14 -B tests/integration/hosted-expiry-restore/replay-starter.py --fixture-only
```

Run the offline readback tests to check the download and authorization assertions.

```sh
python3.14 -B tests/integration/hosted-expiry-restore/test_starter_readback.py
```

For the full replay, select Xcode on macOS and provide enough disk space for
the CLI build and generic iOS Simulator compilation. The launcher acquires
locked Mix and SwiftPM inputs in its private run directory. It compiles the
hosted test application before starting PostgreSQL and Phoenix. Pass `--pg-bin`
with the PostgreSQL 17 bin directory if you use a non-Homebrew installation.
The launcher verifies the four preimages in the pinned CLI source archive,
applies `starter-swift-lock.patch`, and checks the resulting inventory digest.
The patch makes the Swift banner comparison independent of stream order. The
pinned hosted source, worker, and SDK inputs retain their original revisions.

```sh
python3.14 -B tests/integration/hosted-expiry-restore/replay-starter.py
```

The replay submits one free Starter build after the pinned launcher's
pre-POST checks. It requires the terminal PostgreSQL journal, released
capacity and lease, and the single closed worker operation. It stops Oban
and the worker before capturing the PostgreSQL dump, password-free fixture
roles, SQLite backup, native manifest, log projection, and all three artifacts.

The source API and cluster exit before the replay starts the target cluster.
The replay restores the roles and unchanged dump, applies the two pinned
CHECK expressions, and compares the recovered journal and SQLite row. It
starts a separate API under `browser_ordinary` and uses fresh owner and
unrelated-tenant sessions. It checks the build and logs, compares all three
advertised downloads with the original sizes and digests, and checks the
outsider response bodies and both sessions' cache headers.
The target API reads the copied retained store with its build queues disabled.
The restore starts zero workers and zero compilers.

On successful closure, the launcher removes the private run directory and
prints a receipt under `verification/local/`. The receipt includes both
cluster identifiers, backup digests, HTTP digests, and port cleanup. Exit 74
requires preserving the exact printed run directory for custody review.
After a closed failure, a private diagnostics directory retains bounded API
output and the output of failed commands.

The earlier native build and authenticated restore used a separate fixture.
Its recorded digests describe that run. New build and backup digests come
from the current run. [Historical Starter restore receipt](../../verification/receipts/l05-l07-starter-restore-downloads-20261119.json)

The fresh-checkout receipt records the PostgreSQL and HTTP controls, the
single native build, and the limits of the final cross-cluster comparison.
[Fresh-checkout Starter restore receipt](../../verification/receipts/l07-fresh-starter-backup-restore-20261119.json)

The settled-build receipt records the matching canonical build and log content,
all three artifact digests, and unchanged restore state after authenticated
reads. [Settled Starter restore receipt](../../verification/receipts/l07-starter-settled-restore-20261120.json)
