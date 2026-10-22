#!/bin/sh
set -eu
MIXER_REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$MIXER_REPO"
python3 scripts/check-policy.py
swift test --package-path cli
swift test --package-path sdk
swift test --package-path updates
cargo test --manifest-path vm/Cargo.toml
cargo build --release --manifest-path vm/Cargo.toml
cd services
go test -race ./...
cd "$MIXER_REPO"
python3 tests/integration/release-workflow.py
