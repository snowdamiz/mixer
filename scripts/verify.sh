#!/bin/sh
set -eu
MIXER_REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$MIXER_REPO"
python3 scripts/check-policy.py
swift test --package-path cli
swift test --package-path sdk
cargo test --manifest-path vm/Cargo.toml
cd services
go test -race ./...
