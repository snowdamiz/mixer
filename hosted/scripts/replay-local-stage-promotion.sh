#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
umask 077
scratch=$(mktemp -d "${TMPDIR:-/tmp}/mixer-stage.XXXXXX")
pgdata="$scratch/db"

finish() {
  status=$?
  trap - EXIT
  if [ -f "$pgdata/postmaster.pid" ] &&
     ! pg_ctl -D "$pgdata" -w -t 15 -m fast stop; then
    echo "PostgreSQL shutdown unconfirmed. Preserved $scratch." >&2
    exit 1
  fi
  if [ "$status" -ne 0 ] && [ -f "$scratch/postgres.log" ]; then
    tail -n 24 "$scratch/postgres.log" >&2
  fi
  rm -rf -- "$scratch"
  [ ! -e "$scratch" ]
  echo 'Removed the owned PostgreSQL cluster and socket.'
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

initdb -D "$pgdata" -U stage_fixture_admin --auth-local=trust --auth-host=reject \
  --encoding=UTF8 --no-locale >/dev/null
pg_ctl -D "$pgdata" -l "$scratch/postgres.log" -w -t 15 \
  -o "-c listen_addresses='' -c unix_socket_directories='$scratch' -c log_error_verbosity=terse" start

env MIX_ENV=test MIXER_STAGE_PROMOTION_SOCKET="$scratch" mix test --warnings-as-errors --trace \
  test/mixer_hosted/releases/environment_promotion
