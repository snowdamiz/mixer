#!/bin/sh
set -eu

[ "$(id -u)" -ne 0 ] || { echo 'Use an unprivileged fixture user.' >&2; exit 2; }
cd "$(dirname "$0")/.."
order=${1:-queue-first}
mode=target-registry
case "$order" in
  queue-first|registry-first) ;;
  export) mode=delivery-export ;;
  publish-fence) mode=delivery-publish-fence ;;
  cross-runtime) mode=delivery-cross-runtime ;;
  *) echo 'Expected queue-first, registry-first, export, publish-fence, or cross-runtime.' >&2; exit 2 ;;
esac
umask 077
scratch=$(mktemp -d /tmp/mxd-run.XXXXXX)
scratch=$(cd "$scratch" && pwd -P)
pgdata="$scratch/db"
finish() {
  result=$?
  trap - EXIT
  if [ "$result" -eq 74 ]; then
    echo "Replay custody unresolved. Preserved $scratch." >&2
    exit 74
  fi
  if [ -f "$pgdata/postmaster.pid" ] &&
     ! pg_ctl -D "$pgdata" -w -t 15 -m fast stop; then
    echo "PostgreSQL shutdown unconfirmed. Preserved $scratch." >&2
    exit 1
  fi
  rm -rf -- "$scratch"
  [ ! -e "$scratch" ]
  echo 'Removed owned PostgreSQL and fixture scratch.'
  exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [ "$mode" = delivery-cross-runtime ]; then
  [ "$(postgres --version | awk '{print $3}')" = "17.11" ] ||
    { echo 'The cross-runtime replay requires PostgreSQL 17.11.' >&2; exit 2; }
  [ "$(node --version)" = "v22.23.3" ] ||
    { echo 'The cross-runtime replay requires the locked Node 22.23.3 toolchain.' >&2; exit 2; }
  root=$(cd .. && pwd -P)
  toolchain=$(cd "${MIXER_DELIVERY_TOOLCHAIN:-$root/hosted-worker-controller}" && pwd -P)
  cmp "$root/hosted-worker-controller/package-lock.json" "$toolchain/package-lock.json"
  node "$toolchain/node_modules/typescript/bin/tsc" -p "$root/release-delivery-origin" \
    --typeRoots "$toolchain/node_modules/@cloudflare" --outDir "$scratch/dist"
  (
    cd "$root/services"
    env -i PATH="$PATH" HOME="$scratch" TMPDIR="$scratch" GOENV=off GOTOOLCHAIN=local \
      GOCACHE="$scratch/go-build" GOMODCACHE="$scratch/go-mod" \
      go build -mod=readonly -modcacherw -o "$scratch/db-probe" ./internal/deliveryreplay
  )
fi

initdb -D "$pgdata" -U mixer_replay_admin --auth=trust --no-locale >/dev/null
{
  openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=Mixer target registry fixture CA' \
    -keyout "$scratch/ca.key" -out "$scratch/ca.pem"
  openssl req -new -newkey rsa:2048 -nodes -subj '/CN=127.0.0.1' \
    -keyout "$scratch/db.key" -out "$scratch/db.csr"
  printf '%s\n' 'subjectAltName=DNS:127.0.0.1,IP:127.0.0.1' \
    'extendedKeyUsage=serverAuth' 'basicConstraints=critical,CA:FALSE' >"$scratch/db.ext"
  openssl x509 -req -days 1 -in "$scratch/db.csr" -out "$scratch/db.pem" \
    -CA "$scratch/ca.pem" -CAkey "$scratch/ca.key" -CAcreateserial -extfile "$scratch/db.ext"
} >"$scratch/openssl.log" 2>&1

cat >>"$pgdata/postgresql.conf" <<CONFIG
listen_addresses = '127.0.0.1'
port = 5432
unix_socket_directories = '$scratch'
ssl = on
ssl_cert_file = '$scratch/db.pem'
ssl_key_file = '$scratch/db.key'
CONFIG
cat >"$pgdata/pg_hba.conf" <<CONFIG
local all mixer_replay_admin,mixer_replay_writer,mixer_replay_android_writer,mixer_replay_stage trust
hostssl postgres mixer_replay_writer,mixer_replay_android_writer,mixer_release_delivery,mixer_release_processor 127.0.0.1/32 scram-sha-256
CONFIG
if [ "$mode" = delivery-cross-runtime ]; then
  trap 'exit 74' INT TERM
  env -i PATH="$PATH" HOME="$HOME" TMPDIR="$scratch" LC_ALL=C MIX_ENV=test HEX_OFFLINE=1 \
    MIX_DEPS_PATH="${MIX_DEPS_PATH:-$PWD/deps}" MIX_BUILD_PATH="${MIX_BUILD_PATH:-$PWD/_build/test}" \
    MIXER_RELEASE_FIXTURE_MODE="$mode" MIXER_RELEASE_FIXTURE_SCRATCH="$scratch" \
    node "$root/release-delivery-origin/test/cross-runtime.mjs" "$scratch" "$toolchain"
  exit
fi

if ! pg_ctl -D "$pgdata" -l "$scratch/postgres.log" -w -t 15 start; then
  cat "$scratch/postgres.log" >&2
  exit 1
fi

env -i PATH="$PATH" HOME="$HOME" TMPDIR="$scratch" MIX_ENV=test HEX_OFFLINE=1 \
  MIXER_RELEASE_FIXTURE_MODE="$mode" MIXER_RELEASE_FIXTURE_SCRATCH="$scratch" \
  MIXER_RELEASE_QUEUE_ORDER="$order" \
  mix test --warnings-as-errors --trace test/mixer_hosted/releases/configured_release_replay_test.exs
