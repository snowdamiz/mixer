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
