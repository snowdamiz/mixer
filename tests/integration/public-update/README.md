# Replay a public update against local PostgreSQL

Use macOS with Swift 6.2 or later, Go 1.26 or later, Python 3.10 or later,
and PostgreSQL 14 or later. Put `initdb`, `postgres`, and `psql` on your
`PATH` and run as a non-root user. Builds may fetch the locked public
dependencies. The replay uses generated development signing keys and local
bearers. It needs no account, card, payment service, or external credential.

Run from the repository root.

```sh
umask 077
mkdir -p verification/local
run=$(mktemp -d "$PWD/verification/local/public-update-postgres.XXXXXXXX")
mkdir -p "$run/tmp"
export TMPDIR="$run/tmp"
export GOCACHE="$run/go-cache" GOMODCACHE="$run/go-modules" GOWORK=off
export CLANG_MODULE_CACHE_PATH="$run/clang-module-cache"
export SWIFTPM_MODULECACHE_OVERRIDE="$run/swift-module-cache"

swift build --package-path cli --product mixer \
  --scratch-path "$run/swift-build" --cache-path "$run/swift-cache" \
  --config-path "$run/swift-config" --security-path "$run/swift-security" \
  --manifest-cache local --disable-dependency-cache --force-resolved-versions

go -C services build -mod=readonly -o "$run/mixer-service" ./cmd/mixer-service
python3 -I -B - "$run/signer-overlay.json" <<'PY'
import json
from pathlib import Path
import sys

root = Path.cwd()
virtual = root / "services/internal/publicupdatefixture/fixture_test.go"
source = root / "tests/integration/public-update/fixture_test.go"
Path(sys.argv[1]).write_text(json.dumps({"Replace": {str(virtual): str(source)}}))
PY
go -C services test -vet=off -mod=readonly -overlay "$run/signer-overlay.json" \
  -c -o "$run/fixture-signer" ./internal/publicupdatefixture

python3 -I -B -S tests/integration/public-update/replay.py --postgres \
  "$run/swift-build/debug/mixer" "$run/mixer-service" "$run/fixture-signer" \
  "$run/replay.json"
```

The overlay lets Go compile the fixture signer under the service's internal
package prefix without writing to the checkout. Disable vet for this
compile-only command because vet requires the virtual package directory on disk.

Use `storage_backend: postgres` in `replay.json` to identify the PostgreSQL
result. Omit `--postgres` to exercise the default local file store. Use a fresh
output path on each run.

The PostgreSQL run uses one private Unix-socket cluster. The origin uses a
restricted runtime login, while the fixture applies the real migration and
reads committed rows over a separate connection. The signer exits before any
CLI operation. The CLI takes an explicit channel and percentage for publish.
Promote takes a percentage. Promote and rollback derive an omitted channel
from the signed assignment. Rollback requires a reason.

On success the runner reaps both origin instances and PostgreSQL and removes
their fixture and socket directory. Build outputs and the receipt remain in
`$run`. If a run fails, the driver prints the retained fixture location.
`HOLD.json` identifies any process groups whose exit could not be verified.

The fixture uses one synthetic iOS runtime and two test payloads. It restarts
the Go origin while PostgreSQL stays up. The release outbox stays
`pending_local_only`. Console, Phoenix, Oban dispatch, build artifact handoff,
and installed app activation still need a joined local L05 run.
