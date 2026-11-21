#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
umask 077

case "$(postgres --version)" in
  'postgres (PostgreSQL) 16.'*|'postgres (PostgreSQL) 17.'*) ;;
  *)
    echo 'Place PostgreSQL 16 or 17 tools on PATH for the browser catalog fixture.' >&2
    exit 2
    ;;
esac

port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')
scratch=$(mktemp -d "${TMPDIR:-/tmp}/mixer-browser-promotion.XXXXXX")
pgdata="$scratch/db"

finish() {
  status=$?
  trap - EXIT
  if [ -f "$pgdata/postmaster.pid" ] &&
     ! pg_ctl -D "$pgdata" -m fast -w -t 15 stop; then
    echo "PostgreSQL shutdown unconfirmed. Preserved $scratch." >&2
    exit 1
  fi
  if [ "$status" -ne 0 ] && [ -f "$scratch/postgres.log" ]; then
    tail -n 24 "$scratch/postgres.log" >&2
  fi
  rm -rf -- "$scratch"
  [ ! -e "$scratch" ]
  python3 - "$port" <<'PY'
import socket
import sys

with socket.socket() as listener:
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", int(sys.argv[1])))
PY
  echo 'Removed the owned PostgreSQL cluster and fixture scratch. Loopback port reusable.'
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

initdb -D "$pgdata" -U mixer_fixture --auth=trust --no-locale -E UTF8 >/dev/null
pg_ctl -D "$pgdata" -l "$scratch/postgres.log" -w -t 15 \
  -o "-h 127.0.0.1 -p $port -k '' -c timezone=UTC" start
psql -X -h 127.0.0.1 -p "$port" -U mixer_fixture -d postgres -v ON_ERROR_STOP=1 >/dev/null <<'SQL'
CREATE ROLE browser_admin LOGIN SUPERUSER;
CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
CREATE ROLE mixer_customer_build_catalog_definer_v1 NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;
CREATE DATABASE browser_storage OWNER browser_schema_owner;
SQL

mkdir "$scratch/catalog"
env MIX_ENV=test MIXER_BROWSER_STORAGE_PORT="$port" MIXER_BROWSER_CATALOG_FIXTURE_ROOT="$scratch/catalog" \
  mix test --warnings-as-errors --seed 0 --timeout 120000 \
  test/mixer_hosted/releases/browser_publication_test.exs
