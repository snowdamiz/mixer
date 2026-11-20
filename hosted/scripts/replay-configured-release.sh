#!/bin/sh
set -eu

mode=linux
case "$#:${1:-}:${2:-}" in
  0::) ;;
  1:--startup-only:) mode=startup-only ;;
  1:--stock-cli:) mode=stock-cli ;;
  2:--startup-only:--stock-cli) mode=stock-cli-startup ;;
  *) echo "Usage: $0 [--startup-only] [--stock-cli]" >&2; exit 2 ;;
esac

if [ "$mode" = linux ] || [ "$mode" = stock-cli ]; then
  if [ "$(uname -s)" != Linux ]; then
    echo "Configured identity replay requires a fresh Linux network namespace." >&2
    exit 2
  fi
  current=$(readlink /proc/self/ns/net)
  if [ -z "${MIXER_RELEASE_PARENT_NETNS:-}" ] || [ "$current" = "$MIXER_RELEASE_PARENT_NETNS" ]; then
    echo "Enter a fresh network namespace before running this script." >&2
    exit 2
  fi
fi

if [ "$mode" = stock-cli ]; then
  current_pid=$(readlink /proc/self/ns/pid)
  if [ -z "${MIXER_RELEASE_PARENT_PIDNS:-}" ] || [ "$current_pid" = "$MIXER_RELEASE_PARENT_PIDNS" ]; then
    echo "Enter a fresh PID namespace before running the stock CLI fixture." >&2
    exit 2
  fi
fi

if [ "$(id -u)" -eq 0 ]; then
  echo "Run the fixture as an unprivileged user." >&2
  exit 2
fi

cd "$(dirname "$0")/.."
umask 077
scratch=$(mktemp -d /tmp/mixer-configured-release.XXXXXX)
pgdata="$scratch/db"
cleanup() {
  if [ -f "$pgdata/postmaster.pid" ] &&
     ! pg_ctl -D "$pgdata" -w -t 15 -m fast stop; then
    echo "PostgreSQL cleanup unconfirmed. Preserved $scratch." >&2
    return 1
  fi
  if ! rm -rf -- "$scratch" || [ -e "$scratch" ]; then
    echo "Could not remove $scratch." >&2
    return 1
  fi
  echo "Removed owned PostgreSQL and fixture scratch."
}
finish() {
  result=$1
  trap - EXIT
  cleanup || result=1
  exit "$result"
}
trap 'finish "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

initdb -D "$pgdata" -U mixer_replay_admin --auth=trust --no-locale >/dev/null
{
  openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=Mixer release replay database CA' \
    -keyout "$scratch/ca.key" -out "$scratch/ca.pem"
  openssl req -new -newkey rsa:2048 -nodes -subj /CN=127.0.0.1 \
    -keyout "$scratch/db.key" -out "$scratch/db.csr"
  printf '%s\n' 'subjectAltName=DNS:127.0.0.1,IP:127.0.0.1' \
    'extendedKeyUsage=serverAuth' 'basicConstraints=critical,CA:FALSE' >"$scratch/db.ext"
  openssl x509 -req -days 1 -in "$scratch/db.csr" -out "$scratch/db.pem" \
    -CA "$scratch/ca.pem" -CAkey "$scratch/ca.key" -CAcreateserial -extfile "$scratch/db.ext"
} >"$scratch/openssl.log" 2>&1
cat >> "$pgdata/postgresql.conf" <<CONFIG
listen_addresses = '127.0.0.1'
port = 5432
unix_socket_directories = '$scratch'
ssl = on
ssl_cert_file = '$scratch/db.pem'
ssl_key_file = '$scratch/db.key'
CONFIG
tls_roles=mixer_replay_writer,mixer_release_delivery
case "$mode" in
  stock-cli*) tls_roles="$tls_roles,mixer_artifact_uploader" ;;
esac
cat > "$pgdata/pg_hba.conf" <<CONFIG
local all mixer_replay_admin trust
local all mixer_replay_stage trust
hostssl postgres $tls_roles 127.0.0.1/32 scram-sha-256
CONFIG
if ! pg_ctl -D "$pgdata" -l "$scratch/postgres.log" -w -t 15 start; then
  cat "$scratch/postgres.log" >&2
  exit 1
fi

env -i PATH="$PATH" HOME="$HOME" TMPDIR="$scratch" MIX_ENV=test HEX_OFFLINE=1 \
  MIXER_RELEASE_FIXTURE_MODE="$mode" MIXER_RELEASE_FIXTURE_SCRATCH="$scratch" \
  MIXER_RELEASE_PARENT_NETNS="${MIXER_RELEASE_PARENT_NETNS:-}" \
  MIXER_RELEASE_PARENT_PIDNS="${MIXER_RELEASE_PARENT_PIDNS:-}" \
  mix test --warnings-as-errors --trace test/mixer_hosted/releases/configured_release_replay_test.exs
