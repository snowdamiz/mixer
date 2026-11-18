#!/bin/sh
set -eu
MIXER_REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$MIXER_REPO"
python3 scripts/check-verification-artifacts.py
python3 scripts/check-policy.py
swift build --package-path cli --product mixer -j 2
MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"
test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"
MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" swift test --package-path cli
swift test --package-path sdk
swift test --package-path updates
(
    MIXER_UPDATE_BIN_DIR="$(swift build --package-path updates --show-bin-path)"
    test -x "$MIXER_UPDATE_BIN_DIR/mixer-update"
    MIXER_UPDATE_SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/mixer-update-vectors.XXXXXXXX")"
    trap 'rm -rf -- "$MIXER_UPDATE_SCRATCH"' EXIT
    python3 updates/verification/verify-cli.py "$MIXER_UPDATE_BIN_DIR/mixer-update" "$MIXER_UPDATE_SCRATCH"
)
cargo test --manifest-path vm/Cargo.toml
cargo build --release --manifest-path vm/Cargo.toml
cd services
go test -race ./...
cd "$MIXER_REPO"
python3 tests/integration/release-workflow.py
