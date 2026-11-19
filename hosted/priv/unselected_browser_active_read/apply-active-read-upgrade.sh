#!/bin/sh
set -eu

case "${L06_DB_URL-}" in
  *[![:space:]]*) ;;
  *)
    printf '%s\n' 'Set L06_DB_URL to the private database connection URL' >&2
    exit 1
    ;;
esac

sql=$(mktemp "${TMPDIR:-/tmp}/mixer-active-read.XXXXXXXX")
trap 'rm -f "$sql"' 0
trap 'exit 1' HUP INT TERM

elixir -r lib/mixer_hosted/browser_auth/active_read_schema.ex \
  priv/unselected_browser_active_read/print_upgrade_sql.exs "$@" > "$sql"

if ! test -s "$sql"; then
  printf '%s\n' 'Active-load SQL emitter returned an empty file' >&2
  exit 1
fi

psql -X -v ON_ERROR_STOP=1 --dbname="$L06_DB_URL" -f "$sql"
