# Restored stage promotion commands

These commands record the successful run at `2acaac67605c369ff1667e3ccc3eb56d376e536e`. The test-only patch restores the exact two executed fixtures. The receipt records the fixture hashes, PostgreSQL readback, and process and listener closure. [Unified patch](l05-l07-restored-stage-promotion-2acaac67-overlay.patch) · [Original receipt](l05-l07-restored-stage-promotion-2acaac67.json)

## Prepare the pinned source

Here, `PROJECTION` is the extracted `project/` directory, `PATCH` is the absolute path to the companion patch, and `RUN` and `BUILD` are owned directories. The successful run used PostgreSQL 17.11, Elixir 1.20.4, and offline Hex packages.

~~~sh
git archive --format=tar --prefix=project/ 2acaac67605c369ff1667e3ccc3eb56d376e536e \
	hosted services/protocol/testdata docs/operations \
	scripts/restore-local-authz-expiry.sql \
	tests/integration/phoenix-release-restore/restore-artifact-key.sql > "$RUN/pinned.tar"
tar -xf "$RUN/pinned.tar" -C "$(dirname "$PROJECTION")"

cd "$PROJECTION"
git apply --check --whitespace=error "$PATCH"
git apply --whitespace=error "$PATCH"
shasum -a 256 hosted/test/mixer_hosted/releases/browser_publication_test.exs \
	hosted/test/support/ordinary_browser_startup_fixture.ex

cd "$PROJECTION/hosted"
export MIX_ENV=test HEX_OFFLINE=1 ERL_FLAGS='+S 4:4' MIX_BUILD_PATH="$BUILD"
mix deps.get --check-locked
mix compile --warnings-as-errors
~~~

## Prepare the source database and run the selected test

Each cluster used its own directory and loopback port. Here, `PGDATA` and `PORT` identify the owned cluster for each invocation. The original driver owned the foreground PostgreSQL process in a separate process group and verified its exit, group absence, and port rebind.

~~~sh
initdb -D "$PGDATA" -U mixer_fixture -A trust --no-locale -E UTF8
postgres -D "$PGDATA" -h 127.0.0.1 -p "$PORT" -k '' \
	-c timezone=UTC -c statement_timeout=20000
~~~

The source cluster was initialized with the maintained browser fixture roles before the source test. The fixture created the release database.

~~~sh
psql -X -qAt -h 127.0.0.1 -p "$SOURCE_PORT" -U mixer_fixture -w \
	-v ON_ERROR_STOP=1 -d postgres <<'SQL'
CREATE ROLE browser_admin LOGIN SUPERUSER;
CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;
CREATE DATABASE browser_storage OWNER browser_schema_owner;
SQL
~~~

Both test phases used this invocation from `$PROJECTION/hosted`. For the first invocation, `PHASE=source` and `PORT=$SOURCE_PORT`. For the second, `PHASE=target` and `PORT=$TARGET_PORT`. Each phase had a fresh catalog directory. The two phases shared the same synthetic signing bundle in `RUN`.

~~~sh
mkdir "$RUN/$PHASE-catalog"
MIXER_BROWSER_STORAGE_PORT="$PORT" \
MIXER_BROWSER_CATALOG_FIXTURE_ROOT="$RUN/$PHASE-catalog" \
MIXER_RESTORED_WRITE_PHASE="$PHASE" \
MIXER_RESTORED_WRITE_BUNDLE="$RUN/synthetic-key-bundle" \
MIXER_RESTORED_WRITE_RESULT="$RUN/$PHASE-evidence.json" \
MIXER_RESTORED_WRITE_PORTS="$RUN/$PHASE-ports" \
mix test --warnings-as-errors --trace --no-color --seed 0 --timeout 90000 \
	test/mixer_hosted/releases/browser_publication_test.exs:488
~~~

## Restore before the target test

After the source test exited, the driver set the cluster read-only and verified that the release database had no remaining application connections. It then ran these dumps and stopped the source cluster before starting the fresh target cluster.

~~~sh
DB=browser_ordinary_installation_r1422
pg_dump -h 127.0.0.1 -p "$SOURCE_PORT" -U mixer_fixture -w \
	-Fc -f "$RUN/release.dump" "$DB"
pg_dumpall -h 127.0.0.1 -p "$SOURCE_PORT" -U mixer_fixture -w \
	--roles-only --no-role-passwords --no-comments -f "$RUN/roles.sql"
~~~

The driver checked that the target lacked the release database. It built `target-roles.sql` by dropping the single `CREATE ROLE mixer_fixture;` line because `initdb` had already created that role on the target.

~~~sh
psql -X -qAt -h 127.0.0.1 -p "$TARGET_PORT" -U mixer_fixture -w \
	-v ON_ERROR_STOP=1 -d postgres -f "$RUN/target-roles.sql"
pg_restore -h 127.0.0.1 -p "$TARGET_PORT" -U mixer_fixture -w \
	--exit-on-error --create -d postgres "$RUN/release.dump"
psql -X -qAt -h 127.0.0.1 -p "$TARGET_PORT" -U mixer_fixture -w \
	-v ON_ERROR_STOP=1 -d "$DB" -f "$PROJECTION/scripts/restore-local-authz-expiry.sql"
psql -X -qAt -h 127.0.0.1 -p "$TARGET_PORT" -U mixer_fixture -w \
	-v ON_ERROR_STOP=1 -d "$DB" \
	-f "$PROJECTION/tests/integration/phoenix-release-restore/restore-artifact-key.sql"
~~~

The driver compared the repaired CHECK definitions and the restored ledger snapshot against the source before starting the target test. After the target test exited, a separate SQL connection confirmed the committed pair and its queue entries. The original run produced `Result: 1 passed, 7 excluded` in each phase.
